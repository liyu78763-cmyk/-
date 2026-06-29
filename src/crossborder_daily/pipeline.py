from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from crossborder_daily.ai_client import maybe_polish_report
from crossborder_daily.config import RuntimePaths
from crossborder_daily.dedupe import dedupe_items
from crossborder_daily.dingtalk import DingTalkClient, dingtalk_config_from_env
from crossborder_daily.filters import filter_news_items
from crossborder_daily.history import HistoryStore
from crossborder_daily.http_client import HttpClient
from crossborder_daily.models import RejectedNews, ScoredNews
from crossborder_daily.report import ReportMetadata, format_daily_report, report_title
from crossborder_daily.scorer import score_and_filter
from crossborder_daily.security import redact_text
from crossborder_daily.source_config import SourceRules, load_source_rules
from crossborder_daily.sources.registry import build_providers
from crossborder_daily.time_utils import now_beijing, window_start

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RunOptions:
    paths: RuntimePaths
    dry_run: bool
    hours: int = 24
    max_items: int = 10
    max_news_age_days: int = 7
    amz123_items: int = 5
    min_high_value_items: int = 0
    use_ai: bool = True
    fixture_path: Path | None = None
    run_key: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineResult:
    report: str
    report_path: Path
    sent: bool
    sent_chunks: int
    selected_count: int
    window_hours: int
    rejected_count: int
    provider_errors: list[str]


def run_pipeline(options: RunOptions) -> PipelineResult:
    http_client = HttpClient()
    rules = load_source_rules(options.paths.sources_path)
    generated_at = now_beijing()

    if not options.dry_run and options.run_key:
        with HistoryStore(options.paths.history_path) as history:
            if history.run_was_sent(options.run_key):
                report = _skip_report(generated_at, options.run_key)
                options.paths.output_path.parent.mkdir(parents=True, exist_ok=True)
                options.paths.output_path.write_text(report, encoding="utf-8")
                history.cleanup(days=30)
                return PipelineResult(
                    report=report,
                    report_path=options.paths.output_path,
                    sent=False,
                    sent_chunks=0,
                    selected_count=0,
                    window_hours=options.hours,
                    rejected_count=0,
                    provider_errors=[],
                )

    selected, rejected, provider_errors, window_hours = _collect_selecting_window(
        rules=rules,
        http_client=http_client,
        generated_at=generated_at,
        options=options,
    )
    selected = _select_report_items(selected, options=options)

    metadata = ReportMetadata(
        generated_at=generated_at,
        window_hours=window_hours,
        expanded_to_48h=window_hours == 48 and options.hours < 48,
        used_history=True,
        rejected_count=len(rejected),
        provider_errors=provider_errors,
    )
    draft = format_daily_report(selected, metadata)
    facts = _facts_payload(selected, metadata)
    report = maybe_polish_report(
        use_ai=options.use_ai,
        prompt_path=options.paths.prompt_path,
        draft=draft,
        facts=facts,
        http_client=http_client,
    )
    options.paths.output_path.parent.mkdir(parents=True, exist_ok=True)
    options.paths.output_path.write_text(report, encoding="utf-8")

    sent_chunks = 0
    if not options.dry_run:
        client = DingTalkClient(dingtalk_config_from_env(), http_client)
        sent_chunks = client.send_markdown(title=report_title(generated_at), text=report)
        with HistoryStore(options.paths.history_path) as history:
            history.record_sent(selected, sent_at=generated_at)
            if options.run_key:
                history.record_run_sent(options.run_key, sent_at=generated_at)
            history.cleanup(days=30)
    else:
        with HistoryStore(options.paths.history_path) as history:
            history.cleanup(days=30)

    return PipelineResult(
        report=report,
        report_path=options.paths.output_path,
        sent=not options.dry_run,
        sent_chunks=sent_chunks,
        selected_count=len(selected),
        window_hours=window_hours,
        rejected_count=len(rejected),
        provider_errors=provider_errors,
    )


