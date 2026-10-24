"""Game loop glue: calibrated controls in, batched TFT drawing out.

Each frame is one `arcade_draw_ops` Bridge call: it carries this frame's drawing
commands to the sketch and returns the next input snapshot.
"""

import json
import struct
import time
import traceback

import costmodel
from fontdata import ADVANCES, BODY, EXTRA_CHARS, FIRST_CHAR, METRICS, NUM, TINY, TITLE, WIDTHS
from preview import (DEAD_ZONE, INVERT_X, INVERT_Y, MOVEMENT_DEAD_ZONE_MG,
                     MOVEMENT_ZERO_MG, validate_inputs)

WIDTH, HEIGHT = 480, 320          # Landscape TFT, origin top-left.
FPS = 20                          # Target; the log prints the measured rate.
BUTTONS, JOYSTICK, MOVEMENT = 1, 2, 4   # `connected` bits
A, B, C, STICK = 1, 2, 4, 8             # button bits
MAX_CHUNK = 200                   # Keeps each request under the 256-byte RPC limit.


def rgb(r, g, b):
    """8-bit RGB to the TFT's RGB565."""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


BLACK, WHITE = rgb(0, 0, 0), rgb(255, 255, 255)
RED, GREEN, BLUE = rgb(255, 0, 0), rgb(0, 255, 0), rgb(0, 0, 255)
YELLOW, CYAN, MAGENTA = rgb(255, 255, 0), rgb(0, 255, 255), rgb(255, 0, 255)
GRAY, ORANGE = rgb(128, 128, 128), rgb(255, 140, 0)


def dim565(color):
    """The darkening `dim=True` applies to every opaque asset pixel."""
    return (color >> 1) & 0x7BEF


class Asset:
    """One packed animation; instances are generated into python/assets.py."""

    def __init__(self, id, w, h, frames, fps):
        self.id, self.w, self.h, self.frames, self.fps = id, w, h, frames, fps

    def frame_at(self, seconds):
        return int(seconds * self.fps) % self.frames


class Controls:
    """Calibrated control state. Stick axes are -1..1 in screen directions (+x right, +y down)."""

    def __init__(self):
        self.connected = 0
        self.held = 0
        self.pressed = 0    # Went down this frame: use for one-shot actions.
        self.released = 0
        self.x = 0.0
        self.y = 0.0
        self.tilt = (0, 0, 0)  # Acceleration change from the calibrated baseline, mg.

    def down(self, button):
        return bool(self.held & button)

    def tapped(self, button):
        return bool(self.pressed & button)

    def update(self, raw):
        validate_inputs(raw)
        connected = raw["connected"]
        mask = (7 if connected & BUTTONS else 0) | (8 if connected & JOYSTICK else 0)
        held = raw["buttons"] & mask
        self.pressed = held & ~self.held
        self.released = self.held & ~held
        self.held = held
        self.connected = connected
        stick = connected & JOYSTICK
        self.x = _axis(raw["x"], INVERT_X) if stick else 0.0
        self.y = _axis(raw["y"], INVERT_Y) if stick else 0.0
        tilt = []
        for key, zero in zip(("ax", "ay", "az"), MOVEMENT_ZERO_MG):
            delta = raw[key] - zero if connected & MOVEMENT else 0
            tilt.append(0 if abs(delta) < MOVEMENT_DEAD_ZONE_MG else delta)
        self.tilt = tuple(tilt)


def _axis(value, invert):
    if abs(value) < DEAD_ZONE:
        return 0.0
    magnitude = min(1.0, (abs(value) - DEAD_ZONE) / (128 - DEAD_ZONE))
    value = magnitude if value > 0 else -magnitude
    return -value if invert else value


def _i16(value):
    return max(-32768, min(32767, int(round(value))))


