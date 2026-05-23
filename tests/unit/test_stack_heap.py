"""Tests for stack/heap auto-detection."""

from __future__ import annotations

from cortex_memory_budget.models import Section, Symbol
from cortex_memory_budget.stack_heap import detect_stack_heap


def _sym(name: str, size: int = 0, addr: int = 0, type_char: str = "A") -> Symbol:
    return Symbol(name=name, raw_name=name, address=addr, size=size, type_char=type_char)


def _section(name: str, size: int, flags: tuple[str, ...] = ("ALLOC",)) -> Section:
    return Section(name=name, size=size, vma=0, lma=0, flags=frozenset(flags))


class TestDetectStackHeap:
    def test_config_overrides_everything(self) -> None:
        info = detect_stack_heap(
            symbols=[_sym("_Min_Stack_Size", size=0x2000)],
            sections=[_section(".heap", 0x1000)],
            config={"stack_bytes": 4096, "heap_bytes": 0},
        )
        assert info.stack_bytes == 4096
        assert info.stack_source == "config"
        assert info.heap_bytes == 0
        assert info.heap_source == "config"

    def test_size_symbol_with_size_attribute(self) -> None:
        info = detect_stack_heap(
            symbols=[
                _sym("_Min_Stack_Size", size=0x800),
                _sym("_Min_Heap_Size", size=0x400),
            ],
            sections=[],
        )
        assert info.stack_bytes == 0x800 and "_Min_Stack_Size" in info.stack_source
        assert info.heap_bytes == 0x400 and "_Min_Heap_Size" in info.heap_source

    def test_size_symbol_with_address_value(self) -> None:
        # Some startup files declare the size as an ABS symbol whose value (address) is the size.
        info = detect_stack_heap(
            symbols=[_sym("_Min_Stack_Size", addr=0x1000)],
            sections=[],
        )
        assert info.stack_bytes == 0x1000
        assert "value" in info.stack_source

    def test_pair_fallback(self) -> None:
        info = detect_stack_heap(
            symbols=[
                _sym("__StackLimit", addr=0x20000000),
                _sym("__StackTop", addr=0x20002000),
                _sym("__HeapBase", addr=0x20003000),
                _sym("__HeapLimit", addr=0x20004000),
            ],
            sections=[],
        )
        assert info.stack_bytes == 0x2000
        assert info.heap_bytes == 0x1000

    def test_section_fallback(self) -> None:
        info = detect_stack_heap(
            symbols=[],
            sections=[_section(".stack", 0x800), _section(".heap", 0x400)],
        )
        assert info.stack_bytes == 0x800
        assert info.heap_bytes == 0x400
        assert info.stack_source.startswith("section:")
        assert info.heap_source.startswith("section:")

    def test_diagnostics_when_undetectable(self) -> None:
        info = detect_stack_heap(symbols=[], sections=[])
        assert info.stack_bytes == 0
        assert info.heap_bytes == 0
        assert any("stack" in d for d in info.diagnostics)
        assert any("heap" in d for d in info.diagnostics)

    def test_custom_symbol_aliases(self) -> None:
        info = detect_stack_heap(
            symbols=[_sym("CUSTOM_STACK", size=0x1234)],
            sections=[],
            config={"stack_size_symbols": ["CUSTOM_STACK"]},
        )
        assert info.stack_bytes == 0x1234
        assert "CUSTOM_STACK" in info.stack_source
