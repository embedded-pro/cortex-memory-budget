"""Tests for section parsing and classification."""

from __future__ import annotations

import pytest

from cortex_memory_budget.models import Section
from cortex_memory_budget.sections import classify_section, parse_sections, summarise


def _section(name: str, size: int = 100, vma: int = 0, flags: tuple[str, ...] = ("ALLOC",)) -> Section:
    return Section(name=name, size=size, vma=vma, lma=vma, flags=frozenset(flags))


class TestClassify:
    @pytest.mark.parametrize(
        ("name", "flags", "expected"),
        [
            (".text", ("ALLOC", "READONLY", "CODE"), "flash"),
            (".text.foo", ("ALLOC", "READONLY", "CODE"), "flash"),
            (".rodata", ("ALLOC", "READONLY"), "flash"),
            (".isr_vector", ("ALLOC", "READONLY"), "flash"),
            (".ARM.exidx", ("ALLOC", "READONLY"), "flash"),
            (".data", ("ALLOC",), "ram_init"),
            (".data.foo", ("ALLOC",), "ram_init"),
            (".bss", ("ALLOC",), "ram_static"),
            (".bss.foo", ("ALLOC",), "ram_static"),
            (".noinit", ("ALLOC",), "ram_static"),
            (".stack", ("ALLOC",), "stack"),
            (".heap", ("ALLOC",), "heap"),
            (".debug_info", (), "debug"),
            (".comment", (), "debug"),
            (".ARM.attributes", (), "ignored"),
        ],
    )
    def test_classification(self, name: str, flags: tuple[str, ...], expected: str) -> None:
        assert classify_section(_section(name, flags=flags)) == expected

    def test_non_alloc_data_is_ignored(self) -> None:
        assert classify_section(_section(".data", flags=())) == "ignored"


class TestParseSections:
    def test_real_objdump_output(self) -> None:
        text = """build/firmware.elf:     file format elf32-littlearm

Sections:
Idx Name          Size      VMA       LMA       File off  Algn
  0 .isr_vector   00000188  08000000  08000000  00010000  2**0
                  CONTENTS, ALLOC, LOAD, READONLY, DATA
  1 .text         00001234  08000188  08000188  00010188  2**2
                  CONTENTS, ALLOC, LOAD, READONLY, CODE
  2 .data         00000100  20000000  080013bc  000113bc  2**2
                  CONTENTS, ALLOC, LOAD, DATA
  3 .bss          00000400  20000100  20000100  000114bc  2**2
                  ALLOC
  4 .debug_info   00001000  00000000  00000000  000114bc  2**0
                  CONTENTS, READONLY, DEBUGGING
"""
        sections = parse_sections(text)
        assert {s.name for s in sections} == {".isr_vector", ".text", ".data", ".bss", ".debug_info"}
        bss = next(s for s in sections if s.name == ".bss")
        assert bss.size == 0x400
        assert bss.is_alloc
        data = next(s for s in sections if s.name == ".data")
        assert data.lma == 0x080013BC and data.vma == 0x20000000

    def test_summarise(self) -> None:
        sections = [
            _section(".text", size=1000, flags=("ALLOC", "READONLY", "CODE")),
            _section(".rodata", size=200, flags=("ALLOC", "READONLY")),
            _section(".data", size=50, flags=("ALLOC",)),
            _section(".bss", size=400, flags=("ALLOC",)),
            _section(".debug_info", size=9999, flags=()),
        ]
        totals = summarise(sections)
        assert totals["flash"] == 1200
        assert totals["ram_init"] == 50
        assert totals["ram_static"] == 400
        assert totals["debug"] == 9999