def _skip_report(generated_at: datetime, run_key: str) -> str:
    return (
        f"{report_title(generated_at)}\n\n"
        f"本时段已经成功发送过快讯，本次自动跳过，避免重复推送。\n"
        f"运行标识：{run_key}\n"
    )


def _collect_selecting_window(
    *,
    rules: SourceRules,
    http_client: HttpClient,
    generated_at: datetime,
    options: RunOptions,
) -> tuple[list[ScoredNews], list[RejectedNews], list[str], int]:
    selected, rejected, provider_errors = _collect_and_score(
        rules=rules,
        http_client=http_client,
        generated_at=generated_at,
        options=options,
        hours=options.hours,
    )
    if len(selected) >= options.min_high_value_items or options.hours >= 48:
        return selected, rejected, provider_errors, options.hours

    LOGGER.info(
        "High-value news count is %d; expanding search window to 48 hours.",
        len(selected),
    )
    expanded_selected, expanded_rejected, expanded_errors = _collect_and_score(
        rules=rules,
        http_client=http_client,
        generated_at=generated_at,
        options=options,
        hours=48,
    )
    return (
        expanded_selected,
        expanded_rejected,
        [*provider_errors, *expanded_errors],
        48,
    )


def _collect_and_score(
    *,
    rules: SourceRules,
    http_client: HttpClient,
    generated_at: datetime,
    options: RunOptions,
    hours: int,
) -> tuple[list[ScoredNews], list[RejectedNews], list[str]]:
    until = generated_at
    requested_since = window_start(until, hours)
    max_age_since = window_start(until, options.max_news_age_days * 24)
    since = max(requested_since, max_age_since)
    providers = build_providers(rules, http_client, fixture_path=options.fixture_path)
    raw_items = []
    provider_errors: list[str] = []
    for provider in providers:
        try:
            raw_items.extend(provider.fetch(since, until))
        except Exception as exc:
            message = f"{provider.name}: {redact_text(str(exc))}"
            provider_errors.append(message)
            LOGGER.warning("News provider failed and was skipped: %s", message)

    filtered = filter_news_items(raw_items, since=since, until=until, rules=rules)
    deduped = dedupe_items(filtered.accepted)
    scored = score_and_filter(deduped, now=generated_at, minimum_score=40)
    with HistoryStore(options.paths.history_path) as history:
        fresh = [item for item in scored if not history.seen_recent(item, days=7)]
    return fresh, filtered.rejected, provider_errors


def _select_report_items(items: list[ScoredNews], *, options: RunOptions) -> list[ScoredNews]:
    amazon_items = [item for item in items if _source_bucket(item) == "amazon"]
    amz123_items = [item for item in items if _source_bucket(item) == "amz123"]
    cpsc_items = [item for item in items if _source_bucket(item) == "cpsc"]

    amz123_selected = amz123_items[: options.amz123_items]
    remaining_slots = options.max_items - len(amazon_items) - len(amz123_selected)
    if options.max_items <= 0:
        return [*amazon_items, *amz123_selected, *cpsc_items]
    if remaining_slots <= 0:
        return [*amazon_items, *amz123_selected]
    return [*amazon_items, *amz123_selected, *cpsc_items[:remaining_slots]]


def _source_bucket(scored: ScoredNews) -> str:
    text = f"{scored.item.source_name} {scored.item.url}".lower()
    if "amz123" in text:
        return "amz123"
    if "amazon" in text:
        return "amazon"
    if "cpsc" in text:
        return "cpsc"
    return "other"


def _facts_payload(items: list[ScoredNews], metadata: ReportMetadata) -> dict[str, Any]:
    return {
        "window_hours": metadata.window_hours,
        "generated_at": metadata.generated_at.isoformat(),
        "items": [
            {
                "title": scored.item.title,
                "url": scored.item.url,
                "source": scored.item.source_name,
                "published_at": scored.item.published_at.isoformat()
                if scored.item.published_at
                else None,
                "category": scored.item.category.value,
                "score": scored.score,
                "level": scored.level.value,
                "actions": scored.actions,
            }
            for scored in items
        ],
    }
