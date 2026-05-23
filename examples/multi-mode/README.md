# multi-mode example

Same ELF, two configs (`release.json` and `strict.json`). Use the
`cortex-memory-budget-multi` entry point.

```sh
arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -Os -g \
  -nostdlib -ffreestanding -T link.ld -o firmware.elf main.c

cortex-memory-budget-multi analyses.json \
  --target multi-demo --build-config Release --cortex m4 \
  --output-dir out
```
