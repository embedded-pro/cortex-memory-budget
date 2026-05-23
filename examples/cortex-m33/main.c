/* Cortex-M33 (Armv8-M Mainline) example with split secure/non-secure RAM. */
#include <stdint.h>

volatile uint32_t ns_counter;
uint8_t ns_buffer[1024];
uint8_t s_buffer[256] __attribute__((section(".s_data")));

void Reset_Handler(void) {
  for (uint32_t i = 0; i < 256; ++i) {
    ns_counter += i;
    ns_buffer[i % sizeof(ns_buffer)] = (uint8_t)(i ^ 0x5A);
    s_buffer[i % sizeof(s_buffer)] = (uint8_t)i;
  }
  while (1) {
  }
}

__attribute__((section(".isr_vector"), used))
const void *vector_table[] = {(void *)0x20008000, (void *)Reset_Handler};
