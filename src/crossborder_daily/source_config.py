from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import yaml

from crossborder_daily.models import Category, SourceGrade


@dataclass(frozen=True, slots=True)
class FeedConfig:
    name: str
    url: str
    grade: SourceGrade
    category: Category


@dataclass(frozen=True, slots=True)
class GdeltQueryConfig:
    name: str
    query: str
    category: Category


@dataclass(frozen=True, slots=True)
class Amz123BriefConfig:
    name: str
    base_url: str
    grade: SourceGrade
    category: Category


@dataclass(frozen=True, slots=True)
class SourceRules:
    feeds: list[FeedConfig]
    gdelt_queries: list[GdeltQueryConfig]
    amz123_briefs: list[Amz123BriefConfig]
    source_grades: dict[str, SourceGrade]
    blocked_domain_keywords: list[str]

    def grade_for_url(self, url: str, default: SourceGrade = SourceGrade.C) -> SourceGrade:
        hostname = (urlparse(url).hostname or "").lower()
        if not hostname:
            return default
        best_match = ""
        best_grade = default
        for domain, grade in self.source_grades.items():
            normalized = domain.lower()
            matches = hostname == normalized or hostname.endswith(f".{normalized}")
            if matches and len(normalized) > len(best_match):
                best_match = normalized
                best_grade = grade
        return best_grade

    def is_blocked_url(self, url: str) -> bool:
        lowered = url.lower()
        return any(keyword.lower() in lowered for keyword in self.blocked_domain_keywords)


def load_source_rules(path: Path) -> SourceRules:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data = cast(dict[str, Any], raw)

    feeds = [
        FeedConfig(
            name=str(item["name"]),
            url=str(item["url"]),
            grade=SourceGrade.from_value(str(item.get("grade", "C"))),
            category=Category.from_value(str(item.get("category", ""))),
        )
        for item in cast(list[dict[str, Any]], data.get("feeds", []))
    ]
    queries = [
        GdeltQueryConfig(
            name=str(item["name"]),
            query=str(item["query"]),
            category=Category.from_value(str(item.get("category", ""))),
        )
        for item in cast(list[dict[str, Any]], data.get("gdelt_queries", []))
    ]
    amz123_briefs = [
        Amz123BriefConfig(
            name=str(item["name"]),
            base_url=str(item["base_url"]).rstrip("/"),
            grade=SourceGrade.from_value(str(item.get("grade", "C"))),
            category=Category.from_value(str(item.get("category", ""))),
        )
        for item in cast(list[dict[str, Any]], data.get("amz123_briefs", []))
    ]
    source_grades = {
        str(domain).lower(): SourceGrade.from_value(str(grade))
        for domain, grade in cast(dict[str, Any], data.get("source_grades", {})).items()
    }
    blocked = [str(item) for item in cast(list[Any], data.get("blocked_domain_keywords", []))]
    return SourceRules(
        feeds=feeds,
        gdelt_queries=queries,
        amz123_briefs=amz123_briefs,
        source_grades=source_grades,
        blocked_domain_keywords=blocked,
    )
