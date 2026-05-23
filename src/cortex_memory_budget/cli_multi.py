"""Multi-ELF CLI — analyze several configurations and emit a combined report."""

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
    PR_COMMENT_MARKER,
    generate_json_metrics,
    generate_pr_comment,
)
from .tooling import log


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cortex-memory-budget-multi",
        description="Run cortex-memory-budget against several ELF/config pairs and combine the output.",
    )
    p.add_argument("analyses", help="Path to a JSON array describing every analysis")
    p.add_argument("--target", required=True)
    p.add_argument("--build-config", required=True)
    p.add_argument(
        "--cortex",
        choices=sorted(SUPPORTED_CORTEX),
        default="m4",
    )
    p.add_argument("--output-dir", default=".")
    p.add_argument("--linker-script")
    p.add_argument("--objdump", default="arm-none-eabi-objdump")
    p.add_argument("--nm", default="arm-none-eabi-nm")
    p.add_argument("--addr2line", default="arm-none-eabi-addr2line")
    p.add_argument("--no-dwarf", action="store_true")
    p.add_argument("--fail-over-flash-pct", type=float)
    p.add_argument("--fail-over-ram-pct", type=float)
    return p


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        analyses = _load_json(args.analyses)
        if not isinstance(analyses, list) or not analyses:
            raise ConfigError("analyses file must contain a non-empty JSON array")
    except (OSError, ConfigError, json.JSONDecodeError) as exc:
        log(f"ERROR: {exc}")
        return 1

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    combined_pr: list[str] = [PR_COMMENT_MARKER, "\n## 📦 Memory budget (multi-mode)\n\n"]
    combined_metrics: list[dict[str, Any]] = []
    overall_max_flash_pct = 0.0
    overall_max_ram_pct = 0.0
    exit_code = 0

    for i, entry in enumerate(analyses):
        if not isinstance(entry, dict):
            log(f"ERROR: analyses[{i}] must be an object")
            return 1
        label = str(entry.get("label", f"mode-{i}"))
        try:
            config = _load_json(entry["config_path"])
            validate_config(config)
            report = analyze(
                elf_path=entry["elf_path"],
                config=config,
                target=args.target,
                build_config=args.build_config,
                cortex=args.cortex,
                linker_script_path=entry.get("linker_script", args.linker_script),
                objdump_tool=args.objdump,
                nm_tool=args.nm,
                addr2line_tool=args.addr2line,
                use_dwarf=not args.no_dwarf,
            )
            diff = None
            if entry.get("baseline_elf"):
                baseline = analyze(
                    elf_path=entry["baseline_elf"],
                    config=config,
                    target=args.target,
                    build_config=f"{args.build_config} (baseline)",
                    cortex=args.cortex,
                    linker_script_path=entry.get("linker_script", args.linker_script),
                    objdump_tool=args.objdump,
                    nm_tool=args.nm,
                    addr2line_tool=args.addr2line,
                    use_dwarf=not args.no_dwarf,
                )
                diff = diff_reports(baseline, report)
        except (FileNotFoundError, KeyError, ConfigError, ToolError, json.JSONDecodeError) as exc:
            log(f"ERROR: analyses[{i}] ({label}): {exc}")
            return 1

        combined_pr.append(f"\n### {label}\n\n")
        combined_pr.append(generate_pr_comment(report, diff=diff).split(PR_COMMENT_MARKER, 1)[1])
        combined_metrics.append(
            {
                "label": label,
                "metrics": json.loads(generate_json_metrics(report, diff=diff)),
            }
        )
        for u in report.regions:
            if any(tag in u.region.name.upper() for tag in ("FLASH", "ROM")):
                overall_max_flash_pct = max(overall_max_flash_pct, u.used_pct)
            if any(tag in u.region.name.upper() for tag in ("RAM", "SRAM", "DTCM", "ITCM", "AXI")):
                overall_max_ram_pct = max(overall_max_ram_pct, u.used_pct)

    (out_dir / "combined_pr_comment.md").write_text("".join(combined_pr), encoding="utf-8")
    (out_dir / "combined_metrics.json").write_text(
        json.dumps(
            {
                "overall_max_flash_pct": round(overall_max_flash_pct, 3),
                "overall_max_ram_pct": round(overall_max_ram_pct, 3),
                "analyses": combined_metrics,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if args.fail_over_flash_pct is not None and overall_max_flash_pct > args.fail_over_flash_pct:
        log(f"FAIL: max flash region {overall_max_flash_pct:.2f}% > {args.fail_over_flash_pct}%")
        exit_code = 2
    if args.fail_over_ram_pct is not None and overall_max_ram_pct > args.fail_over_ram_pct:
        log(f"FAIL: max RAM region {overall_max_ram_pct:.2f}% > {args.fail_over_ram_pct}%")
        exit_code = 2
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
