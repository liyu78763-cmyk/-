from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from crossborder_daily.http_client import HttpClient
from crossborder_daily.models import Category, NewsItem
from crossborder_daily.source_config import Amz123BriefConfig
from crossborder_daily.time_utils import BEIJING_TZ, to_beijing

AMZ123_AMAZON_KEYWORDS = [
    "amazon",
    "prime",
    "fba",
    "mfn",
    "seller central",
    "asin",
    "亚马逊",
    "美国站",
]

AMZ123_OTHER_PLATFORM_KEYWORDS = [
    "ebay",
    "lazada",
    "shopee",
    "shein",
    "target",
    "temu",
    "tiktok",
    "walmart",
    "whatnot",
    "独立站",
    "沃尔玛",
    "速卖通",
]

AMZ123_NON_NORTH_AMERICA_KEYWORDS = [
    "eu",
    "uk",
    "巴西",
    "德国",
    "东南亚",
    "俄罗斯",
    "法国",
    "菲律宾",
    "韩国",
    "荷兰",
    "拉美",
    "拉丁美洲",
    "马来西亚",
    "美国以外",
    "墨西哥以外",
    "南非",
    "欧盟",
    "欧洲",
    "日本",
    "沙特",
    "泰国",
    "土耳其",
    "西班牙",
    "新加坡",
    "意大利",
    "印度",
    "印尼",
    "英国",
    "越南",
]

AMZ123_NORTH_AMERICA_KEYWORDS = [
    "canada",
    "fedex",
    "mexico",
    "north america",
    "u.s.",
    "ups",
    "usa",
    "usps",
    "北美",
    "加拿大",
    "独立日",
    "美国",
    "美国站",
    "墨西哥",
]

AMZ123_US_PLATFORM_KEYWORDS = [
    "target",
    "walmart",
    "whatnot",
    "沃尔玛",
]

AMZ123_LOGISTICS_COMPLIANCE_KEYWORDS = [
    "cbp",
    "cpsc",
    "customs",
    "fba",
    "fda",
    "fedex",
    "ftc",
    "recall",
    "tariff",
    "ups",
    "usps",
    "仓储",
    "关税",
    "港口",
    "合规",
    "海关",
    "空运",
    "物流",
    "配送",
    "入库",
    "召回",
]


@dataclass(frozen=True, slots=True)
class Amz123Headline:
    title: str
    url: str
    relevance_priority: int


class Amz123BriefProvider:
    name = "amz123"

    def __init__(self, configs: list[Amz123BriefConfig], http_client: HttpClient) -> None:
        self.configs = configs
        self.http_client = http_client

    def fetch(self, since: datetime, until: datetime) -> list[NewsItem]:
        items: list[NewsItem] = []
        for config in self.configs:
            for page_date in _dates_between(since, until):
                published_at = datetime.combine(page_date, time(hour=8), tzinfo=BEIJING_TZ)
                if not since <= published_at <= until:
                    continue
                page_url = f"{config.base_url}/{page_date:%Y%m%d}"
                html = self.http_client.get_text(page_url)
                for index, headline in enumerate(parse_amz123_headlines(html, page_url), start=1):
                    items.append(
                        NewsItem(
                            title=headline.title,
                            url=headline.url,
                            source_name=config.name,
                            published_at=published_at,
                            summary=headline.title,
                            category=_category_from_title(headline.title, config.category),
                            source_grade=config.grade,
                            metadata={
                                "source_order": str(index),
                                "amz123_relevance_priority": str(headline.relevance_priority),
                            },
                        )
                    )
        return items


def parse_amz123_headlines(html: str, page_url: str) -> list[Amz123Headline]:
    parser = _LinkParser(base_url=page_url)
    parser.feed(html)
    buckets: dict[int, list[Amz123Headline]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    seen_urls: set[str] = set()
    for title, url in parser.links:
        if url in seen_urls:
            continue
        if not _is_amz123_article_url(url):
            continue
        relevance_priority = _title_relevance_priority(title)
        if relevance_priority is None:
            continue
        seen_urls.add(url)
        buckets[relevance_priority].append(
            Amz123Headline(title=title, url=url, relevance_priority=relevance_priority)
        )
    return [headline for priority in sorted(buckets) for headline in buckets[priority]]


class _LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self._href: str | None = None
        self._text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attr_map = dict(attrs)
        href = attr_map.get("href")
        if href:
            self._href = href
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        title = " ".join("".join(self._text_parts).split())
        if title:
            self.links.append((title, urljoin(self.base_url, self._href)))
        self._href = None
        self._text_parts = []


def _dates_between(since: datetime, until: datetime) -> list[date]:
    start = to_beijing(since).date()
    end = to_beijing(until).date()
    days = (end - start).days
    return [start + timedelta(days=offset) for offset in range(days + 1)]


def _is_amz123_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.hostname != "www.amz123.com":
        return False
    return parsed.path.startswith(("/t/", "/kx/"))


def _is_relevant_title(title: str) -> bool:
    return _title_relevance_priority(title) is not None


def _title_relevance_priority(title: str) -> int | None:
    lowered = title.lower()
    has_amazon = _contains_any(lowered, AMZ123_AMAZON_KEYWORDS)
    has_other_platform = _contains_any(lowered, AMZ123_OTHER_PLATFORM_KEYWORDS)
    has_non_north_america = _contains_any(lowered, AMZ123_NON_NORTH_AMERICA_KEYWORDS)
    has_north_america = _contains_any(lowered, AMZ123_NORTH_AMERICA_KEYWORDS)
    has_us_platform = _contains_any(lowered, AMZ123_US_PLATFORM_KEYWORDS)
    has_logistics_or_compliance = _contains_any(lowered, AMZ123_LOGISTICS_COMPLIANCE_KEYWORDS)

    if has_amazon and not has_other_platform and not has_non_north_america:
        return 1
    if has_amazon and not has_other_platform:
        return 2
    if (has_north_america or has_logistics_or_compliance) and not has_other_platform:
        return 3
    if has_amazon:
        return 4
    if has_other_platform and (has_north_america or has_us_platform):
        return 5
    return None


def _category_from_title(title: str, fallback: Category) -> Category:
    lowered = title.lower()
    if any(keyword in lowered for keyword in ["amazon", "prime", "fba", "mfn", "亚马逊"]):
        return Category.AMAZON_PLATFORM
    if any(
        keyword in lowered
        for keyword in [
            "cbp",
            "cpsc",
            "customs",
            "fda",
            "ftc",
            "recall",
            "tariff",
            "关税",
            "合规",
            "海关",
            "召回",
        ]
    ):
        return Category.POLICY_COMPLIANCE
    if any(
        keyword in lowered
        for keyword in [
            "fedex",
            "ups",
            "usps",
            "仓储",
            "港口",
            "海运",
            "空运",
            "物流",
            "配送",
            "入库",
        ]
    ):
        return Category.LOGISTICS
    return fallback


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)
