"""Thin wrappers around the ARM binutils used by the analyzer."""

from __future__ import annotations

import shutil
import subprocess
import sys

from .models import ToolError


def log(msg: str) -> None:
    """Write a single-line diagnostic to stderr."""
    print(msg, file=sys.stderr)


def _ensure_tool(tool: str) -> str:
    resolved = shutil.which(tool)
    if resolved is None:
        raise ToolError(f"tool not found on PATH: {tool!r}")
    return resolved


def _run(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"failed to execute {args[0]!r}: {exc}") from exc
    if proc.returncode != 0:
        raise ToolError(
            f"{args[0]} exited with status {proc.returncode}:\n{proc.stderr.strip()}"
        )
    return proc.stdout


def run_size(elf_path: str, tool: str = "arm-none-eabi-size") -> str:
    """Run `size -A -d <elf>` and return stdout."""
    _ensure_tool(tool)
    return _run([tool, "-A", "-d", elf_path])


def run_nm(elf_path: str, tool: str = "arm-none-eabi-nm") -> str:
    """Run `nm -S --print-size --size-sort --demangle --print-file-name <elf>`.

    Returns symbols newest-largest first (size-sorted ascending in nm; consumers
    will re-sort as needed).
    """
    _ensure_tool(tool)
    return _run(
        [
            tool,
            "-S",
            "--print-size",
            "--demangle",
            "--print-file-name",
            elf_path,
        ]
    )


def run_objdump_sections(elf_path: str, tool: str = "arm-none-eabi-objdump") -> str:
    """Run `objdump -h -w <elf>` to dump section headers (wide mode)."""
    _ensure_tool(tool)
    return _run([tool, "-h", "-w", elf_path])


def run_addr2line(
    elf_path: str,
    addresses: list[str],
    tool: str = "arm-none-eabi-addr2line",
) -> list[tuple[str, str]]:
    """Resolve a batch of addresses to (function, file:line) tuples.

    Empty list of addresses → returns empty list without invoking the tool.
    """
    if not addresses:
        return []
    _ensure_tool(tool)
    proc_input = "\n".join(addresses) + "\n"
    try:
        proc = subprocess.run(
            [tool, "-f", "-e", elf_path, "-C"],
            input=proc_input,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"failed to execute {tool!r}: {exc}") from exc
    if proc.returncode != 0:
        raise ToolError(
            f"{tool} exited with status {proc.returncode}:\n{proc.stderr.strip()}"
        )
    lines = proc.stdout.splitlines()
    out: list[tuple[str, str]] = []
    for idx in range(0, len(lines), 2):
        func = lines[idx] if idx < len(lines) else ""
        loc = lines[idx + 1] if idx + 1 < len(lines) else ""
        out.append((func, loc))
    return out
