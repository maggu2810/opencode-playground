#!/usr/bin/env python3
"""Generate opencode.jsonc config from LiteLLM proxy endpoints."""

import argparse
import json
import sys
from typing import Any

import httpx


def fetch_model_hub(base_url: str, timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch public model hub (no auth required)."""
    url = f"{base_url.rstrip('/')}/public/model_hub"
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except httpx.HTTPError as e:
        print(f"Warning: Failed to fetch /public/model_hub: {e}", file=sys.stderr)
        return []


def fetch_model_info(base_url: str, bearer: str, timeout: float = 60.0) -> dict[str, dict[str, Any]]:
    """Fetch detailed model info from /v1/model/info (auth required)."""
    url = f"{base_url.rstrip('/')}/v1/model/info"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {bearer}"},
            timeout=timeout
        )
        response.raise_for_status()
        data = response.json()
        model_info = {}
        for item in data.get("data", []):
            model_info[item.get("key", item.get("model_name", ""))] = item.get("model_info", {})
        return model_info
    except httpx.HTTPError as e:
        print(f"Warning: Failed to fetch /v1/model/info: {e}", file=sys.stderr)
        return {}


def map_capabilities(model: dict[str, Any], detailed_info: dict[str, Any]) -> dict[str, bool]:
    """Map LiteLLM capabilities to OpenCode format."""
    capabilities = {
        "temperature": True,
        "reasoning": model.get("supports_reasoning", False),
        "attachment": True,
        "toolcall": model.get("supports_function_calling", False) or model.get("supports_parallel_function_calling", False),
        "input": {
            "text": True,
            "audio": detailed_info.get("supports_audio_input", False),
            "image": model.get("supports_vision", False),
            "video": False,
            "pdf": detailed_info.get("supports_pdf_input", False),
        },
        "output": {
            "text": True,
            "audio": detailed_info.get("supports_audio_output", False),
            "image": False,
            "video": False,
            "pdf": False,
        },
        "interleaved": False,
    }
    return capabilities


def map_modalities(capabilities: dict[str, Any]) -> dict[str, list[str]]:
    """Map capabilities to modalities."""
    input_mods = []
    output_mods = []

    if capabilities.get("input", {}).get("text"):
        input_mods.append("text")
    if capabilities.get("input", {}).get("audio"):
        input_mods.append("audio")
    if capabilities.get("input", {}).get("image"):
        input_mods.append("image")
    if capabilities.get("input", {}).get("video"):
        input_mods.append("video")
    if capabilities.get("input", {}).get("pdf"):
        input_mods.append("pdf")

    if capabilities.get("output", {}).get("text"):
        output_mods.append("text")
    if capabilities.get("output", {}).get("audio"):
        output_mods.append("audio")
    if capabilities.get("output", {}).get("image"):
        output_mods.append("image")
    if capabilities.get("output", {}).get("video"):
        output_mods.append("video")
    if capabilities.get("output", {}).get("pdf"):
        output_mods.append("pdf")

    return {"input": input_mods, "output": output_mods}


def map_cost(model: dict[str, Any], detailed_info: dict[str, Any]) -> dict[str, Any]:
    """Map LiteLLM costs to OpenCode format."""
    cost = {
        "input": model.get("input_cost_per_token", 0) or 0,
        "output": model.get("output_cost_per_token", 0) or 0,
    }

    cache_read = (
        detailed_info.get("cache_read_input_token_cost")
        or model.get("cache_read_input_token_cost")
    )
    cache_write = (
        detailed_info.get("cache_creation_input_token_cost")
        or model.get("cache_creation_input_token_cost")
    )

    if cache_read is not None or cache_write is not None:
        cost["cache"] = {
            "read": cache_read if cache_read is not None else 0,
            "write": cache_write if cache_write is not None else 0,
        }

    input_above_128k = (
        detailed_info.get("input_cost_per_token_above_128k_tokens")
        or model.get("input_cost_per_token_above_128k_tokens")
    )
    output_above_128k = (
        detailed_info.get("output_cost_per_token_above_128k_tokens")
        or model.get("output_cost_per_token_above_128k_tokens")
    )

    if input_above_128k is not None or output_above_128k is not None:
        cost["context_over_200k"] = {
            "input": input_above_128k if input_above_128k is not None else 0,
            "output": output_above_128k if output_above_128k is not None else 0,
        }

    return cost


def map_limits(model: dict[str, Any], detailed_info: dict[str, Any]) -> dict[str, Any]:
    """Map LiteLLM limits to OpenCode format."""
    limits = {}

    max_context = (
        detailed_info.get("max_input_tokens")
        or model.get("max_input_tokens")
    )
    if max_context is not None:
        limits["context"] = int(max_context)
        limits["input"] = int(max_context)

    max_output = (
        detailed_info.get("max_output_tokens")
        or detailed_info.get("max_tokens")
        or model.get("max_output_tokens")
        or model.get("max_tokens")
    )
    if max_output is not None:
        limits["output"] = int(max_output)

    return limits


def generate_config(
    base_url: str,
    model_hub_data: list[dict[str, Any]],
    model_info_data: dict[str, dict[str, Any]],
    provider_name: str = "LiteLLM",
    provider_key: str = "litellm",
) -> dict[str, Any]:
    """Generate opencode.jsonc config from LiteLLM data."""
    models = {}

    for model in model_hub_data:
        model_id = model.get("model_group", "")
        if not model_id:
            continue

        detailed_info = model_info_data.get(model_id, {})

        capabilities = map_capabilities(model, detailed_info)
        modalities = map_modalities(capabilities)
        cost = map_cost(model, detailed_info)
        limits = map_limits(model, detailed_info)

        models[model_id] = {
            "id": model_id,
            "name": model_id,
            "capabilities": capabilities,
            "cost": cost,
            "limit": limits,
            "modalities": modalities,
        }

    config = {
        "providers": {
            provider_key: {
                "npm": "@ai-sdk/openai-compatible",
                "name": provider_name,
                "options": {
                    "baseURL": f"{base_url.rstrip('/')}/v1",
                    "apiKey": "",
                    "litellmProxy": True,
                },
                "models": models,
            }
        }
    }

    return config


def output_jsonc(data: dict[str, Any]) -> str:
    """Output config as JSONC (JSON with minimal formatting)."""
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Generate opencode.jsonc config from LiteLLM proxy endpoints"
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="LiteLLM proxy base URL (e.g., https://litellm.example.com)",
    )
    parser.add_argument(
        "--bearer",
        help="Bearer token for authenticated endpoints (optional)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--provider-name",
        default="LiteLLM",
        help="Display name for the provider (default: LiteLLM)",
    )
    parser.add_argument(
        "--provider-key",
        default="litellm",
        help="Provider key in config (default: litellm)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30)",
    )

    args = parser.parse_args()

    model_hub = fetch_model_hub(args.base_url, args.timeout)
    model_info = fetch_model_info(args.base_url, args.bearer, args.timeout) if args.bearer else {}

    config = generate_config(
        args.base_url,
        model_hub,
        model_info,
        args.provider_name,
        args.provider_key,
    )

    output = output_jsonc(config)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()