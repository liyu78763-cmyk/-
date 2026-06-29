from __future__ import annotations

from typing import Any

from crossborder_daily.models import Category, SourceGrade
from crossborder_daily.sources.cpsc_api import CpscRecallApiProvider
from tests.conftest import bjt


class FakeResponse:
    def json(self) -> list[dict[str, str]]:
        return [
            {
                "Title": "Example Product Recalled Due to Fire Hazard",
                "URL": "https://www.cpsc.gov/Recalls/2026/example-product-recall",
                "RecallDate": "2026-06-29",
                "Description": "The product can overheat.",
            },
            {
                "Title": "Old Product Recall",
                "URL": "https://www.cpsc.gov/Recalls/2026/old-product-recall",
                "RecallDate": "2026-06-20",
                "Description": "Older recall.",
            },
        ]


class FakeHttpClient:
    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> FakeResponse:
        assert method == "GET"
        assert params is not None
        assert params["format"] == "json"
        return FakeResponse()


def test_cpsc_api_provider_keeps_recent_official_recalls() -> None:
    provider = CpscRecallApiProvider(FakeHttpClient())  # type: ignore[arg-type]

    items = provider.fetch(since=bjt(2026, 6, 28, 16), until=bjt(2026, 6, 29, 16))

    assert len(items) == 1
    assert items[0].title == "Example Product Recalled Due to Fire Hazard"
    assert items[0].source_name == "CPSC"
    assert items[0].category == Category.POLICY_COMPLIANCE
    assert items[0].source_grade == SourceGrade.A
