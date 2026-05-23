# Linker-script detection

`cortex-memory-budget` reads a GNU linker script (`*.ld`) passed via
`--linker-script` to auto-detect the **memory regions** of your target. It
parses the `MEMORY { … }` block; everything else (`SECTIONS`, `PROVIDE`,
`ENTRY`, etc.) is ignored at this stage.

## Supported `MEMORY` syntax

```ld
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
    SRAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 128 * 1024
    ITCM  (xrw) : ORIGIN = 0x00000000, LENGTH = 64KB
    DTCM  (rw)  : ORIGIN = 0x20000000, LENGTH = 128M - 1K
}
```

### Expressions

`ORIGIN` and `LENGTH` are evaluated with a deliberately small expression
language that **only** supports:

- Decimal integers: `1024`
- Hexadecimal integers: `0x08000000`, `0xFF`
- Multiplier suffixes (case-insensitive): `K`, `KB`, `M`, `MB`
- Binary operators: `+`, `-`, `*`
- Parentheses

Anything else (function calls, references to other symbols, `?:`,
bit-shifts) is unsupported. A region whose expression can't be evaluated is
**skipped** and a warning is recorded — it never silently produces bogus
sizes.

### Attribute strings

The parenthesised attributes (`(rx)`, `(rwx)`, `(xrw!a)`, …) are captured
verbatim into the region's `attrs` field and used by the CLI to classify
regions as flash-like (`X` + `R` and not `W`) or RAM-like (`W` present, or
name contains `RAM`/`SRAM`/`DTCM`/`ITCM`/`AXI`).

## Combining with config overrides

Linker-script-detected regions and config-supplied regions are merged
case-insensitively by name. Config overrides **always win** field-by-field
for matching names. Config-only regions are appended verbatim. This lets you
mix:

- `--linker-script` for a complex board file you don't want to duplicate.
- `regions:` in the config for a single override (e.g. carving an OTA slot
  out of FLASH).

## What's _not_ parsed

- `INCLUDE` directives — the script is read as a single flat file.
- Symbol assignments that influence region sizes (e.g. `_estack = …;`).
  These are still picked up by `nm` for stack/heap detection (see
  [memory-model.md](memory-model.md)).
- C preprocessor directives — feed the post-`cpp` script if you use them.

## Limits

The parser is intentionally conservative: it favours rejecting an ambiguous
region (with a warning) over guessing. If your linker script uses advanced
features the parser doesn't support, supply the affected region(s)
explicitly in the JSON config — they will override whatever the parser
produced.
