"""Tests for the nm symbol parser."""

from __future__ import annotations

from cortex_memory_budget.symbols import filter_largest, parse_symbols


def test_parse_basic_nm_output() -> None:
    text = """\
build/firmware.elf:08000200 00000040 T main
build/firmware.elf:08000240 00000080 t static_helper
build/firmware.elf:08000300 00000010 R version_string
build/firmware.elf:20000000 00000004 D global_counter
build/firmware.elf:20000100 00000200 B large_buffer
build/firmware.elf:20000400 00000100 C common_block
build/firmware.elf:00000800 A _Min_Stack_Size
"""
    syms = parse_symbols(text)
    by_name = {s.name: s for s in syms}
    assert by_name["main"].size == 0x40
    assert by_name["main"].section == ".text"
    assert by_name["large_buffer"].section == ".bss"
    assert by_name["common_block"].section == ".bss"
    assert by_name["version_string"].section == ".rodata"
    assert by_name["global_counter"].section == ".data"
    # Linker-script ABS symbols are retained (no size column) so stack/heap
    # auto-detect can find them.
    assert by_name["_Min_Stack_Size"].size == 0
    assert by_name["_Min_Stack_Size"].address == 0x800


def test_filter_largest_orders_desc() -> None:
    text = """\
20000000 00000010 B small
20000100 00000200 B medium
20000300 00001000 B big
"""
    top = filter_largest(parse_symbols(text), top_n=2)
    assert [s.name for s in top] == ["big", "medium"]


def test_handles_size_less_entries() -> None:
    text = """\
20000000 D undef_size_symbol
20000100 00000080 D ok_symbol
"""
    syms = parse_symbols(text)
    names = {s.name for s in syms}
    assert "ok_symbol" in names and "undef_size_symbol" in names
    assert next(s for s in syms if s.name == "ok_symbol").size == 0x80
    assert next(s for s in syms if s.name == "undef_size_symbol").size == 0
