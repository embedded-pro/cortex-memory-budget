"""Single-ELF CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .analysis import analyze
from .config import SUPPORTED_CORTEX, validate_config
from .diff import diff_reports
from .models import ConfigError, ToolError
from .reports import (
    generate_diff_report,
    generate_json_metrics,
    generate_main_report,
    generate_pr_comment,
)
from .tooling import log


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cortex-memory-budget",
        description="Static flash/RAM footprint analysis for ARM Cortex-M binaries.",
    )
    p.add_argument("config", help="Path to the memory-analysis JSON config")
    p.add_argument("--elf", required=True, help="Path to the ELF binary to analyze")
    p.add_argument("--target", required=True, help="Free-form target label (e.g. nucleo-h743zi)")
    p.add_argument("--build-config", required=True, help="Build label (Release, Debug, …)")
    p.add_argument(
        "--cortex",
        choices=sorted(SUPPORTED_CORTEX),
        default="m4",
        help="Cortex-M variant (default: m4)",
    )
    p.add_argument("--output-dir", default=".", help="Directory for generated reports")
    p.add_argument("--baseline-elf", help="Optional baseline ELF for diff mode")
    p.add_argument("--linker-script", help="Optional linker script for region auto-detect")
    p.add_argument("--objdump", default="arm-none-eabi-objdump", help="Override objdump binary")
    p.add_argument("--nm", default="arm-none-eabi-nm", help="Override nm binary")
    p.add_argument("--addr2line", default="arm-none-eabi-addr2line", help="Override addr2line binary")
    p.add_argument("--top-n-symbols", type=int, default=20, help="Number of top symbols to list")
    p.add_argument("--top-n-sources", type=int, default=20, help="Number of top source files to list")
    p.add_argument("--no-dwarf", action="store_true", help="Skip addr2line lookups (faster, no per-file rollup)")
    p.add_argument("--fail-over-flash-pct", type=float, help="Exit 2 when any flash region exceeds N%%")
    p.add_argument("--fail-over-ram-pct", type=float, help="Exit 2 when any RAM region exceeds N%%")
    return p


def _load_config(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ConfigError("config must be a JSON object")
    return data


def _is_flashy(region_name: str, attrs: str) -> bool:
    name = region_name.upper()
    if "X" in attrs.upper() and "R" in attrs.upper() and "W" not in attrs.upper():
        return True
    return any(tag in name for tag in ("FLASH", "ROM", "CODE"))


def _is_ramy(region_name: str, attrs: str) -> bool:
    name = region_name.upper()
    if "W" in attrs.upper():
        return True
    return any(tag in name for tag in ("RAM", "SRAM", "DTCM", "ITCM", "AXI"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load_config(args.config)
        validate_config(config)
    except (OSError, ConfigError, json.JSONDecodeError) as exc:
        log(f"ERROR: {exc}")
        return 1

    try:
        report = analyze(
            elf_path=args.elf,
            config=config,
            target=args.target,
            build_config=args.build_config,
            cortex=args.cortex,
            linker_script_path=args.linker_script,
            objdump_tool=args.objdump,
            nm_tool=args.nm,
            addr2line_tool=args.addr2line,
            use_dwarf=not args.no_dwarf,
        )
        diff = None
        if args.baseline_elf:
            baseline = analyze(
                elf_path=args.baseline_elf,
                config=config,
                target=args.target,
                build_config=f"{args.build_config} (baseline)",
                cortex=args.cortex,
                linker_script_path=args.linker_script,
                objdump_tool=args.objdump,
                nm_tool=args.nm,
                addr2line_tool=args.addr2line,
                use_dwarf=not args.no_dwarf,
            )
            diff = diff_reports(baseline, report)
    except (FileNotFoundError, ToolError) as exc:
        log(f"ERROR: {exc}")
        return 1

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "memory_report.md").write_text(
        generate_main_report(report, top_n_symbols=args.top_n_symbols, top_n_sources=args.top_n_sources),
        encoding="utf-8",
    )
    (out_dir / "pr_comment.md").write_text(
        generate_pr_comment(report, diff=diff, top_n_symbols=min(args.top_n_symbols, 10)),
        encoding="utf-8",
    )
    (out_dir / "memory_metrics.json").write_text(
        generate_json_metrics(report, diff=diff),
        encoding="utf-8",
    )
    if diff:
        (out_dir / "memory_diff.md").write_text(generate_diff_report(diff), encoding="utf-8")

    log(
        f"flash={report.flash_bytes} ram_static={report.ram_static_bytes} "
        f"stack={report.stack_heap.stack_bytes} heap={report.stack_heap.heap_bytes}"
    )

    exit_code = 0
    if args.fail_over_flash_pct is not None:
        for u in report.regions:
            if _is_flashy(u.region.name, u.region.attrs) and u.used_pct > args.fail_over_flash_pct:
                log(
                    f"FAIL: flash region {u.region.name!r} is "
                    f"{u.used_pct:.2f}% > {args.fail_over_flash_pct}%"
                )
                exit_code = 2
    if args.fail_over_ram_pct is not None:
        for u in report.regions:
            if _is_ramy(u.region.name, u.region.attrs) and u.used_pct > args.fail_over_ram_pct:
                log(
                    f"FAIL: RAM region {u.region.name!r} is "
                    f"{u.used_pct:.2f}% > {args.fail_over_ram_pct}%"
                )
                exit_code = 2
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
