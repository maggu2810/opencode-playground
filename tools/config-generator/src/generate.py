#!/usr/bin/env python3
"""Generate opencode.jsonc config from LiteLLM proxy endpoints.

Two endpoints are used:
  /public/model_hub       — flat list, no auth required, always queried.
  /v1/model/info          — nested model_info sub-object, auth required,
                            queried only when --bearer is supplied. Provides
                            audio/pdf capability flags and cache/extended-
                            context cost fields that the public hub lacks.

The generated config follows the OpenCode ConfigProvider / ModelConfig schema
as defined in packages/opencode/src/config/provider.ts (dev branch).

Usage
-----
    python src/generate.py --base-url https://litellm.example.com \\
        [--bearer TOKEN] [--output opencode.jsonc] \\
        [--provider-name "My LiteLLM"] [--provider-key litellm] \\
        [--enable-embedding] [--enable-audio-speech] \\
        [--enable-transcription] [--enable-image-generation] \\
        [--enable-video-generation] [--enable-ocr] [--enable-ranking] \\
        [--enable-all]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

import httpx


# ---------------------------------------------------------------------------
# Non-chat categories — models in these categories are commented out by
# default. Each can be re-enabled with its own --enable-* flag.
# ---------------------------------------------------------------------------

NON_CHAT_CATEGORIES: frozenset[str] = frozenset({
    "embedding",
    "audio_speech",
    "transcription",
    "image_generation",
    "video_generation",
    "ocr",
    "ranking",
    "router",
})

# Human-readable labels used in JSONC comments.
_CATEGORY_LABEL: dict[str, str] = {
    "embedding":        "embedding",
    "audio_speech":     "audio speech (TTS)",
    "transcription":    "audio transcription (STT)",
    "image_generation": "image generation",
    "video_generation": "video generation",
    "ocr":              "document / OCR",
    "ranking":          "reranking",
    "router":           "router",
}


# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

def _mode_to_category(mode: str) -> str | None:
    """Convert a LiteLLM 'mode' field to a category string.

    Returns None for chat / unknown so the caller falls back to name
    heuristics via categorize_model().
    """
    mapping: dict[str, str] = {
        "embedding":            "embedding",
        "audio_speech":         "audio_speech",
        "audio_transcription":  "transcription",
        "image_generation":     "image_generation",
        "video_generation":     "video_generation",
        "rerank":               "ranking",
        "moderations":          "router",
    }
    return mapping.get(mode)


def categorize_model(name: str, mode: str = "") -> str:
    """Return the category for a model, preferring the API 'mode' field."""
    from_mode = _mode_to_category(mode)
    if from_mode:
        return from_mode
    n = name.lower()
    if "embedding" in n:
        return "embedding"
    if "tts" in n or "chirp" in n:
        return "audio_speech"
    if "transcribe" in n or "whisper" in n:
        return "transcription"
    if "image" in n or "dall-e" in n or "stable-diffusion" in n:
        return "image_generation"
    if "veo" in n or "video" in n:
        return "video_generation"
    if "doc-intel" in n or "ocr" in n:
        return "ocr"
    if "ranker" in n or "rerank" in n:
        return "ranking"
    if "router" in n:
        return "router"
    return "chat"


# ---------------------------------------------------------------------------
# HTTP fetchers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Field mapping helpers
# ---------------------------------------------------------------------------

def _get_first(*sources: tuple[dict[str, Any], str]) -> Any:
    """Return the first non-None value from (dict, key) pairs."""
    for d, k in sources:
        v = d.get(k)
        if v is not None:
            return v
    return None


def map_flags(hub: dict[str, Any], info: dict[str, Any]) -> dict[str, bool]:
    """Map LiteLLM capability flags to flat OpenCode ModelConfig boolean fields.

    OpenCode ModelConfig fields (provider.ts):
        tool_call   — supports_function_calling / supports_parallel_function_calling
        attachment  — supports_vision (image input)
        reasoning   — supports_reasoning
        temperature — no LiteLLM source; True for all chat models

    'interleaved' is intentionally omitted: the schema only accepts `true` (not
    false) and there is no reliable LiteLLM source for it.
    """
    tool_call = bool(
        hub.get("supports_function_calling")
        or hub.get("supports_parallel_function_calling")
        or info.get("supports_function_calling")
    )
    attachment = bool(hub.get("supports_vision") or info.get("supports_vision"))
    reasoning = bool(hub.get("supports_reasoning") or info.get("supports_reasoning"))
    return {
        "tool_call": tool_call,
        "attachment": attachment,
        "reasoning": reasoning,
        "temperature": True,  # all chat-capable models support temperature
    }


def map_modalities(hub: dict[str, Any], info: dict[str, Any]) -> dict[str, list[str]]:
    """Build modalities.{input,output} arrays from LiteLLM capability flags.

    Input modalities:
        text   — always present for chat models
        image  — supports_vision  (hub or info)
        audio  — supports_audio_input  (info only)
        pdf    — supports_pdf_input    (info only)
        video  — no LiteLLM source; omitted

    Output modalities:
        text   — always present
        audio  — supports_audio_output (info only)
        image/video/pdf — no LiteLLM source; omitted
    """
    inputs: list[str] = ["text"]
    outputs: list[str] = ["text"]

    if hub.get("supports_vision") or info.get("supports_vision"):
        inputs.append("image")
    if info.get("supports_audio_input"):
        inputs.append("audio")
    if info.get("supports_pdf_input"):
        inputs.append("pdf")

    if info.get("supports_audio_output"):
        outputs.append("audio")

    return {"input": inputs, "output": outputs}


def map_cost(hub: dict[str, Any], info: dict[str, Any]) -> dict[str, Any] | None:
    """Map LiteLLM cost fields to OpenCode ModelConfig cost struct.

    OpenCode requires both cost.input and cost.output; if either is missing
    from both sources, the whole cost block is omitted.

    Schema (provider.ts L22-36):
        cost.input          number   required
        cost.output         number   required
        cost.cache_read     number?  optional
        cost.cache_write    number?  optional
        cost.context_over_200k.input    number   (required inside the sub-struct)
        cost.context_over_200k.output   number   (required inside the sub-struct)
        cost.context_over_200k.cache_read  number?
        cost.context_over_200k.cache_write number?
    """
    input_cost = _get_first((info, "input_cost_per_token"), (hub, "input_cost_per_token"))
    output_cost = _get_first((info, "output_cost_per_token"), (hub, "output_cost_per_token"))

    if input_cost is None or output_cost is None:
        return None

    cost: dict[str, Any] = {
        "input": input_cost,
        "output": output_cost,
    }

    # Optional cache costs — only available from /v1/model/info.
    cache_read = _get_first(
        (info, "cache_read_input_token_cost"),
        (hub, "cache_read_input_token_cost"),
    )
    cache_write = _get_first(
        (info, "cache_creation_input_token_cost"),
        (hub, "cache_creation_input_token_cost"),
    )
    if cache_read is not None:
        cost["cache_read"] = cache_read
    if cache_write is not None:
        cost["cache_write"] = cache_write

    # Extended context cost tier.
    # LiteLLM uses "above_128k" in /v1/model/info and "above_200k" in
    # /public/model_hub (KION-specific). Check both field names.
    input_over = _get_first(
        (info, "input_cost_per_token_above_128k_tokens"),
        (hub, "input_cost_per_token_above_200k_tokens"),
        (hub, "input_cost_per_token_above_128k_tokens"),
    )
    output_over = _get_first(
        (info, "output_cost_per_token_above_128k_tokens"),
        (hub, "output_cost_per_token_above_200k_tokens"),
        (hub, "output_cost_per_token_above_128k_tokens"),
    )
    if input_over is not None and output_over is not None:
        cost["context_over_200k"] = {
            "input": input_over,
            "output": output_over,
        }

    return cost


def map_limit(hub: dict[str, Any], info: dict[str, Any]) -> dict[str, Any] | None:
    """Map LiteLLM token limits to OpenCode ModelConfig limit struct.

    OpenCode requires both limit.context and limit.output; if either is
    absent from both sources, the whole limit block is omitted.

    Schema (provider.ts L38-44):
        limit.context   number   required
        limit.input     number?  optional (set to same value as context)
        limit.output    number   required
    """
    max_context = _get_first(
        (info, "max_input_tokens"),
        (hub, "max_input_tokens"),
    )
    max_output = _get_first(
        (info, "max_output_tokens"),
        (info, "max_tokens"),
        (hub, "max_output_tokens"),
        (hub, "max_tokens"),
    )

    if max_context is None or max_output is None:
        return None

    return {
        "context": int(max_context),
        "input": int(max_context),
        "output": int(max_output),
    }


# ---------------------------------------------------------------------------
# Model entry builder
# ---------------------------------------------------------------------------

def build_model_entry(
    hub: dict[str, Any],
    info: dict[str, Any],
    category: str,
) -> dict[str, Any]:
    """Build the full ModelConfig dict for one model.

    Only fields with actual data are included; empty / False values are
    omitted so the config stays minimal and readable.
    """
    model_id: str = hub["model_group"]
    model: dict[str, Any] = {
        "id": model_id,
        "name": model_id,
    }

    # Flat capability flags (all optional; omit when False to keep config clean).
    flags = map_flags(hub, info)
    for key, value in flags.items():
        if value:
            model[key] = value

    # Modalities (always populated — at minimum ["text"] for both).
    model["modalities"] = map_modalities(hub, info)

    # Cost block (omit entirely if input or output cost is unknown).
    cost = map_cost(hub, info)
    if cost is not None:
        model["cost"] = cost

    # Limit block (omit entirely if context or output limit is unknown).
    limit = map_limit(hub, info)
    if limit is not None:
        model["limit"] = limit

    return model


# ---------------------------------------------------------------------------
# JSONC rendering
# ---------------------------------------------------------------------------

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


def _render_model(model: dict[str, Any], indent: str, trailing_comma: bool) -> list[str]:
    """Render one ModelConfig dict as indented JSONC lines."""
    model_id = model["id"]
    # Serialize the whole dict in one shot (floats already handled).
    value_json = _dumps_value({k: v for k, v in model.items()})
    trailer = "," if trailing_comma else ""
    return [f'{indent}"{model_id}": {value_json}{trailer}']


def render_jsonc(
    base_url: str,
    models_by_id: dict[str, dict[str, Any]],  # model_id → ModelConfig dict
    categories: dict[str, str],                # model_id → category string
    enabled_categories: set[str],
    provider_name: str,
    provider_key: str,
) -> str:
    """Render the full opencode.jsonc string for a single provider.

    Non-chat models whose category is not in enabled_categories are written
    as JSONC comment blocks (two-line style):
        // <category label> model — not typically used by opencode
        // "<id>": {...},
    """
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
    lines.append('      "models": {')

    model_ids = list(models_by_id.keys())
    for idx, model_id in enumerate(model_ids):
        model = models_by_id[model_id]
        category = categories[model_id]
        is_last = idx == len(model_ids) - 1
        # Last active model must not have a trailing comma; commented models
        # always get a comma in the comment text so the uncommented block
        # stays valid JSON.
        trailing_comma = not is_last

        if category in NON_CHAT_CATEGORIES and category not in enabled_categories:
            label = _CATEGORY_LABEL.get(category, category)
            lines.append(
                f"        // {label} model — not typically used by opencode"
            )
            value_json = _dumps_value({k: v for k, v in model.items()})
            lines.append(f'        // "{model_id}": {value_json},')
        else:
            value_json = _dumps_value({k: v for k, v in model.items()})
            trailer = "," if trailing_comma else ""
            lines.append(f'        "{model_id}": {value_json}{trailer}')

    lines.append("      }")
    lines.append("    }")
    lines.append("  }")
    lines.append("}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Top-level orchestration
# ---------------------------------------------------------------------------

def generate(
    base_url: str,
    bearer: str | None,
    provider_name: str,
    provider_key: str,
    enabled_categories: set[str],
    timeout: float,
) -> str:
    """Fetch data, build model entries, and render JSONC."""
    print("Fetching /public/model_hub …", file=sys.stderr)
    hub_list = fetch_model_hub(base_url, timeout)
    if not hub_list:
        print("Error: /public/model_hub returned no models.", file=sys.stderr)
        sys.exit(1)
    print(f"  {len(hub_list)} model groups received.", file=sys.stderr)

    info_map: dict[str, dict[str, Any]] = {}
    if bearer:
        print("Fetching /v1/model/info …", file=sys.stderr)
        info_map = fetch_model_info(base_url, bearer, timeout=max(timeout, 60.0))
        print(f"  {len(info_map)} detailed model entries received.", file=sys.stderr)

    models_by_id: dict[str, dict[str, Any]] = {}
    categories: dict[str, str] = {}

    for hub_entry in hub_list:
        model_id = hub_entry.get("model_group", "")
        if not model_id:
            continue
        info = info_map.get(model_id, {})
        category = categorize_model(model_id, hub_entry.get("mode", ""))
        categories[model_id] = category
        models_by_id[model_id] = build_model_entry(hub_entry, info, category)

    # Report category breakdown.
    chat_count = sum(1 for c in categories.values() if c == "chat")
    nonchat_count = len(categories) - chat_count
    print(
        f"  {len(models_by_id)} models mapped: {chat_count} chat, "
        f"{nonchat_count} non-chat.",
        file=sys.stderr,
    )
    disabled = [
        c for c in NON_CHAT_CATEGORIES if c not in enabled_categories
        and any(cat == c for cat in categories.values())
    ]
    if disabled:
        labels = ", ".join(_CATEGORY_LABEL.get(c, c) for c in sorted(disabled))
        print(
            f"  Non-chat models commented out: {labels}.\n"
            f"  Use --enable-<category> or --enable-all to activate them.",
            file=sys.stderr,
        )

    return render_jsonc(
        base_url=base_url,
        models_by_id=models_by_id,
        categories=categories,
        enabled_categories=enabled_categories,
        provider_name=provider_name,
        provider_key=provider_key,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate opencode.jsonc config from a LiteLLM proxy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--base-url",
        required=True,
        metavar="URL",
        help="LiteLLM proxy base URL (e.g. https://litellm.example.com)",
    )
    parser.add_argument(
        "--bearer",
        metavar="TOKEN",
        help=(
            "Bearer token for /v1/model/info (optional). "
            "Enables audio/pdf capability flags and cache cost fields."
        ),
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--provider-name",
        default="LiteLLM",
        metavar="NAME",
        help='Display name for the provider (default: "LiteLLM")',
    )
    parser.add_argument(
        "--provider-key",
        default="litellm",
        metavar="KEY",
        help='Provider key in config (default: "litellm")',
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="Request timeout for /public/model_hub in seconds (default: 30)",
    )

    # Per-category enable flags.
    cat_group = parser.add_argument_group(
        "non-chat model categories",
        "By default, non-chat models are written as JSONC comments. "
        "Use these flags to activate specific categories as live entries.",
    )
    cat_group.add_argument(
        "--enable-embedding", action="store_true",
        help="Enable embedding models",
    )
    cat_group.add_argument(
        "--enable-audio-speech", action="store_true",
        help="Enable text-to-speech (TTS) models",
    )
    cat_group.add_argument(
        "--enable-transcription", action="store_true",
        help="Enable speech-to-text (STT / transcription) models",
    )
    cat_group.add_argument(
        "--enable-image-generation", action="store_true",
        help="Enable image generation models",
    )
    cat_group.add_argument(
        "--enable-video-generation", action="store_true",
        help="Enable video generation models",
    )
    cat_group.add_argument(
        "--enable-ocr", action="store_true",
        help="Enable document / OCR models",
    )
    cat_group.add_argument(
        "--enable-ranking", action="store_true",
        help="Enable reranking models",
    )
    cat_group.add_argument(
        "--enable-all", action="store_true",
        help="Enable all non-chat model categories",
    )

    args = parser.parse_args()

    # Build the set of enabled non-chat categories.
    if args.enable_all:
        enabled_categories = set(NON_CHAT_CATEGORIES)
    else:
        enabled_categories: set[str] = set()
        if args.enable_embedding:        enabled_categories.add("embedding")
        if args.enable_audio_speech:     enabled_categories.add("audio_speech")
        if args.enable_transcription:    enabled_categories.add("transcription")
        if args.enable_image_generation: enabled_categories.add("image_generation")
        if args.enable_video_generation: enabled_categories.add("video_generation")
        if args.enable_ocr:              enabled_categories.add("ocr")
        if args.enable_ranking:          enabled_categories.add("ranking")

    output = generate(
        base_url=args.base_url,
        bearer=args.bearer,
        provider_name=args.provider_name,
        provider_key=args.provider_key,
        enabled_categories=enabled_categories,
        timeout=args.timeout,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nGenerated: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
