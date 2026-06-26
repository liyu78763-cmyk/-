from __future__ import annotations

from pathlib import Path

from crossborder_daily.http_client import HttpClient
from crossborder_daily.source_config import SourceRules
from crossborder_daily.sources.amz123 import Amz123BriefProvider
from crossborder_daily.sources.base import NewsProvider
from crossborder_daily.sources.fixture import FixtureNewsProvider
from crossborder_daily.sources.gdelt import GdeltNewsProvider
from crossborder_daily.sources.rss import RssFeedProvider


def build_providers(
    rules: SourceRules,
    http_client: HttpClient,
    *,
    fixture_path: Path | None = None,
) -> list[NewsProvider]:
    if fixture_path is not None:
        return [FixtureNewsProvider(fixture_path)]
    providers: list[NewsProvider] = []
    if rules.feeds:
        providers.append(RssFeedProvider(rules.feeds, http_client))
    if rules.gdelt_queries:
        providers.append(GdeltNewsProvider(rules.gdelt_queries, rules, http_client))
    if rules.amz123_briefs:
        providers.append(Amz123BriefProvider(rules.amz123_briefs, http_client))
    return providers
