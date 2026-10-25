#!/usr/bin/env python3
"""Synthesize every Meowcana sound (numpy only, reproducible) into arcade/pc/sfx/<name>.wav.

22050 Hz, mono, 16-bit. Soft, cozy chiptune + bell / pluck timbres for a moonlit tarot parlor with cats.
Names are the fixed list in arcade/docs/pc-version.md. Run:  python arcade/pc/sfx/gen_sfx.py
"""

import os
import sys
import wave
import zlib

import numpy as np

SR = 22050
HERE = os.path.dirname(os.path.abspath(__file__))

# peak targets in dBFS per group (hard ceiling -6 dBFS; UI is quieter)
PEAK_UI, PEAK_CARD, PEAK_RUN, PEAK_BATTLE = -15.0, -12.0, -10.0, -7.5
MUSIC_RMS = -21.0          # dBFS, loops stay under -18
MUSIC_PEAK_MAX = -7.0

R = np.random.default_rng(0)
REGISTRY = {}              # name -> (fn, kind, peak_db)


def snd(name, kind="sfx", peak=PEAK_BATTLE):
    def deco(fn):
        REGISTRY[name] = (fn, kind, peak)
        return fn
    return deco


# ---------------------------------------------------------------------------- primitives
def hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def tt(d):
    return np.arange(int(round(d * SR))) / SR


def fade(x, fin=0.004, fout=0.012):
    x = x.copy()
    n = len(x)
    a = min(int(fin * SR), n // 2)
    b = min(int(fout * SR), n // 2)
    if a > 0:
        x[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    if b > 0:
        x[-b:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(b) / b)
    return x


def phase(f):
    return 2 * np.pi * np.cumsum(f) / SR


def sine(f, d=None):
    if np.isscalar(f):
        f = np.full(len(tt(d)), float(f))
    return np.sin(phase(f))


def tri(f, d=None):
    if np.isscalar(f):
        f = np.full(len(tt(d)), float(f))
    p = phase(f) / (2 * np.pi)
    return 2 * np.abs(2 * (p - np.floor(p + 0.5))) - 1


def pulse(f, d=None, duty=0.25, soft=True):
    """Chiptune pulse; `soft` rounds the edges with a short moving average."""
    if np.isscalar(f):
        f = np.full(len(tt(d)), float(f))
    p = phase(f) / (2 * np.pi)
    x = np.where((p - np.floor(p)) < duty, 1.0, -1.0)
    if soft:
        x = np.convolve(x, np.ones(5) / 5, mode="same")
    return x - x.mean() * 0


def expdec(n, rate):
    return np.exp(-np.arange(n) / SR * rate)


def ad(n, atk=0.003, rate=12.0):
    e = expdec(n, rate)
    a = max(1, int(atk * SR))
    e[:a] *= np.linspace(0, 1, a)
    return e


def noise(d):
    return R.standard_normal(int(round(d * SR)))


def _fft_filter(x, gain_fn):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * gain_fn(np.maximum(f, 1e-3)), len(x))


def lp(x, fc, order=2):
    return _fft_filter(x, lambda f: 1.0 / np.sqrt(1 + (f / fc) ** (2 * order)))


def hpf(x, fc, order=2):
    return _fft_filter(x, lambda f: 1.0 / np.sqrt(1 + (fc / f) ** (2 * order)))


def bp(x, lo, hi, order=2):
    return hpf(lp(x, hi, order), lo, order)


def bell(f, d, amp=1.0, rate=5.0, bright=1.0):
    """Gentle bell: slightly inharmonic sine partials, upper ones fade faster."""
    t = tt(d)
    parts = ((1.0, 1.0, 1.0), (2.0, 0.42, 1.8), (2.76, 0.22, 2.6), (4.07, 0.12 * bright, 3.6), (5.4, 0.06 * bright, 5.0))
    out = np.zeros(len(t))
    for r, a, k in parts:
        if f * r < SR * 0.45:
            out += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * rate * k)
    a = int(0.002 * SR)
    out[:a] *= np.linspace(0, 1, a)
    return amp * out / 1.5


def pluck(f, d, amp=1.0, rate=4.0, bright=1.0):
    """Soft plucked string (additive, harmonics decay faster the higher they are)."""
    t = tt(d)
    out = np.zeros(len(t))
    for k in range(1, 10):
        if f * k > SR * 0.42:
            break
        out += (1.0 / k ** 1.4) * bright ** (k - 1) * np.sin(2 * np.pi * f * k * t) * np.exp(-t * rate * (1 + 0.55 * (k - 1)))
    a = int(0.003 * SR)
    out[:a] *= np.linspace(0, 1, a)
    return amp * out


def musicbox(f, d, amp=1.0):
    t = tt(d)
    out = np.zeros(len(t))
    for r, a, k in ((1.0, 1.0, 1.0), (2.0, 0.28, 2.2), (4.02, 0.14, 4.0), (6.1, 0.05, 6.0)):
        if f * r < SR * 0.45:
            out += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * 3.2 * k)
    a = int(0.002 * SR)
    out[:a] *= np.linspace(0, 1, a)
    return amp * out


