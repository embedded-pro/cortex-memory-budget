"""Tests for diff_reports."""

from __future__ import annotations

from cortex_memory_budget.diff import diff_reports
from cortex_memory_budget.models import (
    MemoryRegion,
    MemoryReport,
    RegionUsage,
    Section,
    Symbol,
)


def _sym(name: str, size: int, section: str = ".text") -> Symbol:
    return Symbol(name=name, raw_name=name, address=0, size=size, type_char="T", section=section)


def _report(
    *,
    symbols: list[Symbol] | None = None,
    sections: list[Section] | None = None,
    regions: list[RegionUsage] | None = None,
) -> MemoryReport:
    return MemoryReport(
        target="t",
        build_config="Release",
        cortex="m4",
        elf_path="x",
        symbols=symbols or [],
        sections=sections or [],
        regions=regions or [],
    )


def test_added_removed_grew_shrunk_classified() -> None:
    base = _report(symbols=[_sym("a", 100), _sym("b", 50), _sym("c", 25)])
    cur = _report(symbols=[_sym("a", 80), _sym("b", 50), _sym("d", 75)])
    diff = diff_reports(base, cur)
    by_name = {(e.kind, e.name): e for e in diff}
    assert by_name[("symbol", "a")].status == "shrunk"
    assert by_name[("symbol", "c")].status == "removed"
    assert by_name[("symbol", "d")].status == "added"
    assert ("symbol", "b") not in by_name


def test_section_diff_only_includes_changes() -> None:
    base_sec = [Section(name=".text", size=100, vma=0, lma=0, flags=frozenset({"ALLOC"}))]
    cur_sec = [Section(name=".text", size=120, vma=0, lma=0, flags=frozenset({"ALLOC"}))]
    diff = diff_reports(_report(sections=base_sec), _report(sections=cur_sec))
    entry = next(e for e in diff if e.kind == "section")
    assert entry.delta_bytes == 20
    assert entry.status == "grew"


def test_region_diff_present() -> None:
    region = MemoryRegion(name="FLASH", origin=0, length=1024)
    base = _report(regions=[RegionUsage(region=region, used_bytes=100)])
    cur = _report(regions=[RegionUsage(region=region, used_bytes=200)])
    diff = diff_reports(base, cur)
    entry = next(e for e in diff if e.kind == "region")
    assert entry.delta_bytes == 100


def test_diff_sorted_by_magnitude_descending() -> None:
    base = _report(symbols=[_sym("a", 0), _sym("b", 0), _sym("c", 0)])
    cur = _report(symbols=[_sym("a", 10), _sym("b", 1000), _sym("c", 100)])
    diff = diff_reports(base, cur)
    sym_entries = [e for e in diff if e.kind == "symbol"]
    assert [e.name for e in sym_entries] == ["b", "c", "a"]
