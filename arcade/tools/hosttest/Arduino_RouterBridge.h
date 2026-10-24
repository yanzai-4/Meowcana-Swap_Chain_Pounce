#pragma once
#include "Arduino.h"
namespace MsgPack {
template <class T> struct bin_t {
  const T* ptr; size_t n;
  const T* data() const { return ptr; }
  size_t size() const { return n; }
};
}
struct BridgeStub {
  bool begin() { return true; }
  template <class F> void provide_safe(const char*, F) {}
};
static BridgeStub Bridge;
