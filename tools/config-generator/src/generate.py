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
import sys
from typing import Any

from .build import build_model_entry
from .categorize import CATEGORY_LABEL, NON_CHAT_CATEGORIES, categorize_model
from .fetch import fetch_model_hub, fetch_model_info
from .render import render_jsonc


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
        labels = ", ".join(CATEGORY_LABEL.get(c, c) for c in sorted(disabled))
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
