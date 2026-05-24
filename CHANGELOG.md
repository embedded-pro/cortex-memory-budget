# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0](https://github.com/embedded-pro/cortex-memory-budget/compare/v0.1.0...v0.2.0) (2026-05-24)


### Features

* initial cortex-memory-budget v0.1.0 release ([141e371](https://github.com/embedded-pro/cortex-memory-budget/commit/141e371d72a4d7cfa318d26551ebaf64179bdde0))


### Bug Fixes

* action ([#10](https://github.com/embedded-pro/cortex-memory-budget/issues/10)) ([8202112](https://github.com/embedded-pro/cortex-memory-budget/commit/82021126c96f4daee482d3556e79449b888fc2cb))

## [0.1.0] - Unreleased

### Added
- Initial release of `cortex-memory-budget`.
- ELF analysis for Cortex-M0 / M4 / M7 / M33 producing flash, RAM static,
  pre-allocated stack and heap totals.
- Linker-script `MEMORY {}` block auto-detection with JSON-config overrides.
- Per-section, top-N symbol, and per-source-file (via DWARF/`addr2line`)
  breakdowns.
- Pre-allocated stack/heap detection with symbol-based primary, address-pair
  fallback, dedicated-section fallback, and explicit config override.
- Diff mode against a baseline ELF producing per-symbol / per-section /
  per-region deltas.
- Multi-mode CLI for analysing several configs in one run.
- GitHub composite action with idempotent PR comment, step summary, and
  artifact upload.
- Reusable GitHub Actions workflow.
- `--fail-over-flash-pct` / `--fail-over-ram-pct` CI gates.
- Five runnable examples: `minimal`, `cortex-m7`, `cortex-m33`,
  `multi-mode`, `diff-mode`.
