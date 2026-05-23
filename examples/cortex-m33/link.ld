ENTRY(Reset_Handler)

MEMORY
{
  FLASH_NS (rx)  : ORIGIN = 0x08000000, LENGTH = 256K
  RAM_NS   (rwx) : ORIGIN = 0x20000000, LENGTH = 32K
  RAM_S    (rw)  : ORIGIN = 0x30000000, LENGTH = 16K
}

_Min_Stack_Size = 0x800;
_Min_Heap_Size  = 0x400;

SECTIONS
{
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH_NS
  .text       : { *(.text*) *(.rodata*) } > FLASH_NS
  .data       : AT(ADDR(.text) + SIZEOF(.text)) { *(.data*) } > RAM_NS
  .bss        : { *(.bss*) *(COMMON) } > RAM_NS
  .s_data     : { *(.s_data*) } > RAM_S
  /DISCARD/   : { *(.ARM*) *(.note*) *(.comment*) }
}
