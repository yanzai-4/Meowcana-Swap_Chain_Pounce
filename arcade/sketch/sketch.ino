#include <Arduino.h>
#include <Arduino_RouterBridge.h>
#include <Arduino_Modulino.h>
#include <DIYables_TFT_Touch_Shield.h>
#include <math.h>
#include "video_protocol.h"
#include "assets.h"

#if !defined(ARDUINO_UNO_Q)
#error "Select Arduino UNO Q for this starter."
#endif

// Hosts select the controller fitted to their preassembled consoles.
#ifndef ARCADE_TFT_HX8357D
#define ARCADE_TFT_HX8357D 1
#endif
#if ARCADE_TFT_HX8357D
DIYables_TFT_HX8357D_Shield display;
#else
DIYables_TFT_RM68140_Shield display;
#endif

// ARCADE_FAST_BUS: 0 = every pixel goes through the DIYables library (digitalWrite per bus line);
// 1 = fills, bitmaps and glyph cells drive the 8-bit TFT bus with direct GPIO writes (see FastBus and
// README "Faster TFT bus"). Flip it here, or deploy with `python scripts/deploy.py --fast-bus`.
#ifndef ARCADE_FAST_BUS
#define ARCADE_FAST_BUS 0
#endif

#if ARCADE_FAST_BUS
#if !__has_include(<stm32_ll_gpio.h>)
#error "ARCADE_FAST_BUS needs the STM32 LL GPIO header; set ARCADE_FAST_BUS to 0."
#endif
#include <stm32_ll_gpio.h>

// Direct GPIO drive of the DIYables shield bus on the UNO Q (STM32U585). Pin map, from the core's
// arduino_uno_q_stm32u585xx.overlay and the shield's wiring (library defaults D0..D7 = pins 8,9,2..7,
// RD/WR/CD/CS/RST = A0..A4):
//   TFT D0 PB4  D1 PB8  D2 PB3  D3 PB0  D4 PA12  D5 PA11  D6 PB1  D7 PB2
//   RD PA4  WR PA5  CD PA6  CS PA7
// Each data byte is two BSRR writes (port B, port A carrying the WR-low bit) from 256-entry tables,
// then WR goes high. The library still does the controller init and the primitives (circles, lines).
namespace FastBus {
constexpr uint32_t WR_LOW = 1UL << (5 + 16), WR_HIGH = 1UL << 5;
constexpr uint32_t CD_LOW = 1UL << (6 + 16), CD_HIGH = 1UL << 6;
static uint32_t tabA[256], tabB[256];  // BSRR words: pins to set in the low half, to reset in the high half
uint8_t mode = 0;                      // 0 library, 1..3 direct with 0 / 2 / 6 nop between WR edges

void init() {
  struct Bit { bool onA; uint8_t pin; };
  static const Bit bits[8] = {{false, 4}, {false, 8}, {false, 3}, {false, 0},
                              {true, 12}, {true, 11}, {false, 1}, {false, 2}};
  for (int v = 0; v < 256; ++v) {
    uint32_t a = 0, b = 0;
    for (int i = 0; i < 8; ++i) {
      uint32_t word = (v >> i) & 1 ? (1UL << bits[i].pin) : (1UL << (bits[i].pin + 16));
      (bits[i].onA ? a : b) |= word;
    }
    tabA[v] = a;
    tabB[v] = b;
  }
  // The library leaves the pins at the core's default (low) output speed; edges need to be sharp.
  for (int i = 0; i < 8; ++i)
    LL_GPIO_SetPinSpeed(bits[i].onA ? GPIOA : GPIOB, 1UL << bits[i].pin, LL_GPIO_SPEED_FREQ_VERY_HIGH);
  LL_GPIO_SetPinSpeed(GPIOA, LL_GPIO_PIN_5 | LL_GPIO_PIN_6, LL_GPIO_SPEED_FREQ_VERY_HIGH);
}

template <int NOPS> inline void nops() {
  for (int i = 0; i < NOPS; ++i) __asm__ volatile("nop");
}
template <int NOPS> inline void put(uint8_t v) {
  GPIOB->BSRR = tabB[v];
  GPIOA->BSRR = tabA[v] | WR_LOW;
  nops<NOPS>();
  GPIOA->BSRR = WR_HIGH;
  nops<NOPS / 2>();
}
template <int NOPS> inline void command(uint8_t c) {
  GPIOA->BSRR = CD_LOW;
  put<NOPS>(c);
  GPIOA->BSRR = CD_HIGH;
}
template <int NOPS> void window(int x0, int y0, int x1, int y1) {
  command<NOPS>(0x2A);
  put<NOPS>(x0 >> 8); put<NOPS>(x0); put<NOPS>(x1 >> 8); put<NOPS>(x1);
  command<NOPS>(0x2B);
  put<NOPS>(y0 >> 8); put<NOPS>(y0); put<NOPS>(y1 >> 8); put<NOPS>(y1);
  command<NOPS>(0x2C);
}
template <int NOPS> void fill(uint16_t color, uint32_t count) {  // inside an open window
  const uint8_t hi = color >> 8, lo = color & 0xFF;
  if (hi == lo) {  // one data setup, then only WR toggles
    GPIOB->BSRR = tabB[hi];
    GPIOA->BSRR = tabA[hi];
    for (uint32_t n = count * 2; n; --n) {
      GPIOA->BSRR = WR_LOW;
      nops<NOPS>();
      GPIOA->BSRR = WR_HIGH;
      nops<NOPS / 2>();
    }
    return;
  }
  while (count--) { put<NOPS>(hi); put<NOPS>(lo); }
}
template <int NOPS> void push(const uint16_t* colors, uint32_t count) {
  while (count--) {
    uint16_t c = *colors++;
    put<NOPS>(c >> 8);
    put<NOPS>(c & 0xFF);
  }
}
}  // namespace FastBus
#endif

