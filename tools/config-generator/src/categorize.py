"""Category detection for LiteLLM models.

Determines the category (chat, embedding, audio_speech, etc.) for a model
based on its API 'mode' field or name heuristics.
"""

from __future__ import annotations

# Non-chat categories — models in these categories are commented out by
# default. Each can be re-enabled with its own --enable-* flag.
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
CATEGORY_LABEL: dict[str, str] = {
    "embedding":        "embedding",
    "audio_speech":     "audio speech (TTS)",
    "transcription":    "audio transcription (STT)",
    "image_generation": "image generation",
    "video_generation": "video generation",
    "ocr":              "document / OCR",
    "ranking":          "reranking",
    "router":           "router",
}


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
