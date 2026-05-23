"""Tests for the single-mode CLI parsing (no real ELF needed)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cortex_memory_budget import cli_single
from cortex_memory_budget.models import MemoryReport, StackHeapInfo


def test_build_parser_has_required_flags() -> None:
    parser = cli_single.build_parser()
    help_text = parser.format_help()
    for flag in ("--elf", "--target", "--build-config", "--cortex", "--output-dir", "--baseline-elf", "--linker-script"):
        assert flag in help_text


def test_main_invalid_json_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json")
    rc = cli_single.main([
        str(bad), "--elf", "x", "--target", "t", "--build-config", "B", "--cortex", "m4",
    ])
    assert rc == 1
    assert "ERROR" in capsys.readouterr().err


def test_main_invalid_config_returns_1(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"cortex": "m99"}))
    rc = cli_single.main([
        str(bad), "--elf", "x", "--target", "t", "--build-config", "B",
    ])
    assert rc == 1


def test_main_runs_writes_outputs(tmp_path: Path) -> None:
    config = tmp_path / "c.json"
    config.write_text("{}")
    out_dir = tmp_path / "out"
    fake = MemoryReport(
        target="t", build_config="B", cortex="m4", elf_path="x",
        flash_bytes=100, ram_static_bytes=50, stack_heap=StackHeapInfo(stack_bytes=10, heap_bytes=5),
    )

    with patch("cortex_memory_budget.cli_single.analyze", return_value=fake):
        rc = cli_single.main([
            str(config), "--elf", "x", "--target", "t", "--build-config", "B",
            "--cortex", "m4", "--output-dir", str(out_dir),
        ])
    assert rc == 0
    assert (out_dir / "memory_report.md").exists()
    assert (out_dir / "pr_comment.md").exists()
    assert (out_dir / "memory_metrics.json").exists()