// TFT access used by every drawing op: the library, or the fast bus when selected at run time.
void tftWindow(int x0, int y0, int x1, int y1) {
#if ARCADE_FAST_BUS
  switch (FastBus::mode) {
    case 1: return FastBus::window<0>(x0, y0, x1, y1);
    case 2: return FastBus::window<2>(x0, y0, x1, y1);
    case 3: return FastBus::window<6>(x0, y0, x1, y1);
  }
#endif
  display.setAddrWindow(x0, y0, x1, y1);
}

void tftPush(uint16_t* colors, int count) {
#if ARCADE_FAST_BUS
  switch (FastBus::mode) {
    case 1: return FastBus::push<0>(colors, count);
    case 2: return FastBus::push<2>(colors, count);
    case 3: return FastBus::push<6>(colors, count);
  }
#endif
  display.pushColors(colors, count);
}

// Solid rectangle, clipped to the screen.
void tftFillRect(int x, int y, int w, int h, uint16_t color) {
#if ARCADE_FAST_BUS
  if (FastBus::mode) {
    int x1 = min(x + w, (int)display.width()), y1 = min(y + h, (int)display.height());
    x = max(x, 0);
    y = max(y, 0);
    if (x >= x1 || y >= y1) return;
    tftWindow(x, y, x1 - 1, y1 - 1);
    uint32_t count = (uint32_t)(x1 - x) * (y1 - y);
    switch (FastBus::mode) {
      case 1: return FastBus::fill<0>(color, count);
      case 2: return FastBus::fill<2>(color, count);
      case 3: return FastBus::fill<6>(color, count);
    }
  }
#endif
  display.fillRect(x, y, w, h, color);
}

const uint8_t BUTTONS_ADDRESS = 0x3E;
const uint8_t JOYSTICK_ADDRESS = 0x2C;
ModulinoButtons buttons(BUTTONS_ADDRESS);
ModulinoMovement movement;
bool movementReady = false;

const uint16_t TFT_BLACK = 0x0000;
const uint16_t TFT_WHITE = 0xFFFF;
const uint16_t TFT_CYAN = 0x07FF;
unsigned long lastFrameAt = 0;
bool waiting = true;
int videoSession = 0;
int nextVideoSession = 0;
int lastX = -1;
int lastY = -1;
bool gameMode = false;          // A Python game is drawing through arcade_draw_ops.
unsigned long screenEpoch = 0;  // Bumped whenever the sketch repaints on its own.

bool readPacket(uint8_t address, uint8_t payload[3]) {
  // update() means "changed", not "read succeeded"; reject incomplete wire packets.
  int count = Wire1.requestFrom(address, (uint8_t)4);
  if (count != 4) {
    while (Wire1.available()) Wire1.read();
    return false;
  }
  Wire1.read();  // Modulino pinstrap address precedes the three input bytes.
  for (int i = 0; i < 3; ++i) payload[i] = Wire1.read();
  return true;
}

