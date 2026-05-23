/* Same source as the minimal example — reused to demo multi-mode. */
#include <stdint.h>

volatile uint32_t counter;
uint8_t big_buffer[2048];

void Reset_Handler(void) {
  for (uint32_t i = 0; i < 100; ++i) {
    counter += i;
    big_buffer[i] = (uint8_t)i;
  }
  while (1) {
  }
}

__attribute__((section(".isr_vector"), used))
const void *vector_table[] = {(void *)0x20004000, (void *)Reset_Handler};
