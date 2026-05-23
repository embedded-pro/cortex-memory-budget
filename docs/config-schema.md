# Configuration schema

The memory-analysis config is a JSON object. All fields are optional; the
minimum valid config is `{}`.

```json
{
  "top_n_symbols": 20,
  "top_n_source_files": 15,
  "regions": [
    {"name": "FLASH", "length_kb": 1024, "origin": "0x08000000"},
    {"name": "SRAM",  "length_kb": 192}
  ],
  "stack_size_symbols": ["_Min_Stack_Size", "__stack_size__"],
  "heap_size_symbols":  ["_Min_Heap_Size",  "__heap_size__"],
  "stack_limit_pairs":  [["__StackLimit", "__StackTop"]],
  "heap_limit_pairs":   [["__HeapBase",   "__HeapLimit"]],
  "stack_size_bytes": null,
  "heap_size_bytes":  null
}
```

## Fields

| Field                  | Type                       | Default | Description                                                 |
| ---------------------- | -------------------------- | ------- | ----------------------------------------------------------- |
| `top_n_symbols`        | int ≥ 0                    | 20      | Maximum number of largest symbols listed per region         |
| `top_n_source_files`   | int ≥ 0                    | 15      | Maximum number of source files listed                       |
| `regions`              | list of region overrides   | `[]`    | Region overrides; merged onto linker-script-detected ones   |
| `stack_size_symbols`   | list of strings            | _built-in defaults_ | Symbols whose value/size declares the stack budget |
| `heap_size_symbols`    | list of strings            | _built-in defaults_ | Symbols whose value/size declares the heap budget  |
| `stack_limit_pairs`    | list of `[low, high]` pairs| _built-in defaults_ | Address-pair fallback for stack reservation        |
| `heap_limit_pairs`     | list of `[low, high]` pairs| _built-in defaults_ | Address-pair fallback for heap reservation         |
| `stack_size_bytes`     | int ≥ 0 _or_ null          | `null`  | Hard override for the stack budget (skip detection)         |
| `heap_size_bytes`      | int ≥ 0 _or_ null          | `null`  | Hard override for the heap budget (skip detection)          |

### Region overrides

Each region override is an object:

```json
{"name": "FLASH", "length_kb": 1024, "origin": "0x08000000", "attrs": "rx"}
```

| Field        | Required | Description                                                |
| ------------ | :------: | ---------------------------------------------------------- |
| `name`       |   ✅     | Region name; matches linker-script names case-insensitively |
| `length_kb`  |   ✅     | Region size in kilobytes (1 KiB = 1024 bytes)              |
| `origin`     |          | Decimal or `0x…` hex base address                          |
| `attrs`      |          | Attribute string (e.g. `"rx"`, `"rwx"`)                    |

Overrides always win over linker-script-detected values for the same name.
Override-only regions (no linker-script counterpart) are appended verbatim.

### Built-in detection defaults

```text
stack_size_symbols = (_Min_Stack_Size, __stack_size__, __STACK_SIZE, _stack_size, __StackSize)
heap_size_symbols  = (_Min_Heap_Size,  __heap_size__,  __HEAP_SIZE,  _heap_size,  __HeapSize)
stack_limit_pairs  = ((__StackLimit, __StackTop), (_sstack, _estack))
heap_limit_pairs   = ((__HeapBase, __HeapLimit), (_sheap, _eheap), (__heap_start, __heap_end))
```

See also [docs/memory-analysis.schema.json](memory-analysis.schema.json) for a
machine-readable JSON Schema (Draft-07).
