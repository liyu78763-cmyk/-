from __future__ import annotations

import sqlite3
from pathlib import Path

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
            min_high_value_items=1,
        )
    )

    assert not result.sent
    assert result.sent_chunks == 0
    assert result.selected_count >= 1
    assert result.report_path.exists()
    assert "跨境早报" in result.report
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
            min_high_value_items=0,
        )
    )

    assert "fresh FBA update" in result.report
    assert "old seller forum announcement" not in result.report
