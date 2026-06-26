from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from crossborder_daily.http_client import HttpClient

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AiConfig:
    api_key: str
    base_url: str
    model: str

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)


class OpenAICompatibleClient:
    def __init__(self, config: AiConfig, http_client: HttpClient) -> None:
        self.config = config
        self.http_client = http_client

    def polish_report(self, *, prompt_path: Path, draft: str, facts: dict[str, Any]) -> str:
        prompt = prompt_path.read_text(encoding="utf-8")
        endpoint = self.config.base_url.rstrip("/") + "/chat/completions"
        payload: dict[str, Any] = {
            "model": self.config.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": (
                        "请在不新增事实、不删除链接的前提下润色以下早报草稿。"
                        "若草稿已经符合格式，尽量少改。\n\n"
                        f"事实JSON：{json.dumps(facts, ensure_ascii=False)}\n\n"
                        f"草稿：\n{draft}"
                    ),
                },
            ],
        }
        response = self.http_client.post_json(
            endpoint,
            payload,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
        )
        choices = cast(list[dict[str, Any]], response.get("choices", []))
        if not choices:
            raise RuntimeError("AI response did not include choices")
        message = cast(dict[str, Any], choices[0].get("message", {}))
        content = str(message.get("content") or "").strip()
        if not content:
            raise RuntimeError("AI response content is empty")
        return content + "\n"


def ai_config_from_env() -> AiConfig:
    return AiConfig(
        api_key=os.getenv("AI_API_KEY", ""),
        base_url=os.getenv("AI_BASE_URL", ""),
        model=os.getenv("AI_MODEL", ""),
    )


def maybe_polish_report(
    *,
    use_ai: bool,
    prompt_path: Path,
    draft: str,
    facts: dict[str, Any],
    http_client: HttpClient,
) -> str:
    if not use_ai:
        return draft
    config = ai_config_from_env()
    if not config.available:
        LOGGER.info("AI variables are incomplete; using deterministic report formatter.")
        return draft
    try:
        polished = OpenAICompatibleClient(config, http_client).polish_report(
            prompt_path=prompt_path,
            draft=draft,
            facts=facts,
        )
    except Exception as exc:
        LOGGER.warning("AI polishing failed; using deterministic report: %s", exc)
        return draft
    if not _polished_report_is_safe(polished, facts):
        LOGGER.warning("AI polished report failed validation; using deterministic report.")
        return draft
    return polished


def _polished_report_is_safe(report: str, facts: dict[str, Any]) -> bool:
    if "跨境早报" not in report:
        return False
    urls = [str(item["url"]) for item in cast(list[dict[str, Any]], facts.get("items", []))]
    return all(url in report for url in urls)
