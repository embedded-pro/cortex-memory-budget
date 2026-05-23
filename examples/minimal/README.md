# minimal example — Cortex-M4

Bare-metal blob with one function, one large RAM buffer, a stack/heap
declared in the linker script and a tiny vector table.

Build:

```sh
arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -Os -g \
  -nostdlib -ffreestanding -T link.ld -o firmware.elf main.c
```

Analyse:

```sh
cortex-memory-budget memory-analysis.json \
  --elf firmware.elf \
  --target minimal-m4 \
  --build-config Release \
  --cortex m4 \
  --linker-script link.ld \
  --output-dir out
```
