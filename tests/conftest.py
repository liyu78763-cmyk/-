from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from crossborder_daily.models import Category, NewsItem, SourceGrade
from crossborder_daily.source_config import SourceRules


def sample_rules() -> SourceRules:
    return SourceRules(
        feeds=[],
        gdelt_queries=[],
        amz123_briefs=[],
        source_grades={
            "amazon.com": SourceGrade.A,
            "sell.amazon.com": SourceGrade.A,
            "cpsc.gov": SourceGrade.A,
            "reuters.com": SourceGrade.B,
        },
        blocked_domain_keywords=["training", "course", "repost"],
    )


def bjt(year: int = 2026, month: int = 6, day: int = 26, hour: int = 8) -> datetime:
    return datetime(year, month, day, hour, 30, tzinfo=ZoneInfo("Asia/Shanghai"))


def news_item(
    title: str = "Amazon updates FBA fee guidance",
    url: str = "https://sell.amazon.com/blog/fba-fee-guidance",
    source_name: str = "Amazon",
    published_at: datetime | None = None,
    category: Category = Category.AMAZON_PLATFORM,
    grade: SourceGrade = SourceGrade.A,
) -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source_name=source_name,
        published_at=published_at or bjt(),
        summary=title,
        category=category,
        source_grade=grade,
    )
