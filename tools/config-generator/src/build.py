"""Model entry builder for OpenCode ModelConfig."""

from __future__ import annotations

from typing import Any

from .map import map_cost, map_flags, map_limit, map_modalities


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