String readInputs() {
  uint8_t buttonData[3] = {};
  uint8_t stickData[3] = {};
  bool buttonsOk = readPacket(BUTTONS_ADDRESS, buttonData);
  bool joystickOk = readPacket(JOYSTICK_ADDRESS, stickData);
  bool movementOk = movementReady && movement.update();
  float ax = movementOk ? movement.getX() : 0;
  float ay = movementOk ? movement.getY() : 0;
  float az = movementOk ? movement.getZ() : 0;
  movementOk = movementOk && isfinite(ax) && isfinite(ay) && isfinite(az);
  int connected = (buttonsOk ? 1 : 0) | (joystickOk ? 2 : 0) | (movementOk ? 4 : 0);
  int pressed = 0;
  if (buttonsOk) {
    for (int i = 0; i < 3; ++i) if (buttonData[i]) pressed |= 1 << i;
    buttons.setLeds(buttonData[0], buttonData[1], buttonData[2]);
  }
  if (joystickOk && stickData[2]) pressed |= 8;
  char json[200];
  snprintf(json, sizeof(json),
           "{\"video\":%d,\"epoch\":%lu,\"connected\":%d,\"buttons\":%d,\"x\":%d,\"y\":%d,"
           "\"ax\":%d,\"ay\":%d,\"az\":%d}",
           videoSession, screenEpoch, connected, pressed,
           joystickOk ? 128 - (int)stickData[0] : 0,
           joystickOk ? 128 - (int)stickData[1] : 0,
           movementOk ? (int)(constrain(ax, -16.0f, 16.0f) * 1000) : 0,
           movementOk ? (int)(constrain(ay, -16.0f, 16.0f) * 1000) : 0,
           movementOk ? (int)(constrain(az, -16.0f, 16.0f) * 1000) : 0);
  return String(json);
}

void textLine(int y, const char* text) {
  display.setCursor(12, y);
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  display.print(text);
}

void showWaiting() {
  if (videoSession || gameMode) {
    videoSession = 0;
    gameMode = false;
    display.fillScreen(TFT_BLACK);
    textLine(10, "UNO Q arcade starter");
    display.drawRect(12, 160, 456, 148, TFT_WHITE);
  }
  display.fillRect(12, 36, 456, 112, TFT_BLACK);
  textLine(36, "Waiting for App Lab...");
  if (lastX >= 0) display.fillCircle(lastX, lastY, 6, TFT_BLACK);
  lastX = -1;
  waiting = true;
  screenEpoch++;
}

bool drawFrame(int x, int y, int pressed, int ax, int ay, int az, int connected) {
  if (videoSession) return false;  // RetroArch owns the display until release/timeout.
  // Bound every RPC input before using it for drawing or bit masks.
  x = constrain(x, 20, 460);
  y = constrain(y, 168, 300);
  pressed &= 15;
  connected &= 7;
  if (!(connected & 1)) pressed &= 8;
  if (!(connected & 2)) { pressed &= 7; x = 240; y = 234; }
  if (!(connected & 4)) { ax = 0; ay = 0; az = 0; }
  ax = constrain(ax, -16000, 16000);
  ay = constrain(ay, -16000, 16000);
  az = constrain(az, -16000, 16000);
  if (waiting) display.fillRect(12, 36, 456, 112, TFT_BLACK);
  char line[40];
  snprintf(line, sizeof(line), "Buttons:%s Stick:%s IMU:%s  ",
           connected & 1 ? "OK" : "--", connected & 2 ? "OK" : "--",
           connected & 4 ? "OK" : "--");
  textLine(36, line);
  snprintf(line, sizeof(line), "A:%d  B:%d  C:%d  Stick press:%d ",
           !!(pressed & 1), !!(pressed & 2), !!(pressed & 4), !!(pressed & 8));
  textLine(64, line);
  textLine(92, "Motion from neutral (mg)");
  snprintf(line, sizeof(line), "%6d / %6d / %6d   ", ax, ay, az);
  textLine(120, line);
  if (lastX >= 0) display.fillCircle(lastX, lastY, 6, TFT_BLACK);
  display.fillCircle(x, y, 6, pressed ? TFT_WHITE : TFT_CYAN);
  lastX = x;
  lastY = y;
  lastFrameAt = millis();
  waiting = false;
  return true;
}

