# cortex-m7 example

STM32H7-like layout: large flash, fast DTCM for `.bss`/`.data` and a
separate AXI SRAM region for the DMA buffer.

Build:

```sh
arm-none-eabi-gcc -mcpu=cortex-m7 -mthumb -mfpu=fpv5-d16 -mfloat-abi=hard \
  -Os -g -nostdlib -ffreestanding -T link.ld -o firmware.elf main.c
```
