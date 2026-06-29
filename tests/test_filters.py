from __future__ import annotations

from datetime import timedelta

from crossborder_daily.filters import filter_news_items
from crossborder_daily.models import Category, SourceGrade
from tests.conftest import bjt, news_item, sample_rules


def test_filters_unsafe_url_and_missing_source() -> None:
    now = bjt()
    items = [
        news_item(url="javascript:alert(1)", published_at=now),
        news_item(source_name="", published_at=now),
        news_item(url="https://sell.amazon.com/news/valid", published_at=now),
    ]

    result = filter_news_items(
        items,
        since=now - timedelta(hours=24),
        until=now,
        rules=sample_rules(),
    )

    assert len(result.accepted) == 1
    assert sorted(rejected.reason for rejected in result.rejected) == [
        "missing source",
        "unsafe url",
    ]


def test_filters_high_risk_low_authority_source() -> None:
    now = bjt()
    item = news_item(
        title="Major tariff compliance update",
        url="https://example.com/trade/update",
        source_name="Unknown Blog",
        published_at=now,
        category=Category.POLICY_COMPLIANCE,
        grade=SourceGrade.C,
    )

    result = filter_news_items(
        [item],
        since=now - timedelta(hours=24),
        until=now,
        rules=sample_rules(),
    )

    assert not result.accepted
    assert result.rejected[0].reason == "high-risk news without authoritative source"


def test_filters_allow_amz123_cpsc_recall_items() -> None:
    now = bjt()
    item = news_item(
        title="存窒息风险，美国CPSC紧急召回超7万件牙胶玩具",
        url="https://www.amz123.com/t/Q6qtqqCP",
        source_name="AMZ123跨境早报",
        published_at=now,
        category=Category.POLICY_COMPLIANCE,
        grade=SourceGrade.C,
    )

    result = filter_news_items(
        [item],
        since=now - timedelta(hours=24),
        until=now,
        rules=sample_rules(),
    )

    assert result.accepted == [item]
    assert not result.rejected
