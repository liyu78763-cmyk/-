from __future__ import annotations

from crossborder_daily.dedupe import canonical_url, dedupe_items
from crossborder_daily.models import Category
from tests.conftest import news_item


def test_same_url_kept_once() -> None:
    first = news_item(url="https://sell.amazon.com/news/example?utm_source=x")
    second = news_item(url="https://sell.amazon.com/news/example")

    assert canonical_url(first.url) == canonical_url(second.url)
    assert len(dedupe_items([first, second])) == 1


def test_same_event_with_different_titles_is_merged() -> None:
    first = news_item(
        title="Amazon announces new FBA inbound placement fee update",
        url="https://sell.amazon.com/news/fba-inbound-placement",
        category=Category.LOGISTICS,
    )
    second = news_item(
        title="New Amazon FBA inbound placement fee guidance for sellers",
        url="https://reuters.com/business/retail/amazon-fba-inbound-placement",
        source_name="Reuters",
        category=Category.LOGISTICS,
    )

    assert len(dedupe_items([second, first])) == 1
