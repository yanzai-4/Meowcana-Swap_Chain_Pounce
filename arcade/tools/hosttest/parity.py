"""Host parity test: compiles sketch/sketch.ino's op decoder with stub Arduino headers (zig c++) and checks
that it draws the same pixels as tools/sim.py for a battery of ops (fonts, assets, flips, tints, regions,
cards, dotted rects, clipping). Run from arcade/ after tools/pack_assets.py:  python tools/hosttest/parity.py
"""

import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tools"))

import assets  # noqa: E402
import engine  # noqa: E402
import sim  # noqa: E402
from PIL import Image  # noqa: E402


def build(fast):
    exe = ROOT / "build" / ("harness_fast.exe" if fast else "harness.exe")
    sources = [HERE / "harness.cpp", ROOT / "sketch" / "sketch.ino", ROOT / "sketch" / "assets.h"] + list(HERE.glob("*.h"))
    if not exe.exists() or exe.stat().st_mtime < max(s.stat().st_mtime for s in sources):
        subprocess.run([sys.executable, "-m", "ziglang", "c++", "-std=c++17", f"-I{HERE}", f"-I{ROOT / 'sketch'}",
                        f"-DARCADE_FAST_BUS={int(fast)}", "-Wall", "-Wno-unused-function", "-o", str(exe),
                        str(HERE / "harness.cpp")], check=True, capture_output=True)
        exe.with_suffix(".pdb").unlink(missing_ok=True)
    return exe


def battery():
    s = engine.Screen()
    navy = engine.rgb(41, 36, 74)
    s.clear(navy)
    y = 2
    for font in (engine.BODY, engine.TITLE, engine.NUM, engine.TINY):
        s.text(6, y, "Fire Claw 0123 +2 (50%)!", engine.WHITE, navy, font)
        y += engine.measure("A", font)[1] + 1
    s.text(300, 70, "Cups 3 \u00b7 \u2605 \u2192 \u25bc", engine.WHITE, navy, engine.BODY, 2)
    s.text(-9, 90, "clipped left", engine.YELLOW, navy, engine.BODY, 2)
    s.text(440, 90, "clipped right", engine.YELLOW, navy, engine.BODY, 2)
    s.text(200, 120, "transparent", engine.CYAN, None, engine.BODY)
    s.text(200, 135, "Scale3", engine.CYAN, None, engine.TITLE, 2)
    s.text(300, -6, "top clip", engine.GREEN, navy, engine.TITLE)
    d = assets.DOMINO_IDLE
    x = 4
    for kw in ({}, {"flip": True}, {"flip_y": True}, {"flip": True, "flip_y": True}, {"tint": engine.WHITE},
               {"dim": True}, {"bg": None}, {"bg": None, "flip": True, "scale": 2}, {"scale": 2},
               {"scale": 3}, {"scale": 4, "flip_y": True}):
        s.blit(d, 1, x, 150 if x < 400 else 120, **({"bg": navy} | kw))
        x = (x + 66) if x < 400 else 4
    s.blit(d, 0, -20, 230, bg=navy)
    s.blit(d, 0, 450, 280, bg=navy, flip=True)
    s.blit(d, 2, 100, -30, bg=navy, flip_y=True)
    s.blit(d, 0, 300, 250, scale=2, bg=None, tint=engine.RED, dim=True)
    s.asset_region(d, 0, 20, 220, 10, 12, 30, 40, bg=navy)
    s.asset_region(d, 0, 60, 220, 0, 0, 64, 64, bg=None)
    s.asset_region(d, 0, 140, 220, 50, 50, 99, 99, bg=navy)
    s.asset_region(d, 0, 330, 200, 5, 5, 40, 50, bg=navy, dim=True)
    s.dotted_rect(200, 200, 60, 70, engine.GRAY)
    s.dotted_rect(-4, 300, 50, 30, engine.GRAY)
    face = getattr(assets, "CARD_U", None)
    if face:
        star, gem = getattr(assets, "UI_STAR", None), getattr(assets, "UI_GEM", None)
        for i, kw in enumerate(({}, {"stars": 2, "star_asset": star}, {"gem": 2, "gem_asset": gem, "stars": 1, "star_asset": star},
                                {"dim": True, "stars": 3, "star_asset": star}, {"tint": engine.WHITE},
                                {"scale": 2, "stars": 1, "star_asset": star})):
            s.card(face, 3 + i, 4 + i * 52 if i < 5 else 280, 20 if i < 5 else 100,
                   engine.rgb(82, 121, 222), navy, field=engine.rgb(60, 52, 100), **kw)
        s.card(face, 5, 440, -10, engine.RED, navy)
    return s.take()


def compare(raw, ref):
    px = ref.load()
    bad, first = 0, None
    for yy in range(320):
        for xx in range(480):
            word = struct.unpack_from("<H", raw, (yy * 480 + xx) * 2)[0]
            if sim.to_rgb(word) != px[xx, yy]:
                bad += 1
                first = first or (xx, yy)
    return bad, first


def main():
    chunks = battery()
    ops = HERE / "ops.bin"
    ops.write_bytes(b"".join(struct.pack("<H", len(c)) + c for c in chunks))
    device = sim.Device(sim.Library())
    for c in chunks:
        device.apply(c)
    device.img.save(ROOT / "build" / "parity_sim.png")
    out = HERE / "harness.rgb565"
    failed = 0
    print(f"{len(chunks)} chunks, {sum(map(len, chunks))} bytes")
    for label, fast, mode in (("library bus", False, 0), ("fast bus mode 1", True, 1),
                              ("fast bus mode 2", True, 2), ("fast bus mode 3", True, 3),
                              ("fast build, library mode", True, 0)):
        done = subprocess.run([str(build(fast)), str(ops), str(out), str(mode)], capture_output=True, text=True)
        bad, first = compare(out.read_bytes(), device.img)
        print(f"{label}: {bad} differing pixels{f' (first at {first})' if first else ''}; "
              f"exit {done.returncode}; {done.stderr.strip()}")
        failed += bool(bad) or done.returncode != 0
    ops.unlink()
    out.unlink()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
