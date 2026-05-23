# cortex-m33 example

Split secure / non-secure RAM regions, like a TrustZone-enabled target.

```sh
arm-none-eabi-gcc -mcpu=cortex-m33 -mthumb -Os -g \
  -nostdlib -ffreestanding -T link.ld -o firmware.elf main.c
```
