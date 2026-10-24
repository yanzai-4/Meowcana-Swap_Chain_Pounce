// Runs sketch/sketch.ino's real op decoder on the host. Usage: harness ops.bin out.rgb565 [bus mode 0..3]
// ops.bin = repeated [u16 length][op bytes]; writes the 480x320 framebuffer as little-endian RGB565.
// Build with -DARCADE_FAST_BUS=1 to also exercise the direct-GPIO path (modes 1..3) on a modeled bus.
#include "../../sketch/sketch.ino"

int main(int argc, char** argv) {
  if (argc < 3) return 2;
  display.begin();
#if ARCADE_FAST_BUS
  FastBus::init();
  FastBus::mode = argc > 3 ? atoi(argv[3]) : 0;
#endif
  FILE* in = fopen(argv[1], "rb");
  if (!in) return 2;
  static uint8_t buf[4096];
  uint8_t head[2];
  int bad = 0;
  while (fread(head, 1, 2, in) == 2) {
    size_t n = head[0] | (head[1] << 8);
    if (fread(buf, 1, n, in) != n) return 2;
    if (!applyOps(buf, n, false) || !applyOps(buf, n, true)) ++bad;
  }
  fclose(in);
  FILE* out = fopen(argv[2], "wb");
  fwrite(tftModel.fb, 2, 480 * 320, out);
  fclose(out);
  fprintf(stderr, "windows=%ld pushed=%ld strobes=%ld bus_violations=%ld rejected_chunks=%d\n", tftModel.windows,
          tftModel.pushed, tftModel.strobes, tftModel.bad, bad);
  return tftModel.bad ? 3 : 0;
}
