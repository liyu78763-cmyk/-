from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from crossborder_daily.http_client import HttpClient
from crossborder_daily.models import NewsItem
from crossborder_daily.source_config import GdeltQueryConfig, SourceRules
from crossborder_daily.time_utils import parse_datetime, to_beijing

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class GdeltNewsProvider:
    name = "gdelt"

    def __init__(
        self,
        queries: list[GdeltQueryConfig],
        rules: SourceRules,
        http_client: HttpClient,
        max_records_per_query: int = 25,
    ) -> None:
        self.queries = queries
        self.rules = rules
        self.http_client = http_client
        self.max_records_per_query = max_records_per_query

    def fetch(self, since: datetime, until: datetime) -> list[NewsItem]:
        hours = max(1, int((until - since).total_seconds() // 3600))
        items: list[NewsItem] = []
        for query in self.queries:
            payload = self.http_client.get_json(
                GDELT_DOC_URL,
                params={
                    "query": query.query,
                    "mode": "ArtList",
                    "format": "json",
                    "maxrecords": self.max_records_per_query,
                    "sort": "datedesc",
                    "timespan": f"{hours}h",
                },
            )
            articles = cast(list[dict[str, Any]], payload.get("articles", []))
            for article in articles:
                item = self._article_to_item(query, article)
                if item is None:
                    continue
                if item.published_at is not None and since <= item.published_at <= until:
                    items.append(item)
        return items

    def _article_to_item(
        self,
        query: GdeltQueryConfig,
        article: dict[str, Any],
    ) -> NewsItem | None:
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        if not title or not url:
            return None
        published_at = _parse_gdelt_datetime(article.get("seendate"))
        source_name = str(
            article.get("sourceCommonName") or article.get("domain") or query.name
        ).strip()
        return NewsItem(
            title=title,
            url=url,
            source_name=source_name,
            published_at=published_at,
            summary=title,
            category=query.category,
            source_grade=self.rules.grade_for_url(url),
            metadata={"provider_query": query.name},
        )


def _parse_gdelt_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) == 14 and text.isdigit():
        parsed = datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        return to_beijing(parsed)
    return parse_datetime(text)
