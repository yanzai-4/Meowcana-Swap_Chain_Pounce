#pragma once
#include "Arduino.h"
#include "stm32_ll_gpio.h"

// The TFT controller as seen from the bus: 8080 writes decoded into a 480x320 RGB565 framebuffer.
struct TftModel {
  uint16_t fb[480 * 320];
  int wx0 = 0, wy0 = 0, wx1 = 479, wy1 = 319, cx = 0, cy = 0;
  long windows = 0, pushed = 0, strobes = 0, bad = 0;
  int cmd = -1, argc = 0;
  int args[4];
  bool high = true;
  uint8_t hiByte = 0;
  void window(int x0, int y0, int x1, int y1) { wx0 = x0; wy0 = y0; wx1 = x1; wy1 = y1; cx = x0; cy = y0; ++windows; }
  void pixel(uint16_t c) {
    if (cx >= 0 && cx < 480 && cy >= 0 && cy < 320) fb[cy * 480 + cx] = c;
    if (++cx > wx1) { cx = wx0; ++cy; }
    ++pushed;
  }
  // One rising WR edge: latch the data lines.
  void write(bool cd, uint8_t v) {
    ++strobes;
    if (!cd) { cmd = v; argc = 0; high = true; if (v == 0x2C) { cx = wx0; cy = wy0; } return; }
    if (cmd == 0x2A || cmd == 0x2B) {
      args[argc++ & 3] = v;
      if (argc == 4) {
        int a = args[0] << 8 | args[1], b = args[2] << 8 | args[3];
        if (cmd == 0x2A) { wx0 = a; wx1 = b; } else { wy0 = a; wy1 = b; }
        ++windows; argc = 0;
      }
    } else if (cmd == 0x2C) {
      if (high) hiByte = v; else pixel(hiByte << 8 | v);
      high = !high;
    }
  }
};
inline TftModel tftModel;

inline void BsrrReg::operator=(uint32_t v) {
  bool wasHigh = pinHigh(15);  // A1 = WR
  owner->odr = (owner->odr & ~(v >> 16)) | (v & 0xFFFF);  // set wins over reset
  if (!wasHigh && pinHigh(15)) {
    if (pinHigh(17) || !pinHigh(14)) ++tftModel.bad;  // CS (A3) must stay low, RD (A0) high
    static const int dataPins[8] = {8, 9, 2, 3, 4, 5, 6, 7};
    uint8_t byte = 0;
    for (int i = 0; i < 8; ++i) byte |= pinHigh(dataPins[i]) << i;
    tftModel.write(pinHigh(16), byte);  // CD = A2
  }
}

struct DIYables_TFT_HX8357D_Shield {
  void begin() {
    // What the library leaves behind: pins are outputs, RD high, CS low, WR high.
    locate(14).port->odr |= 1u << locate(14).bit;
    locate(15).port->odr |= 1u << locate(15).bit;
    locate(16).port->odr |= 1u << locate(16).bit;
  }
  void setRotation(int) {}
  int width() const { return 480; }
  int height() const { return 320; }
  void setAddrWindow(int x0, int y0, int x1, int y1) { tftModel.window(x0, y0, x1, y1); tftModel.cx = x0; tftModel.cy = y0; }
  void pushColors(uint16_t* c, int n) { for (int i = 0; i < n; ++i) tftModel.pixel(c[i]); }
  void fillRect(int x, int y, int w, int h, uint16_t c) {
    for (int j = max(y, 0); j < min(y + h, 320); ++j)
      for (int i = max(x, 0); i < min(x + w, 480); ++i) tftModel.fb[j * 480 + i] = c;
  }
  void fillScreen(uint16_t c) { fillRect(0, 0, 480, 320, c); }
  void drawRect(int x, int y, int w, int h, uint16_t c) {
    if (w <= 0 || h <= 0) return;
    fillRect(x, y, w, 1, c); fillRect(x, y + h - 1, w, 1, c); fillRect(x, y, 1, h, c); fillRect(x + w - 1, y, 1, h, c);
  }
  void drawCircle(int, int, int, uint16_t) {}
  void fillCircle(int, int, int, uint16_t) {}
  void drawLine(int, int, int, int, uint16_t) {}
  void fillTriangle(int, int, int, int, int, int, uint16_t) {}
  void drawRGBBitmap(int, int, uint16_t*, int, int) {}
  void setCursor(int, int) {}
  void setTextColor(uint16_t, uint16_t) {}
  void setTextSize(int) {}
  void setTextWrap(bool) {}
  void print(const char*) {}
};
typedef DIYables_TFT_HX8357D_Shield DIYables_TFT_RM68140_Shield;
