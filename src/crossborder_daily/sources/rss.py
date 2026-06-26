from __future__ import annotations

import calendar
from datetime import UTC, datetime
from typing import Any, cast

import feedparser

from crossborder_daily.http_client import HttpClient
from crossborder_daily.models import NewsItem
from crossborder_daily.source_config import FeedConfig
from crossborder_daily.time_utils import parse_datetime, to_beijing


class RssFeedProvider:
    name = "rss"

    def __init__(self, feeds: list[FeedConfig], http_client: HttpClient) -> None:
        self.feeds = feeds
        self.http_client = http_client

    def fetch(self, since: datetime, until: datetime) -> list[NewsItem]:
        items: list[NewsItem] = []
        for feed in self.feeds:
            xml = self.http_client.get_text(feed.url)
            parsed = feedparser.parse(xml)
            entries = cast(list[Any], parsed.get("entries", []))
            for entry in entries:
                item = self._entry_to_item(feed, cast(dict[str, Any], entry))
                if item is None:
                    continue
                if item.published_at is not None and since <= item.published_at <= until:
                    items.append(item)
        return items

    @staticmethod
    def _entry_to_item(feed: FeedConfig, entry: dict[str, Any]) -> NewsItem | None:
        title = str(entry.get("title") or "").strip()
        url = str(entry.get("link") or "").strip()
        if not title or not url:
            return None
        published_at = _entry_datetime(entry)
        summary = str(entry.get("summary") or entry.get("description") or "").strip()
        return NewsItem(
            title=title,
            url=url,
            source_name=feed.name,
            published_at=published_at,
            summary=summary,
            category=feed.category,
            source_grade=feed.grade,
        )


def _entry_datetime(entry: dict[str, Any]) -> datetime | None:
    parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_time:
        timestamp = calendar.timegm(parsed_time)
        return to_beijing(datetime.fromtimestamp(timestamp, tz=UTC))
    text_value = entry.get("published") or entry.get("updated") or entry.get("created")
    if text_value:
        return parse_datetime(str(text_value))
    return None
