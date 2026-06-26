from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil import parser

BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def now_beijing() -> datetime:
    return datetime.now(BEIJING_TZ)


def to_beijing(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(BEIJING_TZ)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return to_beijing(value)
    stripped = value.strip()
    if not stripped:
        return None
    parsed = parser.parse(stripped)
    return to_beijing(parsed)


def window_start(until: datetime, hours: int) -> datetime:
    return to_beijing(until) - timedelta(hours=hours)


def in_window(value: datetime | None, since: datetime, until: datetime) -> bool:
    if value is None:
        return False
    bjt_value = to_beijing(value)
    return since <= bjt_value <= until


def format_bjt(value: datetime | None, include_time: bool = True) -> str:
    if value is None:
        return "未知"
    bjt_value = to_beijing(value)
    if include_time:
        return bjt_value.strftime("%Y-%m-%d %H:%M")
    return bjt_value.strftime("%Y-%m-%d")


def chinese_headline_date(value: datetime) -> str:
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    bjt_value = to_beijing(value)
    return f"{bjt_value.month}.{bjt_value.day} {weekdays[bjt_value.weekday()]} 核心要闻速览"


def parse_relative_datetime(value: str, reference: datetime) -> datetime | None:
    normalized = value.strip().lower()
    if normalized == "now":
        return to_beijing(reference)
    if normalized.startswith("now-") and normalized.endswith("h"):
        hours = int(normalized.removeprefix("now-").removesuffix("h"))
        return to_beijing(reference) - timedelta(hours=hours)
    if normalized.startswith("now+") and normalized.endswith("h"):
        hours = int(normalized.removeprefix("now+").removesuffix("h"))
        return to_beijing(reference) + timedelta(hours=hours)
    return parse_datetime(value)


def utc_from_timestamp_ms(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
