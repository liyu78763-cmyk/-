from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from urllib.parse import urlencode

from crossborder_daily.http_client import HttpClient
from crossborder_daily.models import Category, NewsItem, SourceGrade
from crossborder_daily.time_utils import parse_datetime, to_beijing

CPSC_RECALL_API_URL = "https://www.saferproducts.gov/RestWebServices/Recall"


class CpscRecallApiProvider:
    name = "cpsc_api"

    def __init__(self, http_client: HttpClient) -> None:
        self.http_client = http_client

    def fetch(self, since: datetime, until: datetime) -> list[NewsItem]:
        params = {
            "format": "json",
            "RecallDateStart": to_beijing(since).date().isoformat(),
            "RecallDateEnd": to_beijing(until).date().isoformat(),
        }
        response = self.http_client.request(
            "GET",
            CPSC_RECALL_API_URL,
            params=params,
            headers={
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            },
        )
        records = _extract_records(response.json())
        items: list[NewsItem] = []
        for record in records:
            item = _record_to_item(record)
            if item is None:
                continue
            if item.published_at is not None and since <= item.published_at <= until:
                items.append(item)
        return items


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [cast(dict[str, Any], item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("recalls", "Recalls", "results", "Results", "data", "Data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [cast(dict[str, Any], item) for item in value if isinstance(item, dict)]
    return []


def _record_to_item(record: dict[str, Any]) -> NewsItem | None:
    title = _first_string(record, "Title", "RecallTitle", "Name")
    url = _first_string(record, "URL", "Url", "RecallURL", "RecallUrl")
    recall_number = _first_string(record, "RecallNumber", "RecallNo", "Number")
    if not title:
        title = _fallback_title(record)
    if not url and recall_number:
        url = (
            f"{CPSC_RECALL_API_URL}?{urlencode({'format': 'json', 'RecallNumber': recall_number})}"
        )
    published_at = parse_datetime(
        _first_string(record, "RecallDate", "RecallPublishDate", "PublishDate", "LastPublishDate")
    )
    if not title or not url or published_at is None:
        return None
    summary = _first_string(record, "Description", "Hazard", "Remedy", "ConsumerContact")
    return NewsItem(
        title=title,
        url=url,
        source_name="CPSC",
        published_at=published_at,
        summary=summary,
        category=Category.POLICY_COMPLIANCE,
        source_grade=SourceGrade.A,
        metadata={"provider": "cpsc_api"},
    )


def _fallback_title(record: dict[str, Any]) -> str:
    products = _list_names(record.get("Products"))
    firms = _list_names(record.get("Inconjunctions")) or _list_names(record.get("Manufacturers"))
    product = products[0] if products else ""
    firm = firms[0] if firms else ""
    if product and firm:
        return f"{firm} recalls {product}"
    if product:
        return f"CPSC recall: {product}"
    return ""


def _first_string(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _list_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, dict):
            name = _first_string(item, "Name", "CompanyName", "Manufacturer", "ProductName")
            if name:
                names.append(name)
        elif isinstance(item, str) and item.strip():
            names.append(item.strip())
    return names
