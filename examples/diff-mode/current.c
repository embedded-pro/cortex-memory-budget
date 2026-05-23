/* "Current" build — same as baseline.c but with a bigger buffer. */
#include <stdint.h>

volatile uint32_t counter;
uint8_t growing_buffer[4096];

void Reset_Handler(void) {
  for (uint32_t i = 0; i < 100; ++i) {
    counter += i;
    growing_buffer[i % sizeof(growing_buffer)] = (uint8_t)i;
  }
  while (1) {
  }
}

__attribute__((section(".isr_vector"), used))
const void *vector_table[] = {(void *)0x20004000, (void *)Reset_Handler};