// arcade_draw_ops: a packed list of drawing commands from Python. Integers are
// little-endian, colors RGB565. Keep in sync with python/engine.py and tools/sim.py.
//   1 clear(color)                              3
//   2 fill_rect(x, y, w, h, color)              11   (x, y i16; w, h i16)
//   3 rect(x, y, w, h, color)                   11
//   4 fill_circle(x, y, r, color)               9
//   5 circle(x, y, r, color)                    9
//   6 line(x0, y0, x1, y1, color)               11
//   7 text(x i16, y i16, flags u8, fg, [bg], n u8, n chars)   9 + n (transparent) or 11 + n
//       flags: bits 0-2 font, bits 3-5 scale-1, bit 7 transparent
//   8 fill_triangle(x0, y0, x1, y1, x2, y2, color)  15
//   9 asset(id u8, frame u16, x i16, y i16, flags u8, bg, [tint])   11 (+2 with tint)
//       flags: bits 0-1 scale-1, 4 flipX, 8 flipY, 16 transparent, 32 tint, 64 dim
//  10 asset_region(id u8, frame u16, x, y i16, sx, sy, w, h u16, flags u8, bg)   19 (flags: transparent, dim)
//  11 dotted_rect(x, y, w, h, color)            11
//  12 card(face id u8, frame u16, x, y i16, rim, bg, field, flags u8, stars|gem<<2 u8, star id, gem id, [tint])
//       18 (+2 with tint); a tarot card in one window, see drawCard()
int16_t i16(const uint8_t* p) { return (int16_t)(p[0] | (p[1] << 8)); }
uint16_t u16(const uint8_t* p) { return (uint16_t)(p[0] | (p[1] << 8)); }

enum : uint8_t { F_FLIP_X = 4, F_FLIP_Y = 8, F_TRANSPARENT = 16, F_TINT = 32, F_DIM = 64 };

size_t opSize(const uint8_t* p, size_t left) {
  switch (p[0]) {
    case 1: return 3;
    case 2: case 3: case 6: case 11: return 11;
    case 4: case 5: return 9;
    case 7: {
      if (left < 6) return 0;
      size_t count = (p[5] & 0x80) ? 8 : 10;  // index of the character count
      return left > count ? count + 1 + p[count] : 0;
    }
    case 8: return 15;
    case 9: return left >= 9 ? ((p[8] & F_TINT) ? 13 : 11) : 0;
    case 10: return 19;
    case 12: return left >= 15 ? ((p[14] & F_TINT) ? 20 : 18) : 0;
    default: return 0;
  }
}

// One frame of packed pixels read as palette indices (0 = transparent).
struct FrameReader {
  const ArcadeAssets::Asset* asset;
  const uint8_t* start;
  const uint8_t* p;
  const uint8_t* pal;
  int left;
  uint8_t idx;
  bool high;
  void rewind() {
    p = start;
    left = 0;
    high = true;
  }
  void open(const ArcadeAssets::Asset& a, int frame) {
    using namespace ArcadeAssets;
    asset = &a;
    start = DATA + FRAME_OFFSETS[a.firstFrame + frame];
    pal = DATA + a.palOffset;
    rewind();
  }
  void nextRun() {  // RLE6: length 1-3 in the top bits, or a separate length byte
    uint8_t b = p[0];
    idx = pal[b & 63];
    left = b >> 6;
    if (left) {
      p += 1;
    } else {
      left = p[1];
      p += 2;
    }
  }
  void skip(uint32_t n) {  // from the current position
    if (asset->mode) {
      uint32_t at = n + (high ? 0 : 1);
      p += at / 2;
      high = !(at & 1);
      return;
    }
    while (n) {
      if (!left) nextRun();
      uint32_t take = n < (uint32_t)left ? n : (uint32_t)left;
      left -= take;
      n -= take;
    }
  }
  void read(uint8_t* out, int n) {
    if (asset->mode) {
      for (int i = 0; i < n; ++i) {
        uint8_t v = high ? (*p >> 4) : (*p & 15);
        if (!high) ++p;
        high = !high;
        out[i] = pal[v];
      }
      return;
    }
    while (n > 0) {
      if (!left) nextRun();
      int take = n < left ? n : left;
      memset(out, idx, take);
      out += take;
      n -= take;
      left -= take;
    }
  }
};

