"""HTTP fetchers for LiteLLM proxy endpoints."""

from __future__ import annotations

import re
import sys
from typing import Any

import httpx

# Matches LiteLLM flags like "supports_low_reasoning_effort" -> "low".
_REASONING_EFFORT_FLAG = re.compile(r"^supports_([a-z]+)_reasoning_effort$")


def _extract_reasoning_efforts(*sources: dict[str, Any] | None) -> list[str]:
    """Derive the set of reasoning-effort levels a model supports by
    scanning `supports_<level>_reasoning_effort` boolean flags across
    `model_info` and `litellm_params`. LiteLLM does not report this as a
    single list field — each level is its own boolean flag.
    """
    efforts: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            match = _REASONING_EFFORT_FLAG.match(key)
            if match and value is True:
                efforts.add(match.group(1))
    return sorted(efforts)


def fetch_model_hub(base_url: str, timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch /public/model_hub — returns a plain list, no auth required."""
    url = f"{base_url.rstrip('/')}/public/model_hub"
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        # The endpoint returns a plain JSON array, not {"data": [...]}.
        if isinstance(data, list):
            return data
        # Defensive: some proxy versions may wrap in {"data": [...]}.
        if isinstance(data, dict):
            return data.get("data", [])
        return []
    except httpx.HTTPError as e:
        print(f"Warning: Failed to fetch /public/model_hub: {e}", file=sys.stderr)
        return []


def fetch_model_info(
    base_url: str, bearer: str, timeout: float = 60.0
) -> dict[str, dict[str, Any]]:
    """Fetch /v1/model/info (auth required).

    Returns a dict keyed by model alias (item["key"] or item["model_name"])
    whose values are the nested model_info sub-objects containing capability
    flags and extended cost fields.
    """
    url = f"{base_url.rstrip('/')}/v1/model/info"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        result: dict[str, dict[str, Any]] = {}
        for item in data.get("data", []):
            key = item.get("key") or item.get("model_name") or ""
            if not key:
                continue
            info = dict(item.get("model_info", {}))
            efforts = _extract_reasoning_efforts(info, item.get("litellm_params"))
            if efforts:
                info["supports_reasoning_efforts"] = efforts
            result[key] = info
        return result
    except httpx.HTTPError as e:
        print(f"Warning: Failed to fetch /v1/model/info: {e}", file=sys.stderr)
        return {}
