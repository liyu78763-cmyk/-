from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from crossborder_daily.config import RuntimePaths
from crossborder_daily.models import Category
from crossborder_daily.pipeline import RunOptions, _select_report_items
from crossborder_daily.scorer import score_and_filter
from tests.conftest import bjt, news_item


def test_recent_news_wins_when_scores_are_similar() -> None:
    now = bjt()
    older = news_item(
        title="Amazon FBA logistics update for US sellers older",
        url="https://sell.amazon.com/blog/fba-logistics-older",
        published_at=now - timedelta(hours=20),
        category=Category.LOGISTICS,
    )
    newer = news_item(
        title="Amazon FBA logistics update for US sellers newer",
        url="https://sell.amazon.com/blog/fba-logistics-newer",
        published_at=now - timedelta(hours=2),
        category=Category.LOGISTICS,
    )

    ranked = score_and_filter([older, newer], now=now, minimum_score=0)

    assert ranked[0].item.url == newer.url


def test_source_priority_orders_amazon_amz123_then_cpsc() -> None:
    now = bjt()
    amazon = news_item(
        title="Amazon official US marketplace update",
        url="https://www.aboutamazon.com/news/retail/update",
        source_name="Amazon",
        category=Category.AMAZON_PLATFORM,
    )
    amz123 = news_item(
        title="AMZ123 Amazon US marketplace update",
        url="https://www.amz123.com/t/example",
        source_name="AMZ123跨境早报",
        category=Category.AMAZON_PLATFORM,
    )
    cpsc = news_item(
        title="CPSC recall update",
        url="https://www.cpsc.gov/Recalls/2026/example",
        source_name="CPSC",
        category=Category.POLICY_COMPLIANCE,
    )

    ranked = score_and_filter([cpsc, amz123, amazon], now=now, minimum_score=0)

    assert [item.item.source_name for item in ranked] == ["Amazon", "AMZ123跨境早报", "CPSC"]


def test_amz123_items_keep_page_order() -> None:
    now = bjt()
    second = news_item(
        title="AMZ123 Amazon Canada second",
        url="https://www.amz123.com/t/second",
        source_name="AMZ123跨境早报",
        category=Category.AMAZON_PLATFORM,
    )
    second.metadata["source_order"] = "2"
    first = news_item(
        title="AMZ123 Amazon US first",
        url="https://www.amz123.com/t/first",
        source_name="AMZ123跨境早报",
        category=Category.AMAZON_PLATFORM,
    )
    first.metadata["source_order"] = "1"

    ranked = score_and_filter([second, first], now=now, minimum_score=0)

    assert [item.item.url for item in ranked] == [first.url, second.url]


def test_report_selection_keeps_amazon_then_five_amz123_then_cpsc(tmp_path: Path) -> None:
    now = bjt()
    amazon = score_and_filter(
        [
            news_item(
                title="Amazon official update",
                url="https://www.aboutamazon.com/news/update",
                source_name="Amazon",
                category=Category.AMAZON_PLATFORM,
            )
        ],
        now=now,
        minimum_score=0,
    )
    amz123_items = []
    for index in range(6):
        item = news_item(
            title=f"AMZ123 Amazon headline {index}",
            url=f"https://www.amz123.com/t/{index}",
            source_name="AMZ123跨境早报",
            category=Category.AMAZON_PLATFORM,
        )
        item.metadata["source_order"] = str(index + 1)
        amz123_items.append(item)
    cpsc = news_item(
        title="CPSC recall",
        url="https://www.cpsc.gov/Recalls/2026/example",
        source_name="CPSC",
        category=Category.POLICY_COMPLIANCE,
    )
    ranked = [
        *amazon,
        *score_and_filter(amz123_items, now=now, minimum_score=0),
        *score_and_filter([cpsc], now=now, minimum_score=0),
    ]
    options = RunOptions(
        paths=RuntimePaths(
            sources_path=tmp_path / "sources.yml",
            history_path=tmp_path / "history.sqlite",
            prompt_path=tmp_path / "prompt.md",
            output_path=tmp_path / "report.md",
        ),
        dry_run=True,
        max_items=10,
        amz123_items=5,
    )

    selected = _select_report_items(ranked, options=options)

    assert len(selected) == 7
    assert selected[0].item.source_name == "Amazon"
    assert [item.item.source_name for item in selected[1:6]] == ["AMZ123跨境早报"] * 5
    assert selected[6].item.source_name == "CPSC"
