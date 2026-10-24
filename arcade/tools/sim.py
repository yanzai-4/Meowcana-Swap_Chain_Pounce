"""PC simulator for the arcade console: runs the real Python game against a fake Bridge that decodes
the exact `arcade_draw_ops` bytes (same semantics as sketch/sketch.ino, using the packed asset and
font data from build/sim_assets.bin) into a 480x320 image, and charges every frame the device cost
model from python/costmodel.py.

Headless, scripted (deterministic virtual clock that advances by the estimated device time):
  python tools/sim.py --game nla.flow:make --keys "1.0s,A,R,R,A,2.0s" --shots build/shots/ --every 0.5

Interactive window at 2x (arrows = stick, Z = A, X = B, C = C; holding a key is a held stick/button):
  python tools/sim.py --game nla.flow:make --window

--keys is a comma list, played in order:
  1.5s            wait
  A | B | C       tap a button (0.1 s down, 0.1 s up)       L | R | U | D   tap the stick
  R:0.5s          hold for a duration                        R+A:0.3s        several inputs at once
  S               tap the stick press                        EPOCH           the sketch repainted the screen
  SHOT[:name]     save a screenshot now (also --every N)
Writes PNGs and cost.csv (one row per game frame) to --shots; prints warnings for frames above
45 ms (70 ms while the game sets `busy = True`) and a summary. Run from arcade/.
"""

import argparse
import csv
import importlib
import json
import random
import struct
import sys
import time as real_time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from PIL import Image, ImageOps  # noqa: E402

import costmodel  # noqa: E402
import engine  # noqa: E402

W, H = engine.WIDTH, engine.HEIGHT
SIM_BIN = ROOT / "build" / "sim_assets.bin"
WAITING_AFTER_S = 1.5       # the sketch shows its waiting screen after this long without a draw call
TAP_S = 0.1


def to_rgb(c):
    r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


def tdiv(a, b):
    """C integer division (truncates toward zero)."""
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


# ------------------------------------------------------------------ packed data

class Library:
    """Decodes frames and glyphs from build/sim_assets.bin exactly as the sketch does."""

    def __init__(self, path=SIM_BIN):
        blob = Path(path).read_bytes()
        if blob[:4] != b"NLA1":
            raise SystemExit(f"{path}: not a sim asset file; run tools/pack_assets.py")
        n = struct.unpack("<I", blob[4:8])[0]
        head = json.loads(blob[8:8 + n])
        self.palette = head["palette"]
        self.assets = head["assets"]
        self.offsets = head["frame_offsets"]
        self.fonts = head["fonts"]
        start = 8 + n
        self.data = blob[start:start + head["data_len"]]
        self.font_data = blob[start + head["data_len"]:]
        self.first_char = head["first_char"]
        self.glyph_count = head["glyph_count"]
        self._indices = {}
        self._glyphs = {}
        self.rgb_table = [(0, 0, 0)] + [to_rgb(c) for c in self.palette]

    def indices(self, asset_id, frame):
        """Palette indices (0 = transparent) of one frame, row-major bytes."""
        key = (asset_id, frame)
        if key not in self._indices:
            a = self.assets[asset_id]
            if frame >= a["frames"]:
                raise ValueError("frame out of range")
            start = self.offsets[a["first"] + frame]
            end = self.offsets[a["first"] + frame + 1]
            n = a["w"] * a["h"]
            blob = self.data[start:end]
            local = self.data[a["pal"]:a["pal"] + 64]
            if a["mode"] == 0:
                out = bytearray()
                i = 0
                while len(out) < n:  # blob may run on into the next asset's palette
                    run, idx = blob[i] >> 6, local[blob[i] & 63]
                    if run:
                        i += 1
                    else:
                        run, i = blob[i + 1], i + 2
                    out += bytes((idx,)) * run
            else:
                out = bytearray(len(blob) * 2)
                out[0::2] = bytes(local[b >> 4] for b in blob)
                out[1::2] = bytes(local[b & 15] for b in blob)
            self._indices[key] = bytes(out[:n])
        return self._indices[key]

    def glyph_mask(self, font_id, code):
        """('1' mask image, advance, ink width) for one character."""
        key = (font_id, code)
        if key not in self._glyphs:
            font = self.fonts[font_id]
            h = font["height"]
            adv, width, offset = font["glyphs"][code - self.first_char]
            stride = (width + 7) // 8
            mask = None
            if width:
                mask = Image.frombytes("1", (width, h), self.font_data[offset:offset + stride * h])
            self._glyphs[key] = (mask, adv, width)
        return self._glyphs[key]


