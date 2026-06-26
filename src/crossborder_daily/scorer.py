from __future__ import annotations

from datetime import datetime, timedelta

from crossborder_daily.advice import actions_for_item, advice_type_for_item
from crossborder_daily.dedupe import event_fingerprint
from crossborder_daily.models import (
    Category,
    ImportanceLevel,
    NewsItem,
    ScoreComponents,
    ScoredNews,
)
from crossborder_daily.time_utils import to_beijing

IMPACT_BY_CATEGORY = {
    Category.POLICY_COMPLIANCE: 22,
    Category.AMAZON_PLATFORM: 20,
    Category.LOGISTICS: 18,
    Category.ADS_TRAFFIC: 14,
    Category.HOT: 13,
    Category.MARKET_PLATFORM: 10,
}

OPERATIONAL_BY_CATEGORY = {
    Category.POLICY_COMPLIANCE: 23,
    Category.AMAZON_PLATFORM: 21,
    Category.LOGISTICS: 19,
    Category.ADS_TRAFFIC: 17,
    Category.HOT: 12,
    Category.MARKET_PLATFORM: 10,
}

URGENT_KEYWORDS = {
    "effective immediately",
    "recall",
    "suspend",
    "account health",
    "fee increase",
    "tariff",
    "customs",
    "disruption",
    "delay",
}


def score_item(item: NewsItem, *, now: datetime) -> ScoredNews:
    components = ScoreComponents(
        impact_scope=_impact_scope(item),
        operational_impact=_operational_impact(item),
        urgency=_urgency(item, now=now),
        source_trust=item.source_grade.trust_score,
        amazon_relevance=_amazon_relevance(item),
    )
    total = components.total
    level = _importance_level(total)
    action_priority = _action_priority(total, components.urgency)
    return ScoredNews(
        item=item,
        components=components,
        level=level,
        action_priority=action_priority,
        advice_type=advice_type_for_item(item),
        actions=actions_for_item(item, action_priority=action_priority),
        event_fingerprint=event_fingerprint(item),
    )


def score_and_filter(
    items: list[NewsItem], *, now: datetime, minimum_score: int = 40
) -> list[ScoredNews]:
    scored = [score_item(item, now=now) for item in items]
    filtered = [item for item in scored if item.score >= minimum_score]
    return sorted(
        filtered,
        key=lambda item: (
            _source_priority(item),
            _source_order_score(item, now=now),
            item.score,
        ),
        reverse=True,
    )


def _source_priority(scored: ScoredNews) -> int:
    text = f"{scored.item.source_name} {scored.item.url}".lower()
    if "amz123" in text:
        return 30
    if "amazon" in text:
        return 40
    if "cpsc" in text:
        return 10
    return 20


def _source_order_score(scored: ScoredNews, *, now: datetime) -> int:
    if "amz123" in f"{scored.item.source_name} {scored.item.url}".lower():
        try:
            return 10000 - int(scored.item.metadata.get("source_order", "9999"))
        except ValueError:
            return 0
    return _heat_score(scored, now=now)


def _heat_score(scored: ScoredNews, *, now: datetime) -> int:
    published_at = scored.item.published_at
    if published_at is None:
        recency_boost = 0
    else:
        age_hours = max(
            0, int((to_beijing(now) - to_beijing(published_at)).total_seconds() // 3600)
        )
        recency_boost = max(0, 12 - age_hours // 2)
    return scored.score + recency_boost


def _impact_scope(item: NewsItem) -> int:
    text = _combined_text(item)
    base = IMPACT_BY_CATEGORY[item.category]
    if any(keyword in text for keyword in ["all sellers", "us sellers", "marketplace", "fba"]):
        base += 3
    if any(keyword in text for keyword in ["china", "import", "tariff", "customs"]):
        base += 2
    return min(base, 25)


def _operational_impact(item: NewsItem) -> int:
    text = _combined_text(item)
    base = OPERATIONAL_BY_CATEGORY[item.category]
    if any(keyword in text for keyword in ["fee", "cost", "tariff", "surcharge", "storage"]):
        base += 3
    if any(keyword in text for keyword in ["recall", "compliance", "listing", "account"]):
        base += 3
    if any(keyword in text for keyword in ["ads", "sponsored", "campaign", "dsp"]):
        base += 2
    return min(base, 25)


def _urgency(item: NewsItem, *, now: datetime) -> int:
    bjt_now = to_beijing(now)
    published = to_beijing(item.published_at) if item.published_at else bjt_now
    age = bjt_now - published
    if age <= timedelta(hours=24):
        base = 12
    elif age <= timedelta(hours=48):
        base = 9
    else:
        base = 4
    if item.effective_at is not None:
        effective = to_beijing(item.effective_at)
        if effective <= bjt_now:
            base += 6
        elif effective <= bjt_now + timedelta(days=7):
            base += 5
        elif effective <= bjt_now + timedelta(days=30):
            base += 3
    text = _combined_text(item)
    if any(keyword in text for keyword in URGENT_KEYWORDS):
        base += 4
    return min(base, 20)


def _amazon_relevance(item: NewsItem) -> int:
    text = _combined_text(item)
    if item.category in {Category.AMAZON_PLATFORM, Category.ADS_TRAFFIC}:
        return 10
    if "amazon" in text or "fba" in text or "seller central" in text:
        return 10
    if item.category == Category.LOGISTICS and any(
        keyword in text for keyword in ["us", "u.s.", "china"]
    ):
        return 7
    if item.category == Category.POLICY_COMPLIANCE:
        return 6
    if any(keyword in text for keyword in ["walmart", "tiktok shop", "temu", "ebay"]):
        return 4
    return 2


def _importance_level(score: int) -> ImportanceLevel:
    if score >= 80:
        return ImportanceLevel.MAJOR
    if score >= 60:
        return ImportanceLevel.IMPORTANT
    return ImportanceLevel.NORMAL


def _action_priority(score: int, urgency: int) -> str:
    if score >= 80 or urgency >= 17:
        return "P0"
    if score >= 60:
        return "P1"
    return "P2"


def _combined_text(item: NewsItem) -> str:
    return f"{item.title} {item.summary} {item.content} {item.source_name}".lower()
