"""JSON configuration validation."""

from __future__ import annotations

from typing import Any

from .models import ConfigError

SUPPORTED_CORTEX: frozenset[str] = frozenset({"m0", "m4", "m7", "m33"})


def _err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def validate_config(config: dict[str, Any]) -> None:
    """Validate a memory-analysis config dict; raise aggregated ``ConfigError``."""
    if not isinstance(config, dict):
        raise ConfigError("config must be a JSON object")
    errors: list[str] = []

    cortex = config.get("cortex")
    if cortex is not None and cortex not in SUPPORTED_CORTEX:
        _err(errors, f"cortex {cortex!r} is not supported (allowed: {sorted(SUPPORTED_CORTEX)})")

    regions = config.get("regions", [])
    if not isinstance(regions, list):
        _err(errors, "regions must be a list")
    else:
        for i, region in enumerate(regions):
            if not isinstance(region, dict):
                _err(errors, f"regions[{i}] must be an object")
                continue
            if "name" not in region or not str(region["name"]).strip():
                _err(errors, f"regions[{i}].name is required")
            for key in ("origin", "length"):
                if key in region and not isinstance(region[key], int):
                    _err(errors, f"regions[{i}].{key} must be an integer")
            if region.get("length", 1) <= 0:
                _err(errors, f"regions[{i}].length must be positive")

    for key in ("stack_bytes", "heap_bytes"):
        if key in config and (not isinstance(config[key], int) or config[key] < 0):
            _err(errors, f"{key} must be a non-negative integer")

    for key in ("stack_size_symbols", "heap_size_symbols"):
        if key in config and not (
            isinstance(config[key], list) and all(isinstance(s, str) for s in config[key])
        ):
            _err(errors, f"{key} must be a list of strings")

    top_n = config.get("top_n_symbols")
    if top_n is not None and (not isinstance(top_n, int) or top_n <= 0):
        _err(errors, "top_n_symbols must be a positive integer")

    thresholds = config.get("thresholds", {})
    if not isinstance(thresholds, dict):
        _err(errors, "thresholds must be an object")
    else:
        for key in ("flash_pct", "ram_pct"):
            if key in thresholds:
                value = thresholds[key]
                if not isinstance(value, int | float) or not (0 < float(value) <= 100):
                    _err(errors, f"thresholds.{key} must be a number in (0, 100]")

    if errors:
        raise ConfigError("invalid configuration:\n  - " + "\n  - ".join(errors))
