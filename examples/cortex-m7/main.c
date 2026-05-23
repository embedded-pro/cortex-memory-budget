/* Cortex-M7 example with AXI SRAM region and a few FPU operations. */
#include <stdint.h>

volatile float samples[256];
volatile float result;
uint8_t axi_buffer[4096] __attribute__((section(".axi_data")));

/* Small polynomial Hann-window approximation (avoids pulling in libm). */
static float window(float x) {
  float c1 = 1.0f - 0.5f * x * x;
  float c3 = c1 + (x * x * x * x) / 24.0f;
  return 0.5f - 0.5f * c3;
}

void Reset_Handler(void) {
  for (int i = 0; i < 256; ++i) {
    float x = (float)i / 256.0f * 6.283185f;
    samples[i] = window(x);
  }
  float acc = 0.0f;
  for (int i = 0; i < 256; ++i) {
    acc += samples[i] * samples[i];
    axi_buffer[i] = (uint8_t)(samples[i] * 255.0f);
  }
  result = acc;
  while (1) {
  }
}

__attribute__((section(".isr_vector"), used))
const void *vector_table[] = {(void *)0x20010000, (void *)Reset_Handler};
