"""Blacklist filter for non-chat models."""

from __future__ import annotations

from .categorize import NON_CHAT_CATEGORIES


def build_blacklist(
    categories: dict[str, str],
    enabled_categories: set[str],
) -> list[tuple[str, str]]:
    """Return (model_id, category) pairs for the provider blacklist.

    Only models whose category is in NON_CHAT_CATEGORIES and is NOT in
    enabled_categories are included. Entries are grouped by category (in a
    stable order) so that the JSONC comment per group is meaningful, and
    sorted by model ID within each group.
    """
    # Stable category ordering for readable output.
    category_order = [
        "embedding",
        "audio_speech",
        "transcription",
        "image_generation",
        "video_generation",
        "ocr",
        "ranking",
        "router",
    ]

    # Group disabled non-chat model IDs by category.
    by_category: dict[str, list[str]] = {c: [] for c in category_order}
    for model_id, category in categories.items():
        if category in NON_CHAT_CATEGORIES and category not in enabled_categories:
            by_category.setdefault(category, []).append(model_id)

    result: list[tuple[str, str]] = []
    for category in category_order:
        for model_id in sorted(by_category.get(category, [])):
            result.append((model_id, category))
    return result