# Opcodes shared with sketch/sketch.ino and tools/sim.py.
OP_CLEAR, OP_FILL_RECT, OP_RECT, OP_FILL_CIRCLE, OP_CIRCLE, OP_LINE = 1, 2, 3, 4, 5, 6
OP_TEXT, OP_FILL_TRIANGLE, OP_ASSET, OP_REGION, OP_DOTTED, OP_CARD = 7, 8, 9, 10, 11, 12
CARD_INK = 0x1044    # night0: the 1-px ring inside a card's rim
# Asset flag byte: bits 0-1 scale-1, then flip X, flip Y, transparent, tint, dim.
F_FLIP_X, F_FLIP_Y, F_TRANSPARENT, F_TINT, F_DIM = 4, 8, 16, 32, 64
# Text flag byte: bits 0-2 font, bits 3-5 scale-1, bit 7 transparent.
T_TRANSPARENT = 128


def _glyph(c):
    """Glyph index of a character: ASCII 32..126, then EXTRA_CHARS; anything else is '?'."""
    if " " <= c <= "~":
        return ord(c) - FIRST_CHAR
    if c in EXTRA_CHARS:
        return 95 + EXTRA_CHARS.index(c)
    return ord("?") - FIRST_CHAR


def _clean(message):
    return "".join(chr(_glyph(c) + FIRST_CHAR) for c in str(message))   # extras become bytes 127..


def font_metrics(font):
    """(height, ascent) of a font's text cell: the baseline is `ascent` px below the cell top."""
    return METRICS[font]


def measure(message, font=BODY, scale=1):
    """(width, height) of the pixels `text` covers. The opaque cell is exactly this big."""
    text = [_glyph(c) for c in str(message)]
    height = METRICS[font][0] * scale
    if not text:
        return 0, height
    advance, width = ADVANCES[font], WIDTHS[font]
    last = text[-1]
    run = sum(advance[g] for g in text[:-1]) + max(advance[last], width[last])
    return run * scale, height