class Buf:
    def __init__(self, d, wrap=False):
        self.n = int(round(d * SR))
        self.a = np.zeros(self.n)
        self.wrap = wrap

    def add(self, x, at=0.0, gain=1.0):
        i = int(round(at * SR))
        n = len(x)
        if self.wrap:
            i %= self.n
            while n > 0:
                m = min(n, self.n - i)
                self.a[i:i + m] += gain * x[len(x) - n:len(x) - n + m]
                n -= m
                i = 0
            return self
        end = min(self.n, i + n)
        if end > i:
            self.a[i:end] += gain * x[:end - i]
        return self


def pad_to(x, d):
    n = int(round(d * SR))
    return np.concatenate([x, np.zeros(max(0, n - len(x)))])[:max(n, len(x))]


# ---------------------------------------------------------------------------- UI
@snd("move", peak=PEAK_UI)
def _move():
    d = 0.035
    return pulse(1300, d, 0.5) * ad(len(tt(d)), 0.002, 55)


@snd("confirm", peak=PEAK_UI)
def _confirm():
    b = Buf(0.1)
    b.add(pluck(hz(76), 0.07, rate=14), 0).add(pluck(hz(81), 0.08, rate=12), 0.04)
    return b.a


@snd("back", peak=PEAK_UI)
def _back():
    b = Buf(0.1)
    b.add(pluck(hz(79), 0.07, rate=14), 0).add(pluck(hz(72), 0.08, rate=12), 0.04)
    return b.a


@snd("info", peak=PEAK_UI)
def _info():
    return bell(hz(88), 0.12, rate=14)


@snd("blocked", peak=PEAK_UI)
def _blocked():
    b = Buf(0.115)
    for at in (0.0, 0.055):
        d = 0.05
        b.add(tri(hz(46), d) * ad(len(tt(d)), 0.003, 28), at)
    return b.a


@snd("open", peak=PEAK_UI)
def _open():
    d = 0.1
    f = np.linspace(380, 760, len(tt(d)))
    return tri(f) * np.sin(np.pi * np.linspace(0, 1, len(f))) ** 0.7


@snd("close", peak=PEAK_UI)
def _close():
    d = 0.09
    f = np.linspace(700, 340, len(tt(d)))
    return tri(f) * np.sin(np.pi * np.linspace(0, 1, len(f))) ** 0.7


@snd("transition", peak=PEAK_UI)
def _transition():
    d = 0.16
    n = bp(noise(d), 500, 2600)
    env = np.sin(np.pi * np.linspace(0, 1, len(n))) ** 1.5
    return n * env * 0.7 + sine(np.linspace(260, 520, len(n))) * env * 0.5


@snd("type", peak=PEAK_UI - 3)
def _type():
    d = 0.03
    return pulse(1650, d, 0.5) * ad(len(tt(d)), 0.001, 70)


# ---------------------------------------------------------------------------- cards
@snd("pickup", peak=PEAK_CARD)
def _pickup():
    d = 0.08
    n = len(tt(d))
    x = sine(np.linspace(500, 900, n)) * ad(n, 0.004, 14)
    return x + 0.25 * hpf(noise(d), 2500) * ad(n, 0.001, 50)


