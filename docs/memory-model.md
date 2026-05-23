# Memory model

This document explains exactly **what counts as flash** and **what counts as
RAM** in the generated reports. Getting this right is critical — the same byte
can legitimately appear in both flash and RAM (`.data`), and several
section-flag combinations require careful interpretation.

## Section classification

Each section emitted by `arm-none-eabi-objdump -h -w` is classified by name
and ELF flags into one of:

| Bucket       | Examples                                  | Counts toward      |
| ------------ | ----------------------------------------- | ------------------ |
| `flash`      | `.text`, `.rodata`, `.isr_vector`, `.ARM*`| **Flash**          |
| `ram_static` | `.bss`, `.noinit`, `COMMON`               | **RAM (static)**   |
| `ram_init`   | LMA copy of `.data`                       | **Flash** (image)  |
| `ram_static` | VMA copy of `.data`                       | **RAM** (live)     |
| `stack`      | `.stack`, `.stackArea`                    | **RAM (stack)**    |
| `heap`       | `.heap`, `.heapArea`                      | **RAM (heap)**     |
| `debug`      | `.debug_*`, `.comment`, `.symtab`, …      | _ignored_          |
| `ignored`    | non-`ALLOC` sections                      | _ignored_          |

### `.data` is counted **twice**

`.data` lives at two addresses in the ELF: its **load address (LMA)** in
flash (the initialisation image) and its **virtual address (VMA)** in RAM
(the live, writable copy that the startup code populates on reset).

Both are real and both consume memory:

- The LMA contributes to the **flash** region containing it
  (`used_by["ram_init"]`).
- The VMA contributes to the **RAM** region containing it
  (`used_by["ram_static"]`).

A 4 KiB `.data` therefore costs 4 KiB of flash **and** 4 KiB of RAM. This is
the same accounting that `arm-none-eabi-size` does.

### COMMON symbols (nm type `C`)

`nm` reports uninitialised globals as `C` (COMMON) when the link hasn't
folded them into `.bss` yet, or for objects compiled with
`-fno-common` disabled. We treat them as `.bss` (RAM static).

### ARM unwind sections

`.ARM.exidx`, `.ARM.extab`, `.ARM.attributes` are classified as flash —
they're emitted into the load image for exception unwinding.

### Debug & metadata

`.debug_*`, `.comment`, `.symtab`, `.strtab`, `.shstrtab`, etc. are tagged
as `debug` and excluded from both flash and RAM totals — they're not loaded
to the device.

## Stack & heap

Stack and heap are **pre-allocated** in the linker script. They are detected,
in order of precedence:

1. **Config override** (`stack_size_bytes`, `heap_size_bytes`) — always wins.
2. **Size symbols** (`_Min_Stack_Size`, `__stack_size__`, …) — the symbol's
   `nm` size attribute, or its address treated as a value when the size is 0
   (typical for ABS symbols defined with `= 0x800;`).
3. **Limit pairs** (`__StackLimit`/`__StackTop`, `__HeapBase`/`__HeapLimit`,
   …) — subtraction of the two addresses.
4. **Dedicated sections** (`.stack`, `.heap`) — section size from the
   section table.

Whichever method succeeds first wins. The chosen source (`stack_source` /
`heap_source` field in the JSON metrics) tells you which.

## Region assignment

Each `ALLOC` section is assigned to the **single** declared region whose
`[origin, origin + length)` window contains the section's load (LMA) and/or
virtual (VMA) address. A section that straddles two regions yields a warning
that names the section, the address, and both candidate regions — the
analysis still proceeds but the report flags the inconsistency for review.

Regions detected from the linker script and regions supplied in the config
are merged case-insensitively; config overrides win field-by-field for any
matching region name.
