from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from crossborder_daily.models import NewsItem

TRACKING_PARAM_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "igshid", "ref", "source"}
TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a",
    "about",
    "after",
    "and",
    "announces",
    "for",
    "from",
    "in",
    "latest",
    "new",
    "news",
    "of",
    "on",
    "or",
    "the",
    "to",
    "update",
    "updates",
    "with",
}


def canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    hostname = (parsed.hostname or "").lower()
    netloc = hostname
    if parsed.port:
        netloc = f"{hostname}:{parsed.port}"
    query_items = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered_key = key.lower()
        if lowered_key in TRACKING_PARAMS:
            continue
        if any(lowered_key.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES):
            continue
        query_items.append((key, value))
    normalized_path = parsed.path.rstrip("/") or "/"
    return urlunparse(
        (
            parsed.scheme.lower(),
            netloc,
            normalized_path,
            "",
            urlencode(sorted(query_items)),
            "",
        )
    )


def title_tokens(title: str) -> set[str]:
    tokens = {token.lower() for token in TOKEN_RE.findall(title)}
    return {token for token in tokens if len(token) > 2 and token not in STOPWORDS}


def event_fingerprint(item: NewsItem) -> str:
    tokens = sorted(title_tokens(item.title))
    if not tokens:
        tokens = [canonical_url(item.url)]
    key = "|".join([item.category.value, *tokens[:14]])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def are_same_event(left: NewsItem, right: NewsItem) -> bool:
    if canonical_url(left.url) == canonical_url(right.url):
        return True
    if left.category != right.category:
        return False
    left_tokens = title_tokens(left.title)
    right_tokens = title_tokens(right.title)
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    if union == 0:
        return False
    return overlap / union >= 0.58


def dedupe_items(items: list[NewsItem]) -> list[NewsItem]:
    ordered = sorted(
        items,
        key=lambda item: (
            item.source_grade.trust_score,
            item.published_at.isoformat() if item.published_at else "",
        ),
        reverse=True,
    )
    deduped: list[NewsItem] = []
    for item in ordered:
        existing = next(
            (candidate for candidate in deduped if are_same_event(candidate, item)), None
        )
        if existing is None:
            deduped.append(item)
            continue
        sources = existing.metadata.get("additional_sources", "")
        source_parts = [part for part in sources.split(";") if part]
        source_parts.append(f"{item.source_name}|{item.url}")
        existing.metadata["additional_sources"] = ";".join(sorted(set(source_parts)))
        if not existing.summary and item.summary:
            existing.summary = item.summary
        if not existing.content and item.content:
            existing.content = item.content
    return deduped
