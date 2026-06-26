from __future__ import annotations

import ipaddress
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

SENSITIVE_QUERY_KEYS = {"access_token", "sign", "signature", "key", "api_key", "token"}
SECRET_ENV_KEYS = {"DINGTALK_WEBHOOK", "DINGTALK_SECRET", "AI_API_KEY"}


def is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc or not parsed.hostname:
        return False
    if len(url) > 4096:
        return False
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        return False
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local)


def mask_url(url: str) -> str:
    try:
        parsed = urlparse(url)
    except ValueError:
        return "<invalid-url>"
    safe_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key.lower() in SENSITIVE_QUERY_KEYS:
            safe_query.append((key, "***"))
        else:
            safe_query.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(safe_query)))


def redact_text(text: str) -> str:
    redacted = text
    for key in SECRET_ENV_KEYS:
        value = os.getenv(key)
        if value and len(value) >= 4:
            redacted = redacted.replace(value, "***")
    return redacted
