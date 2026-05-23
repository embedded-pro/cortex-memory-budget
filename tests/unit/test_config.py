"""Tests for config validation."""

from __future__ import annotations

import pytest

from cortex_memory_budget.config import validate_config
from cortex_memory_budget.models import ConfigError


def test_empty_config_is_valid() -> None:
    validate_config({})


@pytest.mark.parametrize(
    "bad",
    [
        {"cortex": "m99"},
        {"regions": "not-a-list"},
        {"regions": [{}]},
        {"regions": [{"name": "FLASH", "origin": "x", "length": 1}]},
        {"regions": [{"name": "RAM", "length": 0}]},
        {"stack_bytes": -1},
        {"heap_bytes": "big"},
        {"stack_size_symbols": "not a list"},
        {"top_n_symbols": 0},
        {"thresholds": "no"},
        {"thresholds": {"flash_pct": 0}},
        {"thresholds": {"ram_pct": 150}},
    ],
)
def test_invalid_configs_raise(bad: dict[str, object]) -> None:
    with pytest.raises(ConfigError):
        validate_config(bad)


def test_aggregates_multiple_errors() -> None:
    with pytest.raises(ConfigError) as excinfo:
        validate_config({"cortex": "m99", "stack_bytes": -1, "top_n_symbols": -2})
    message = str(excinfo.value)
    assert "cortex" in message
    assert "stack_bytes" in message
    assert "top_n_symbols" in message


def test_non_dict_rejected() -> None:
    with pytest.raises(ConfigError):
        validate_config([])  # type: ignore[arg-type]
