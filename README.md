# cortex-memory-budget

[![CI](https://github.com/embedded-pro/cortex-memory-budget/actions/workflows/ci.yml/badge.svg)](https://github.com/embedded-pro/cortex-memory-budget/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/cortex-memory-budget.svg)](https://pypi.org/project/cortex-memory-budget/)
[![Python](https://img.shields.io/pypi/pyversions/cortex-memory-budget.svg)](https://pypi.org/project/cortex-memory-budget/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> Static flash/RAM footprint analysis for ARM Cortex-M binaries —
> **CI-friendly, framework-agnostic, zero runtime dependencies**.

`cortex-memory-budget` analyzes an ELF binary (via `arm-none-eabi-objdump`,
`nm`, and `addr2line`) and reports how much **flash** and **RAM** your
firmware consumes, **broken down by memory region, section, symbol, and
source file**. Pre-allocated **stack** and **heap** are detected via linker
symbols with section-based fallback.

It supports **Cortex-M0**, **Cortex-M4**, **Cortex-M7**, and **Cortex-M33**
and is designed for **resource-constrained MCUs** where every kilobyte of
flash and every byte of RAM matters.

---

## ✨ Features

| Feature                                                     | Status |
| ----------------------------------------------------------- | :----: |
| Cortex-M0 / M4 / M7 / M33 supported                         |   ✅   |
| Linker-script `MEMORY {}` auto-detect (with config override)|   ✅   |
| Region utilisation report with ASCII bar charts             |   ✅   |
| `.data` double-counted (flash LMA + RAM VMA)                |   ✅   |
| Per-section breakdown                                       |   ✅   |
| Top-N symbol table (per region)                             |   ✅   |
| Per-source-file aggregation via DWARF (`addr2line`)         |   ✅   |
| Pre-allocated stack & heap detection (symbol + section)     |   ✅   |
| Diff mode against a baseline ELF                            |   ✅   |
| Multi-mode analyzer (multiple configs in one run)           |   ✅   |
| GitHub composite action + reusable workflow                 |   ✅   |
| PR comment with stable marker (idempotent update)           |   ✅   |
| `--fail-over-flash-pct` / `--fail-over-ram-pct` CI gates    |   ✅   |
| Machine-readable JSON metrics                               |   ✅   |

---

## 🚀 Quickstart

### 1. Install

```bash
pip install cortex-memory-budget
```

Runtime dependencies: **none** (Python ≥ 3.11 stdlib only). At analysis time
you need `arm-none-eabi-objdump`, `arm-none-eabi-nm`, and
`arm-none-eabi-addr2line` on `PATH`, or pass `--objdump`/`--nm`/`--addr2line`.

### 2. Write a config (`memory-analysis.json`)

```json
{
  "top_n_symbols": 20,
  "top_n_source_files": 15,
  "regions": [
    {"name": "FLASH", "length_kb": 1024},
    {"name": "SRAM",  "length_kb": 192}
  ]
}
```

`regions` is optional — if omitted (or for regions not listed), values are
taken from the linker script passed via `--linker-script`. See
[docs/config-schema.md](docs/config-schema.md) for the full schema.

### 3. Run

```bash
cortex-memory-budget memory-analysis.json \
    --elf build/firmware.elf \
    --target nucleo-h743zi \
    --build-config Release \
    --cortex m7 \
    --linker-script firmware.ld \
    --output-dir reports
```

Outputs in `reports/`:

| File                    | Purpose                                                   |
| ----------------------- | --------------------------------------------------------- |
| `memory_report.md`      | Full Markdown report (regions / sections / symbols / src) |
| `pr_comment.md`         | Compact PR comment (with idempotent marker)               |
| `memory_metrics.json`   | Machine-readable summary for downstream tooling           |
| `memory_diff.md`        | (When `--baseline-elf` given) per-symbol/section delta    |

### 4. Use in GitHub Actions

```yaml
- uses: embedded-pro/cortex-memory-budget@v0
  with:
    config-path: memory-analysis.json
    elf-path: build/firmware.elf
    baseline-elf-path: baseline/firmware.elf   # optional, enables diff
    target: nucleo-h743zi
    build-config: Release
    cortex: m7
    linker-script-path: firmware.ld
    fail-over-flash-pct: 85
    fail-over-ram-pct: 80
```

The action posts an idempotent PR comment, appends a step summary, and uploads
all reports as an artifact. See [docs/usage.md](docs/usage.md) for the full
input/output reference.

---

## 📚 Documentation

| Document                                                              | What it covers                              |
| --------------------------------------------------------------------- | ------------------------------------------- |
| [docs/usage.md](docs/usage.md)                                        | CLI flags, action inputs/outputs, examples  |
| [docs/config-schema.md](docs/config-schema.md)                        | Full JSON config schema + reference         |
| [docs/memory-model.md](docs/memory-model.md)                          | What counts where (.data, COMMON, debug)    |
| [docs/linker-script-detection.md](docs/linker-script-detection.md)    | Linker-script parser scope & limits         |
| [docs/cortex-variants.md](docs/cortex-variants.md)                    | M0 / M4 / M7 / M33 notes for memory layout  |
| [docs/architecture.md](docs/architecture.md)                          | Internal module layout & data flow          |
| [docs/troubleshooting.md](docs/troubleshooting.md)                    | Common errors & their fixes                 |
| [CONTRIBUTING.md](CONTRIBUTING.md)                                    | Dev setup, testing, release process         |
| [CHANGELOG.md](CHANGELOG.md)                                          | Version history                             |

---

## 🧪 Examples

Five runnable examples ship in [examples/](examples/):

| Example                                         | Highlights                                       |
| ----------------------------------------------- | ------------------------------------------------ |
| [examples/minimal](examples/minimal/)           | Single-region M4 firmware with explicit budgets  |
| [examples/cortex-m7](examples/cortex-m7/)       | Multi-region layout incl. AXI SRAM               |
| [examples/cortex-m33](examples/cortex-m33/)     | Single binary spanning two RAM regions           |
| [examples/multi-mode](examples/multi-mode/)     | One ELF analysed against two budget profiles     |
| [examples/diff-mode](examples/diff-mode/)       | `baseline.elf` vs. `current.elf` growth report   |

---

## ⚠️ Scope & limitations

This tool gives **static** post-link footprint analysis. It does **not** model:

- Worst-case **dynamic** stack depth (use `-fstack-usage` + a call-graph
  walker for that). We report only the **pre-allocated** stack reservation.
- Runtime heap fragmentation. We report only the configured **heap budget**.
- Cache line / row paddings inserted at runtime.
- Externally loaded / overlay / XIP-from-PSRAM code that isn't part of the ELF.

Estimates are intended as a **CI guardrail** for the static link image.

---

## 📄 License

Apache-2.0 — see [LICENSE](LICENSE).
