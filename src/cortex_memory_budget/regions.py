"""Resolve the device memory map from linker script and/or config overrides.

Linker-script auto-detect is the primary source. Any region named in the
config under ``regions`` either **overrides** (matched by name) an
auto-detected entry or **adds** a new one. The resulting list is then used to
attribute every allocated section to a region by address containment.
"""

from __future__ import annotations

from typing import Any

from .models import MemoryRegion, RegionUsage, Section
from .sections import classify_section


def merge_regions(
    detected: list[MemoryRegion],
    overrides: list[dict[str, Any]],
) -> tuple[list[MemoryRegion], list[str]]:
    """Merge auto-detected regions with config overrides.

    Override semantics (per region name, case-insensitive):
      * If both sources define a region with the same name, the override's
        ``origin``/``length``/``attrs`` win.
      * Otherwise, the override is appended as a new region.
    """
    warnings: list[str] = []
    by_name: dict[str, MemoryRegion] = {r.name.upper(): r for r in detected}
    for entry in overrides:
        name = str(entry.get("name", "")).strip()
        if not name:
            warnings.append("region override missing 'name'; skipping")
            continue
        try:
            origin = int(entry.get("origin", 0))
            length = int(entry.get("length", 0))
        except (TypeError, ValueError):
            warnings.append(f"region {name!r}: origin/length must be integers; skipping")
            continue
        if length <= 0:
            warnings.append(f"region {name!r}: non-positive length; skipping")
            continue
        attrs = str(entry.get("attrs", "")).strip()
        by_name[name.upper()] = MemoryRegion(name=name, origin=origin, length=length, attrs=attrs)
    return list(by_name.values()), warnings


def _region_contains(region: MemoryRegion, addr: int, size: int) -> bool:
    end = region.origin + region.length
    return region.origin <= addr and addr + size <= end


def _category_for(section: Section) -> str:
    cls = classify_section(section)
    if cls in {"flash", "ram_init", "ram_static", "stack", "heap"}:
        return cls
    return "other"


def assign_sections(
    regions: list[MemoryRegion],
    sections: list[Section],
) -> tuple[list[RegionUsage], list[str]]:
    """Attribute every allocated section to a region by VMA / LMA containment.

    ``.data``-style sections (``ram_init``) are counted **twice**: their LMA
    image goes to the flash region, while their VMA copy goes to the RAM
    region.
    """
    warnings: list[str] = []
    usages: dict[str, RegionUsage] = {r.name: RegionUsage(region=r) for r in regions}

    def _account(region_name: str, section: Section, category: str, bytes_: int) -> None:
        usage = usages[region_name]
        usage.used_bytes += bytes_
        usage.used_by[category] = usage.used_by.get(category, 0) + bytes_
        usage.sections.append(section)

    for sec in sections:
        if not sec.is_alloc or sec.size == 0:
            continue
        category = _category_for(sec)
        if category == "other":
            continue

        # For ram_init (.data), bill flash at LMA as "ram_init" (image stored
        # in flash) and RAM at VMA as "ram_static" (runtime copy).
        targets: list[tuple[int, str]] = []
        if category == "ram_init":
            targets.append((sec.lma, "ram_init"))
            targets.append((sec.vma, "ram_static"))
        else:
            targets.append((sec.vma, category))

        for addr, billing in targets:
            owner = next(
                (r for r in regions if _region_contains(r, addr, sec.size)),
                None,
            )
            if owner is None:
                warnings.append(
                    f"section {sec.name!r} ({sec.size} bytes @ 0x{addr:x}) "
                    f"does not fit any declared region"
                )
                continue
            _account(owner.name, sec, billing, sec.size)

    return list(usages.values()), warnings
