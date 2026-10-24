// Host stand-ins for the Arduino core, just enough to compile and run sketch/sketch.ino's drawing code.
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <algorithm>

template <class T> T min(T a, T b) { return a < b ? a : b; }   // strict: mixed types must not compile
template <class T> T max(T a, T b) { return a > b ? a : b; }
#define constrain(amt, low, high) ((amt) < (low) ? (low) : ((amt) > (high) ? (high) : (amt)))
inline unsigned long millis() { return 0; }
inline void delay(unsigned long) {}
#define ARDUINO_UNO_Q 1

struct String {
  String() {}
  String(const char*) {}
};

struct WireStub {
  int requestFrom(uint8_t, uint8_t) { return 0; }
  int available() { return 0; }
  int read() { return 0; }
};
static WireStub Wire1;