@snd("drop", peak=PEAK_CARD)
def _drop():
    d = 0.11
    n = len(tt(d))
    return sine(np.linspace(220, 120, n)) * ad(n, 0.002, 30) + 0.2 * lp(noise(d), 1800) * ad(n, 0.001, 70)


@snd("swap", peak=PEAK_CARD)
def _swap():
    b = Buf(0.13)
    b.add(pluck(hz(74), 0.07, rate=14), 0).add(pluck(hz(79), 0.07, rate=14), 0.055)
    return b.a


@snd("flip", peak=PEAK_CARD)
def _flip():
    d = 0.13
    n = len(tt(d))
    sw = bp(noise(d), 1500, 5500) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    return sw + 0.5 * bell(hz(86), d, rate=18) * (np.arange(n) > n * 0.55)


@snd("deal", peak=PEAK_CARD)
def _deal():
    d = 0.075
    n = len(tt(d))
    return bp(noise(d), 1800, 6000) * ad(n, 0.001, 55) + 0.4 * sine(hz(67), d) * ad(n, 0.002, 40)


@snd("merge", peak=PEAK_CARD)
def _merge():
    b = Buf(0.34)
    for i, m in enumerate((72, 76, 79, 84)):
        b.add(bell(hz(m), 0.2, rate=9), i * 0.05)
    return b.a


@snd("reward", peak=PEAK_CARD)
def _reward():
    b = Buf(0.55)
    for i, m in enumerate((79, 83, 86, 91)):
        b.add(bell(hz(m), 0.4, rate=5), i * 0.07)
    for m in (67, 71, 74):
        b.add(sine(hz(m), 0.45) * ad(len(tt(0.45)), 0.02, 5), 0.0, 0.18)
    return b.a


# ---------------------------------------------------------------------------- run
@snd("hop", peak=PEAK_RUN)
def _hop():
    d = 0.085
    n = len(tt(d))
    return sine(np.linspace(330, 620, n)) * ad(n, 0.004, 22)


@snd("node", peak=PEAK_RUN)
def _node():
    return pluck(hz(76), 0.11, rate=11)


@snd("coin", peak=PEAK_RUN)
def _coin():
    b = Buf(0.17)
    for at, m in ((0, 83), (0.05, 88)):
        d = 0.12
        b.add(pulse(hz(m), d, 0.5) * ad(len(tt(d)), 0.002, 14), at)
    return b.a


@snd("buy", peak=PEAK_RUN)
def _buy():
    b = Buf(0.26)
    b.add(sine(hz(55), 0.06) * ad(len(tt(0.06)), 0.002, 40), 0)
    b.add(_coin(), 0.07)
    return b.a


@snd("sell", peak=PEAK_RUN)
def _sell():
    b = Buf(0.2)
    for at, m in ((0, 88), (0.05, 83)):
        d = 0.12
        b.add(pulse(hz(m), d, 0.5) * ad(len(tt(d)), 0.002, 14), at)
    return b.a


@snd("heal", peak=PEAK_RUN)
def _heal():
    b = Buf(0.42)
    for i, m in enumerate((72, 76, 79)):
        d = 0.3
        b.add(sine(hz(m), d) * ad(len(tt(d)), 0.015, 7) + 0.2 * sine(hz(m + 12), d) * ad(len(tt(d)), 0.015, 9), i * 0.07)
    return b.a


@snd("levelup", peak=PEAK_RUN)
def _levelup():
    b = Buf(0.62)
    for i, m in enumerate((72, 76, 79, 84)):
        b.add(bell(hz(m), 0.3, rate=6), i * 0.085)
    b.add(bell(hz(88), 0.4, rate=5), 0.34)
    b.add(bell(hz(79), 0.4, rate=5), 0.34, 0.5)
    return b.a


@snd("nap", peak=PEAK_RUN)
def _nap():
    b = Buf(0.9)
    for i, m in enumerate((76, 72, 67)):
        d = 0.4
        b.add(tri(hz(m), d) * ad(len(tt(d)), 0.03, 5.5), i * 0.22)
    return b.a


