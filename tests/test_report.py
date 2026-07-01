from __future__ import annotations

from datetime import date

from crossborder_daily.exchange_rate import ExchangeRateQuote
from crossborder_daily.report import ReportMetadata, format_daily_report
from crossborder_daily.scorer import score_item
from tests.conftest import bjt, news_item


def test_report_places_exchange_rate_before_first_news() -> None:
    now = bjt(year=2026, month=7, day=1, hour=10)
    source_url = (
        "https://www.pbc.gov.cn/zhengcehuobisi/125207/125217/125925/2026070109002618850/index.html"
    )
    quote = ExchangeRateQuote(
        usd_cny="6.8067",
        source_name="中国人民银行",
        source_url=source_url,
        published_date=date(2026, 7, 1),
    )
    item = score_item(news_item(title="Amazon US seller update", published_at=now), now=now)
    metadata = ReportMetadata(
        generated_at=now,
        window_hours=24,
        expanded_to_48h=False,
        used_history=True,
        rejected_count=0,
        provider_errors=[],
    )

    report = format_daily_report([item], metadata, exchange_rate=quote)

    assert "今日汇率：  \n1美元=6.8067人民币  \n来源：中国人民银行" in report
    assert report.index("今日汇率：") < report.index("1.Amazon US seller update")
    assert "1.Amazon US seller update  \n来源：Amazon" in report
