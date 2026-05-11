"""HTTP fetchers for LiteLLM proxy endpoints."""

from __future__ import annotations

import sys
from typing import Any

import httpx


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
            if key:
                result[key] = item.get("model_info", {})
        return result
    except httpx.HTTPError as e:
        print(f"Warning: Failed to fetch /v1/model/info: {e}", file=sys.stderr)
        return {}