@snd("box_open", peak=PEAK_RUN)
def _box_open():
    b = Buf(0.5)
    d = 0.16
    n = len(tt(d))
    creak = tri(np.linspace(180, 320, n) + 14 * np.sin(np.linspace(0, 40, n))) * np.sin(np.pi * np.linspace(0, 1, n))
    b.add(creak, 0, 0.6)
    for i, m in enumerate((84, 88, 91)):
        b.add(bell(hz(m), 0.3, rate=7), 0.15 + i * 0.06)
    return b.a


@snd("bell", peak=PEAK_RUN)
def _bell():
    return bell(hz(79), 0.75, rate=3.2) + 0.3 * bell(hz(67), 0.75, rate=3.2)


# ---------------------------------------------------------------------------- battle
@snd("play_fire")
def _play_fire():
    d = 0.28
    n = len(tt(d))
    x = lp(noise(d), 500) * 0.8 * ad(n, 0.01, 6)
    pops = np.zeros(n)
    for _ in range(26):
        at = int(R.uniform(0, 0.8 * n))
        m = int(R.uniform(0.002, 0.007) * SR)
        burst = R.standard_normal(m) * np.linspace(1, 0, m) ** 2 * R.uniform(0.3, 1.0)
        pops[at:at + m] += burst[:max(0, n - at)]
    pops = hpf(pops, 1200)
    return x + 1.4 * pops * np.linspace(1, 0.3, n)


@snd("play_air")
def _play_air():
    d = 0.3
    n = len(tt(d))
    t = np.linspace(0, 1, n)
    out = np.zeros(n)
    for i, (c, w) in enumerate(((600, 500), (1200, 900), (2200, 1500))):
        env = np.exp(-((t - (0.3 + 0.17 * i)) / 0.2) ** 2)
        out += bp(noise(d), c - w / 2, c + w) * env
    return out


@snd("play_water")
def _play_water():
    b = Buf(0.3)
    for at, f0, a in ((0.0, 330, 1.0), (0.11, 440, 0.6)):
        d = 0.16
        n = len(tt(d))
        f = f0 * np.exp(np.linspace(0, 1.0, n) * 1.1)
        b.add(sine(f) * ad(n, 0.004, 17) + 0.2 * sine(f * 2) * ad(n, 0.004, 25), at, a)
    return b.a


@snd("play_earth")
def _play_earth():
    d = 0.24
    n = len(tt(d))
    f = 55 + 70 * np.exp(-np.arange(n) / SR * 28)
    return sine(f) * ad(n, 0.003, 11) + 0.6 * lp(noise(d), 350) * ad(n, 0.001, 30) + 0.15 * lp(noise(d), 2500) * ad(n, 0.0005, 120)


@snd("play_major")
def _play_major():
    b = Buf(0.55)
    for i, m in enumerate((72, 76, 79, 84, 88)):
        b.add(bell(hz(m), 0.45, rate=4.5, bright=1.3), i * 0.045)
    for m in (60, 64, 67):
        d = 0.5
        b.add(sine(hz(m), d) * ad(len(tt(d)), 0.03, 5), 0.0, 0.18)
    return b.a


@snd("play_scrap")
def _play_scrap():
    b = Buf(0.17)
    for at, m in ((0.0, 55), (0.05, 51), (0.1, 58)):
        d = 0.05
        n = len(tt(d))
        b.add(pulse(hz(m), d, 0.5) * ad(n, 0.001, 40) * 0.6 + bp(noise(d), 900, 3500) * ad(n, 0.0005, 70), at)
    return b.a


def _thump(f0, f1, d, rate):
    n = len(tt(d))
    f = f1 + (f0 - f1) * np.exp(-np.arange(n) / SR * 40)
    return sine(f) * ad(n, 0.002, rate)


@snd("hit")
def _hit():
    d = 0.13
    n = len(tt(d))
    return _thump(190, 80, d, 22) + 0.5 * lp(noise(d), 2200) * ad(n, 0.0005, 80)


@snd("hit_big")
def _hit_big():
    d = 0.3
    n = len(tt(d))
    return (_thump(150, 55, d, 11) + 0.6 * lp(noise(d), 1600) * ad(n, 0.0005, 35)
            + 0.4 * tri(np.full(n, 98.0)) * ad(n, 0.002, 14))


