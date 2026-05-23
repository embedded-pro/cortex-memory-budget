"""Tests for the linker-script MEMORY parser."""

from __future__ import annotations

import pytest

from cortex_memory_budget.linker_script import _eval_size, parse_linker_script


class TestEvalSize:
    @pytest.mark.parametrize(
        ("expr", "expected"),
        [
            ("1024", 1024),
            ("0x100", 256),
            ("0X100", 256),
            ("1K", 1024),
            ("4kb", 4096),
            ("1M", 1024 * 1024),
            ("2 * 1024", 2048),
            ("(64K + 8K)", 72 * 1024),
            ("1M - 4K", 1024 * 1024 - 4096),
        ],
    )
    def test_supported_expressions(self, expr: str, expected: int) -> None:
        assert _eval_size(expr) == expected

    @pytest.mark.parametrize("expr", ["", "ALIGN(4)", "ABS(0x10)", "foo + 1"])
    def test_rejects_unsupported_expressions(self, expr: str) -> None:
        with pytest.raises(ValueError):
            _eval_size(expr)


class TestParseLinkerScript:
    def test_simple_stm32_layout(self) -> None:
        script = """
        /* STM32F407 */
        MEMORY
        {
          FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
          RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
          CCMRAM (rw) : ORIGIN = 0x10000000, LENGTH = 64K
        }
        """
        regions, warnings = parse_linker_script(script)
        names = [r.name for r in regions]
        assert names == ["FLASH", "RAM", "CCMRAM"]
        assert regions[0].origin == 0x08000000
        assert regions[0].length == 1024 * 1024
        assert "rx" in regions[0].attrs.lower()
        assert warnings == []

    def test_handles_arithmetic(self) -> None:
        script = "MEMORY { FLASH (rx) : ORIGIN = 0x08000000 + 0x4000, LENGTH = 2M - 16K }"
        regions, _ = parse_linker_script(script)
        assert regions[0].origin == 0x08004000
        assert regions[0].length == 2 * 1024 * 1024 - 16 * 1024

    def test_missing_memory_block(self) -> None:
        regions, warnings = parse_linker_script("SECTIONS { .text : { *(.text) } }")
        assert regions == []
        assert any("no MEMORY" in w for w in warnings)

    def test_unparseable_expression_warns_and_skips(self) -> None:
        script = "MEMORY { FLASH (rx) : ORIGIN = 0x0, LENGTH = ALIGN(0x100) }"
        regions, warnings = parse_linker_script(script)
        assert regions == []
        assert any("FLASH" in w for w in warnings)

    def test_comments_stripped(self) -> None:
        script = """
        // line comment
        MEMORY {
          /* block
             comment */
          FLASH (rx) : ORIGIN = 0, LENGTH = 1K
        }
        """
        regions, warnings = parse_linker_script(script)
        assert len(regions) == 1
        assert warnings == []
