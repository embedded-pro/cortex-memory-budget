# diff-mode example

Two ELFs — baseline and current — analysed together to surface the
delta in the PR comment / Markdown report.

```sh
arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -Os -g -nostdlib -ffreestanding \
  -T link.ld -o baseline.elf baseline.c
arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -Os -g -nostdlib -ffreestanding \
  -T link.ld -o current.elf  current.c

cortex-memory-budget memory-analysis.json \
  --elf current.elf \
  --baseline-elf baseline.elf \
  --target diff-demo --build-config Release --cortex m4 \
  --linker-script link.ld --output-dir out
```
