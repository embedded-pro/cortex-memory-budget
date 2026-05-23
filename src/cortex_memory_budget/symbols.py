"""Parser for ``nm -S --print-size --demangle --print-file-name`` output."""

from __future__ import annotations

import re

from .models import Symbol

# nm --print-file-name prefixes each line with "<elfname>:" — strip that.
# Format then is: <address> [<size>] <type> <name>
# Some symbols (linker-script ABS, undefined) have no size column. We keep
# zero-size and unsized symbols so downstream consumers (e.g. stack/heap
# auto-detect) can find linker-defined ABS markers.
_LINE_RE = re.compile(
    r"""
    ^(?:[^:]+:\s*)?
    (?P<addr>[0-9a-fA-F]+)
    \s+
    (?:(?P<size>[0-9a-fA-F]+)\s+)?
    (?P<type>[A-Za-z?])
    \s+
    (?P<name>.+?)
    \s*$
    """,
    re.VERBOSE,
)

# Type letter → which section bucket the symbol belongs to.
_TYPE_TO_SECTION: dict[str, str] = {
    "T": ".text", "t": ".text",
    "W": ".text", "w": ".text",
    "R": ".rodata", "r": ".rodata",
    "D": ".data", "d": ".data",
    "B": ".bss", "b": ".bss",
    "C": ".bss",  # COMMON → treated as .bss
    "V": ".data", "v": ".data",
}


def parse_symbols(nm_output: str) -> list[Symbol]:
    """Parse nm output into a list of symbols.

    Zero-size and size-less entries are retained because linker-script
    absolute symbols (e.g. ``_Min_Stack_Size = 0x800``) carry their value in
    the address field with no explicit size.
    """
    syms: list[Symbol] = []
    for raw_line in nm_output.splitlines():
        match = _LINE_RE.match(raw_line)
        if not match:
            continue
        size_str = match.group("size")
        size = int(size_str, 16) if size_str else 0
        name = match.group("name").strip()
        object_file = ""
        if "\t" in name:
            object_file, name = name.split("\t", 1)
        type_char = match.group("type")
        syms.append(
            Symbol(
                name=name,
                raw_name=name,
                address=int(match.group("addr"), 16),
                size=size,
                type_char=type_char,
                section=_TYPE_TO_SECTION.get(type_char, ""),
                object_file=object_file,
            )
        )
    return syms


def filter_largest(symbols: list[Symbol], top_n: int) -> list[Symbol]:
    """Return the top-N largest symbols (descending size, then by name)."""
    return sorted(symbols, key=lambda s: (-s.size, s.name))[:top_n]
