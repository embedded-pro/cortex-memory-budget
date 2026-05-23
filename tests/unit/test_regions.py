"""Tests for region merging and section assignment."""

from __future__ import annotations

from cortex_memory_budget.models import MemoryRegion, Section
from cortex_memory_budget.regions import assign_sections, merge_regions


def _section(name: str, size: int, vma: int, lma: int | None = None, flags: tuple[str, ...] = ("ALLOC",)) -> Section:
    return Section(name=name, size=size, vma=vma, lma=lma if lma is not None else vma, flags=frozenset(flags))


class TestMerge:
    def test_override_wins_for_same_name(self) -> None:
        detected = [MemoryRegion(name="FLASH", origin=0, length=1024)]
        overrides = [{"name": "FLASH", "origin": 0x08000000, "length": 2048}]
        merged, warnings = merge_regions(detected, overrides)
        assert warnings == []
        assert len(merged) == 1
        assert merged[0].origin == 0x08000000 and merged[0].length == 2048

    def test_override_appends_new_region(self) -> None:
        detected = [MemoryRegion(name="FLASH", origin=0x08000000, length=1024)]
        overrides = [{"name": "DTCM", "origin": 0x20000000, "length": 0x10000, "attrs": "rw"}]
        merged, _ = merge_regions(detected, overrides)
        assert {r.name for r in merged} == {"FLASH", "DTCM"}

    def test_invalid_override_warns(self) -> None:
        _, warnings = merge_regions(
            [],
            [
                {"origin": 0, "length": 1024},                # missing name
                {"name": "BAD", "origin": "x", "length": 1},  # bad types
                {"name": "ZERO", "origin": 0, "length": 0},   # non-positive length
            ],
        )
        assert len(warnings) == 3


class TestAssignSections:
    def test_data_is_counted_in_both_flash_and_ram(self) -> None:
        regions = [
            MemoryRegion(name="FLASH", origin=0x08000000, length=0x100000, attrs="rx"),
            MemoryRegion(name="RAM", origin=0x20000000, length=0x10000, attrs="rw"),
        ]
        sections = [
            _section(".text", size=0x400, vma=0x08000000, flags=("ALLOC", "READONLY", "CODE")),
            _section(".data", size=0x80, vma=0x20000000, lma=0x08000400),
            _section(".bss", size=0x200, vma=0x20000080),
        ]
        usages, warnings = assign_sections(regions, sections)
        assert warnings == []
        flash = next(u for u in usages if u.region.name == "FLASH")
        ram = next(u for u in usages if u.region.name == "RAM")
        assert flash.used_by["flash"] == 0x400
        assert flash.used_by["ram_init"] == 0x80
        assert ram.used_by["ram_static"] == 0x80 + 0x200

    def test_section_outside_any_region_warns(self) -> None:
        regions = [MemoryRegion(name="FLASH", origin=0x08000000, length=0x1000)]
        sections = [_section(".text", size=0x100, vma=0x90000000, flags=("ALLOC", "READONLY", "CODE"))]
        _, warnings = assign_sections(regions, sections)
        assert any("does not fit" in w for w in warnings)

    def test_skips_zero_size_and_non_alloc(self) -> None:
        regions = [MemoryRegion(name="FLASH", origin=0, length=0x1000)]
        sections = [
            _section(".empty", size=0, vma=0, flags=("ALLOC", "READONLY")),
            _section(".comment", size=100, vma=0, flags=()),
        ]
        usages, warnings = assign_sections(regions, sections)
        assert warnings == []
        assert usages[0].used_bytes == 0
