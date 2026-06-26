from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    sources_path: Path
    history_path: Path
    prompt_path: Path
    output_path: Path


def default_paths(cwd: Path | None = None) -> RuntimePaths:
    root = cwd or Path.cwd()
    return RuntimePaths(
        sources_path=root / "data" / "sources.yml",
        history_path=root / "data" / "history.sqlite",
        prompt_path=root / "prompts" / "daily_report.md",
        output_path=root / "data" / "latest_report.md",
    )


def default_min_high_value_items() -> int:
    return int(os.getenv("MIN_HIGH_VALUE_ITEMS", "0"))


def default_max_news_age_days() -> int:
    return int(os.getenv("MAX_NEWS_AGE_DAYS", "7"))


def default_amz123_items() -> int:
    return int(os.getenv("AMZ123_ITEMS", "5"))
