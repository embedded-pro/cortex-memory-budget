# Troubleshooting

## "Tool not found: arm-none-eabi-objdump"

Install the ARM GNU toolchain (Debian/Ubuntu):

```bash
sudo apt-get install -y --no-install-recommends gcc-arm-none-eabi
```

Or pass `--objdump /path/to/your/objdump` (and `--nm`, `--addr2line`).

## "flash=0 ram_static=0" on a real ELF

Almost always a section-parsing mismatch. Run:

```bash
arm-none-eabi-objdump -h -w your.elf
```

If the output is in the **single-line** format (flags appended to the same
line as the size/VMA/LMA), it should be supported. If not, please open an
issue with the verbatim output. As a workaround, add explicit `regions:` to
your JSON config.

## Region "FLASH" never appears in the report

Make sure your linker script's `MEMORY {}` block declares a region whose
**name** matches one of the heuristics or whose **attributes** include `X`
and `R` without `W`. Otherwise add it via the config:

```json
{"regions": [{"name": "FLASH", "length_kb": 1024, "attrs": "rx"}]}
```

## "Section straddles two regions"

A section's `[address, address + size)` window overlaps the boundary
between two declared regions. Either:

- Fix the linker script so the section is contained in exactly one region.
- If the overlap is intentional, expand one region in the config so the
  whole section fits.

## Stack/heap reported as 0 bytes

The default detection looks for well-known symbols (`_Min_Stack_Size`,
`__StackLimit`/`__StackTop`, etc.) and falls back to dedicated `.stack` /
`.heap` sections. If your project uses different names, add them to the
config:

```json
{
  "stack_size_symbols": ["my_stack_size"],
  "heap_limit_pairs":   [["my_heap_lo", "my_heap_hi"]]
}
```

Or force the value with `stack_size_bytes` / `heap_size_bytes`.

## DWARF source files show as `??`

`addr2line` couldn't map the symbol's address back to a source line —
typically because the ELF wasn't built with `-g`, or because the symbol is
in a linker-generated section. The analyzer falls back to the object-file
name reported by `nm --print-file-name`, which is usually still informative.

Re-build with `-g` (or pass `--no-dwarf` to skip the lookup entirely if you
don't need source-file attribution).

## CI gate fires unexpectedly

`--fail-over-flash-pct` / `--fail-over-ram-pct` check **every** declared
region. If a tiny region (e.g. backup SRAM, 4 KiB) goes over the threshold
because a single variable was placed there, the gate trips. Either raise
the threshold or list that region with a larger `length_kb` in the config.

## "unknown name 'XYZ'" from the linker-script parser

The expression evaluator only understands integer constants, `K`/`M` /
`KB`/`MB` suffixes, `+`/`-`/`*`, and parentheses (see
[linker-script-detection.md](linker-script-detection.md)). For
unsupported expressions, supply the region explicitly in the JSON config.
