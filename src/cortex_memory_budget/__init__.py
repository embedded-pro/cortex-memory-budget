"""Public API for cortex-memory-budget."""

from __future__ import annotations

from .analysis import analyze
from .config import SUPPORTED_CORTEX, validate_config
from .diff import diff_reports
from .linker_script import load_linker_script, parse_linker_script
from .models import (
    ConfigError,
    DiffEntry,
    MemoryRegion,
    MemoryReport,
    RegionUsage,
    Section,
    SourceFileGroup,
    StackHeapInfo,
    Symbol,
    ToolError,
)
from .regions import assign_sections, merge_regions
from .reports import (
    PR_COMMENT_MARKER,
    generate_diff_report,
    generate_json_metrics,
    generate_main_report,
    generate_pr_comment,
)
from .sections import classify_section, parse_sections, summarise
from .stack_heap import detect_stack_heap
from .symbols import parse_symbols

__version__ = "0.2.0"

__all__ = [
    "PR_COMMENT_MARKER",
    "SUPPORTED_CORTEX",
    "ConfigError",
    "DiffEntry",
    "MemoryRegion",
    "MemoryReport",
    "RegionUsage",
    "Section",
    "SourceFileGroup",
    "StackHeapInfo",
    "Symbol",
    "ToolError",
    "__version__",
    "analyze",
    "assign_sections",
    "classify_section",
    "detect_stack_heap",
    "diff_reports",
    "generate_diff_report",
    "generate_json_metrics",
    "generate_main_report",
    "generate_pr_comment",
    "load_linker_script",
    "merge_regions",
    "parse_linker_script",
    "parse_sections",
    "parse_symbols",
    "summarise",
    "validate_config",
]