// Draws a source rectangle (sx, sy, rw, rh) of one asset frame at (x, y), see opcodes 9 and 10.
void blitAsset(uint8_t id, int frame, int x, int y, int sx, int sy, int rw, int rh, int scale,
               uint8_t flags, uint16_t bg, uint16_t tint) {
  using namespace ArcadeAssets;
  static uint8_t row[MAX_ASSET_WIDTH];
  static uint8_t solid[480];
  static uint16_t line[480];
  if (id >= ASSET_COUNT) return;
  const Asset& asset = ASSETS[id];
  if (frame >= asset.frames || sx >= asset.w || sy >= asset.h) return;
  rw = min(rw, (int)asset.w - sx);
  rh = min(rh, (int)asset.h - sy);
  if (rw <= 0 || rh <= 0) return;
  const bool flipX = flags & F_FLIP_X, flipY = flags & F_FLIP_Y, transparent = flags & F_TRANSPARENT;
  uint16_t colors[PALETTE_COUNT];
  colors[0] = bg;
  for (int i = 1; i < PALETTE_COUNT; ++i) {
    uint16_t c = (flags & F_TINT) ? tint : PALETTE[i];
    colors[i] = (flags & F_DIM) ? (c >> 1) & 0x7BEF : c;
  }
  const int x0 = max(x, 0), x1 = min(x + rw * scale, (int)display.width());
  const int y0 = max(y, 0), y1 = min(y + rh * scale, (int)display.height());
  if (x0 >= x1 || y0 >= y1) return;
  const int cols = x1 - x0;
  FrameReader rd;
  rd.open(asset, frame);
  if (!flipY && sy) rd.skip((uint32_t)sy * asset.w);
  if (!transparent) tftWindow(x0, y0, x1 - 1, y1 - 1);
  for (int r = 0; r < rh; ++r) {
    const int oy = y + r * scale;
    if (oy >= y1) break;
    if (oy + scale <= y0) {  // fully above the screen: keep the reader moving
      if (!flipY) rd.skip(asset.w);
      continue;
    }
    if (flipY) {
      rd.rewind();
      rd.skip((uint32_t)(sy + rh - 1 - r) * asset.w);
    }
    rd.read(row, asset.w);
    for (int k = 0; k < cols; ++k) {
      int c = (x0 - x + k) / scale;
      uint8_t v = row[sx + (flipX ? rw - 1 - c : c)];
      line[k] = colors[v];
      solid[k] = v != 0;
    }
    const int wy0 = max(oy, y0), wy1 = min(oy + scale, y1);
    if (!transparent) {
      for (int k = wy0; k < wy1; ++k) tftPush(line, cols);
      continue;
    }
    for (int k = 0; k < cols;) {  // one short window per opaque run
      while (k < cols && !solid[k]) ++k;
      int begin = k;
      while (k < cols && solid[k]) ++k;
      if (k > begin) {
        tftWindow(x0 + begin, wy0, x0 + k - 1, wy1 - 1);
        for (int j = wy0; j < wy1; ++j) tftPush(line + begin, k - begin);
      }
    }
  }
}

