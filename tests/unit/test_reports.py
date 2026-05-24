"""Tests for report generators."""

from __future__ import annotations

import json

from cortex_memory_budget.diff import diff_reports
from cortex_memory_budget.models import (
    MemoryRegion,
    MemoryReport,
    RegionUsage,
    Section,
    StackHeapInfo,
    Symbol,
)
from cortex_memory_budget.reports import (
    PR_COMMENT_MARKER,
    generate_diff_report,
    generate_json_metrics,
    generate_main_report,
    generate_pr_comment,
)


def _make_report() -> MemoryReport:
    region = MemoryRegion(name="FLASH", origin=0x08000000, length=0x100000, attrs="rx")
    ram = MemoryRegion(name="RAM", origin=0x20000000, length=0x10000, attrs="rw")
    return MemoryReport(
        target="nucleo-h743zi",
        build_config="Release",
        cortex="m7",
        elf_path="firmware.elf",
        flash_bytes=10240,
        ram_static_bytes=4096,
        stack_heap=StackHeapInfo(stack_bytes=8192, heap_bytes=4096, stack_source="symbol:_Min_Stack_Size(size)", heap_source="symbol:_Min_Heap_Size(size)"),
        sections=[
            Section(name=".text", size=8000, vma=0x08000000, lma=0x08000000, flags=frozenset({"ALLOC", "READONLY", "CODE"})),
            Section(name=".rodata", size=2240, vma=0x08001f40, lma=0x08001f40, flags=frozenset({"ALLOC", "READONLY"})),
            Section(name=".bss", size=4096, vma=0x20000000, lma=0x20000000, flags=frozenset({"ALLOC"})),
        ],
        symbols=[
            Symbol(name="main", raw_name="main", address=0x08000200, size=512, type_char="T", section=".text", source_file="src/main.c"),
            Symbol(name="control_loop", raw_name="control_loop", address=0x08000400, size=1024, type_char="T", section=".text", source_file="src/foc.c"),
            Symbol(name="big_buffer", raw_name="big_buffer", address=0x20000100, size=2048, type_char="B", section=".bss", source_file="src/buffers.c"),
        ],
        regions=[
            RegionUsage(region=region, used_bytes=10240, used_by={"flash": 10240}),
            RegionUsage(region=ram, used_bytes=4096, used_by={"ram_static": 4096}),
        ],
        warnings=["section .foo did not fit any region"],
    )


class TestMainReport:
    def test_contains_all_sections(self) -> None:
        text = generate_main_report(_make_report())
        for header in (
            "# Memory Report",
            "## Totals",
            "## Region utilisation",
            "## Sections",
            "## Top symbols",
            "## Top source files",
            "## ⚠ Warnings",
        ):
            assert header in text

    def test_region_bar_absent(self) -> None:
        text = generate_main_report(_make_report())
        assert "█" not in text and "·" not in text


class TestPrComment:
    def test_starts_with_marker(self) -> None:
        text = generate_pr_comment(_make_report())
        assert text.startswith(PR_COMMENT_MARKER)

    def test_includes_totals_and_top_symbols(self) -> None:
        text = generate_pr_comment(_make_report())
        assert "flash" in text.lower()
        assert "big_buffer" in text

    def test_appends_diff_section_when_provided(self) -> None:
        cur = _make_report()
        baseline = _make_report()
        baseline.symbols[0] = Symbol(name="main", raw_name="main", address=0, size=400, type_char="T", section=".text")
        text = generate_pr_comment(cur, diff=diff_reports(baseline, cur))
        assert "Changes vs. baseline" in text


class TestDiffReport:
    def test_empty_diff(self) -> None:
        assert "No changes" in generate_diff_report([])

    def test_table_includes_status(self) -> None:
        cur = _make_report()
        baseline = _make_report()
        baseline.symbols[1] = Symbol(name="control_loop", raw_name="control_loop", address=0, size=800, type_char="T", section=".text")
        diff = diff_reports(baseline, cur)
        text = generate_diff_report(diff)
        assert "grew" in text or "shrunk" in text


class TestJsonMetrics:
    def test_round_trips_and_contains_keys(self) -> None:
        report = _make_report()
        payload = json.loads(generate_json_metrics(report))
        assert payload["target"] == "nucleo-h743zi"
        assert payload["cortex"] == "m7"
        assert payload["flash_bytes"] == 10240
        assert payload["ram_total_bytes"] == 4096 + 8192 + 4096
        assert payload["regions"][0]["name"] in {"FLASH", "RAM"}
        assert len(payload["top_symbols"]) >= 3

    def test_includes_diff_when_provided(self) -> None:
        cur = _make_report()
        baseline = _make_report()
        baseline.symbols[1] = Symbol(name="control_loop", raw_name="control_loop", address=0, size=600, type_char="T", section=".text")
        payload = json.loads(generate_json_metrics(cur, diff=diff_reports(baseline, cur)))
        assert "diff" in payload
        assert any(e["name"] == "control_loop" for e in payload["diff"])
