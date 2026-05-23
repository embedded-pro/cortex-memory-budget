"""Baseline-vs-current diff computation."""

from __future__ import annotations

from .models import DiffEntry, MemoryReport


def _symbol_index(report: MemoryReport) -> dict[str, int]:
    out: dict[str, int] = {}
    for sym in report.symbols:
        out[sym.name] = out.get(sym.name, 0) + sym.size
    return out


def _section_index(report: MemoryReport) -> dict[str, int]:
    return {sec.name: sec.size for sec in report.sections}


def _region_index(report: MemoryReport) -> dict[str, int]:
    return {usage.region.name: usage.used_bytes for usage in report.regions}


def _diff_dicts(kind: str, baseline: dict[str, int], current: dict[str, int]) -> list[DiffEntry]:
    keys = set(baseline) | set(current)
    out: list[DiffEntry] = []
    for key in keys:
        b = baseline.get(key, 0)
        c = current.get(key, 0)
        if b == c:
            continue
        out.append(DiffEntry(kind=kind, name=key, baseline_bytes=b, current_bytes=c))
    out.sort(key=lambda e: (-abs(e.delta_bytes), e.name))
    return out


def diff_reports(baseline: MemoryReport, current: MemoryReport) -> list[DiffEntry]:
    """Compute per-symbol, per-section, and per-region diffs."""
    entries: list[DiffEntry] = []
    entries.extend(_diff_dicts("region", _region_index(baseline), _region_index(current)))
    entries.extend(_diff_dicts("section", _section_index(baseline), _section_index(current)))
    entries.extend(_diff_dicts("symbol", _symbol_index(baseline), _symbol_index(current)))
    return entries
