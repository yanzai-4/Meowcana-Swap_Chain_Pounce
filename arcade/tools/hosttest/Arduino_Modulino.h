#pragma once
#include "Arduino.h"
#include "Wire.h"
struct ModulinoStub { void begin(WireStub&) {} };
static ModulinoStub Modulino;
struct ModulinoButtons {
  explicit ModulinoButtons(uint8_t) {}
  void begin() {}
  void setLeds(bool, bool, bool) {}
};
struct ModulinoMovement {
  bool begin() { return false; }
  bool update() { return false; }
  float getX() { return 0; } float getY() { return 0; } float getZ() { return 0; }
};
