"""End-to-end analysis orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .dwarf import attach_source_files, group_by_source_file
from .linker_script import load_linker_script
from .models import MemoryReport, SourceFileGroup
from .regions import assign_sections, merge_regions
from .sections import classify_section, parse_sections
from .stack_heap import detect_stack_heap
from .symbols import parse_symbols
from .tooling import run_nm, run_objdump_sections


def _build_source_groups(symbols: list[Any]) -> list[SourceFileGroup]:
    groups: list[SourceFileGroup] = []
    for source, group_syms in group_by_source_file(symbols).items():
        flash = 0
        ram = 0
        for sym in group_syms:
            if sym.section in {".text", ".rodata"}:
                flash += sym.size
            elif sym.section in {".bss"}:
                ram += sym.size
            elif sym.section in {".data"}:
                flash += sym.size
                ram += sym.size
        groups.append(
            SourceFileGroup(
                source_file=source,
                flash_bytes=flash,
                ram_static_bytes=ram,
                symbols=group_syms,
            )
        )
    groups.sort(key=lambda g: -(g.flash_bytes + g.ram_static_bytes))
    return groups


def analyze(
    elf_path: str,
    config: dict[str, Any],
    *,
    target: str,
    build_config: str,
    cortex: str,
    linker_script_path: str | None = None,
    objdump_tool: str = "arm-none-eabi-objdump",
    nm_tool: str = "arm-none-eabi-nm",
    addr2line_tool: str = "arm-none-eabi-addr2line",
    use_dwarf: bool = True,
) -> MemoryReport:
    """Produce a full :class:`MemoryReport` for ``elf_path``."""
    if not Path(elf_path).is_file():
        raise FileNotFoundError(f"ELF not found: {elf_path}")

    sections = parse_sections(run_objdump_sections(elf_path, tool=objdump_tool))
    symbols = parse_symbols(run_nm(elf_path, tool=nm_tool))
    if use_dwarf:
        attach_source_files(symbols, elf_path, tool=addr2line_tool)

    detected_regions: list[Any] = []
    warnings: list[str] = []
    if linker_script_path:
        detected_regions, ls_warnings = load_linker_script(linker_script_path)
        warnings.extend(f"linker-script: {w}" for w in ls_warnings)
    merged_regions, merge_warnings = merge_regions(detected_regions, config.get("regions", []))
    warnings.extend(f"regions: {w}" for w in merge_warnings)

    usages, assign_warnings = assign_sections(merged_regions, sections)
    warnings.extend(f"sections: {w}" for w in assign_warnings)

    stack_heap = detect_stack_heap(symbols, sections, config=config)
    warnings.extend(f"stack/heap: {d}" for d in stack_heap.diagnostics)

    flash_bytes = 0
    ram_static_bytes = 0
    for sec in sections:
        cls = classify_section(sec)
        if cls == "flash":
            flash_bytes += sec.size
        elif cls == "ram_init":
            flash_bytes += sec.size
            ram_static_bytes += sec.size
        elif cls == "ram_static":
            ram_static_bytes += sec.size

    report = MemoryReport(
        target=target,
        build_config=build_config,
        cortex=cortex,
        elf_path=elf_path,
        flash_bytes=flash_bytes,
        ram_static_bytes=ram_static_bytes,
        stack_heap=stack_heap,
        sections=sections,
        symbols=symbols,
        regions=usages,
        source_groups=_build_source_groups(symbols),
        warnings=warnings,
    )
    return report
