// Host model of the UNO Q's TFT bus: GPIOA/GPIOB with BSRR semantics, wired to the shield's 8080 bus.
// Independent of the sketch's tables: wiring comes from the core's overlay (pin -> port/bit) and the shield
// (TFT D0..D7 = Arduino pins 8,9,2,3,4,5,6,7; WR = A1, CD = A2, CS = A3, RD = A0).
#pragma once
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

struct Gpio;
struct BsrrReg {
  Gpio* owner;
  void operator=(uint32_t v);
};
struct Gpio {
  uint32_t odr = 0;
  BsrrReg BSRR{this};
};
static Gpio gpioA, gpioB, gpioC;
#define GPIOA (&gpioA)
#define GPIOB (&gpioB)
#define GPIOC (&gpioC)
typedef Gpio GPIO_TypeDef;
#define LL_GPIO_PIN_5 (1UL << 5)
#define LL_GPIO_PIN_6 (1UL << 6)
#define LL_GPIO_SPEED_FREQ_VERY_HIGH 3
inline void LL_GPIO_SetPinSpeed(Gpio*, uint32_t, uint32_t) {}

// Arduino pin number -> (port, bit), from arduino_uno_q_stm32u585xx.overlay (D0..D13, A0..A5).
struct PinLoc { Gpio* port; int bit; };
inline PinLoc locate(int pin) {  // pin: D0..D13 = 0..13, A0..A5 = 14..19
  static const struct { char port; int bit; } map[] = {
      {'B', 7}, {'B', 6}, {'B', 3}, {'B', 0}, {'A', 12}, {'A', 11}, {'B', 1}, {'B', 2}, {'B', 4}, {'B', 8},
      {'B', 9}, {'B', 15}, {'B', 14}, {'B', 13}, {'A', 4}, {'A', 5}, {'A', 6}, {'A', 7}, {'C', 1}, {'C', 0}};
  char p = map[pin].port;
  return {p == 'A' ? &gpioA : p == 'B' ? &gpioB : &gpioC, map[pin].bit};
}
inline bool pinHigh(int pin) { PinLoc l = locate(pin); return (l.port->odr >> l.bit) & 1; }
