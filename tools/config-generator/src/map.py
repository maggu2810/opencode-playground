"""Field mapping helpers for LiteLLM to OpenCode ModelConfig translation."""

from __future__ import annotations

from typing import Any


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
    # /public/model_hub. Check both field names.
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
