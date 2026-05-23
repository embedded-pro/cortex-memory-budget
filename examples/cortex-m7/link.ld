ENTRY(Reset_Handler)

MEMORY
{
  FLASH    (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
  DTCM     (rwx) : ORIGIN = 0x20000000, LENGTH = 64K
  AXI_SRAM (rw)  : ORIGIN = 0x24000000, LENGTH = 256K
}

_Min_Stack_Size = 0x1000;
_Min_Heap_Size  = 0x800;

SECTIONS
{
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
  .text       : { *(.text*) *(.rodata*) } > FLASH
  .data       : AT(ADDR(.text) + SIZEOF(.text)) { *(.data*) } > DTCM
  .bss        : { *(.bss*) *(COMMON) } > DTCM
  .axi_data   : { *(.axi_data*) } > AXI_SRAM
  /DISCARD/   : { *(.ARM*) *(.note*) *(.comment*) }
}
