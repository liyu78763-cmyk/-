from __future__ import annotations

from datetime import timedelta

from crossborder_daily.models import Category, SourceGrade
from crossborder_daily.source_config import FeedConfig, SourceRules
from crossborder_daily.sources.registry import build_providers
from tests.conftest import bjt


class FakeHttpClient:
    def get_text(self, url: str) -> str:
        if "failing.example" in url:
            raise RuntimeError("temporary feed failure")
        return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>CPSC recall update for imported product sold online</title>
      <link>https://www.cpsc.gov/Recalls/2026/example</link>
      <pubDate>Mon, 29 Jun 2026 07:00:00 GMT</pubDate>
      <description>Recall update.</description>
    </item>
  </channel>
</rss>
"""


def test_one_failed_rss_feed_does_not_skip_other_rss_feeds() -> None:
    rules = SourceRules(
        feeds=[
            FeedConfig(
                name="CBP Newsroom",
                url="https://failing.example/rss",
                grade=SourceGrade.A,
                category=Category.POLICY_COMPLIANCE,
            ),
            FeedConfig(
                name="CPSC Recalls",
                url="https://working.example/rss",
                grade=SourceGrade.A,
                category=Category.POLICY_COMPLIANCE,
            ),
        ],
        gdelt_queries=[],
        amz123_briefs=[],
        source_grades={},
        blocked_domain_keywords=[],
    )
    until = bjt(2026, 6, 29, 16)
    since = until - timedelta(hours=24)

    providers = build_providers(rules, FakeHttpClient())  # type: ignore[arg-type]
    items = []
    failed_names = []
    for provider in providers:
        try:
            items.extend(provider.fetch(since, until))
        except RuntimeError:
            failed_names.append(provider.name)

    assert failed_names == ["rss: CBP Newsroom"]
    assert [item.source_name for item in items] == ["CPSC Recalls"]