// Text: glyphs of one font composed row by row into a single window (opaque) or per run (transparent).
void drawText(const uint8_t* p) {
  using namespace ArcadeAssets;
  static uint8_t cover[480];
  static uint16_t line[480];
  const bool transparent = p[5] & 0x80;
  const int fontId = p[5] & 7, scale = ((p[5] >> 3) & 7) + 1;
  if (fontId >= FONT_COUNT) return;
  const Font& font = FONTS[fontId];
  uint16_t fg = u16(p + 6), bg = transparent ? 0 : u16(p + 8);
  int head = transparent ? 8 : 10;
  int n = p[head];
  const uint8_t* chars = p + head + 1;
  int x = i16(p + 1), y = i16(p + 3);
  // Total width = advances of all but the last glyph + ink of the last.
  int total = 0;
  for (int i = 0; i < n; ++i) {
    int g = font.firstGlyph + constrain((int)chars[i] - FIRST_CHAR, 0, GLYPHS_PER_FONT - 1);
    total += (i == n - 1) ? max((int)GLYPHS[g].advance, (int)GLYPHS[g].width) : GLYPHS[g].advance;
  }
  int cw = total * scale, ch = font.height * scale;
  int x0 = max(x, 0), x1 = min(x + cw, (int)display.width());
  int y0 = max(y, 0), y1 = min(y + ch, (int)display.height());
  if (x0 >= x1 || y0 >= y1) return;
  if (!transparent) tftWindow(x0, y0, x1 - 1, y1 - 1);
  const int first = (x0 - x) / scale;                 // first font column on screen
  const int last = (x1 - x + scale - 1) / scale;      // one past the last
  const int cols = x1 - x0;
  for (int r = 0; r < font.height; ++r) {
    int oy = y + r * scale;
    if (oy >= y1) break;
    if (oy + scale <= y0) continue;
    int rows = min(oy + scale, y1) - max(oy, y0);
    memset(cover, 0, last - first);
    int pen = 0;
    for (int i = 0; i < n && pen < last; ++i) {
      int g = font.firstGlyph + constrain((int)chars[i] - FIRST_CHAR, 0, GLYPHS_PER_FONT - 1);
      const Glyph& glyph = GLYPHS[g];
      if (pen + glyph.width > first && glyph.width) {
        int stride = (glyph.width + 7) / 8;
        const uint8_t* bits = FONT_DATA + glyph.offset + r * stride;
        for (int c = 0; c < glyph.width; ++c) {
          int at = pen + c;
          if (at >= first && at < last && (bits[c >> 3] & (0x80 >> (c & 7)))) cover[at - first] = 1;
        }
      }
      pen += glyph.advance;
    }
    if (!transparent) {
      for (int k = 0; k < cols; ++k) line[k] = cover[(x0 - x + k) / scale - first] ? fg : bg;
      for (int k = 0; k < rows; ++k) tftPush(line, cols);
      continue;
    }
    int col = 0;
    while (col < cols) {
      while (col < cols && !cover[(x0 - x + col) / scale - first]) ++col;
      int begin = col;
      while (col < cols && cover[(x0 - x + col) / scale - first]) ++col;
      if (col > begin) tftFillRect(x0 + begin, max(oy, y0), col - begin, rows, fg);
    }
  }
}

void dottedRect(int x, int y, int w, int h, uint16_t color) {
  if (w <= 0 || h <= 0) return;
  for (int i = 0; i < w; i += 4) {
    int n = min(2, w - i);
    tftFillRect(x + i, y, n, 1, color);
    if (h > 1) tftFillRect(x + i, y + h - 1, n, 1, color);
  }
  for (int i = 4; i < h - 1; i += 4) {
    int n = min(2, h - 1 - i);
    tftFillRect(x, y + i, 1, n, color);
    if (w > 1) tftFillRect(x + w - 1, y + i, 1, n, color);
  }
}

// Paints one asset frame into an RGB565 buffer (transparent pixels become `clear`).
void paintAsset(uint16_t* dst, int stride, int bw, int bh, int dx, int dy, uint8_t id, int frame,
                uint16_t clear, bool useTint, uint16_t tint, bool dim) {
  using namespace ArcadeAssets;
  static uint8_t row[MAX_ASSET_WIDTH];
  if (id >= ASSET_COUNT) return;
  const Asset& asset = ASSETS[id];
  if (frame >= asset.frames) return;
  FrameReader rd;
  rd.open(asset, frame);
  for (int r = 0; r < asset.h; ++r) {
    rd.read(row, asset.w);
    int y = dy + r;
    if (y < 0 || y >= bh) continue;
    for (int c = 0; c < asset.w; ++c) {
      int x = dx + c;
      if (x < 0 || x >= bw) continue;
      uint16_t color = clear;
      if (row[c]) {
        color = useTint ? tint : PALETTE[row[c]];
        if (dim) color = (color >> 1) & 0x7BEF;
      }
      dst[y * stride + x] = color;
    }
  }
}

