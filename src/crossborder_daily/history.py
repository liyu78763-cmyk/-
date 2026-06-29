from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from crossborder_daily.dedupe import canonical_url
from crossborder_daily.models import ScoredNews
from crossborder_daily.time_utils import format_bjt, now_beijing, to_beijing


@dataclass(slots=True)
class HistoryStore:
    path: Path
    connection: sqlite3.Connection = field(init=False)

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_url TEXT NOT NULL,
                event_fingerprint TEXT NOT NULL,
                title TEXT NOT NULL,
                source_name TEXT NOT NULL,
                published_at TEXT,
                sent_at TEXT NOT NULL
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_sent_url ON sent_items(canonical_url, sent_at)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_sent_fp ON sent_items(event_fingerprint, sent_at)"
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_runs (
                run_key TEXT PRIMARY KEY,
                sent_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def __enter__(self) -> HistoryStore:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def seen_recent(self, scored: ScoredNews, *, days: int = 7) -> bool:
        cutoff = to_beijing(now_beijing() - timedelta(days=days)).isoformat()
        url = canonical_url(scored.item.url)
        cursor = self.connection.execute(
            """
            SELECT 1
            FROM sent_items
            WHERE sent_at >= ?
              AND (canonical_url = ? OR event_fingerprint = ?)
            LIMIT 1
            """,
            (cutoff, url, scored.event_fingerprint),
        )
        return cursor.fetchone() is not None

    def record_sent(self, items: list[ScoredNews], *, sent_at: datetime | None = None) -> None:
        actual_sent_at = to_beijing(sent_at or now_beijing()).isoformat()
        rows = [
            (
                canonical_url(scored.item.url),
                scored.event_fingerprint,
                scored.item.title,
                scored.item.source_name,
                format_bjt(scored.item.published_at),
                actual_sent_at,
            )
            for scored in items
        ]
        self.connection.executemany(
            """
            INSERT INTO sent_items (
                canonical_url, event_fingerprint, title, source_name, published_at, sent_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self.connection.commit()

    def run_was_sent(self, run_key: str) -> bool:
        cursor = self.connection.execute(
            "SELECT 1 FROM sent_runs WHERE run_key = ? LIMIT 1",
            (run_key,),
        )
        return cursor.fetchone() is not None

    def record_run_sent(self, run_key: str, *, sent_at: datetime | None = None) -> None:
        actual_sent_at = to_beijing(sent_at or now_beijing()).isoformat()
        self.connection.execute(
            """
            INSERT OR IGNORE INTO sent_runs (run_key, sent_at)
            VALUES (?, ?)
            """,
            (run_key, actual_sent_at),
        )
        self.connection.commit()

    def cleanup(self, *, days: int = 30) -> int:
        cutoff = to_beijing(now_beijing() - timedelta(days=days)).isoformat()
        cursor = self.connection.execute("DELETE FROM sent_items WHERE sent_at < ?", (cutoff,))
        deleted_count = int(cursor.rowcount)
        cursor = self.connection.execute("DELETE FROM sent_runs WHERE sent_at < ?", (cutoff,))
        self.connection.commit()
        return deleted_count + int(cursor.rowcount)
