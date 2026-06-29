from __future__ import annotations

from pathlib import Path

from crossborder_daily.history import HistoryStore
from crossborder_daily.scorer import score_item
from tests.conftest import bjt, news_item


def test_history_blocks_recently_sent_url(tmp_path: Path) -> None:
    scored = score_item(news_item(), now=bjt())

    with HistoryStore(tmp_path / "history.sqlite") as history:
        assert not history.seen_recent(scored, days=7)
        history.record_sent([scored], sent_at=bjt())
        assert history.seen_recent(scored, days=7)


def test_history_records_once_only_run_key(tmp_path: Path) -> None:
    with HistoryStore(tmp_path / "history.sqlite") as history:
        assert not history.run_was_sent("amazon-us-2026-06-29")
        history.record_run_sent("amazon-us-2026-06-29", sent_at=bjt())
        assert history.run_was_sent("amazon-us-2026-06-29")
