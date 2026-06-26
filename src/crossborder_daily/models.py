from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class SourceGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"

    @classmethod
    def from_value(cls, value: str | None) -> SourceGrade:
        normalized = (value or "C").strip().upper()
        if normalized in cls.__members__:
            return cls[normalized]
        return cls.C

    @property
    def trust_score(self) -> int:
        return {
            SourceGrade.A: 20,
            SourceGrade.B: 16,
            SourceGrade.C: 10,
            SourceGrade.D: 0,
        }[self]


class Category(StrEnum):
    HOT = "hot"
    AMAZON_PLATFORM = "amazon_platform"
    POLICY_COMPLIANCE = "policy_compliance"
    ADS_TRAFFIC = "ads_traffic"
    LOGISTICS = "logistics"
    MARKET_PLATFORM = "market_platform"

    @classmethod
    def from_value(cls, value: str | None) -> Category:
        if not value:
            return cls.MARKET_PLATFORM
        normalized = value.strip().lower()
        for category in cls:
            if normalized in {category.value, category.name.lower()}:
                return category
        return cls.MARKET_PLATFORM

    @property
    def section_label(self) -> str:
        return {
            Category.HOT: "📑时事热点",
            Category.AMAZON_PLATFORM: "📦Amazon平台动态",
            Category.POLICY_COMPLIANCE: "⚖️政策与合规",
            Category.ADS_TRAFFIC: "📢广告与流量",
            Category.LOGISTICS: "🚢物流与供应链",
            Category.MARKET_PLATFORM: "📊市场与平台动态",
        }[self]


class AdviceType(StrEnum):
    COMPLIANCE = "合规警示"
    OPERATIONS = "运营提示"
    ADS = "广告提示"
    COST = "成本提示"
    LOGISTICS = "物流提示"
    MARKET = "市场提示"


class ImportanceLevel(StrEnum):
    MAJOR = "重大"
    IMPORTANT = "重要"
    NORMAL = "一般"


@dataclass(slots=True)
class NewsItem:
    title: str
    url: str
    source_name: str
    published_at: datetime | None
    summary: str = ""
    content: str = ""
    category: Category = Category.MARKET_PLATFORM
    source_grade: SourceGrade = SourceGrade.C
    effective_at: datetime | None = None
    discovered_at: datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ScoreComponents:
    impact_scope: int
    operational_impact: int
    urgency: int
    source_trust: int
    amazon_relevance: int

    @property
    def total(self) -> int:
        return (
            self.impact_scope
            + self.operational_impact
            + self.urgency
            + self.source_trust
            + self.amazon_relevance
        )


@dataclass(slots=True)
class ScoredNews:
    item: NewsItem
    components: ScoreComponents
    level: ImportanceLevel
    action_priority: str
    advice_type: AdviceType
    actions: list[str]
    event_fingerprint: str

    @property
    def score(self) -> int:
        return self.components.total


@dataclass(frozen=True, slots=True)
class RejectedNews:
    item: NewsItem
    reason: str
