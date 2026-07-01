from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from crossborder_daily.config import RuntimePaths
from crossborder_daily.pipeline import RunOptions, run_pipeline


def test_dry_run_end_to_end_does_not_send_or_record_history(tmp_path: Path) -> None:
    paths = RuntimePaths(
        sources_path=Path("data/sources.yml"),
        history_path=tmp_path / "history.sqlite",
        prompt_path=Path("prompts/daily_report.md"),
        output_path=tmp_path / "latest_report.md",
    )
    result = run_pipeline(
        RunOptions(
            paths=paths,
            dry_run=True,
            fixture_path=Path("tests/fixtures/sample_news.json"),
            use_ai=False,
            include_exchange_rate=False,
            min_high_value_items=1,
        )
    )

    assert not result.sent
    assert result.sent_chunks == 0
    assert result.selected_count >= 1
    assert result.report_path.exists()
    assert "跨境快讯" in result.report
    assert "来源：" in result.report
    assert "查看原文" in result.report
    assert "事件：" not in result.report

    with sqlite3.connect(paths.history_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM sent_items").fetchone()[0]
    assert count == 0


def test_pipeline_rejects_news_older_than_max_age(tmp_path: Path) -> None:
    paths = RuntimePaths(
        sources_path=Path("data/sources.yml"),
        history_path=tmp_path / "history.sqlite",
        prompt_path=Path("prompts/daily_report.md"),
        output_path=tmp_path / "latest_report.md",
    )
    result = run_pipeline(
        RunOptions(
            paths=paths,
            dry_run=True,
            hours=48,
            max_news_age_days=1,
            fixture_path=Path("tests/fixtures/max_age_news.json"),
            use_ai=False,
            include_exchange_rate=False,
            min_high_value_items=0,
        )
    )

    assert "fresh FBA update" in result.report
    assert "old seller forum announcement" not in result.report


def test_pipeline_does_not_send_empty_report_after_history_dedupe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = RuntimePaths(
        sources_path=Path("data/sources.yml"),
        history_path=tmp_path / "history.sqlite",
        prompt_path=Path("prompts/daily_report.md"),
        output_path=tmp_path / "latest_report.md",
    )
    send_calls: list[str] = []

    def fake_send_markdown(self: object, *, title: str, text: str) -> int:
        send_calls.append(text)
        return 1

    monkeypatch.setenv("DINGTALK_WEBHOOK", "https://oapi.dingtalk.com/robot/send?access_token=test")
    monkeypatch.setenv("DINGTALK_SECRET", "SECtest")
    monkeypatch.setattr(
        "crossborder_daily.dingtalk.DingTalkClient.send_markdown",
        fake_send_markdown,
    )

    first = run_pipeline(
        RunOptions(
            paths=paths,
            dry_run=False,
            fixture_path=Path("tests/fixtures/sample_news.json"),
            use_ai=False,
            include_exchange_rate=False,
            min_high_value_items=1,
        )
    )

    second = run_pipeline(
        RunOptions(
            paths=paths,
            dry_run=False,
            fixture_path=Path("tests/fixtures/sample_news.json"),
            use_ai=False,
            include_exchange_rate=False,
            min_high_value_items=1,
        )
    )

    assert first.sent
    assert not second.sent
    assert second.sent_chunks == 0
    assert second.selected_count == 0
    assert len(send_calls) == 1
