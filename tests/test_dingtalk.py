from __future__ import annotations

import base64
import hashlib
import hmac
from urllib.parse import parse_qsl, urlparse

from crossborder_daily.dingtalk import build_signed_webhook


def test_dingtalk_signature() -> None:
    webhook = "https://oapi.dingtalk.com/robot/send?access_token=abc"
    secret = "SEC000000"
    timestamp = 1719388800000

    signed = build_signed_webhook(webhook, secret, timestamp_ms=timestamp)
    query = dict(parse_qsl(urlparse(signed).query))
    expected = base64.b64encode(
        hmac.new(
            secret.encode("utf-8"),
            f"{timestamp}\n{secret}".encode(),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    assert query["access_token"] == "abc"
    assert query["timestamp"] == str(timestamp)
    assert query["sign"] == expected
