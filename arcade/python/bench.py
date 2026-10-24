"""Board benchmark: times arcade_draw_ops RPCs for each kind of drawing and prints measured costs, so
python/costmodel.py can be checked against the console. Deploy with `python scripts/deploy.py --bench`
and read the output with `make logs`. Not part of the game.
"""

import time

import assets
from engine import BODY, TITLE, Screen, rgb, MAX_CHUNK

NAVY = rgb(41, 36, 74)       # 0x2929: fast fill
PURPLE = rgb(90, 60, 150)    # slow fill
REPEAT = 20


def measure_ms(bridge, build):
    """Average wall ms per call of the ops `build(screen)` queues (one chunk per call)."""
    screen = Screen()
    build(screen)
    chunks = screen.take()
    assert len(chunks) == 1, "benchmark ops must fit one chunk"
    start = time.monotonic()
    for _ in range(REPEAT):
        bridge.call("arcade_draw_ops", chunks[0])
    return 1000 * (time.monotonic() - start) / REPEAT


def set_mode(bridge, mode):
    """Select the TFT bus path (0 = library, 1..3 = direct GPIO); returns the active mode, -1 if unsupported."""
    try:
        return int(bridge.call("arcade_bus_mode", mode))
    except Exception as error:  # firmware without the method
        print(f"bench: arcade_bus_mode unavailable ({error!r})", flush=True)
        return -1


def pattern(bridge):
    """Held on screen for a few seconds so a person can spot a corrupted bus (noise, wrong colors)."""
    screen = Screen()
    screen.clear(NAVY)
    for i, color in enumerate((0xF800, 0x07E0, 0x001F, 0xFFE0, 0x07FF, 0xF81F, 0xFFFF, 0x8410)):
        screen.fill_rect(8 + i * 58, 8, 50, 40, color)
    screen.text(8, 60, "Bus pattern check: text, bars and the sprite must be clean", 0xFFFF, NAVY, BODY)
    screen.text(8, 80, "Fire Claw 0123456789", 0xFFE0, NAVY, TITLE)
    domino = getattr(assets, "DOMINO", None)
    if domino:
        screen.blit(domino, 0, 8, 120, bg=NAVY)
        screen.blit(domino, 0, 100, 120, flip=True, tint=0xFFFF, bg=None)
    for chunk in screen.take():
        bridge.call("arcade_draw_ops", chunk)


def main():
    from arduino.app_utils import Bridge

    domino = getattr(assets, "DOMINO", None)
    cases = [
        ("fill 100x100 fast (0x2929)", 10000, lambda s: s.fill_rect(0, 0, 100, 100, NAVY)),
        ("fill 100x100 slow", 10000, lambda s: s.fill_rect(0, 0, 100, 100, PURPLE)),
        ("fill 400x200 fast", 80000, lambda s: s.fill_rect(0, 0, 400, 200, NAVY)),
        ("fill 400x200 slow", 80000, lambda s: s.fill_rect(0, 0, 400, 200, PURPLE)),
        ("text BODY x30 opaque", 30 * 6 * 15, lambda s: s.text(0, 0, "x" * 30, 0xFFFF, NAVY, BODY)),
        ("text TITLE x12 opaque", 12 * 14 * 19, lambda s: s.text(0, 0, "x" * 12, 0xFFFF, NAVY, TITLE)),
        ("text BODY x30 transparent", 30 * 6 * 15, lambda s: s.text(0, 0, "x" * 30, 0xFFFF, None, BODY)),
    ]
    if domino:
        cases += [
            ("asset 64x64 opaque", 4096, lambda s: s.blit(domino, 0, 0, 0, bg=NAVY)),
            ("asset 64x64 transparent", 4096, lambda s: s.blit(domino, 0, 0, 0, bg=None)),
            ("asset 64x64 scale 2", 16384, lambda s: s.blit(domino, 0, 0, 0, scale=2, bg=NAVY)),
        ]
    summary = []
    for mode in (0, 1, 2, 3):
        active = set_mode(Bridge, mode)
        if active != mode:
            print(f"bench: mode {mode} not available (firmware reports {active}); "
                  "build with ARCADE_FAST_BUS 1 (scripts/deploy.py --fast-bus)", flush=True)
            continue
        label = "library bus" if mode == 0 else f"direct GPIO mode {mode}"
        pattern(Bridge)
        time.sleep(3)
        base = measure_ms(Bridge, lambda s: s.fill_rect(0, 0, 1, 1, NAVY))
        print(f"bench: [{label}] rpc + 1 px op = {base:.1f} ms", flush=True)
        for name, pixels, build in cases:
            ms = measure_ms(Bridge, build)
            net = max(ms - base, 0.001)
            print(f"bench: [{label}] {name}: {ms:.1f} ms/call, {net:.1f} ms net, {pixels / net:.0f} kpx/s",
                  flush=True)
            summary.append((label, name, pixels / net))
        ms = measure_ms(Bridge, lambda s: [s.fill_rect(i * 4, 0, 2, 2, NAVY) for i in range(10)])
        print(f"bench: [{label}] 10 tiny ops: {ms:.1f} ms/call, {(ms - base) / 9:.2f} ms per extra op", flush=True)
    names = [c[0] for c in cases]
    print("bench: ---- kpx/s by bus mode ----", flush=True)
    for name in names:
        row = ", ".join(f"{label}: {rate:.0f}" for label, n, rate in summary if n == name)
        print(f"bench: {name}: {row}", flush=True)
    print(f"bench: done (chunk limit {MAX_CHUNK} B). Copy the best SAFE mode's numbers into costmodel.py "
          "and set FastBus::mode in sketch.ino.", flush=True)
    set_mode(Bridge, 3 if any(label != "library bus" for label, *_ in summary) else 0)
    while True:
        time.sleep(60)
