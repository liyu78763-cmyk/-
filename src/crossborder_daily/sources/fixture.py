from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from crossborder_daily.models import Category, NewsItem, SourceGrade
from crossborder_daily.time_utils import parse_relative_datetime


class FixtureNewsProvider:
    name = "fixture"

    def __init__(self, fixture_path: Path) -> None:
        self.fixture_path = fixture_path

    def fetch(self, since: datetime, until: datetime) -> list[NewsItem]:
        raw = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        records = cast(list[dict[str, Any]], raw)
        items: list[NewsItem] = []
        for record in records:
            published_at = parse_relative_datetime(str(record.get("published_at", "")), until)
            effective_at = None
            if record.get("effective_at"):
                effective_at = parse_relative_datetime(str(record["effective_at"]), until)
            item = NewsItem(
                title=str(record.get("title", "")),
                url=str(record.get("url", "")),
                source_name=str(record.get("source_name", "")),
                published_at=published_at,
                summary=str(record.get("summary", "")),
                content=str(record.get("content", "")),
                category=Category.from_value(str(record.get("category", ""))),
                source_grade=SourceGrade.from_value(str(record.get("source_grade", "C"))),
                effective_at=effective_at,
                metadata={
                    str(key): str(value)
                    for key, value in cast(dict[str, Any], record.get("metadata", {})).items()
                },
            )
            if item.published_at is not None and since <= item.published_at <= until:
                items.append(item)
        return items
