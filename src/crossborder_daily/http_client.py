from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, cast

import requests

from crossborder_daily.security import mask_url

LOGGER = logging.getLogger(__name__)


class HttpRequestError(RuntimeError):
    pass


@dataclass(slots=True)
class HttpClient:
    timeout_seconds: float = 15.0
    max_retries: int = 3
    backoff_seconds: float = 0.6
    session: requests.Session = field(init=False)

    def __post_init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "crossborder-dingtalk-daily/0.1 "
                    "(news verification automation; contact repository owner)"
                )
            }
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_body,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise HttpRequestError(f"retryable HTTP {response.status_code}")
                response.raise_for_status()
                return response
            except (requests.RequestException, HttpRequestError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                sleep_seconds = self.backoff_seconds * (2**attempt)
                LOGGER.warning(
                    "HTTP request failed; retrying in %.1fs: %s",
                    sleep_seconds,
                    mask_url(url),
                )
                time.sleep(sleep_seconds)
        raise HttpRequestError(
            f"HTTP request failed after retries: {mask_url(url)}"
        ) from last_error

    def get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        return self.request("GET", url, params=params).text

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return cast(dict[str, Any], self.request("GET", url, params=params).json())

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = self.request("POST", url, json_body=payload, headers=headers)
        if not response.text:
            return {}
        return cast(dict[str, Any], response.json())