// A card: 1-px rim, 1-px ink ring (0x1044), the face frame inset 2 px, star and gem overlays on
// `field`, and the four outermost corner pixels in `bg`. Drawn through one address window.
constexpr int CARD_MAX_W = 80, CARD_MAX_H = 96;
void drawCard(const uint8_t* p) {
  using namespace ArcadeAssets;
  static uint16_t buf[CARD_MAX_W * CARD_MAX_H];
  static uint16_t line[480];
  if (p[1] >= ASSET_COUNT) return;
  const Asset& face = ASSETS[p[1]];
  const int cw = face.w + 4, ch = face.h + 4;
  if (cw > CARD_MAX_W || ch > CARD_MAX_H) return;
  const uint8_t flags = p[14];
  const int scale = (flags & 3) + 1;
  const bool dim = flags & F_DIM;
  auto shade = [dim](uint16_t c) -> uint16_t { return dim ? (c >> 1) & 0x7BEF : c; };
  const uint16_t rim = shade(u16(p + 8)), bg = u16(p + 10), field = shade(u16(p + 12)), ink = shade(0x1044);
  const int stars = p[15] & 3, gem = p[15] >> 2;
  for (int i = 0; i < cw * ch; ++i) buf[i] = rim;
  for (int y = 1; y < ch - 1; ++y)
    for (int x = 1; x < cw - 1; ++x) buf[y * cw + x] = ink;
  paintAsset(buf, cw, cw, ch, 2, 2, p[1], u16(p + 2), ink, flags & F_TINT, (flags & F_TINT) ? u16(p + 18) : 0, dim);
  for (int i = 0; i < stars; ++i) paintAsset(buf, cw, cw, ch, cw - 8 - 6 * i, 5, p[16], 0, field, false, 0, dim);
  if (gem > 0) paintAsset(buf, cw, cw, ch, cw - 12, face.w == 44 ? ch - 12 : ch - 10, p[17], gem - 1, field, false, 0, dim);
  buf[0] = buf[cw - 1] = buf[(ch - 1) * cw] = buf[ch * cw - 1] = bg;
  const int x = i16(p + 4), y = i16(p + 6);
  const int x0 = max(x, 0), x1 = min(x + cw * scale, (int)display.width());
  const int y0 = max(y, 0), y1 = min(y + ch * scale, (int)display.height());
  if (x0 >= x1 || y0 >= y1) return;
  tftWindow(x0, y0, x1 - 1, y1 - 1);
  for (int r = 0; r < ch; ++r) {
    const int oy = y + r * scale;
    const int rows = min(oy + scale, y1) - max(oy, y0);
    if (rows <= 0) continue;
    for (int k = 0; k < x1 - x0; ++k) line[k] = buf[r * cw + (x0 - x + k) / scale];
    for (int k = 0; k < rows; ++k) tftPush(line, x1 - x0);
  }
}

void drawOp(const uint8_t* p) {
  switch (p[0]) {
    case 1: tftFillRect(0, 0, 480, 320, u16(p + 1)); break;
    case 2: tftFillRect(i16(p + 1), i16(p + 3), constrain(i16(p + 5), 0, 480),
                        constrain(i16(p + 7), 0, 320), u16(p + 9)); break;
    case 3: {  // outline: same pixels as Adafruit_GFX::drawRect
      int x = i16(p + 1), y = i16(p + 3), w = constrain(i16(p + 5), 0, 480), h = constrain(i16(p + 7), 0, 320);
      uint16_t c = u16(p + 9);
      if (w > 0 && h > 0) {
        tftFillRect(x, y, w, 1, c);
        tftFillRect(x, y + h - 1, w, 1, c);
        tftFillRect(x, y, 1, h, c);
        tftFillRect(x + w - 1, y, 1, h, c);
      }
      break;
    }
    case 4: display.fillCircle(i16(p + 1), i16(p + 3), constrain(i16(p + 5), 0, 320), u16(p + 7)); break;
    case 5: display.drawCircle(i16(p + 1), i16(p + 3), constrain(i16(p + 5), 0, 320), u16(p + 7)); break;
    case 6: display.drawLine(i16(p + 1), i16(p + 3), i16(p + 5), i16(p + 7), u16(p + 9)); break;
    case 7: drawText(p); break;
    case 8: display.fillTriangle(i16(p + 1), i16(p + 3), i16(p + 5), i16(p + 7),
                                 i16(p + 9), i16(p + 11), u16(p + 13)); break;
    case 9: {
      uint8_t flags = p[8];
      int scale = (flags & 3) + 1;
      const ArcadeAssets::Asset* a = p[1] < ArcadeAssets::ASSET_COUNT ? &ArcadeAssets::ASSETS[p[1]] : nullptr;
      if (!a) break;
      blitAsset(p[1], u16(p + 2), i16(p + 4), i16(p + 6), 0, 0, a->w, a->h, scale, flags,
                u16(p + 9), (flags & F_TINT) ? u16(p + 11) : 0);
      break;
    }
    case 10:
      blitAsset(p[1], u16(p + 2), i16(p + 4), i16(p + 6), u16(p + 8), u16(p + 10), u16(p + 12),
                u16(p + 14), 1, p[16] & (F_TRANSPARENT | F_DIM), u16(p + 17), 0);
      break;
    case 12: drawCard(p); break;
    case 11: dottedRect(i16(p + 1), i16(p + 3), i16(p + 5), i16(p + 7), u16(p + 9)); break;
  }
}

