# Architecture

`cortex-memory-budget` is a small Python package organised as a one-way
pipeline from "ELF on disk" to "Markdown + JSON reports". No persistent
state, no daemon, no plugin system.

## Module layout (`src/cortex_memory_budget/`)

```
__init__.py          # Public API re-exports
__main__.py          # python -m cortex_memory_budget → cli_single.main

cli_single.py        # CLI entry point: cortex-memory-budget
cli_multi.py         # CLI entry point: cortex-memory-budget-multi

config.py            # Config loading + validation
models.py            # Dataclasses (Symbol, Section, MemoryRegion, MemoryReport, DiffEntry, …)

tooling.py           # Thin wrappers around nm / objdump / addr2line
linker_script.py     # MEMORY {} block parser
sections.py          # objdump -h output parser + section classifier
symbols.py           # nm output parser
dwarf.py             # addr2line batch resolver
regions.py           # Region merge (linker + config) and section assignment
stack_heap.py        # Stack/heap budget detection
analysis.py          # Pipeline orchestrator → MemoryReport
diff.py              # diff_reports(baseline, current) → list[DiffEntry]
reports.py           # Markdown + JSON renderers
```

## Data flow

```
                 ┌────────────────────────────────────────────────┐
ELF file ──▶ tooling ──▶ {sections, symbols, addr2line, ld script}┘
                                          │
                                          ▼
        ┌──────────── analysis.analyze() ───────────┐
        │                                            │
        │  parse_sections ──┐                        │
        │  parse_symbols ───┤                        │
        │  attach_source_files (DWARF)               │
        │  load_linker_script ─▶ merge_regions       │
        │  assign_sections                           │
        │  detect_stack_heap                         │
        │  group_by_source_file                      │
        │                                            │
        └──────────────────┬─────────────────────────┘
                           ▼
                    MemoryReport
                           │
        ┌──────────────────┼──────────────────────────┐
        ▼                  ▼                          ▼
 reports.generate_   reports.generate_         reports.generate_
  main_report          pr_comment                json_metrics
        │                  │                          │
  memory_report.md   pr_comment.md            memory_metrics.json

         (optional: diff.diff_reports → memory_diff.md)
```

## Design constraints

- **Python ≥ 3.11, stdlib only** at runtime. Dev-only deps (`ruff`, `mypy`,
  `pytest`, `coverage`) are isolated in the `[dev]` extra.
- **No global state.** Every module exposes pure functions that take their
  inputs and return their outputs.
- **Strict typing.** `mypy --strict` passes on the whole package.
- **Subprocess boundaries are explicit.** All shell-outs go through
  `tooling._run()` and are exercised end-to-end by `tests/integration/`.
- **Defensive parsing.** The linker-script parser and the objdump parser
  both prefer to warn and skip over guessing.

## Testing strategy

| Layer        | Location                       | What it covers                              |
| ------------ | ------------------------------ | ------------------------------------------- |
| Unit         | `tests/unit/`                  | One module per test file, pure-Python only  |
| Integration  | `tests/integration/test_e2e.py`| Real `arm-none-eabi-gcc` + linker script + CLI |
| Smoke        | CI `action-smoke` job          | Composite action end-to-end on 3 examples   |

## Extending

- **A new region heuristic** — add to `cli_single._is_flashy` /
  `_is_ramy` (or generalise to per-cortex tables if the heuristics diverge).
- **A new stack/heap convention** — add the symbol names to
  `stack_heap.DEFAULT_*` and the configurable lists in `config`.
- **A new report format** — add a function to `reports.py` and a CLI flag.
  Keep the existing four outputs unchanged.
- **A new diff comparator** — extend `diff.py`; tests in
  `tests/unit/test_diff.py` enumerate the existing classification matrix.
