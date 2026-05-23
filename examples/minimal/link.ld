ENTRY(Reset_Handler)

MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 128K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 16K
}

_Min_Stack_Size = 0x400;
_Min_Heap_Size  = 0x200;

SECTIONS
{
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
  .text       : { *(.text*) *(.rodata*) } > FLASH
  .data       : AT(ADDR(.text) + SIZEOF(.text)) { *(.data*) } > RAM
  .bss        : { *(.bss*) *(COMMON) } > RAM
  /DISCARD/   : { *(.ARM*) *(.note*) *(.comment*) }
}