// arcade_bus_mode(m): 0 = library bus, 1..3 = direct GPIO (0 / 2 / 6 nops per strobe); returns the mode
// now active. Without ARCADE_FAST_BUS it always returns 0. The benchmark (python/bench.py) sweeps it.
int busMode(int mode) {
#if ARCADE_FAST_BUS
  if (mode >= 0 && mode <= 3) FastBus::mode = mode;
  return FastBus::mode;
#else
  (void)mode;
  return 0;
#endif
}

// Validate the whole packet first so a bad packet draws nothing.
bool applyOps(const uint8_t* data, size_t size, bool draw) {
  for (size_t i = 0; i < size;) {
    size_t n = opSize(data + i, size - i);
    if (n == 0 || n > size - i) return false;
    if (draw) drawOp(data + i);
    i += n;
  }
  return true;
}

// Draws one batch and returns a fresh input snapshot, so a game frame is one RPC.
String drawOps(MsgPack::bin_t<uint8_t> data) {
  if (!videoSession && applyOps(data.data(), data.size(), false)) {
    applyOps(data.data(), data.size(), true);
    gameMode = true;
    lastFrameAt = millis();
    waiting = false;
  }
  return readInputs();
}

int beginVideo() {
  if (videoSession) return 0;  // Only one stream may own the display.
  nextVideoSession = nextVideoSession == 2147483647 ? 1 : nextVideoSession + 1;
  videoSession = nextVideoSession;
  display.fillScreen(TFT_BLACK);
  screenEpoch++;
  textLine(10, "RetroArch / TFT bridge");
  textLine(294, "C + stick press: menu");
  lastX = -1;
  lastFrameAt = millis();
  waiting = false;
  return videoSession;
}

String pollVideo(int session) {
  if (!videoSession || session != videoSession) return String("");
  String inputs = readInputs();
  lastFrameAt = millis();
  return inputs;
}

String videoTile(int session, int tile, MsgPack::bin_t<uint8_t> data) {
  static uint16_t pixels[ArcadeVideo::TILE_PIXELS * 4];
  if (!videoSession || session != videoSession ||
      !ArcadeVideo::decode(tile, data.data(), data.size(), pixels)) return String("");
  display.drawRGBBitmap(80 + (tile % 10) * 32, 40 + (tile / 10) * 16, pixels, 32, 16);
  return pollVideo(session);  // Return fresh controls after each acknowledged tile.
}

bool endVideo(int session) {
  if (!videoSession || session != videoSession) return false;
  showWaiting();
  return true;
}

void setup() {
  Modulino.begin(Wire1);
  buttons.begin();
  movementReady = movement.begin();
  display.begin();
  display.setRotation(1);  // Landscape: 480 x 320.
  display.fillScreen(TFT_BLACK);
#if ARCADE_FAST_BUS
  FastBus::init();
  FastBus::mode = 3;
#endif
  display.setTextSize(2);
  display.setTextWrap(false);
  textLine(10, "UNO Q arcade starter");
  display.drawRect(12, 160, 456, 148, TFT_WHITE);
  showWaiting();
  if (Bridge.begin()) {
    Bridge.provide_safe("arcade_read_inputs", readInputs);
    Bridge.provide_safe("arcade_draw_frame", drawFrame);
    Bridge.provide_safe("arcade_draw_ops", drawOps);
    Bridge.provide_safe("arcade_bus_mode", busMode);
    Bridge.provide_safe("arcade_video_begin", beginVideo);
    Bridge.provide_safe("arcade_video_tile", videoTile);
    Bridge.provide_safe("arcade_video_poll", pollVideo);
    Bridge.provide_safe("arcade_video_end", endVideo);
  } else {
    textLine(36, "Bridge failed: restart app");
  }
}

void loop() {
  if (!waiting && millis() - lastFrameAt > 1500) showWaiting();
  delay(5);
}
