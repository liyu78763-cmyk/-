from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from crossborder_daily.models import Category, ScoredNews
from crossborder_daily.time_utils import to_beijing

HTML_TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
CATEGORY_ORDER = [
    Category.HOT,
    Category.AMAZON_PLATFORM,
    Category.POLICY_COMPLIANCE,
    Category.ADS_TRAFFIC,
    Category.LOGISTICS,
    Category.MARKET_PLATFORM,
]


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    generated_at: datetime
    window_hours: int
    expanded_to_48h: bool
    used_history: bool
    rejected_count: int
    provider_errors: list[str]


def format_daily_report(items: list[ScoredNews], metadata: ReportMetadata) -> str:
    title_date = _compact_title_date(metadata.generated_at)
    lines: list[str] = [
        f"跨境快讯｜{title_date}",
        "",
    ]
    if not items:
        lines.extend(
            [
                "今日暂无需要立即处理的重大行业变化，建议按正常节奏持续关注平台及监管机构通知。",
                "",
            ]
        )
    else:
        lines.extend(_format_news_sections(items))
    return "\n".join(lines).strip() + "\n"


def _format_news_sections(items: list[ScoredNews]) -> list[str]:
    lines: list[str] = []
    number = 1
    for category in CATEGORY_ORDER:
        category_items = [item for item in items if item.item.category == category]
        if not category_items:
            continue
        for scored in category_items:
            lines.extend(_format_single_news(scored, number))
            number += 1
    return lines


def _format_single_news(scored: ScoredNews, number: int) -> list[str]:
    item = scored.item
    return [
        f"{number}.{item.title}",
        "",
        f"来源：{_source_label(item.source_name)}｜[查看原文]({item.url})",
        "",
    ]


def _format_info(metadata: ReportMetadata) -> list[str]:
    if metadata.window_hours == 48:
        window_text = "本期先检索最近24小时；高价值新闻不足，已扩展至最近48小时。"
    else:
        window_text = "本期使用最近24小时范围。"
    history_text = (
        "已使用过去7天历史记录做 URL 与事件指纹去重。"
        if metadata.used_history
        else "未使用历史去重。"
    )
    error_text = ""
    if metadata.provider_errors:
        error_text = f"有{len(metadata.provider_errors)}个新闻源本次失败，已跳过，不影响其他来源。"
    return [
        "信息说明：",
        "",
        window_text,
        history_text,
        f"过滤了{metadata.rejected_count}条缺少来源、时间、链接、可信度不足或不在时间范围内的信息。",
        error_text,
    ]


def _clean_text(value: str) -> str:
    without_tags = HTML_TAG_RE.sub("", value)
    return WHITESPACE_RE.sub(" ", without_tags).strip()


def _compact_title_date(value: datetime) -> str:
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    bjt_value = to_beijing(value)
    return f"{bjt_value.month}月{bjt_value.day}日 {weekdays[bjt_value.weekday()]}"


def _daily_focus(items: list[ScoredNews]) -> str:
    if not items:
        return "今日暂无需要立即处理的重大行业变化。"
    top = items[0]
    if top.item.category == Category.POLICY_COMPLIANCE:
        return "重点关注官方合规与召回信息，优先排查相似ASIN和高风险库存。"
    if top.item.category == Category.LOGISTICS:
        return "重点关注物流和FBA变化，优先复核补货、在途货件和成本测算。"
    if top.item.category == Category.ADS_TRAFFIC:
        return "重点关注广告与流量变化，优先控制预算并复盘转化数据。"
    return "重点关注平台与市场变化，优先核对对账号、广告、库存和利润的影响。"


def _source_label(source_name: str) -> str:
    lowered = source_name.lower()
    if "cpsc" in lowered:
        return "CPSC"
    if "amazon" in lowered:
        return "Amazon"
    if "cbp" in lowered:
        return "CBP"
    if "ustr" in lowered:
        return "USTR"
    if "fda" in lowered:
        return "FDA"
    if "ftc" in lowered:
        return "FTC"
    return source_name


def report_title(generated_at: datetime) -> str:
    value = to_beijing(generated_at)
    return f"跨境快讯 {value:%Y-%m-%d}"
