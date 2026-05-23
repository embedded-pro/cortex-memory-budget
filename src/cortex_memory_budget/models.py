"""Public dataclasses and exceptions for cortex-memory-budget."""

from __future__ import annotations

from dataclasses import dataclass, field


class ConfigError(Exception):
    """Raised when the JSON configuration is invalid."""


class ToolError(Exception):
    """Raised when an external binutils tool fails or is unavailable."""


@dataclass(frozen=True)
class MemoryRegion:
    """A named memory region from the linker script or config override."""

    name: str          # e.g. "FLASH", "RAM", "DTCM", "AXI_SRAM"
    origin: int        # byte address
    length: int        # bytes
    attrs: str = ""    # e.g. "rx", "rw", "rwx" (best-effort)


@dataclass
class Section:
    """An ELF section as reported by objdump -h."""

    name: str
    size: int
    vma: int           # load/runtime virtual address
    lma: int           # load address (where the image is stored — relevant for .data)
    flags: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_alloc(self) -> bool:
        return "ALLOC" in self.flags

    @property
    def is_load(self) -> bool:
        return "LOAD" in self.flags

    @property
    def is_readonly(self) -> bool:
        return "READONLY" in self.flags

    @property
    def is_code(self) -> bool:
        return "CODE" in self.flags


@dataclass
class Symbol:
    """A symbol entry parsed from `nm -S --print-size`."""

    name: str          # demangled when possible
    raw_name: str      # original (mangled) name as emitted by nm
    address: int
    size: int
    type_char: str     # nm type letter ('T','t','D','d','B','b','R','r','C','W',...)
    section: str = ""  # section name when known
    source_file: str = ""
    object_file: str = ""


@dataclass
class SourceFileGroup:
    """Roll-up of symbols belonging to the same source file."""

    source_file: str
    flash_bytes: int = 0
    ram_static_bytes: int = 0
    symbols: list[Symbol] = field(default_factory=list)


@dataclass
class StackHeapInfo:
    """Pre-allocated stack and heap sizes discovered in the ELF or config."""

    stack_bytes: int = 0
    heap_bytes: int = 0
    stack_source: str = "unknown"   # "symbol:<name>", "section:.stack", "config", "unknown"
    heap_source: str = "unknown"
    diagnostics: list[str] = field(default_factory=list)


@dataclass
class RegionUsage:
    """How a region is filled (in bytes) and by what."""

    region: MemoryRegion
    used_bytes: int = 0
    used_by: dict[str, int] = field(default_factory=dict)  # category -> bytes
    sections: list[Section] = field(default_factory=list)

    @property
    def free_bytes(self) -> int:
        return max(self.region.length - self.used_bytes, 0)

    @property
    def used_pct(self) -> float:
        if self.region.length == 0:
            return 0.0
        return 100.0 * self.used_bytes / self.region.length


@dataclass
class MemoryReport:
    """Top-level analysis result."""

    target: str
    build_config: str
    cortex: str
    elf_path: str
    flash_bytes: int = 0                 # flash image footprint (.text+.rodata+.data init)
    ram_static_bytes: int = 0            # .data + .bss live RAM
    stack_heap: StackHeapInfo = field(default_factory=StackHeapInfo)
    sections: list[Section] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    regions: list[RegionUsage] = field(default_factory=list)
    source_groups: list[SourceFileGroup] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ram_total_bytes(self) -> int:
        return self.ram_static_bytes + self.stack_heap.stack_bytes + self.stack_heap.heap_bytes


@dataclass(frozen=True)
class DiffEntry:
    """One row of a baseline-vs-current diff."""

    kind: str          # "symbol" | "section" | "region"
    name: str
    baseline_bytes: int
    current_bytes: int

    @property
    def delta_bytes(self) -> int:
        return self.current_bytes - self.baseline_bytes

    @property
    def status(self) -> str:
        if self.baseline_bytes == 0 and self.current_bytes > 0:
            return "added"
        if self.current_bytes == 0 and self.baseline_bytes > 0:
            return "removed"
        if self.delta_bytes > 0:
            return "grew"
        if self.delta_bytes < 0:
            return "shrunk"
        return "unchanged"
