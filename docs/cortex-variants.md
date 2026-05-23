# Cortex-M variants

`cortex-memory-budget` works with **Cortex-M0**, **Cortex-M4**, **Cortex-M7**,
and **Cortex-M33** ELFs. The memory analysis itself is **architecture-agnostic
post-link** — it operates on the ELF, not on instruction semantics — so the
`--cortex` flag is a label used in reports rather than a switch that changes
classification logic.

Where the variants matter is in the **typical memory layout** you should
expect, and consequently which region names appear in your linker script.

## Cortex-M0 / M0+

- Usually a single `FLASH` region (often 16–256 KiB) and a single `SRAM`
  region (often 4–64 KiB).
- No FPU, no DSP — `.rodata` tends to dominate flash on math-heavy code.
- No cache; what you see in `.text` is what you pay for.

## Cortex-M4

- Single `FLASH`, single `SRAM`. Some vendors split SRAM into a small CCM
  (Core-Coupled Memory, e.g. STM32F4 `CCMRAM` 64 KiB) addressable only by
  the CPU (no DMA). Treat it as a separate region.
- Single-precision FPU. Floating-point constants in `.rodata` are common.

## Cortex-M7

- Often **two RAM regions**: tightly-coupled DTCM (no wait states, single
  cycle) and AXI SRAM (cacheable, DMA-accessible). Plus ITCM for code that
  must run with deterministic timing.
- Optional I-cache and D-cache. **Cache contents are NOT in the ELF**; only
  the backing memory is.
- Pay attention to which RAM bank holds `.data` and `.bss` — your linker
  script chooses, the analyzer just reports what's there.

## Cortex-M33

- Optional FPU and DSP. Optional TrustZone (separates S / NS regions, but
  the static image is still a single ELF unless you produce two).
- May have multiple SRAM banks (e.g. AN555: `SRAM0`/`SRAM1`/`SRAM2`).

## What `--cortex` actually changes today

Currently only the label in the generated reports. It is validated against
the supported set (`m0`, `m4`, `m7`, `m33`) and forwarded to the JSON
metrics so downstream tools can pivot on it.

Future versions may add per-variant heuristics (e.g. flagging non-cacheable
`.data` placed in cacheable RAM on M7), but the static post-link accounting
remains the same across all four variants.