@snd("crit")
def _crit():
    b = Buf(0.36)
    b.add(_hit(), 0, 0.9)
    b.add(bell(hz(91), 0.3, rate=6), 0.04)
    b.add(bell(hz(95), 0.3, rate=7), 0.09, 0.7)
    return b.a


@snd("meow")
def _meow():
    d = 0.38
    n = len(tt(d))
    t = np.linspace(0, 1, n)
    f0 = 430 + 330 * np.sin(np.pi * np.clip(t * 1.15, 0, 1)) ** 0.8 - 90 * t
    f0 *= 1 + 0.012 * np.sin(2 * np.pi * 6.5 * t * d)
    # formants: "m-e-o-w" -> F1 low/high/low, F2 sweeps up then down
    F1 = 420 + 420 * np.sin(np.pi * np.clip(t * 1.1, 0, 1)) ** 1.2
    F2 = 1000 + 1500 * np.sin(np.pi * np.clip(t * 1.05, 0, 1)) ** 0.9 - 400 * t
    p = phase(f0)
    out = np.zeros(n)
    for k in range(1, 30):
        fk = f0 * k
        a = np.exp(-((fk - F1) / 260) ** 2) + 0.7 * np.exp(-((fk - F2) / 420) ** 2) + 0.12 * np.exp(-((fk - 3300) / 700) ** 2)
        a = a / k ** 0.4 * (fk < SR * 0.45)
        out += a * np.sin(k * p)
    env = np.minimum(1, t / 0.07) * np.exp(-np.maximum(0, t - 0.55) * 5) * (1 - 0.35 * np.exp(-((t - 0.04) / 0.04) ** 2))
    out *= env
    out += 0.06 * hpf(noise(d), 2500) * env
    return out


@snd("curl")
def _curl():
    d = 0.22
    n = len(tt(d))
    f = 260 + 120 * np.sin(np.pi * np.linspace(0, 1, n))
    return (sine(f) * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.8 + 0.5 * lp(noise(d), 700) * np.sin(np.pi * np.linspace(0, 1, n)) ** 2 * 0.6)


@snd("singe")
def _singe():
    d = 0.3
    n = len(tt(d))
    am = np.clip(lp(R.standard_normal(n), 90) * 6 + 0.6, 0.0, 1.6)
    sz = hpf(noise(d), 3000) * am * np.exp(-np.arange(n) / SR * 5)
    return sz + 0.25 * sine(np.linspace(520, 200, n)) * ad(n, 0.004, 9)


@snd("hiss")
def _hiss():
    d = 0.36
    n = len(tt(d))
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.3
    return bp(noise(d), 3500, 9500) * env


_PENTA = (72, 74, 76, 79, 81)


def _chain(i):
    m = _PENTA[i]
    d = 0.16 + 0.05 * i
    b = Buf(d + 0.05)
    b.add(bell(hz(m), d, rate=7 - i * 0.6), 0)
    b.add(pluck(hz(m - 12), 0.08, rate=18), 0, 0.5)
    if i >= 2:
        b.add(bell(hz(m + 12), d * 0.8, rate=9), 0.04, 0.45)
    if i >= 4:
        b.add(bell(hz(m + 19), 0.3, rate=8), 0.08, 0.4)
    return b.a


for _i in range(5):
    snd("chain_%d" % (_i + 1))(lambda i=_i: _chain(i))


@snd("eat")
def _eat():
    b = Buf(0.36)
    for at, f0, f1 in ((0.0, 420, 190), (0.14, 360, 150)):
        d = 0.14
        n = len(tt(d))
        f = np.linspace(f0, f1, n)
        b.add(sine(f) * np.sin(np.pi * np.linspace(0, 1, n)) ** 0.7 + 0.3 * lp(noise(d), 900) * np.sin(np.pi * np.linspace(0, 1, n)), at)
    b.add(_thump(130, 70, 0.1, 25), 0.26, 0.6)
    return b.a


