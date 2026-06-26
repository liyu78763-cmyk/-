from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from crossborder_daily.http_client import HttpClient
from crossborder_daily.security import is_safe_url
from crossborder_daily.splitter import split_message


@dataclass(frozen=True, slots=True)
class DingTalkConfig:
    webhook: str
    secret: str = ""
    max_chars: int = 3500


class DingTalkClient:
    def __init__(self, config: DingTalkConfig, http_client: HttpClient) -> None:
        if not config.webhook:
            raise ValueError("DINGTALK_WEBHOOK is required when dry-run is disabled")
        if not is_safe_url(config.webhook):
            raise ValueError("DINGTALK_WEBHOOK is not a safe HTTP(S) URL")
        self.config = config
        self.http_client = http_client

    def send_markdown(self, *, title: str, text: str) -> int:
        chunks = split_message(text, max_chars=self.config.max_chars)
        for index, chunk in enumerate(chunks, start=1):
            chunk_title = title if len(chunks) == 1 else f"{title} ({index}/{len(chunks)})"
            payload: dict[str, Any] = {
                "msgtype": "markdown",
                "markdown": {"title": chunk_title, "text": chunk},
            }
            signed_url = build_signed_webhook(self.config.webhook, self.config.secret)
            response = self.http_client.post_json(signed_url, payload)
            if int(response.get("errcode", -1)) != 0:
                errmsg = str(response.get("errmsg", "unknown error"))
                raise RuntimeError(f"DingTalk returned error: {errmsg}")
        return len(chunks)


def build_signed_webhook(
    webhook: str,
    secret: str = "",
    *,
    timestamp_ms: int | None = None,
) -> str:
    if not secret:
        return webhook
    actual_timestamp = timestamp_ms if timestamp_ms is not None else int(time.time() * 1000)
    string_to_sign = f"{actual_timestamp}\n{secret}".encode()
    digest = hmac.new(secret.encode("utf-8"), string_to_sign, hashlib.sha256).digest()
    sign = base64.b64encode(digest).decode("utf-8")
    parsed = urlparse(webhook)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["timestamp"] = str(actual_timestamp)
    query["sign"] = sign
    return urlunparse(parsed._replace(query=urlencode(query)))


def dingtalk_config_from_env() -> DingTalkConfig:
    max_chars = int(os.getenv("DINGTALK_MAX_CHARS", "3500"))
    return DingTalkConfig(
        webhook=os.getenv("DINGTALK_WEBHOOK", ""),
        secret=os.getenv("DINGTALK_SECRET", ""),
        max_chars=max_chars,
    )