# ------------------------------------------------------------------ device

class Device:
    """The sketch's drawing half: decodes op bytes onto a 480x320 image and counts cost."""

    def __init__(self, lib):
        self.lib = lib
        self.img = Image.new("RGB", (W, H), (0, 0, 0))
        self.px = self.img.load()
        self.reset_cost()
        self._runs_cache = {}

    def reset_cost(self):
        self.fast = self.slow = self.runs = self.ops = 0

    # -- raster helpers (clipped); each counts pixels
    def fill(self, x, y, w, h, c):
        x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
        if x0 >= x1 or y0 >= y1:
            return
        self.img.paste(to_rgb(c), (x0, y0, x1, y1))
        if costmodel.is_fast(c):
            self.fast += (x1 - x0) * (y1 - y0)
        else:
            self.slow += (x1 - x0) * (y1 - y0)
        self.runs += 1

    def hline(self, x, y, n, c):
        if n > 0:
            self.fill(x, y, n, 1, c)

    def vline(self, x, y, n, c):
        if n > 0:
            self.fill(x, y, 1, n, c)

    def pixel(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[x, y] = to_rgb(c)
        self.slow += 1
        self.runs += 1

    # -- Adafruit_GFX algorithms, as used by the DIYables library
    def line(self, x0, y0, x1, y1, c):
        if x0 == x1:
            return self.vline(x0, min(y0, y1), abs(y1 - y0) + 1, c)
        if y0 == y1:
            return self.hline(min(x0, x1), y0, abs(x1 - x0) + 1, c)
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0, x1, y1 = y0, x0, y1, x1
        if x0 > x1:
            x0, x1, y0, y1 = x1, x0, y1, y0
        dx, dy = x1 - x0, abs(y1 - y0)
        err, ystep = dx // 2, 1 if y0 < y1 else -1
        for x in range(x0, x1 + 1):
            self.pixel(y0, x, c) if steep else self.pixel(x, y0, c)
            err -= dy
            if err < 0:
                y0 += ystep
                err += dx

    def rect(self, x, y, w, h, c):
        if w <= 0 or h <= 0:
            return
        self.hline(x, y, w, c)
        self.hline(x, y + h - 1, w, c)
        self.vline(x, y, h, c)
        self.vline(x + w - 1, y, h, c)

    def circle(self, x0, y0, r, c):
        f, ddx, ddy, x, y = 1 - r, 1, -2 * r, 0, r
        for p in ((x0, y0 + r), (x0, y0 - r), (x0 + r, y0), (x0 - r, y0)):
            self.pixel(*p, c)
        while x < y:
            if f >= 0:
                y -= 1
                ddy += 2
                f += ddy
            x += 1
            ddx += 2
            f += ddx
            for dx, dy in ((x, y), (-x, y), (x, -y), (-x, -y), (y, x), (-y, x), (y, -x), (-y, -x)):
                self.pixel(x0 + dx, y0 + dy, c)

    def fill_circle(self, x0, y0, r, c):
        self.vline(x0, y0 - r, 2 * r + 1, c)
        f, ddx, ddy, x, y, px, py = 1 - r, 1, -2 * r, 0, r, 0, r
        while x < y:
            if f >= 0:
                y -= 1
                ddy += 2
                f += ddy
            x += 1
            ddx += 2
            f += ddx
            if x < y + 1:
                self.vline(x0 + x, y0 - y, 2 * y + 1, c)
                self.vline(x0 - x, y0 - y, 2 * y + 1, c)
            if y != py:
                self.vline(x0 + py, y0 - px, 2 * px + 1, c)
                self.vline(x0 - py, y0 - px, 2 * px + 1, c)
                py = y
            px = x

    def fill_triangle(self, x0, y0, x1, y1, x2, y2, c):
        if y0 > y1:
            y0, y1, x0, x1 = y1, y0, x1, x0
        if y1 > y2:
            y2, y1, x2, x1 = y1, y2, x1, x2
        if y0 > y1:
            y0, y1, x0, x1 = y1, y0, x1, x0
        if y0 == y2:
            a, b = min(x0, x1, x2), max(x0, x1, x2)
            return self.hline(a, y0, b - a + 1, c)
        dx01, dy01, dx02, dy02, dx12, dy12 = x1 - x0, y1 - y0, x2 - x0, y2 - y0, x2 - x1, y2 - y1
        sa = sb = 0
        last = y1 if y1 == y2 else y1 - 1
        y = y0
        while y <= last:
            a, b = x0 + tdiv(sa, dy01), x0 + tdiv(sb, dy02)
            sa += dx01
            sb += dx02
            if a > b:
                a, b = b, a
            self.hline(a, y, b - a + 1, c)
            y += 1
        sa, sb = dx12 * (y - y1), dx02 * (y - y0)
        while y <= y2:
            a, b = x1 + tdiv(sa, dy12), x0 + tdiv(sb, dy02)
            sa += dx12
            sb += dx02
            if a > b:
                a, b = b, a
            self.hline(a, y, b - a + 1, c)
            y += 1

    # -- assets and text
    def solid_runs(self, asset_id, frame):
        """(opaque pixels, horizontal runs) of a frame, for transparent-draw cost."""
        key = (asset_id, frame)
        if key not in self._runs_cache:
            a = self.lib.assets[asset_id]
            idx, w = self.lib.indices(asset_id, frame), a["w"]
            solid = runs = 0
            for r in range(a["h"]):
                prev = 0
                for v in idx[r * w:(r + 1) * w]:
                    solid += v != 0
                    runs += (v != 0) and not prev
                    prev = v
            self._runs_cache[key] = (solid, runs)
        return self._runs_cache[key]

    def tile(self, asset_id, frame, region, flags, bg, tint):
        """(RGB tile, L mask) of an asset frame region with flips/tint/dim applied; None if invalid."""
        lib = self.lib
        if asset_id >= len(lib.assets):
            return None
        a = lib.assets[asset_id]
        if frame >= a["frames"]:
            return None
        sx, sy, rw, rh = region or (0, 0, a["w"], a["h"])
        if sx >= a["w"] or sy >= a["h"]:
            return None
        rw, rh = min(rw, a["w"] - sx), min(rh, a["h"] - sy)
        if rw <= 0 or rh <= 0:
            return None
        table = list(lib.rgb_table)
        for i in range(1, len(table)):
            c = tint if flags & engine.F_TINT else lib.palette[i - 1]
            table[i] = to_rgb(engine.dim565(c) if flags & engine.F_DIM else c)
        table[0] = to_rgb(bg)
        idx = lib.indices(asset_id, frame)
        pal = Image.frombytes("P", (a["w"], a["h"]), idx)
        pal.putpalette([v for rgb in table + [(0, 0, 0)] * (256 - len(table)) for v in rgb])
        mask = Image.frombytes("L", (a["w"], a["h"]), bytes(255 if v else 0 for v in idx))
        box = (sx, sy, sx + rw, sy + rh)
        tile, mask = pal.crop(box).convert("RGB"), mask.crop(box)
        if flags & engine.F_FLIP_X:
            tile, mask = ImageOps.mirror(tile), ImageOps.mirror(mask)
        if flags & engine.F_FLIP_Y:
            tile, mask = ImageOps.flip(tile), ImageOps.flip(mask)
        return tile, mask

    def blit(self, asset_id, frame, x, y, region, scale, flags, bg, tint):
        made = self.tile(asset_id, frame, region, flags, bg, tint)
        if made is None:
            return
        tile, mask = made
        a = self.lib.assets[asset_id]
        rw, rh = tile.size
        if scale > 1:
            tile = tile.resize((rw * scale, rh * scale), Image.NEAREST)
            mask = mask.resize((rw * scale, rh * scale), Image.NEAREST)
        dw, dh = rw * scale, rh * scale
        clip = (max(0, min(x + dw, W) - max(x, 0)) * max(0, min(y + dh, H) - max(y, 0))) / (dw * dh)
        if flags & engine.F_TRANSPARENT:
            self.img.paste(tile, (x, y), mask)
            solid, runs = self.solid_runs(asset_id, frame)
            area = rw * rh / (a["w"] * a["h"])
            self.slow += solid * area * scale * scale * clip
            self.runs += runs * area * scale * clip
        else:
            self.img.paste(tile, (x, y))
            self.slow += dw * dh * clip

    def card(self, p):
        aid, frame, x, y, rim, bg, field, flags, sg, star_id, gem_id = struct.unpack_from("<BHhhHHHBBBB", p, 1)
        if aid >= len(self.lib.assets):
            return
        face = self.lib.assets[aid]
        cw, ch = face["w"] + 4, face["h"] + 4
        dim = bool(flags & engine.F_DIM)
        tint = struct.unpack_from("<H", p, 18)[0] if flags & engine.F_TINT else 0
        shade = (lambda c: engine.dim565(c)) if dim else (lambda c: c)
        ink = shade(engine.CARD_INK)
        card = Image.new("RGB", (cw, ch), to_rgb(shade(rim)))
        card.paste(to_rgb(ink), (1, 1, cw - 1, ch - 1))
        dflag = engine.F_DIM if dim else 0

        def overlay(asset_id, frame_no, at, clear, extra):
            made = self.tile(asset_id, frame_no, None, dflag | extra, clear, tint)
            if made:
                card.paste(made[0], at)

        overlay(aid, frame, (2, 2), ink, flags & engine.F_TINT)
        for i in range(sg & 3):
            overlay(star_id, 0, (cw - 8 - 6 * i, 5), shade(field), 0)
        if sg >> 2:
            overlay(gem_id, (sg >> 2) - 1, (cw - 12, ch - 12 if face["w"] == 44 else ch - 10), shade(field), 0)
        for corner in ((0, 0), (cw - 1, 0), (0, ch - 1), (cw - 1, ch - 1)):
            card.putpixel(corner, to_rgb(bg))
        scale = (flags & 3) + 1
        if scale > 1:
            card = card.resize((cw * scale, ch * scale), Image.NEAREST)
        self.img.paste(card, (x, y))
        clip = (max(0, min(x + card.width, W) - max(x, 0)) * max(0, min(y + card.height, H) - max(y, 0))) \
            / (card.width * card.height)
        self.slow += card.width * card.height * clip

    def text(self, x, y, font_id, scale, fg, bg, chars):
        lib = self.lib
        font = lib.fonts[font_id]
        h = font["height"]
        glyphs = [lib.glyph_mask(font_id, c if lib.first_char <= c < lib.first_char + lib.glyph_count else 63)
                  for c in chars]
        total = sum(adv for _, adv, _ in glyphs[:-1]) + (max(glyphs[-1][1], glyphs[-1][2]) if glyphs else 0)
        run = Image.new("L", (max(total, 1), h), 0)
        pen = 0
        for mask, adv, _ in glyphs:
            if mask is not None:
                run.paste(255, (pen, 0), mask)
            pen += adv
        if scale > 1:
            run = run.resize((run.width * scale, h * scale), Image.NEAREST)
        cw, ch = total * scale, h * scale
        if cw <= 0:
            return
        clip = (max(0, min(x + cw, W) - max(x, 0)) * max(0, min(y + ch, H) - max(y, 0))) / (cw * ch)
        if bg is not None:
            self.img.paste(to_rgb(bg), (x, y, x + cw, y + ch))
            self.slow += cw * ch * clip
        else:
            data = run.tobytes()
            self.slow += sum(1 for v in data if v) * clip
            self.runs += ch * clip
        self.img.paste(to_rgb(fg), (x, y, x + cw, y + ch), run)

    def dotted(self, x, y, w, h, c):
        if w <= 0 or h <= 0:
            return
        for i in range(0, w, 4):
            n = min(2, w - i)
            self.fill(x + i, y, n, 1, c)
            if h > 1:
                self.fill(x + i, y + h - 1, n, 1, c)
        for i in range(4, h - 1, 4):
            n = min(2, h - 1 - i)
            self.fill(x, y + i, 1, n, c)
            if w > 1:
                self.fill(x + w - 1, y + i, 1, n, c)

    # -- op stream
    @staticmethod
    def op_size(p, left):
        op = p[0]
        if op == 1:
            return 3
        if op in (2, 3, 6, 11):
            return 11
        if op in (4, 5):
            return 9
        if op == 7:
            if left < 6:
                return 0
            count = 8 if p[5] & 0x80 else 10
            return count + 1 + p[count] if left > count else 0
        if op == 8:
            return 15
        if op == 9:
            return (13 if p[8] & engine.F_TINT else 11) if left >= 9 else 0
        if op == 10:
            return 19
        if op == 12:
            return (20 if p[14] & engine.F_TINT else 18) if left >= 15 else 0
        return 0

    def apply(self, data):
        """Validates the whole chunk first (a bad chunk draws nothing, like the sketch), then draws."""
        ops, i = [], 0
        while i < len(data):
            n = self.op_size(data[i:], len(data) - i)
            if n == 0 or n > len(data) - i:
                raise ValueError(f"bad op packet at byte {i} (op {data[i]})")
            ops.append(data[i:i + n])
            i += n
        for p in ops:
            self.draw(p)
        self.ops += len(ops)

    def draw(self, p):
        op = p[0]
        if op == 1:
            c = struct.unpack_from("<H", p, 1)[0]
            self.fill(0, 0, W, H, c)
        elif op in (2, 3):
            x, y, w, h, c = struct.unpack_from("<hhhhH", p, 1)
            w, h = max(0, min(w, 480)), max(0, min(h, 320))
            self.fill(x, y, w, h, c) if op == 2 else self.rect(x, y, w, h, c)
        elif op in (4, 5):
            x, y, r, c = struct.unpack_from("<hhhH", p, 1)
            r = max(0, min(r, 320))
            self.fill_circle(x, y, r, c) if op == 4 else self.circle(x, y, r, c)
        elif op == 6:
            self.line(*struct.unpack_from("<hhhhH", p, 1))
        elif op == 7:
            x, y, flags, fg = struct.unpack_from("<hhBH", p, 1)
            transparent = bool(flags & 0x80)
            at = 8
            bg = None
            if not transparent:
                bg = struct.unpack_from("<H", p, 8)[0]
                at = 10
            font, scale = flags & 7, ((flags >> 3) & 7) + 1
            if font < len(self.lib.fonts):
                self.text(x, y, font, scale, fg, bg, p[at + 1:at + 1 + p[at]])
        elif op == 8:
            self.fill_triangle(*struct.unpack_from("<hhhhhhH", p, 1))
        elif op == 9:
            aid, frame, x, y, flags, bg = struct.unpack_from("<BHhhBH", p, 1)
            tint = struct.unpack_from("<H", p, 11)[0] if flags & engine.F_TINT else 0
            self.blit(aid, frame, x, y, None, (flags & 3) + 1, flags, bg, tint)
        elif op == 10:
            aid, frame, x, y, sx, sy, w, h, flags, bg = struct.unpack_from("<BHhhHHHHBH", p, 1)
            self.blit(aid, frame, x, y, (sx, sy, w, h), 1, flags & (engine.F_TRANSPARENT | engine.F_DIM), bg, 0)
        elif op == 12:
            self.card(p)
        elif op == 11:
            self.dotted(*struct.unpack_from("<hhhhH", p, 1))

    def chunk_ms(self):
        """Cost of everything drawn since reset_cost() for one RPC call."""
        return costmodel.frame_ms(1, self.ops, self.fast, self.slow, self.runs)


# ------------------------------------------------------------------ bridge, clock, input

class Clock:
    """Stands in for `time` inside engine.py: virtual and deterministic."""

    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += max(0.0, seconds)


class RealClock:
    """Wall clock with the same interface, for the interactive window."""

    monotonic = staticmethod(real_time.monotonic)
    sleep = staticmethod(real_time.sleep)

    @property
    def now(self):
        return real_time.monotonic()


class Inputs:
    """Timeline of (start, end, button mask, stick x, stick y) built from --keys, or live keys."""

    BUTTONS = {"A": 1, "B": 2, "C": 4, "S": 8}
    STICK = {"L": (-127, 0), "R": (127, 0), "U": (0, 127), "D": (0, -127)}  # raw y is up-positive

    def __init__(self):
        self.timeline = []
        self.events = []          # (time, "shot", name) / (time, "epoch", None)
        self.end = 0.0
        self.live = None          # interactive: callable returning (mask, x, y)

    def parse(self, text):
        t = 0.0
        for token in [s.strip() for s in text.split(",") if s.strip()]:
            name, _, dur = token.partition(":")
            upper = name.upper()
            if upper.endswith("S") and name[:-1].replace(".", "", 1).isdigit() and not dur:
                t += float(name[:-1])
            elif upper == "SHOT":
                self.events.append((t, "shot", dur or None))
            elif upper == "EPOCH":
                self.events.append((t, "epoch", None))
            else:
                mask = x = y = 0
                for part in upper.split("+"):
                    if part in self.BUTTONS:
                        mask |= self.BUTTONS[part]
                    elif part in self.STICK:
                        x, y = x + self.STICK[part][0], y + self.STICK[part][1]
                    else:
                        raise SystemExit(f"--keys: unknown token {token!r}")
                hold = float(dur[:-1] if dur.endswith("s") else dur) if dur else TAP_S
                self.timeline.append((t, t + hold, mask, x, y))
                t += hold + (0 if dur else TAP_S)
        self.end = t

    def at(self, now):
        if self.live:
            return self.live()
        for start, end, mask, x, y in self.timeline:
            if start <= now < end:
                return mask, x, y
        return 0, 0, 0


class FakeBridge:
    """The Bridge methods the engine calls, backed by a Device and the input timeline."""

    def __init__(self, device, clock, inputs, throttle):
        self.device, self.clock, self.inputs, self.throttle = device, clock, inputs, throttle
        self.t0 = clock.now
        self.epoch = 0
        self.last_draw = clock.now
        self.frame_ms = 0.0
        self.chunks = 0
        self.bytes = 0
        self.fast = self.slow = self.ops = 0

    def now(self):
        return self.clock.now - self.t0

    def raw(self):
        mask, x, y = self.inputs.at(self.now())
        return json.dumps({"video": 0, "epoch": self.epoch, "connected": 7, "buttons": mask, "x": x,
                           "y": y, "ax": engine.MOVEMENT_ZERO_MG[0], "ay": engine.MOVEMENT_ZERO_MG[1],
                           "az": engine.MOVEMENT_ZERO_MG[2]})

    def bump_epoch(self):
        """The sketch repainted its own screen: the game must redraw everything."""
        self.epoch += 1
        self.device.img.paste((0, 0, 0), (0, 0, W, H))

    def call(self, name, payload=None):
        if name == "arcade_read_inputs":
            return self.raw()
        if name != "arcade_draw_ops":
            raise ValueError(f"unknown bridge method {name}")
        if self.clock.now - self.last_draw > WAITING_AFTER_S:
            self.bump_epoch()
        dev = self.device
        dev.reset_cost()
        dev.apply(bytes(payload))
        ms = dev.chunk_ms()
        self.frame_ms += ms
        self.chunks += 1
        self.bytes += len(payload)
        self.fast += dev.fast
        self.slow += dev.slow
        self.ops += dev.ops
        if self.throttle:
            real_time.sleep(ms / 1000)
        if isinstance(self.clock, Clock):
            self.clock.sleep(ms / 1000)
        self.last_draw = self.clock.now
        return self.raw()

    def take_frame(self):
        row = (self.frame_ms, self.chunks, self.bytes, self.ops, self.fast, self.slow)
        self.frame_ms, self.chunks, self.bytes = 0.0, 0, 0
        self.fast = self.slow = self.ops = 0
        return row


# ------------------------------------------------------------------ driver

def make_game(spec):
    module, _, attr = spec.partition(":")
    return getattr(importlib.import_module(module), attr or "Game")()


class Recorder:
    def __init__(self):
        self.rows = []
        self.warned = 0

    def add(self, t, row, busy):
        ms, chunks, size, ops, fast, slow = row
        limit = costmodel.BUSY_LIMIT_MS if busy else costmodel.IDLE_LIMIT_MS
        over = ms > limit
        self.rows.append((round(t, 3), round(ms, 1), chunks, size, ops, int(fast), int(slow), int(busy), int(over)))
        if over:
            self.warned += 1
            if self.warned <= 25:
                print(f"warning: t={t:6.2f}s frame cost {ms:5.1f} ms > {limit:.0f} ms "
                      f"({chunks} RPC, {size} B, {ops} ops, {int(fast)} fast px, {int(slow)} slow px"
                      f"{', busy' if busy else ''})")

    def save(self, path):
        with open(path, "w", newline="") as handle:
            out = csv.writer(handle)
            out.writerow(["t", "ms", "chunks", "bytes", "ops", "fast_px", "slow_px", "busy", "over_limit"])
            out.writerows(self.rows)

    def summary(self):
        if not self.rows:
            return "no frames"
        idle = [r[1] for r in self.rows if not r[7]]
        busy = [r[1] for r in self.rows if r[7]]
        def stat(v):
            return f"avg {sum(v) / len(v):.1f} / max {max(v):.1f} ms ({len(v)})" if v else "none"
        return (f"{len(self.rows)} frames; idle: {stat(idle)}; busy: {stat(busy)}; "
                f"{self.warned} over limit")


def run_headless(args):
    lib = Library()
    device = Device(lib)
    clock = Clock()
    engine.time = clock
    random.seed(args.seed)
    inputs = Inputs()
    inputs.parse(args.keys)
    duration = inputs.end if inputs.timeline or inputs.events else args.time
    duration = max(duration, args.time) if not args.keys else duration
    bridge = FakeBridge(device, clock, inputs, throttle=False)
    runner = engine.Runner(make_game(args.game), bridge, fps=args.fps)
    out = Path(args.shots) if args.shots else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    pending = sorted(inputs.events, key=lambda e: e[0])
    next_every = 0.0
    rec = Recorder()
    shots = 0

    def shot(name):
        nonlocal shots
        if out:
            img = device.img if args.scale == 1 else device.img.resize((W * args.scale, H * args.scale), Image.NEAREST)
            img.save(out / (name + ".png"))
            shots += 1

    while bridge.now() < duration:
        while pending and pending[0][0] <= bridge.now():
            _, kind, name = pending.pop(0)
            if kind == "epoch":
                bridge.bump_epoch()
            else:
                shot(name or f"shot_{bridge.now():07.2f}s")
        runner.step()
        if runner.error is not None:
            raise SystemExit("game raised (traceback above)")
        rec.add(bridge.now(), bridge.take_frame(), runner.busy)
        if args.every and bridge.now() >= next_every:
            shot(f"t_{bridge.now():07.2f}s")
            next_every += args.every
    shot("final")
    if out:
        rec.save(out / "cost.csv")
    print(rec.summary())
    print(f"{shots} screenshot(s) in {out}" if out else "no --shots given: nothing saved")


def run_window(args):
    import tkinter as tk
    from PIL import ImageTk

    lib = Library()
    device = Device(lib)
    clock = RealClock()
    engine.time = clock
    random.seed(args.seed)
    held = set()
    inputs = Inputs()

    def live():
        mask = (1 if "z" in held else 0) | (2 if "x" in held else 0) | (4 if "c" in held else 0) \
            | (8 if "Return" in held else 0)
        x = (127 if "Right" in held else 0) - (127 if "Left" in held else 0)
        y = (127 if "Up" in held else 0) - (127 if "Down" in held else 0)
        return mask, x, y

    inputs.live = live
    bridge = FakeBridge(device, clock, inputs, throttle=not args.no_throttle)
    runner = engine.Runner(make_game(args.game), bridge, fps=args.fps)
    root = tk.Tk()
    root.title("UNO Q arcade simulator")
    scale = args.scale if args.scale > 1 else 2
    label = tk.Label(root, bd=0)
    label.pack()
    root.bind("<KeyPress>", lambda e: held.add(e.keysym.lower() if len(e.keysym) == 1 else e.keysym))
    root.bind("<KeyRelease>", lambda e: held.discard(e.keysym.lower() if len(e.keysym) == 1 else e.keysym))
    root.bind("e", lambda e: bridge.bump_epoch())
    root.bind("p", lambda e: device.img.save(ROOT / "build" / "sim_shot.png"))
    rec = Recorder()
    closed = []
    root.protocol("WM_DELETE_WINDOW", lambda: closed.append(1))
    photo = None
    frames = 0
    started = real_time.monotonic()
    while not closed:
        runner.step()
        if runner.error is not None:
            raise SystemExit("game raised (traceback above)")
        ms = bridge.take_frame()
        rec.add(real_time.monotonic() - started, ms, runner.busy)
        photo = ImageTk.PhotoImage(device.img.resize((W * scale, H * scale), Image.NEAREST))
        label.configure(image=photo)
        frames += 1
        if frames % 10 == 0:
            root.title(f"UNO Q arcade simulator - device {ms[0]:.0f} ms/frame (e: redraw, p: save shot)")
        root.update()
    print(rec.summary())


def main():
    parser = argparse.ArgumentParser(description="PC simulator for the UNO Q arcade console")
    parser.add_argument("--game", default="nla.flow:make", help="module:attr, a callable returning the game object")
    parser.add_argument("--keys", default="", help='scripted input, e.g. "1.0s,A,R,R,A,2.0s"')
    parser.add_argument("--shots", help="directory for PNGs and cost.csv (headless)")
    parser.add_argument("--every", type=float, default=0.0, help="screenshot every N virtual seconds")
    parser.add_argument("--time", type=float, default=3.0, help="headless duration without --keys")
    parser.add_argument("--fps", type=int, default=engine.FPS)
    parser.add_argument("--scale", type=int, default=1, help="screenshot / window scale")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--window", action="store_true", help="interactive tkinter window")
    parser.add_argument("--no-throttle", action="store_true", help="window: do not sleep for device time")
    args = parser.parse_args()
    if not SIM_BIN.exists():
        raise SystemExit("run tools/pack_assets.py first")
    (run_window if args.window else run_headless)(args)


if __name__ == "__main__":
    main()