@snd("roar")
def _roar():
    d = 0.5
    n = len(tt(d))
    t = np.linspace(0, 1, n)
    f0 = 85 + 25 * np.sin(np.pi * t)
    out = np.zeros(n)
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * 28 * t * d)
    F1 = 500 + 200 * np.sin(np.pi * t)
    for k in range(1, 25):
        fk = f0 * k
        a = np.exp(-((fk - F1) / 300) ** 2) + 0.5 * np.exp(-((fk - 1300) / 450) ** 2)
        out += a / k ** 0.3 * np.sin(k * phase(f0))
    out *= trem * np.sin(np.pi * np.clip(t * 1.05, 0, 1)) ** 0.6
    return out + 0.25 * lp(noise(d), 900) * np.sin(np.pi * t)


@snd("bite")
def _bite():
    d = 0.14
    n = len(tt(d))
    snap = hpf(noise(d), 1500) * ad(n, 0.0005, 70)
    return snap + 0.8 * _thump(240, 110, d, 30)


@snd("miss")
def _miss():
    d = 0.22
    n = len(tt(d))
    env = np.sin(np.pi * np.linspace(0, 1, n))
    return bp(noise(d), 1000, 4000) * env * 0.8 + 0.5 * sine(np.linspace(700, 400, n)) * env


@snd("ko")
def _ko():
    d = 0.55
    n = len(tt(d))
    t = np.linspace(0, 1, n)
    f = 520 * np.exp(-t * 1.5) * (1 + 0.03 * np.sin(2 * np.pi * 9 * t * d))
    return tri(f) * np.exp(-t * 2.2) + 0.5 * _thump(130, 50, d, 6)


def _jingle(notes, step, hold, timbre, tail):
    b = Buf(step * len(notes) + tail)
    for i, ms in enumerate(notes):
        for m in ms if isinstance(ms, tuple) else (ms,):
            d = hold if i < len(notes) - 1 else tail
            b.add(timbre(hz(m), d), i * step, 1.0 / (len(ms) if isinstance(ms, tuple) else 1) ** 0.5)
    return b.a


@snd("victory", peak=-8.0)
def _victory():
    b = Buf(1.35)
    notes = ((72, 0.0), (76, 0.14), (79, 0.28), (84, 0.42), (79, 0.62), (84, 0.76), (88, 0.9))
    for m, at in notes:
        b.add(bell(hz(m), 0.45, rate=5), at)
    for m in (72, 76, 79):
        b.add(bell(hz(m), 0.6, rate=3.5), 0.9, 0.4)
    b.add(pluck(hz(48), 0.5, rate=5), 0.9, 0.5)
    return b.a


@snd("defeat", peak=-9.0)
def _defeat():
    b = Buf(1.45)
    for m, at in ((69, 0.0), (65, 0.24), (62, 0.48), (57, 0.78)):
        b.add(musicbox(hz(m), 0.6), at)
        b.add(tri(hz(m - 12), 0.5) * ad(len(tt(0.5)), 0.02, 5), at, 0.4)
    for m in (57, 60):
        b.add(bell(hz(m), 0.6, rate=3), 0.78, 0.3)
    return b.a


@snd("burnout")
def _burnout():
    d = 0.46
    n = len(tt(d))
    t = np.linspace(0, 1, n)
    pop = lp(noise(d), 1200) * np.exp(-t * 7) * 0.8
    puff = bp(noise(d), 800, 2800) * np.sin(np.pi * np.clip(t * 1.4, 0, 1)) ** 2 * 0.5
    return pop + puff + 0.6 * sine(500 * np.exp(-t * 1.6)) * np.exp(-t * 4.5)


@snd("squeak")
def _squeak():
    d = 0.17
    n = len(tt(d))
    t = np.linspace(0, 1, n)
    f = 1800 + 900 * np.sin(np.pi * t * 0.9) + 200 * np.sin(2 * np.pi * 14 * t)
    env = np.sin(np.pi * np.clip(t * 1.05, 0, 1)) ** 0.5
    return (sine(f) + 0.35 * sine(f * 2)) * env


# ---------------------------------------------------------------------------- music
def _kick(d=0.2):
    n = len(tt(d))
    f = 45 + 80 * np.exp(-np.arange(n) / SR * 30)
    return sine(f) * ad(n, 0.002, 14)


