"""Detect pre-allocated stack and heap sizes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import Section, StackHeapInfo, Symbol
from .sections import classify_section

_Resolver = Callable[[], tuple[int, str] | None]

DEFAULT_STACK_SIZE_SYMBOLS: tuple[str, ...] = (
    "_Min_Stack_Size",
    "__stack_size__",
    "__STACK_SIZE",
    "_stack_size",
    "__StackSize",
)
DEFAULT_HEAP_SIZE_SYMBOLS: tuple[str, ...] = (
    "_Min_Heap_Size",
    "__heap_size__",
    "__HEAP_SIZE",
    "_heap_size",
    "__HeapSize",
)
DEFAULT_STACK_LIMIT_PAIRS: tuple[tuple[str, str], ...] = (
    ("__StackLimit", "__StackTop"),
    ("_sstack", "_estack"),
)
DEFAULT_HEAP_LIMIT_PAIRS: tuple[tuple[str, str], ...] = (
    ("__HeapBase", "__HeapLimit"),
    ("_sheap", "_eheap"),
    ("__heap_start", "__heap_end"),
)


def _symbols_by_name(symbols: list[Symbol]) -> dict[str, Symbol]:
    return {sym.name: sym for sym in symbols}


def _from_size_symbol(by_name: dict[str, Symbol], candidates: tuple[str, ...]) -> tuple[int, str] | None:
    for cand in candidates:
        sym = by_name.get(cand)
        if sym is not None and sym.size > 0:
            return sym.size, f"symbol:{cand}(size)"
        # Some startup files declare the size as the **address** of an absolute
        # symbol — its size is 0 but the address itself encodes the value.
        if sym is not None and sym.address > 0:
            return sym.address, f"symbol:{cand}(value)"
    return None


def _from_pair(by_name: dict[str, Symbol], pairs: tuple[tuple[str, str], ...]) -> tuple[int, str] | None:
    for lo, hi in pairs:
        lo_sym, hi_sym = by_name.get(lo), by_name.get(hi)
        if lo_sym is not None and hi_sym is not None:
            size = hi_sym.address - lo_sym.address
            if size > 0:
                return size, f"symbol:{lo}..{hi}"
    return None


def _from_sections(sections: list[Section], category: str) -> tuple[int, str] | None:
    total = 0
    chosen: list[str] = []
    for sec in sections:
        if classify_section(sec) == category and sec.size > 0:
            total += sec.size
            chosen.append(sec.name)
    if total > 0:
        return total, f"section:{','.join(chosen)}"
    return None


def detect_stack_heap(
    symbols: list[Symbol],
    sections: list[Section],
    config: dict[str, Any] | None = None,
) -> StackHeapInfo:
    """Resolve stack & heap sizes.

    Precedence:
      1. ``config["stack_bytes"]`` / ``config["heap_bytes"]`` (explicit override)
      2. Size-encoding symbols (``_Min_Stack_Size``, …)
      3. Limit-pair symbols (``__StackLimit``/``__StackTop``, …)
      4. Section sizes (``.stack`` / ``.heap``)
    """
    cfg = config or {}
    by_name = _symbols_by_name(symbols)
    info = StackHeapInfo()

    extra_stack_size: tuple[str, ...] = tuple(cfg.get("stack_size_symbols", ()))
    extra_heap_size: tuple[str, ...] = tuple(cfg.get("heap_size_symbols", ()))
    stack_size_candidates = (*extra_stack_size, *DEFAULT_STACK_SIZE_SYMBOLS)
    heap_size_candidates = (*extra_heap_size, *DEFAULT_HEAP_SIZE_SYMBOLS)

    stack_resolvers: tuple[_Resolver, ...] = (
        lambda: _from_size_symbol(by_name, stack_size_candidates),
        lambda: _from_pair(by_name, DEFAULT_STACK_LIMIT_PAIRS),
        lambda: _from_sections(sections, "stack"),
    )
    heap_resolvers: tuple[_Resolver, ...] = (
        lambda: _from_size_symbol(by_name, heap_size_candidates),
        lambda: _from_pair(by_name, DEFAULT_HEAP_LIMIT_PAIRS),
        lambda: _from_sections(sections, "heap"),
    )

    if "stack_bytes" in cfg:
        info.stack_bytes = int(cfg["stack_bytes"])
        info.stack_source = "config"
    else:
        for stack_resolver in stack_resolvers:
            result = stack_resolver()
            if result is not None:
                info.stack_bytes, info.stack_source = result
                break
        else:
            info.diagnostics.append(
                "could not detect stack size — pass it via config['stack_bytes']"
            )

    if "heap_bytes" in cfg:
        info.heap_bytes = int(cfg["heap_bytes"])
        info.heap_source = "config"
    else:
        for heap_resolver in heap_resolvers:
            result = heap_resolver()
            if result is not None:
                info.heap_bytes, info.heap_source = result
                break
        else:
            info.diagnostics.append(
                "could not detect heap size — pass it via config['heap_bytes']"
            )

    return info
