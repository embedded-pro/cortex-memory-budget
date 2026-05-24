"""Markdown and JSON report generators."""

from __future__ import annotations

import json
from typing import Any

from .models import DiffEntry, MemoryReport, RegionUsage

PR_COMMENT_MARKER = "<!-- cortex-memory-budget-comment -->"


def _human(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.2f} KiB"
    return f"{n / (1024 * 1024):.2f} MiB"


def _region_table(usages: list[RegionUsage]) -> str:
    if not usages:
        return "_No memory regions declared (provide a linker script or config override)._\n"
    rows = [
        "| Region | Used | Free | Total | % |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for u in usages:
        rows.append(
            f"| `{u.region.name}` | {_human(u.used_bytes)} | {_human(u.free_bytes)} | "
            f"{_human(u.region.length)} | {u.used_pct:.1f}% |"
        )
    return "\n".join(rows) + "\n"


def _section_table(report: MemoryReport, top_n: int = 30) -> str:
    sorted_sections = sorted(
        (s for s in report.sections if s.size > 0),
        key=lambda s: -s.size,
    )[:top_n]
    if not sorted_sections:
        return "_No allocated sections found._\n"
    rows = [
        "| Section | Size | VMA | LMA |",
        "| --- | ---: | ---: | ---: |",
    ]
    for sec in sorted_sections:
        rows.append(
            f"| `{sec.name}` | {_human(sec.size)} | `0x{sec.vma:08x}` | `0x{sec.lma:08x}` |"
        )
    return "\n".join(rows) + "\n"


def _symbol_table(report: MemoryReport, top_n: int) -> str:
    syms = sorted(report.symbols, key=lambda s: -s.size)[:top_n]
    if not syms:
        return "_No symbols with size information._\n"
    rows = [
        "| # | Symbol | Section | Size | Source |",
        "| ---: | --- | --- | ---: | --- |",
    ]
    for i, sym in enumerate(syms, 1):
        source = sym.source_file or sym.object_file or "—"
        rows.append(
            f"| {i} | `{sym.name}` | `{sym.section or '?'}` | {_human(sym.size)} | `{source}` |"
        )
    return "\n".join(rows) + "\n"


def _source_table(report: MemoryReport, top_n: int) -> str:
    groups = report.source_groups[:top_n]
    if not groups:
        return "_No per-source-file information available (rebuild with `-g`)._\n"
    rows = [
        "| # | Source file | Flash | RAM (static) | Total |",
        "| ---: | --- | ---: | ---: | ---: |",
    ]
    for i, g in enumerate(groups, 1):
        rows.append(
            f"| {i} | `{g.source_file}` | {_human(g.flash_bytes)} | "
            f"{_human(g.ram_static_bytes)} | {_human(g.flash_bytes + g.ram_static_bytes)} |"
        )
    return "\n".join(rows) + "\n"


def _stack_heap_block(report: MemoryReport) -> str:
    sh = report.stack_heap
    return (
        f"- **Stack** – {_human(sh.stack_bytes)} (source: `{sh.stack_source}`)\n"
        f"- **Heap**  – {_human(sh.heap_bytes)} (source: `{sh.heap_source}`)\n"
    )


def generate_main_report(report: MemoryReport, *, top_n_symbols: int = 20, top_n_sources: int = 20) -> str:
    parts: list[str] = []
    parts.append(f"# Memory Report – {report.target} ({report.cortex.upper()})\n")
    parts.append(f"- Build: `{report.build_config}`\n- ELF: `{report.elf_path}`\n\n")
    parts.append("## Totals\n\n")
    parts.append(
        f"- **Flash image** – {_human(report.flash_bytes)}\n"
        f"- **RAM (static)** – {_human(report.ram_static_bytes)}\n"
        f"{_stack_heap_block(report)}"
        f"- **RAM total (static + stack + heap)** – {_human(report.ram_total_bytes)}\n\n"
    )
    parts.append("## Region utilisation\n\n")
    parts.append(_region_table(report.regions))
    parts.append("\n## Sections (largest first)\n\n")
    parts.append(_section_table(report))
    parts.append("\n## Top symbols\n\n")
    parts.append("<details><summary>Show top symbols</summary>\n\n")
    parts.append(_symbol_table(report, top_n_symbols))
    parts.append("</details>\n")
    parts.append("\n## Top source files\n\n")
    parts.append(_source_table(report, top_n_sources))
    if report.warnings:
        parts.append("\n## ⚠ Warnings\n\n")
        for w in report.warnings:
            parts.append(f"- {w}\n")
    return "".join(parts)


def generate_pr_comment(
    report: MemoryReport,
    diff: list[DiffEntry] | None = None,
    *,
    top_n_symbols: int = 10,
) -> str:
    parts: list[str] = [PR_COMMENT_MARKER, "\n## 📦 Memory budget\n\n"]
    parts.append(
        f"**{report.target}** ({report.cortex.upper()}, {report.build_config}) — "
        f"flash {_human(report.flash_bytes)} · static RAM {_human(report.ram_static_bytes)} · "
        f"stack {_human(report.stack_heap.stack_bytes)} · heap {_human(report.stack_heap.heap_bytes)}\n\n"
    )
    parts.append(_region_table(report.regions))
    parts.append("\n### Top symbols\n\n")
    parts.append("<details><summary>Show top symbols</summary>\n\n")
    parts.append(_symbol_table(report, top_n_symbols))
    parts.append("</details>\n")
    if diff:
        parts.append("\n### Changes vs. baseline\n\n")
        parts.append(generate_diff_report(diff, top_n=top_n_symbols))
    return "".join(parts)


def generate_diff_report(diff: list[DiffEntry], *, top_n: int = 30) -> str:
    if not diff:
        return "_No changes detected._\n"
    rows = [
        "| Kind | Name | Baseline | Current | Δ | Status |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for entry in diff[:top_n]:
        sign = "+" if entry.delta_bytes >= 0 else "−"
        delta_human = f"{sign}{_human(abs(entry.delta_bytes))}"
        rows.append(
            f"| {entry.kind} | `{entry.name}` | {_human(entry.baseline_bytes)} | "
            f"{_human(entry.current_bytes)} | {delta_human} | {entry.status} |"
        )
    return "\n".join(rows) + "\n"


def generate_combined_step_summary(
    labels: list[str],
    reports: list[MemoryReport],
    *,
    top_n_symbols: int = 10,
) -> str:
    if not reports:
        return ""
    first = reports[0]
    parts: list[str] = []
    parts.append(f"## 📦 Memory Budget — {first.target} ({first.cortex.upper()}, {first.build_config})\n\n")
    for label, report in zip(labels, reports):
        parts.append(f"### {label}\n\n")
        parts.append(_region_table(report.regions))
        parts.append("\n<details><summary>Top symbols</summary>\n\n")
        parts.append(_symbol_table(report, top_n_symbols))
        parts.append("</details>\n\n")
    return "".join(parts)


def generate_json_metrics(
    report: MemoryReport,
    diff: list[DiffEntry] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "target": report.target,
        "build_config": report.build_config,
        "cortex": report.cortex,
        "elf_path": report.elf_path,
        "flash_bytes": report.flash_bytes,
        "ram_static_bytes": report.ram_static_bytes,
        "stack_bytes": report.stack_heap.stack_bytes,
        "heap_bytes": report.stack_heap.heap_bytes,
        "ram_total_bytes": report.ram_total_bytes,
        "regions": [
            {
                "name": u.region.name,
                "origin": u.region.origin,
                "length": u.region.length,
                "used_bytes": u.used_bytes,
                "free_bytes": u.free_bytes,
                "used_pct": round(u.used_pct, 3),
                "used_by": dict(u.used_by),
            }
            for u in report.regions
        ],
        "top_symbols": [
            {
                "name": s.name,
                "section": s.section,
                "size": s.size,
                "address": s.address,
                "source_file": s.source_file,
            }
            for s in sorted(report.symbols, key=lambda s: -s.size)[:50]
        ],
        "warnings": list(report.warnings),
    }
    if diff is not None:
        payload["diff"] = [
            {
                "kind": e.kind,
                "name": e.name,
                "baseline_bytes": e.baseline_bytes,
                "current_bytes": e.current_bytes,
                "delta_bytes": e.delta_bytes,
                "status": e.status,
            }
            for e in diff
        ]
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
