from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from crossborder_daily.models import Category, NewsItem, RejectedNews, SourceGrade
from crossborder_daily.security import is_safe_url
from crossborder_daily.source_config import SourceRules
from crossborder_daily.time_utils import in_window

HIGH_RISK_KEYWORDS = {
    "account",
    "ban",
    "cbp",
    "compliance",
    "cpsc",
    "customs",
    "fba fee",
    "fda",
    "fee",
    "ftc",
    "import alert",
    "listing",
    "recall",
    "suspend",
    "tariff",
    "ustr",
}


@dataclass(frozen=True, slots=True)
class FilterResult:
    accepted: list[NewsItem]
    rejected: list[RejectedNews]


def filter_news_items(
    items: list[NewsItem],
    *,
    since: datetime,
    until: datetime,
    rules: SourceRules,
) -> FilterResult:
    accepted: list[NewsItem] = []
    rejected: list[RejectedNews] = []
    for item in items:
        reason = rejection_reason(item, since=since, until=until, rules=rules)
        if reason:
            rejected.append(RejectedNews(item=item, reason=reason))
            continue
        detected_grade = rules.grade_for_url(item.url, item.source_grade)
        if detected_grade.trust_score > item.source_grade.trust_score:
            item.source_grade = detected_grade
        accepted.append(item)
    return FilterResult(accepted=accepted, rejected=rejected)


def rejection_reason(
    item: NewsItem,
    *,
    since: datetime,
    until: datetime,
    rules: SourceRules,
) -> str | None:
    if not item.title.strip():
        return "missing title"
    if not item.source_name.strip():
        return "missing source"
    if not item.url.strip():
        return "missing url"
    if not is_safe_url(item.url):
        return "unsafe url"
    if rules.is_blocked_url(item.url):
        return "blocked source"
    if item.published_at is None:
        return "missing published time"
    if not in_window(item.published_at, since, until):
        return "outside time window"
    detected_grade = rules.grade_for_url(item.url, item.source_grade)
    grade = (
        detected_grade
        if detected_grade.trust_score > item.source_grade.trust_score
        else item.source_grade
    )
    if grade == SourceGrade.D:
        return "low credibility source"
    if (
        is_high_risk(item)
        and grade not in {SourceGrade.A, SourceGrade.B}
        and not _is_allowed_amz123_recall(item)
    ):
        return "high-risk news without authoritative source"
    return None


def is_high_risk(item: NewsItem) -> bool:
    if item.category == Category.POLICY_COMPLIANCE:
        return True
    text = f"{item.title} {item.summary} {item.content}".lower()
    return any(keyword in text for keyword in HIGH_RISK_KEYWORDS)


def _is_allowed_amz123_recall(item: NewsItem) -> bool:
    source_text = f"{item.source_name} {item.url}".lower()
    if "amz123" not in source_text:
        return False
    item_text = f"{item.title} {item.summary} {item.content}".lower()
    return any(keyword in item_text for keyword in ["cpsc", "recall", "召回"])