def _hat(d=0.04):
    return hpf(noise(d), 6000) * ad(len(tt(d)), 0.0005, 90)


@snd("music_title", kind="music")
def _music_title():
    bpm = 108
    beat = 60.0 / bpm
    bars = 16
    b = Buf(bars * 3 * beat, wrap=True)
    # chords: (bass, triad)
    CH = {"Am": (45, (57, 60, 64)), "F": (41, (57, 60, 65)), "C": (48, (55, 60, 64)), "G": (43, (55, 59, 62)),
          "Dm": (50, (57, 62, 65)), "E": (40, (56, 59, 64))}
    prog = ["Am", "F", "C", "G", "Am", "F", "E", "Am", "Am", "F", "C", "G", "Dm", "Am", "E", "Am"]
    mel_a = [((0, 69, 1), (1, 72, 1), (2, 76, 1)), ((0, 77, 2), (2, 76, .5), (2.5, 74, .5)),
             ((0, 72, 1), (1, 76, 1), (2, 79, 1)), ((0, 79, 2), (2, 77, .5), (2.5, 76, .5)),
             ((0, 76, 1), (1, 72, 1), (2, 69, 1)), ((0, 72, 1), (1, 74, 1), (2, 77, 1)),
             ((0, 76, 1.5), (1.5, 74, .5), (2, 71, 1)), ((0, 69, 3),)]
    mel_b = [((0, 76, 1), (1, 81, 1), (2, 79, 1)), ((0, 77, 1), (1, 81, 1), (2, 77, 1)),
             ((0, 79, 1), (1, 76, 1), (2, 72, 1)), ((0, 74, 1), (1, 79, 1), (2, 71, 1)),
             ((0, 77, 1), (1, 74, 1), (2, 69, 1)), ((0, 72, 1), (1, 76, 1), (2, 81, 1)),
             ((0, 80, 1.5), (1.5, 76, .5), (2, 71, 1)), ((0, 69, 3),)]
    mel = mel_a + mel_b
    for bar, name in enumerate(prog):
        root, tri_ = CH[name]
        t0 = bar * 3 * beat
        b.add(pluck(hz(root), 0.9, rate=3.0, bright=0.6), t0, 0.55)
        for k in (1, 2):
            for j, m in enumerate(tri_):
                b.add(musicbox(hz(m), 0.55), t0 + k * beat + j * 0.012, 0.2)
        for off, m, dur in mel[bar]:
            b.add(musicbox(hz(m), max(0.5, dur * beat * 1.4)), t0 + off * beat, 0.5)
            if bar >= 8:
                b.add(musicbox(hz(m - 12), 0.5), t0 + off * beat, 0.12)
    return b.a


