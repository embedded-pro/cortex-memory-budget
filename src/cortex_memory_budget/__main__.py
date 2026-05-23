"""Module entry point: ``python -m cortex_memory_budget``."""

from __future__ import annotations

import sys

from .cli_single import main

if __name__ == "__main__":
    sys.exit(main())
