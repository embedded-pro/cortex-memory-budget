"""Parser for the GNU LD linker-script ``MEMORY { ... }`` block.

Best-effort: handles common syntax used by ST/NXP/TI/Nordic vendor scripts.
Falls back gracefully (skips the offending region with a warning) on
expressions that exceed the supported grammar.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import MemoryRegion

_MEMORY_BLOCK_RE = re.compile(
    r"MEMORY\s*\{(?P<body>.*?)\}",
    re.IGNORECASE | re.DOTALL,
)
_REGION_RE = re.compile(
    r"""
    (?P<name>[A-Za-z_][A-Za-z0-9_]*)        # region name
    (?:\s*\((?P<attrs>[^)]*)\))?            # optional attributes (rx, rw, ...)
    \s*:\s*
    ORIGIN\s*=\s*(?P<origin>[^,]+?),\s*
    LENGTH\s*=\s*(?P<length>[^\r\n,]+)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _strip_comments(text: str) -> str:
    """Remove C-style and line comments to simplify parsing."""
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", " ", text)
    text = re.sub(r"#[^\n]*", " ", text)
    return text


def _eval_size(expr: str) -> int:
    """Evaluate a GNU-LD size/offset expression.

    Supports integer constants (decimal, hex), ``K``/``M``/``KB``/``MB``
    suffixes, ``+``/``-``/``*``, and parentheses. Raises ``ValueError`` on
    anything else.
    """
    cleaned = expr.strip()
    if not cleaned:
        raise ValueError("empty expression")

    # Replace suffixes with explicit multiplication.
    def _suffix_sub(match: re.Match[str]) -> str:
        number = match.group(1)
        suffix = match.group(2).upper()
        multiplier = {"K": 1024, "KB": 1024, "M": 1024 * 1024, "MB": 1024 * 1024}[suffix]
        return f"({number}*{multiplier})"

    cleaned = re.sub(
        r"(0[xX][0-9A-Fa-f]+|\d+)\s*(KB|MB|K|M)\b",
        _suffix_sub,
        cleaned,
        flags=re.IGNORECASE,
    )

    if not re.fullmatch(r"[\s0-9xXa-fA-F+\-*()]+", cleaned):
        raise ValueError(f"unsupported expression: {expr!r}")

    # Only allow integer literals + arithmetic.
    try:
        value = eval(cleaned, {"__builtins__": {}}, {})
    except Exception as exc:
        raise ValueError(f"could not evaluate {expr!r}: {exc}") from exc
    if not isinstance(value, int):
        raise ValueError(f"expression did not yield an integer: {expr!r}")
    return value


def parse_linker_script(text: str) -> tuple[list[MemoryRegion], list[str]]:
    """Parse a linker script source and return (regions, warnings)."""
    warnings: list[str] = []
    cleaned = _strip_comments(text)
    block_match = _MEMORY_BLOCK_RE.search(cleaned)
    if not block_match:
        return [], ["no MEMORY { ... } block found"]
    body = block_match.group("body")
    regions: list[MemoryRegion] = []
    for match in _REGION_RE.finditer(body):
        name = match.group("name")
        attrs = (match.group("attrs") or "").strip()
        try:
            origin = _eval_size(match.group("origin"))
            length = _eval_size(match.group("length"))
        except ValueError as exc:
            warnings.append(f"region {name!r}: {exc}; skipping")
            continue
        regions.append(MemoryRegion(name=name, origin=origin, length=length, attrs=attrs))
    if not regions:
        warnings.append("MEMORY block was found but no regions could be parsed")
    return regions, warnings


def load_linker_script(path: str | Path) -> tuple[list[MemoryRegion], list[str]]:
    """Read a linker script from disk and parse it."""
    p = Path(path)
    return parse_linker_script(p.read_text(encoding="utf-8", errors="replace"))
