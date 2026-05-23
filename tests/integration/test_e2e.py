"""Tests for the single-mode CLI."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ARM_GCC = shutil.which("arm-none-eabi-gcc")
ARM_OBJDUMP = shutil.which("arm-none-eabi-objdump")
ARM_NM = shutil.which("arm-none-eabi-nm")
ARM_ADDR2LINE = shutil.which("arm-none-eabi-addr2line")
TOOLCHAIN_READY = all([ARM_GCC, ARM_OBJDUMP, ARM_NM, ARM_ADDR2LINE])

MINIMAL_C = """
#include <stdint.h>

volatile uint32_t counter;
uint8_t big_static[1024];

uint32_t multiply(uint32_t a, uint32_t b) { return a * b; }

void Reset_Handler(void) {
    for (uint32_t i = 0; i < 100; ++i) {
        counter = multiply(counter + 1, 2);
        big_static[i % 1024] = (uint8_t)i;
    }
    while (1) { }
}

__attribute__((section(".isr_vector"), used))
const void *vector_table[] = { (void *)0x20002000, (void *)Reset_Handler };
"""

MINIMAL_LD = """
ENTRY(Reset_Handler)
MEMORY {
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 64K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 16K
}
_Min_Stack_Size = 0x800;
_Min_Heap_Size  = 0x400;
SECTIONS {
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
  .text       : { *(.text*) *(.rodata*) } > FLASH
  .data       : AT(ADDR(.text) + SIZEOF(.text)) { *(.data*) } > RAM
  .bss        : { *(.bss*) *(COMMON) } > RAM
  /DISCARD/   : { *(.ARM*) *(.note*) *(.comment*) }
}
"""


@pytest.fixture(scope="session")
def example_elf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not TOOLCHAIN_READY:
        pytest.skip("arm-none-eabi toolchain not available")
    workdir = tmp_path_factory.mktemp("e2e")
    src = workdir / "main.c"
    ld = workdir / "link.ld"
    elf = workdir / "firmware.elf"
    src.write_text(MINIMAL_C)
    ld.write_text(MINIMAL_LD)
    subprocess.run(
        [
            ARM_GCC, "-mcpu=cortex-m4", "-mthumb", "-Os", "-g",
            "-nostdlib", "-ffreestanding", "-T", str(ld),
            "-o", str(elf), str(src),
        ],
        check=True,
    )
    return elf


@pytest.mark.parametrize("cortex", ["m0", "m4", "m7", "m33"])
def test_cli_end_to_end_with_real_elf(
    tmp_path: Path,
    example_elf: Path,
    cortex: str,
) -> None:
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"top_n_symbols": 5}))
    out_dir = tmp_path / f"out-{cortex}"

    result = subprocess.run(
        [
            "python3", "-m", "cortex_memory_budget",
            str(config),
            "--elf", str(example_elf),
            "--target", f"test-{cortex}",
            "--build-config", "Release",
            "--cortex", cortex,
            "--output-dir", str(out_dir),
            "--linker-script", str(example_elf.parent / "link.ld"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}"

    metrics = json.loads((out_dir / "memory_metrics.json").read_text())
    assert metrics["cortex"] == cortex
    assert metrics["flash_bytes"] > 0
    assert metrics["ram_static_bytes"] >= 1024  # big_static
    assert metrics["stack_bytes"] == 0x800
    assert metrics["heap_bytes"] == 0x400
    assert any("FLASH" in r["name"] for r in metrics["regions"])

    pr = (out_dir / "pr_comment.md").read_text()
    assert "<!-- cortex-memory-budget-comment -->" in pr
    assert "multiply" in pr or "big_static" in pr


def test_cli_diff_mode(tmp_path: Path, example_elf: Path) -> None:
    if not TOOLCHAIN_READY:
        pytest.skip("toolchain missing")
    # Rebuild a bigger ELF as the "current"
    bigger_c = MINIMAL_C.replace("big_static[1024]", "big_static[2048]")
    workdir = tmp_path / "bigger"
    workdir.mkdir()
    (workdir / "main.c").write_text(bigger_c)
    (workdir / "link.ld").write_text(MINIMAL_LD)
    bigger_elf = workdir / "firmware.elf"
    subprocess.run(
        [
            ARM_GCC, "-mcpu=cortex-m4", "-mthumb", "-Os", "-g",
            "-nostdlib", "-ffreestanding", "-T", str(workdir / "link.ld"),
            "-o", str(bigger_elf), str(workdir / "main.c"),
        ],
        check=True,
    )

    config = tmp_path / "config.json"
    config.write_text("{}")
    out_dir = tmp_path / "diff-out"
    result = subprocess.run(
        [
            "python3", "-m", "cortex_memory_budget",
            str(config),
            "--elf", str(bigger_elf),
            "--baseline-elf", str(example_elf),
            "--target", "diff", "--build-config", "Release", "--cortex", "m4",
            "--output-dir", str(out_dir),
            "--linker-script", str(workdir / "link.ld"),
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    diff_md = (out_dir / "memory_diff.md").read_text()
    assert "big_static" in diff_md


def test_cli_fail_over_ram_pct(tmp_path: Path, example_elf: Path) -> None:
    if not TOOLCHAIN_READY:
        pytest.skip("toolchain missing")
    config = tmp_path / "config.json"
    config.write_text("{}")
    out_dir = tmp_path / "fail-out"
    result = subprocess.run(
        [
            "python3", "-m", "cortex_memory_budget",
            str(config),
            "--elf", str(example_elf),
            "--target", "fail", "--build-config", "Release", "--cortex", "m4",
            "--output-dir", str(out_dir),
            "--linker-script", str(example_elf.parent / "link.ld"),
            "--fail-over-ram-pct", "0.01",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "FAIL" in result.stderr
