"""Resolve symbol addresses to source files via ``arm-none-eabi-addr2line``."""

from __future__ import annotations

from .models import Symbol
from .tooling import run_addr2line


def attach_source_files(
    symbols: list[Symbol],
    elf_path: str,
    tool: str = "arm-none-eabi-addr2line",
) -> None:
    """In-place: populate ``Symbol.source_file`` for every symbol.

    Symbols whose addr2line lookup returns ``??`` or an empty path retain
    whatever ``object_file`` they came in with as a fallback.
    """
    if not symbols:
        return
    addresses = [f"0x{sym.address:x}" for sym in symbols]
    resolved = run_addr2line(elf_path, addresses, tool=tool)
    for sym, (_func, location) in zip(symbols, resolved, strict=False):
        path = location.split(":", 1)[0].strip()
        if path and path != "??":
            sym.source_file = path
        elif sym.object_file:
            sym.source_file = sym.object_file


def group_by_source_file(symbols: list[Symbol]) -> dict[str, list[Symbol]]:
    """Group symbols by ``source_file`` (or ``"<unknown>"`` when absent)."""
    groups: dict[str, list[Symbol]] = {}
    for sym in symbols:
        key = sym.source_file or sym.object_file or "<unknown>"
        groups.setdefault(key, []).append(sym)
    return groups
