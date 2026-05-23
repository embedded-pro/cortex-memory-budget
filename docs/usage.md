# Usage

## CLI

```text
cortex-memory-budget CONFIG --elf ELF --target T --build-config C --cortex {m0,m4,m7,m33} [options]
```

### Required

| Flag                       | Description                                          |
| -------------------------- | ---------------------------------------------------- |
| `CONFIG` (positional)      | Path to the memory-analysis JSON config              |
| `--elf PATH`               | Path to the ELF binary to analyse                    |
| `--target NAME`            | Free-form board / target label                       |
| `--build-config NAME`      | Build configuration label (Release, Debug, …)        |
| `--cortex {m0,m4,m7,m33}`  | Cortex-M variant                                     |

### Optional

| Flag                            | Default                  | Description                                       |
| ------------------------------- | ------------------------ | ------------------------------------------------- |
| `--output-dir DIR`              | `memory-analysis`        | Where reports/metrics are written                 |
| `--baseline-elf PATH`           | _none_                   | Baseline ELF for diff mode                        |
| `--linker-script PATH`          | _none_                   | Linker script for region auto-detect              |
| `--objdump TOOL`                | `arm-none-eabi-objdump`  | Override objdump binary                           |
| `--nm TOOL`                     | `arm-none-eabi-nm`       | Override nm binary                                |
| `--addr2line TOOL`              | `arm-none-eabi-addr2line`| Override addr2line binary                         |
| `--no-dwarf`                    | _off_                    | Skip DWARF source-file attribution                |
| `--fail-over-flash-pct N`       | _none_                   | Exit 2 if any flash region exceeds N%             |
| `--fail-over-ram-pct N`         | _none_                   | Exit 2 if any RAM region exceeds N%               |

### Outputs

| File                    | Always | Description                                                |
| ----------------------- | :----: | ---------------------------------------------------------- |
| `memory_report.md`      |   ✅   | Full report: regions, sections, top symbols, source groups |
| `pr_comment.md`         |   ✅   | Compact PR comment (with stable HTML marker)               |
| `memory_metrics.json`   |   ✅   | Machine-readable summary                                   |
| `memory_diff.md`        |  diff  | Per-symbol / per-section / per-region delta                |

### Exit codes

| Code | Meaning                                            |
| :--: | -------------------------------------------------- |
|  0   | Success                                            |
|  1   | Tool / configuration error                         |
|  2   | Threshold violation (`--fail-over-…-pct` exceeded) |

## Multi-mode CLI

```text
cortex-memory-budget-multi ANALYSES_JSON --target T --build-config C --cortex … [options]
```

`ANALYSES_JSON` is an array of objects with keys `label`, `config_path`,
`elf_path`, optional `baseline_elf`, optional `linker_script`. The combined
report is written to `combined_pr_comment.md` and `combined_metrics.json`.

## GitHub Action

```yaml
- uses: embedded-pro/cortex-memory-budget@v0
  with:
    config-path: memory-analysis.json
    elf-path: build/firmware.elf
    baseline-elf-path: baseline/firmware.elf   # optional
    target: my-board
    build-config: Release
    cortex: m7
    linker-script-path: firmware.ld            # optional
    fail-over-flash-pct: 85                    # optional
    fail-over-ram-pct: 80                      # optional
```

### Inputs

See [action.yml](../action.yml) for the canonical list. All inputs except
`config-path`, `elf-path`, `target`, and `build-config` are optional.

### Outputs

| Output         | Description                                          |
| -------------- | ---------------------------------------------------- |
| `output-dir`   | Absolute path to the generated report directory      |
| `flash-bytes`  | Total flash image bytes                              |
| `ram-bytes`    | Total RAM bytes (static + stack + heap)              |
| `flash-pct`    | Maximum flash region utilisation percentage          |
| `ram-pct`      | Maximum RAM region utilisation percentage            |

### Reusable workflow

```yaml
jobs:
  memory:
    uses: embedded-pro/cortex-memory-budget/.github/workflows/memory-analysis.yml@v0
    with:
      config-path: memory-analysis.json
      elf-artifact-name: firmware
      elf-path: firmware.elf
      target: my-board
      build-config: Release
      cortex: m7
```
