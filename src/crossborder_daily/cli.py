from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from crossborder_daily.config import (
    default_amz123_items,
    default_max_news_age_days,
    default_min_high_value_items,
    default_paths,
)
from crossborder_daily.pipeline import RunOptions, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    defaults = default_paths()
    parser = argparse.ArgumentParser(
        description=(
            "Generate and optionally send a cross-border e-commerce DingTalk daily briefing."
        )
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Generate report without sending DingTalk."
    )
    parser.add_argument(
        "--hours", type=int, default=24, choices=[24, 48], help="Initial search window."
    )
    parser.add_argument(
        "--max-items", type=int, default=10, help="Maximum news items in the report."
    )
    parser.add_argument(
        "--max-news-age-days",
        type=int,
        default=default_max_news_age_days(),
        help="Reject news older than this many days even when the search window is wider.",
    )
    parser.add_argument(
        "--amz123-items",
        type=int,
        default=default_amz123_items(),
        help="Number of AMZ123 Amazon-related items to keep when available.",
    )
    parser.add_argument(
        "--min-high-value-items",
        type=int,
        default=default_min_high_value_items(),
        help=(
            "Expand to 48 hours when selected items are below this count. "
            "Default 0 means strict 24-hour TOP ranking."
        ),
    )
    parser.add_argument("--sources", type=Path, default=defaults.sources_path)
    parser.add_argument("--history", type=Path, default=defaults.history_path)
    parser.add_argument("--prompt", type=Path, default=defaults.prompt_path)
    parser.add_argument("--output", type=Path, default=defaults.output_path)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help="Use local fixture JSON instead of live providers.",
    )
    parser.add_argument(
        "--run-key",
        default=None,
        help="Optional once-only key for scheduled cloud sends.",
    )
    parser.add_argument("--no-ai", action="store_true", help="Disable optional AI polishing.")
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "INFO"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    paths = default_paths()
    paths = paths.__class__(
        sources_path=args.sources,
        history_path=args.history,
        prompt_path=args.prompt,
        output_path=args.output,
    )
    options = RunOptions(
        paths=paths,
        dry_run=bool(args.dry_run),
        hours=int(args.hours),
        max_items=int(args.max_items),
        max_news_age_days=int(args.max_news_age_days),
        amz123_items=int(args.amz123_items),
        min_high_value_items=int(args.min_high_value_items),
        use_ai=not bool(args.no_ai),
        fixture_path=args.fixture,
        run_key=args.run_key,
    )
    try:
        result = run_pipeline(options)
    except Exception:
        logging.getLogger(__name__).exception("Run failed")
        return 1

    if args.dry_run:
        action = "generated only"
    elif result.sent:
        action = f"sent in {result.sent_chunks} chunk(s)"
    else:
        action = "skipped without sending"
    print(f"Report {action}: {result.report_path}")
    print(
        f"items={result.selected_count} | "
        f"window={result.window_hours}h | "
        f"rejected={result.rejected_count}"
    )
    if result.provider_errors:
        print(f"Skipped provider failures: {len(result.provider_errors)}")
    return 0
