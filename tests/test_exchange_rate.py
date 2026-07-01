from __future__ import annotations

from datetime import date

from crossborder_daily.exchange_rate import (
    parse_latest_pbc_rate_article_url,
    parse_pbc_usd_cny_rate,
)


def test_parse_latest_pbc_rate_article_url() -> None:
    html = """
    <html><body>
      <a href="/zhengcehuobisi/125207/125217/125925/2026070109002618850/index.html">
        2026年7月1日中国外汇交易中心受权公布人民币汇率中间价公告
      </a>
      <a href="/other/index.html">其他公告</a>
    </body></html>
    """

    url = parse_latest_pbc_rate_article_url(
        html,
        "https://www.pbc.gov.cn/zhengcehuobisi/125207/125217/125925/index.html",
    )

    assert (
        url
        == "https://www.pbc.gov.cn/zhengcehuobisi/125207/125217/125925/2026070109002618850/index.html"
    )


def test_parse_pbc_usd_cny_rate_from_article_meta() -> None:
    description = (
        "中国人民银行授权中国外汇交易中心公布。"
        "2026年7月1日银行间外汇市场人民币汇率中间价为1美元对人民币6.8067元。"
    )
    html = f"""
    <html><head>
      <meta name="ArticleTitle" content="2026年7月1日中国外汇交易中心受权公布人民币汇率中间价公告">
      <meta name="PubDate" content="2026-07-01">
      <meta name="Description" content="{description}">
    </head><body></body></html>
    """

    quote = parse_pbc_usd_cny_rate(
        html,
        "https://www.pbc.gov.cn/zhengcehuobisi/125207/125217/125925/2026070109002618850/index.html",
    )

    assert quote.usd_cny == "6.8067"
    assert quote.source_name == "中国人民银行"
    assert quote.published_date == date(2026, 7, 1)