@snd("music_attic", kind="music")
def _music_attic():
    bpm = 100
    eighth = 30.0 / bpm
    bars = 12
    b = Buf(bars * 8 * eighth, wrap=True)
    CH = [("Dm", 38, (62, 65, 69, 74)), ("Bb", 34, (58, 62, 65, 70)), ("Gm", 31, (55, 58, 62, 67)), ("A", 33, (57, 61, 64, 69))]
    pats = ([0, 1, 2, 3, 2, 1, 2, 1], [0, 2, 1, 3, 1, 2, 3, 2], [0, 1, 2, 1, 3, 2, 1, 2])
    for bar in range(bars):
        name, root, tones = CH[bar % 4]
        t0 = bar * 8 * eighth
        pat = pats[(bar // 4) % 3]
        for i, ix in enumerate(pat):
            vel = 0.8 if i % 4 == 0 else 0.5
            b.add(pluck(hz(tones[ix]), 0.55, rate=5.5, bright=0.7), t0 + i * eighth, vel * 0.5)
        # pad: root + fifth, slow swell
        d = 8 * eighth + 0.4
        n = len(tt(d))
        swell = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
        b.add((sine(hz(root + 12), d) + 0.5 * sine(hz(root + 19), d)) * swell, t0 - 0.2 + 0.2, 0.28)
        b.add(sine(hz(root), d) * swell, t0, 0.35)
        if bar >= 4 and bar % 2 == 0:
            b.add(bell(hz(tones[3] + 12), 1.4, rate=3), t0 + 5 * eighth, 0.22)
        if bar % 4 == 3:
            b.add(bell(hz(tones[1] + 24), 1.2, rate=3.5), t0 + 7 * eighth, 0.14)
    return b.a


@snd("music_boss", kind="music")
def _music_boss():
    bpm = 132
    beat = 60.0 / bpm
    eighth = beat / 2
    bars = 16
    b = Buf(bars * 4 * beat, wrap=True)
    E, G, C, D, B = 40, 43, 36, 38, 35
    prog = [E, E, C, D, E, G, C, B] * 2
    bass_pat = [0, 12, 0, 7, 0, 12, 3, 10]
    bass_pat2 = [0, 0, 12, 0, 7, 0, 12, 7]
    lead = [((0, 76), (1, 79), (1.5, 76), (2, 74), (3, 71)), ((0, 76), (0.5, 79), (1, 83), (2, 81), (3.5, 79)),
            ((0, 72), (1, 76), (1.5, 79), (2.5, 76), (3, 72)), ((0, 74), (1, 78), (2, 81), (2.5, 78), (3, 74))]
    for bar in range(bars):
        root = prog[bar]
        t0 = bar * 4 * beat
        pat = bass_pat if (bar // 4) % 2 == 0 else bass_pat2
        for i, semi in enumerate(pat):
            d = 0.16
            n = len(tt(d))
            note = hz(root + 12 + (12 if semi >= 12 else semi))
            x = lp(pulse(note, d, 0.35), 1400) * ad(n, 0.003, 11)
            b.add(x, t0 + i * eighth, 0.65 if i % 2 == 0 else 0.45)
        for k in (0, 2):
            b.add(_kick(), t0 + k * beat, 0.55)
        for i in range(8):
            if i % 2 == 1:
                b.add(_hat(), t0 + i * eighth, 0.07)
        # soft 16th pulse arpeggio on the chord (the "pulse")
        third = 3 if root in (E, B) else 4
        tones = (root + 24, root + 24 + third, root + 24 + 7)
        for i in range(16):
            if i % 4 == 3:
                continue
            m = tones[i % 3]
            d = 0.07
            n = len(tt(d))
            b.add(pulse(hz(m), d, 0.125) * ad(n, 0.002, 30), t0 + i * eighth / 2, 0.07)
        # playful lead on the second half of each 8-bar phrase
        if (bar // 4) % 2 == 1 or bar % 4 == 3:
            for off, m in lead[bar % 4]:
                b.add(pluck(hz(m), 0.3, rate=9, bright=0.8), t0 + off * beat, 0.4)
    return b.a


# ---------------------------------------------------------------------------- output
def finalize(name, x, kind, peak_db):
    x = np.asarray(x, dtype=np.float64)
    x = x - np.mean(x) if kind == "music" else x
    if kind == "music":
        rms = np.sqrt(np.mean(x ** 2))
        x = x * (10 ** (MUSIC_RMS / 20) / rms)
        pk = np.max(np.abs(x))
        ceiling = 10 ** (MUSIC_PEAK_MAX / 20)
        if pk > ceiling:
            x = np.tanh(x / ceiling) * ceiling  # soft limiter, unity gain for small signals
        return x
    x = fade(x)
    pk = np.max(np.abs(x))
    return x * (10 ** (peak_db / 20) / max(pk, 1e-9))


def write_wav(path, x):
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main(argv):
    global R
    only = set(argv[1:])
    print("%-14s %9s %9s %9s" % ("name", "dur ms", "peak dBFS", "rms dBFS"))
    for name, (fn, kind, peak) in REGISTRY.items():
        if only and name not in only:
            continue
        R = np.random.default_rng(zlib.crc32(name.encode()))
        x = finalize(name, fn(), kind, peak)
        write_wav(os.path.join(HERE, name + ".wav"), x)
        pk = 20 * np.log10(np.max(np.abs(x)) + 1e-12)
        rms = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
        print("%-14s %9.0f %9.1f %9.1f" % (name, 1000 * len(x) / SR, pk, rms))


if __name__ == "__main__":
    main(sys.argv)
