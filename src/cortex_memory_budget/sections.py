"""Section parsing and classification."""

from __future__ import annotations

import re

from .models import Section

_HEADER_RE = re.compile(
    r"""
    ^\s*\d+\s+                       # index
    (?P<name>\S+)\s+                 # section name
    (?P<size>[0-9a-fA-F]+)\s+        # size (hex)
    (?P<vma>[0-9a-fA-F]+)\s+         # VMA
    (?P<lma>[0-9a-fA-F]+)\s+         # LMA
    [0-9a-fA-F]+\s+                  # file offset
    \d*\*?\*\d+                      # alignment (e.g. 2**2)
    (?:\s+(?P<flags>.+))?            # optional inline flags (objdump -w)
    \s*$
    """,
    re.VERBOSE,
)


def parse_sections(objdump_output: str) -> list[Section]:
    """Parse the output of ``objdump -h`` (with or without ``-w``) into :class:`Section` objects."""
    sections: list[Section] = []
    lines = objdump_output.splitlines()
    i = 0
    while i < len(lines):
        match = _HEADER_RE.match(lines[i])
        if not match:
            i += 1
            continue
        flags: set[str] = set()
        inline_flags = match.group("flags")
        if inline_flags:
            for token in inline_flags.split(","):
                token = token.strip().upper()
                if token:
                    flags.add(token)
        else:
            # Flags appear on the next non-empty line, comma-separated.
            j = i + 1
            if j < len(lines):
                flag_line = lines[j].strip()
                if flag_line and not _HEADER_RE.match(lines[j]):
                    for token in flag_line.split(","):
                        token = token.strip().upper()
                        if token:
                            flags.add(token)
                    i = j
        sections.append(
            Section(
                name=match.group("name"),
                size=int(match.group("size"), 16),
                vma=int(match.group("vma"), 16),
                lma=int(match.group("lma"), 16),
                flags=frozenset(flags),
            )
        )
        i += 1
    return sections


_FLASH_PREFIXES: tuple[str, ...] = (
    ".text",
    ".rodata",
    ".isr_vector",
    ".vectors",
    ".init",
    ".fini",
    ".preinit_array",
    ".init_array",
    ".fini_array",
    ".ctors",
    ".dtors",
    ".eh_frame",
    ".ARM.exidx",
    ".ARM.extab",
)

_RAM_STATIC_PREFIXES: tuple[str, ...] = (
    ".bss",
    ".sbss",
    ".noinit",
    ".uninit",
    ".COMMON",
)

_STACK_PREFIXES: tuple[str, ...] = (".stack", "._stack", ".stack_dummy")
_HEAP_PREFIXES: tuple[str, ...] = (".heap", "._heap", ".heap_dummy")

_DEBUG_PREFIXES: tuple[str, ...] = (".debug", ".comment", ".note", ".gnu", ".symtab", ".strtab", ".shstrtab")

_IGNORED_EXACT: frozenset[str] = frozenset({"", ".ARM.attributes"})


def classify_section(section: Section) -> str:
    """Classify a section as ``flash`` / ``ram_static`` / ``ram_init`` / ``stack`` / ``heap`` / ``debug`` / ``ignored``.

    ``ram_init`` denotes a section that lives in RAM at runtime but whose
    initialiser image is stored in flash (i.e. ``.data``-like sections).
    Callers must count it **once** in flash and **once** in RAM.
    """
    name = section.name
    if name in _IGNORED_EXACT:
        return "ignored"
    if any(name == p or name.startswith(p + ".") for p in _STACK_PREFIXES):
        return "stack"
    if any(name == p or name.startswith(p + ".") for p in _HEAP_PREFIXES):
        return "heap"
    if any(name.startswith(p) for p in _DEBUG_PREFIXES):
        return "debug"
    if any(name == p or name.startswith(p + ".") for p in _RAM_STATIC_PREFIXES):
        return "ram_static" if section.is_alloc else "ignored"
    if name == ".data" or name.startswith(".data.") or name.startswith(".sdata"):
        return "ram_init" if section.is_alloc else "ignored"
    if any(name == p or name.startswith(p + ".") for p in _FLASH_PREFIXES):
        return "flash" if section.is_alloc else "ignored"
    if not section.is_alloc:
        return "ignored"
    # Allocated but unknown: default to flash for readonly/code, ram_static otherwise.
    if section.is_readonly or section.is_code:
        return "flash"
    return "ram_static"


def summarise(sections: list[Section]) -> dict[str, int]:
    """Return cumulative byte totals by classification."""
    totals: dict[str, int] = {
        "flash": 0,
        "ram_static": 0,
        "ram_init": 0,
        "stack": 0,
        "heap": 0,
        "debug": 0,
        "ignored": 0,
    }
    for sec in sections:
        totals[classify_section(sec)] += sec.size
    return totals
