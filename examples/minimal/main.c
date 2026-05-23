/* Minimal Cortex-M4 example for cortex-memory-budget. */
#include <stdint.h>

volatile uint32_t counter;
uint8_t big_buffer[2048];
const uint32_t version_marker[] = {0xDEAD0001, 0xC0FFEE42};

static uint32_t multiply(uint32_t a, uint32_t b) { return a * b; }

void Reset_Handler(void) {
  for (uint32_t i = 0; i < 100; ++i) {
    counter = multiply(counter + 1, 2);
    big_buffer[i % sizeof(big_buffer)] = (uint8_t)i;
  }
  while (1) {
  }
}

__attribute__((section(".isr_vector"), used))
const void *vector_table[] = {(void *)0x20004000, (void *)Reset_Handler};