class Screen:
    """Queues drawing commands; the runner sends them once per frame.

    Nothing is cleared automatically: erase what moves (see `sprite`) and redraw
    everything only when `draw(screen, full=True)` is called.
    """

    def __init__(self):
        self._chunks = []
        self._ops = bytearray()
        self._sprites = {}
        self._reset_stats()

    measure = staticmethod(measure)
    font_metrics = staticmethod(font_metrics)

    def _reset_stats(self):
        self._n_ops = self._n_bytes = self._fast = self._slow = self._runs = 0

    def _add(self, op, fast=0, slow=0, runs=0):
        if len(self._ops) + len(op) > MAX_CHUNK:
            self._chunks.append(bytes(self._ops))
            self._ops = bytearray()
        self._ops += op
        self._n_ops += 1
        self._n_bytes += len(op)
        self._fast += fast
        self._slow += slow
        self._runs += runs

    def _fill(self, color, pixels):
        if costmodel.is_fast(color):
            return {"fast": pixels}
        return {"slow": pixels}

    def stats(self):
        """Queued since the last take(): dict(ops, bytes, chunks, ms). ms is the device-time estimate
        from costmodel.py (RPC chunks + per-op setup + pixels); one RPC is always needed per frame."""
        chunks = len(self._chunks) + 1
        return {"ops": self._n_ops, "bytes": self._n_bytes, "chunks": chunks,
                "ms": costmodel.frame_ms(chunks, self._n_ops, self._fast, self._slow, self._runs)}

    def clear(self, color=BLACK):
        """Full-screen fill; slow on this TFT, so use it for scene changes, not every frame."""
        self._add(struct.pack("<BH", OP_CLEAR, color), **self._fill(color, WIDTH * HEIGHT))
        self._sprites.clear()

    def fill_rect(self, x, y, w, h, color):
        self._add(struct.pack("<BhhhhH", OP_FILL_RECT, _i16(x), _i16(y), _i16(w), _i16(h), color),
                  **self._fill(color, max(0, w) * max(0, h)))

    def rect(self, x, y, w, h, color):
        self._add(struct.pack("<BhhhhH", OP_RECT, _i16(x), _i16(y), _i16(w), _i16(h), color),
                  **self._fill(color, 2 * (max(0, w) + max(0, h))))

    def dotted_rect(self, x, y, w, h, color):
        """1-px outline of dashes (2 px on, 2 px off) starting at each corner; one op."""
        self._add(struct.pack("<BhhhhH", OP_DOTTED, _i16(x), _i16(y), _i16(w), _i16(h), color),
                  slow=w + h, runs=(w + h) // 2)

    def fill_circle(self, x, y, r, color):
        self._add(struct.pack("<BhhhH", OP_FILL_CIRCLE, _i16(x), _i16(y), _i16(r), color),
                  **self._fill(color, 3 * r * r))

    def circle(self, x, y, r, color):
        self._add(struct.pack("<BhhhH", OP_CIRCLE, _i16(x), _i16(y), _i16(r), color), slow=6 * r)

    def line(self, x0, y0, x1, y1, color):
        self._add(struct.pack("<BhhhhH", OP_LINE, _i16(x0), _i16(y0), _i16(x1), _i16(y1), color),
                  slow=max(abs(x1 - x0), abs(y1 - y0)))

    def fill_triangle(self, x0, y0, x1, y1, x2, y2, color):
        self._add(struct.pack("<BhhhhhhH", OP_FILL_TRIANGLE, *map(_i16, (x0, y0, x1, y1, x2, y2)), color),
                  slow=abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) // 2)

    def text(self, x, y, message, color=WHITE, bg=None, font=BODY, scale=1):
        """Baked bitmap text; (x, y) is the top-left of the cell, baseline at y + ascent * scale.
        bg given: opaque cell of exactly measure(message, font, scale) pixels, one window (fast).
        bg=None: only the glyph pixels are drawn (slow; small text only). ASCII 32..126 is baked
        ('?' replaces anything else) plus the extra glyphs · → ★ ▼ (U+00B7, U+2192, U+2605, U+25BC, same bitmaps in every font); NUM covers digits and + - x % ! /; TITLE is mixed case only."""
        data = _clean(message).encode("latin-1")[:MAX_CHUNK - 11]
        scale = max(1, min(8, scale))
        flags = font | (scale - 1) << 3 | (T_TRANSPARENT if bg is None else 0)
        head = struct.pack("<BhhBH", OP_TEXT, _i16(x), _i16(y), flags, color)
        if bg is not None:
            head += struct.pack("<H", bg)
        w, h = measure(str(message)[:len(data)], font, scale)
        self._add(head + bytes((len(data),)) + data, slow=w * h, runs=0 if bg is not None else h)

    def text_center(self, y, message, color=WHITE, bg=None, font=BODY, scale=1, cx=WIDTH // 2):
        """Horizontally centered on `cx` (default: the screen). Returns the x it drew at."""
        x = cx - measure(message, font, scale)[0] // 2
        self.text(x, y, message, color, bg, font, scale)
        return x

    def text_right(self, x_right, y, message, color=WHITE, bg=None, font=BODY, scale=1):
        """Right edge of the text at x_right (exclusive). Returns the x it drew at."""
        x = x_right - measure(message, font, scale)[0]
        self.text(x, y, message, color, bg, font, scale)
        return x

    def sprite(self, name, x, y, w, h, color, bg=BLACK):
        """Moving rectangle: erases only the uncovered part of its last position.
        Returns the previous rect (x, y, w, h) or None."""
        return self._place(name, (_i16(x), _i16(y), _i16(w), _i16(h)), color, bg,
                           lambda rect: self.fill_rect(*rect, color))

    @staticmethod
    def _flags(scale, flip, flip_y, tint, dim, bg):
        scale = max(1, min(4, scale))
        flags = (scale - 1) | (F_FLIP_X if flip else 0) | (F_FLIP_Y if flip_y else 0) \
            | (F_TRANSPARENT if bg is None else 0) | (F_DIM if dim else 0) | (F_TINT if tint is not None else 0)
        return scale, flags

    def blit(self, asset, frame, x, y, scale=1, flip=False, flip_y=False, tint=None, dim=False, bg=None):
        """Untracked asset draw at scale 1-4. One window with transparent pixels painted `bg`;
        bg=None skips transparent pixels (one window per opaque run: slower, best for small sprites).
        tint: every opaque pixel becomes that RGB565 color. dim: opaque pixels darkened (dim565)."""
        scale, flags = self._flags(scale, flip, flip_y, tint, dim, bg)
        frame %= asset.frames
        op = struct.pack("<BBHhhBH", OP_ASSET, asset.id, frame, _i16(x), _i16(y), flags, bg or 0)
        if tint is not None:
            op += struct.pack("<H", tint)
        pixels = asset.w * asset.h * scale * scale
        if bg is None:
            self._add(op, slow=pixels // 2, runs=asset.h * scale * 3)
        else:
            self._add(op, slow=pixels)

    def asset_region(self, asset, frame, x, y, sx, sy, w, h, bg=None, dim=False):
        """Draws the w x h sub-rectangle at (sx, sy) of an asset frame at (x, y), scale 1 (restores a
        background bitmap under something that moved). bg and dim as in `blit`."""
        frame %= asset.frames
        flags = (F_TRANSPARENT if bg is None else 0) | (F_DIM if dim else 0)
        self._add(struct.pack("<BBHhhHHHHBH", OP_REGION, asset.id, frame, _i16(x), _i16(y),
                              sx, sy, w, h, flags, bg or 0), slow=w * h, runs=h if bg is None else 0)

    def card(self, face, frame, x, y, rim, bg, field=0, stars=0, star_asset=None, gem=0,
             gem_asset=None, dim=False, tint=None, scale=1):
        """A whole card in one op, (face.w + 4) x (face.h + 4) px times `scale` at (x, y): 1-px ring
        in `rim`, 1-px ring in CARD_INK, the face frame inset 2 px (transparent pixels become CARD_INK),
        `stars` (0-3) copies of star_asset frame 0 at (card_w - 8 - 6 i, 5) and, if gem > 0, frame
        gem - 1 of gem_asset at (card_w - 12, card_h - 12 if face.w == 44 else card_h - 10), both
        over `field`; the four outermost corner pixels are `bg`. dim darkens everything but those
        corners; tint paints the face's opaque pixels one color (rim, ring, stars and gem keep theirs)."""
        scale = max(1, min(2, scale))
        frame %= face.frames
        flags = (scale - 1) | (F_DIM if dim else 0) | (F_TINT if tint is not None else 0)
        stars = max(0, min(3, stars))
        op = struct.pack("<BBHhhHHHBBBB", OP_CARD, face.id, frame, _i16(x), _i16(y), rim, bg, field, flags,
                         stars | max(0, min(63, gem)) << 2,
                         star_asset.id if star_asset and stars else 255,
                         gem_asset.id if gem_asset and gem else 255)
        if tint is not None:
            op += struct.pack("<H", tint)
        self._add(op, slow=(face.w + 4) * (face.h + 4) * scale * scale)

    def asset(self, name, asset, frame, x, y, scale=1, flip=False, flip_y=False, tint=None,
              dim=False, bg=BLACK):
        """Tracked asset (like `sprite`): redraws only when its frame, flip, tint, dim or position
        changes, and erases the uncovered part of the old position with bg. Returns the previous
        rect or None. bg=None is not allowed here (nothing to erase with); use `blit`."""
        scale = max(1, min(4, scale))
        frame %= asset.frames
        rect = (_i16(x), _i16(y), asset.w * scale, asset.h * scale)
        look = (asset.id, frame, flip, flip_y, tint, dim, bg)
        return self._place(name, rect, look, bg, lambda _: self.blit(
            asset, frame, rect[0], rect[1], scale, flip, flip_y, tint, dim, bg))

    def _place(self, name, rect, look, bg, draw):
        old_rect, old_look = self._sprites.get(name, (None, None))
        if (old_rect, old_look) != (rect, look):
            if old_rect:
                for part in _subtract(old_rect, rect):
                    self.fill_rect(*part, bg)
            draw(rect)
            self._sprites[name] = (rect, look)
        return old_rect

    def hide(self, name, bg=BLACK):
        old_rect, _ = self._sprites.pop(name, (None, None))
        if old_rect:
            self.fill_rect(*old_rect, bg)

    def take(self):
        chunks = self._chunks + [bytes(self._ops)]
        self._chunks, self._ops = [], bytearray()
        self._reset_stats()
        return chunks

    def discard(self):
        self._chunks, self._ops = [], bytearray()
        self._reset_stats()


def _subtract(a, b):
    """Parts of rect a not covered by rect b, as up to four rects."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix0, iy0 = max(ax, bx), max(ay, by)
    ix1, iy1 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if ix0 >= ix1 or iy0 >= iy1:
        return [a]
    parts = []
    if ay < iy0:
        parts.append((ax, ay, aw, iy0 - ay))
    if iy1 < ay + ah:
        parts.append((ax, iy1, aw, ay + ah - iy1))
    if ax < ix0:
        parts.append((ax, iy0, ix0 - ax, iy1 - iy0))
    if ix1 < ax + aw:
        parts.append((ix1, iy0, ax + aw - ix1, iy1 - iy0))
    return parts


class Runner:
    """Drives a game object with:
        required: connected bits the game needs (pauses with a message otherwise)
        update(controls, dt): game rules, dt in seconds
        draw(screen, full): queue drawing; full=True means the screen was just cleared
        busy (optional attribute, read after draw): True while a scene change, transition or long
            animation may take up to 70 ms per frame instead of 45 ms (only the simulator checks)
    """

    def __init__(self, game, bridge, fps=FPS):
        self.game = game
        self.bridge = bridge
        self.frame_time = 1 / fps
        self.controls = Controls()
        self.screen = Screen()
        self.raw = None
        self.epoch = None
        self.busy = False   # game.busy after the last draw: a scene change or long animation
        self.error = None
        self.missing = 0
        self.last = time.monotonic()
        self.stats_at = self.last
        self.frames = 0
        self.rpc_time = 0.0
        self.sent = 0

    def step(self):
        start = time.monotonic()
        try:
            if self.raw is None:
                self.raw = json.loads(self.bridge.call("arcade_read_inputs"))
            raw = self.raw
            if raw.get("video", 0):  # RetroArch owns the TFT; redraw after it releases.
                self.raw = self.epoch = None
                time.sleep(0.5)
                return
            self.controls.update(raw)
            dt = min(start - self.last, 0.1)  # Clamp so a stall can't teleport objects.
            self.last = start
            full = raw.get("epoch") != self.epoch
            self.epoch = raw.get("epoch")
            missing = getattr(self.game, "required", BUTTONS | JOYSTICK) & ~self.controls.connected
            if missing:
                if full or missing != self.missing:
                    self._show_missing(missing)
            else:
                if full or self.missing:
                    self.screen.clear()
                    full = True
                self.game.update(self.controls, dt)
                self.game.draw(self.screen, full)
                self.busy = bool(getattr(self.game, "busy", False))
            self.missing = missing
            self.raw = self._send()
        except Exception as error:
            # Without fresh frames the MCU shows "Waiting" after 1.5 s; the next
            # epoch change then triggers a full redraw.
            print(f"Arcade connection/input error: {error!r}", flush=True)
            traceback.print_exc()
            self.error = error
            self.screen.discard()
            self.raw = self.epoch = None
            time.sleep(1)
            return
        self._report(start)
        time.sleep(max(0.0, self.frame_time - (time.monotonic() - start)))

    def _send(self):
        rpc_start = time.monotonic()
        reply = None
        for chunk in self.screen.take():
            reply = self.bridge.call("arcade_draw_ops", chunk)
            self.sent += len(chunk)
        self.rpc_time += time.monotonic() - rpc_start
        return json.loads(reply)

    def _show_missing(self, missing):
        names = [name for bit, name in ((BUTTONS, "Buttons"), (JOYSTICK, "Joystick"),
                                        (MOVEMENT, "Movement")) if missing & bit]
        self.screen.clear()
        self.screen.text_center(120, "Paused", YELLOW, font=TITLE, scale=2)
        self.screen.text_center(180, "Not connected: " + ", ".join(names))
        self.screen.text_center(210, "Check the Qwiic cable", GRAY)

    def _report(self, now):
        self.frames += 1
        if now - self.stats_at >= 5:
            span = now - self.stats_at
            print(f"{self.frames / span:.1f} fps; RPC {1000 * self.rpc_time / self.frames:.0f} ms/frame; "
                  f"{self.sent / self.frames:.0f} B/frame", flush=True)
            self.stats_at, self.frames, self.rpc_time, self.sent = now, 0, 0.0, 0
