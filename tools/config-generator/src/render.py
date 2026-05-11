"""JSONC rendering for OpenCode config output."""

from __future__ import annotations

import json
import re
from typing import Any

from .categorize import CATEGORY_LABEL
from .filter import build_blacklist


def _format_float(value: float) -> str:
    """Render a float without scientific notation, trimming trailing zeros.

    Per-token costs (e.g. 3e-8) would appear in scientific notation in
    json.dumps output. While OpenCode's JSONC parser accepts scientific
    notation, decimal form is more human-readable in a shared config file.
    """
    formatted = f"{value:.10f}".rstrip("0")
    if formatted.endswith("."):
        formatted += "0"
    return formatted


def _dumps_value(value: Any) -> str:
    """Serialize a value to a JSON string, rendering floats as decimals."""
    raw = json.dumps(value)
    # Replace scientific notation numbers produced by json.dumps.
    return re.sub(
        r"-?\d+(?:\.\d+)?[eE][+-]?\d+",
        lambda m: _format_float(float(m.group(0))),
        raw,
    )


def render_jsonc(
    base_url: str,
    models_by_id: dict[str, dict[str, Any]],  # model_id → ModelConfig dict
    categories: dict[str, str],                # model_id → category string
    enabled_categories: set[str],
    provider_name: str,
    provider_key: str,
) -> str:
    """Render the full opencode.jsonc string for a single provider.

    All models (chat and non-chat) are written as active entries in the
    "models" block so their metadata (cost, limits, capabilities) is
    preserved and visible.

    Non-chat models whose category is not in enabled_categories are added to
    the provider-level "blacklist" array, which causes OpenCode to hide them
    from the model picker while keeping the data intact.  Each group of
    blacklisted models is preceded by a JSONC comment explaining why:

        "blacklist": [
          // embedding model — not used by opencode
          "text-embedding-ada-002",
          "text-embedding-3-large",
          // image generation model — not used by opencode
          "dall-e-3"
        ],

    When --enable-all is passed, enabled_categories == NON_CHAT_CATEGORIES
    and the blacklist is omitted entirely.
    """
    blacklist = build_blacklist(categories, enabled_categories)

    lines: list[str] = []
    lines.append("{")
    lines.append('  "$schema": "https://opencode.ai/config.json",')
    lines.append('  "provider": {')
    lines.append(f'    "{provider_key}": {{')
    lines.append('      "npm": "@ai-sdk/openai-compatible",')
    lines.append(f'      "name": "{provider_name}",')
    lines.append('      "options": {')
    lines.append(f'        "baseURL": "{base_url.rstrip("/")}/v1",')
    lines.append('        "litellmProxy": true')
    lines.append("      },")

    # Blacklist block — omitted when every non-chat category is enabled.
    if blacklist:
        lines.append('      "blacklist": [')
        prev_category: str | None = None
        for idx, (model_id, category) in enumerate(blacklist):
            is_last = idx == len(blacklist) - 1
            trailer = "" if is_last else ","
            if category != prev_category:
                label = CATEGORY_LABEL.get(category, category)
                lines.append(
                    f"        // {label} model — not used by opencode"
                )
                prev_category = category
            lines.append(f'        "{model_id}"{trailer}')
        lines.append("      ],")

    # Models block — all models, always active.
    lines.append('      "models": {')
    model_ids = list(models_by_id.keys())
    for idx, model_id in enumerate(model_ids):
        model = models_by_id[model_id]
        is_last = idx == len(model_ids) - 1
        trailer = "" if is_last else ","
        value_json = _dumps_value({k: v for k, v in model.items()})
        lines.append(f'        "{model_id}": {value_json}{trailer}')

    lines.append("      }")
    lines.append("    }")
    lines.append("  }")
    lines.append("}")

    return "\n".join(lines)
