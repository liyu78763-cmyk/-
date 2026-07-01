from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from crossborder_daily.http_client import HttpClient
from crossborder_daily.security import is_safe_url

LOGGER = logging.getLogger(__name__)

PBC_RATE_INDEX_URL = "https://www.pbc.gov.cn/zhengcehuobisi/125207/125217/125925/index.html"
PBC_SOURCE_NAME = "中国人民银行"

PBC_TITLE_RE = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日中国外汇交易中心受权公布人民币汇率中间价公告")
USD_CNY_RE = re.compile(r"1\s*美元\s*对\s*人民币\s*([0-9]+(?:\.[0-9]+)?)\s*元")
CHINESE_DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
META_RE = re.compile(
    r"<meta\s+name=[\"']([^\"']+)[\"']\s+content=[\"']([^\"']*)[\"']",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ExchangeRateQuote:
    usd_cny: str
    source_name: str
    source_url: str
    published_date: date | None


def fetch_pbc_usd_cny_rate(http_client: HttpClient) -> ExchangeRateQuote:
    index_html = _get_utf8_html(http_client, PBC_RATE_INDEX_URL)
    article_url = parse_latest_pbc_rate_article_url(index_html, PBC_RATE_INDEX_URL)
    if not article_url:
        raise ValueError("PBC exchange-rate article link was not found")
    if not _is_pbc_rate_url(article_url):
        raise ValueError("PBC exchange-rate article URL failed safety checks")

    article_html = _get_utf8_html(http_client, article_url)
    return parse_pbc_usd_cny_rate(article_html, article_url)


def parse_latest_pbc_rate_article_url(html: str, index_url: str) -> str | None:
    parser = _AnchorParser(base_url=index_url)
    parser.feed(html)
    for title, href in parser.links:
        if PBC_TITLE_RE.search(title) and _is_pbc_rate_url(href):
            return href
    return None


def parse_pbc_usd_cny_rate(html: str, source_url: str) -> ExchangeRateQuote:
    metadata = _parse_meta_tags(html)
    searchable_text = " ".join(
        value
        for value in [
            metadata.get("ArticleTitle", ""),
            metadata.get("Description", ""),
            _strip_html(html),
        ]
        if value
    )
    rate_match = USD_CNY_RE.search(searchable_text)
    if not rate_match:
        raise ValueError("USD/CNY central parity rate was not found in PBC article")

    published_date = _parse_iso_date(metadata.get("PubDate")) or _parse_chinese_date(
        searchable_text
    )
    return ExchangeRateQuote(
        usd_cny=rate_match.group(1),
        source_name=PBC_SOURCE_NAME,
        source_url=source_url,
        published_date=published_date,
    )


def _get_utf8_html(http_client: HttpClient, url: str) -> str:
    response = http_client.request("GET", url)
    return response.content.decode("utf-8", errors="replace")


def _parse_meta_tags(html: str) -> dict[str, str]:
    return {match.group(1): unescape(match.group(2)).strip() for match in META_RE.finditer(html)}


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _parse_chinese_date(text: str) -> date | None:
    match = CHINESE_DATE_RE.search(text)
    if not match:
        return None
    try:
        return date(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )
    except ValueError:
        return None


def _is_pbc_rate_url(url: str) -> bool:
    if not is_safe_url(url):
        return False
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and hostname == "www.pbc.gov.cn"
        and "/zhengcehuobisi/125207/125217/125925/" in parsed.path
        and parsed.path.endswith("/index.html")
    )


class _AnchorParser(HTMLParser):
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
            self._href = urljoin(self.base_url, href)
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._href is None:
            return
        title = " ".join("".join(self._text_parts).split())
        if title:
            self.links.append((unescape(title), self._href))
        self._href = None
        self._text_parts = []
