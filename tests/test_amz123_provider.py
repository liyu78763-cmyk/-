from __future__ import annotations

from pathlib import Path

from crossborder_daily.sources.amz123 import parse_amz123_headlines


def test_parse_amz123_headlines_keeps_relevant_article_links() -> None:
    html = Path("tests/fixtures/amz123_brief.html").read_text(encoding="utf-8")

    headlines = parse_amz123_headlines(html, "https://www.amz123.com/zb/20260626")

    assert [headline.title for headline in headlines] == [
        "2026年美国Prime Day首日销售额达83亿美元",
        "26年加拿大Prime Day总消费将达54亿加元，购物意愿提升",
        "亚马逊MFN备货时间新规6月29日生效，严禁虚报时效",
        "亚马逊自有品牌Amazon Basics进军巴西市场",
    ]
    assert all(headline.url.startswith("https://www.amz123.com/") for headline in headlines)
