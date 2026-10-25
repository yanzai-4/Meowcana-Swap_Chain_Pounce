"""Moonlit Grimoire widgets. Every widget redraws only what changed and paints opaque (text over flat fills).

API. All drawing goes through an engine Screen `scr`; `bg` is the flat color a widget sits on. Text y is the TOP of
the font cell (BODY is 15 px tall). Import as `from nla.ui import widgets as W` and `from nla.ui import theme as T`.

Static helpers (draw every call; use them inside a full redraw):
    panel(scr, x, y, w, h, fill=PANEL, edge=RULE, orn=True)   boxed area, flourish corners if orn
    corners(scr, x, y, w, h)                                  just the four flourishes
    divider(scr, x0, x1, y, bg=GROUND, mid=True)              1 px gold-brown rule with a diamond
    ground(scr, x, y, w, h)                                   fill with the fast ground color
    rich(scr, x, y, text, color, bg, font=BODY) -> width      one opaque text op; markers {.} {>} {*} {v} become the
    rich_w(scr, text, font=BODY) -> width                     font glyphs middle dot, arrow, star, down triangle
    glyphs(text)                                              the same marker -> glyph mapping (also for plain text)
    text_y(row_y, row_h, font=BODY)                           top y that centers a font cell in a row
    fmt_num(n) fmt_signed(n) fmt_pct(p) fmt_hp(cur, mx) fmt_k(n)   number formatting ("+2", "+25%", "30/36")
    portrait(key) -> Asset|None                               48x48 story portrait ("zero", "domino", ...)

Stateful widgets: create once with a position, call .set*(...) when data changes, call .draw(scr, full) every
frame (full=True after the screen was cleared / the scene is shown). Nothing is sent when nothing changed, and every
widget has .invalidate() (forget what is on screen; the next draw repaints).
    Label(x, y, w, font=BODY, color=TEXT, bg=GROUND, align="l"|"c"|"r")   .set(msg, color=None)
    TextRun(x, y, bg=GROUND)                     .set([("Fire Claw", LABEL, TITLE), 10, ("{.} Wands 4", TEXT)])
                                                 one line of mixed fonts/colors; (text, color[, font]) or int gap
    CardView(x, y, small=False, bg=GROUND)       .set_card(card) .set_enemy_card(scrap_or_card) .set_back()
                                                 .set_face(def_id, reversed, star, charm, rarity) .set_empty()
                                                 .set_scrap(frame, number) .set_chewed(frame) .set_curse()
                                                 attributes: .dim .ghost .lift .glow .flash .rim   (+ .rect)
    Cursor(bg=GROUND)                            .to(x, y, w, h, paw=True) / .hide()   amber brackets + paw below
    Button(x, y, w, h, label, bg=GROUND)         .set(label=None, focused=None, disabled=None)
    FightPlaque(x, y)                            .set(focused=None, disabled=None)   baked 92x64 plaque, 2 frames
    HpBar(x, y, w, h=9, hero=False, tick=None)   .set(cur, mx=None) .flash(frames=2) .update()  tick=0.5 threshold mark
    ChipRow(x, y, w, align="l"|"r", gap=14)      .set([chip("DMG 38", ACCENT), status_chip("singe", 2),
                                                 chip("HEAL 3", HEAL, ("ui_heart", 0))])
    Footer(left=None, hints=None, gap=10)        .set_left([("name","Domino"), ("hp","HP 30/36"), ("treat","Treats 14"),
                                                 ("txt","..."), ("bar", cur, mx, flashing)])
                                                 .set_hints([("A","Fight"), ("B","Menu"), ("C","Info")])  .left_end
    Toast(x, y, w, h=20, bg=GROUND)              .show(msg, seconds=1.5, color=ACCENT) .update(dt) .active
    ChainPopup(rect=BATTLE_POPUP, restore=None)  .show(tier, line, title, chain=None) .hide()

Overlays are modal layers opened with `app.open(...)` (or app.say / app.confirm / app.card_info), never drawn by
scenes. They report `busy` while they paint a lot and are painted progressively (a few thousand px per frame):
    Dialogue(lines, on_done=None)                typewriter box + portrait; lines are story.Line or str; A next, B skip
    Confirm(question, on_yes, on_no=None, yes="Yes", no="No")   cursor starts on No; B = No
    InfoOverlay(title, subtitle, body, card=None, notes=(), side=())   full-screen page; B or C closes
    card_info(card) -> InfoOverlay               Card Info for a rules Card

Frame budget (see demo-plan.md section 2): an op costs 1.5 ms, a non-fast pixel 1/180 ms, and every frame at least
17 ms. Widgets therefore skip an optional redraw when it would push the frame past 45 ms (`over_budget`) and stay
dirty, so a big change takes two or three frames instead of one slow one. Draw the widget the player is
interacting with (the cursor) FIRST in your draw(): the first widget of a frame is always accepted.
    over_budget(scr, px=0, ops=1) -> bool        use it for your own optional redraws
"""

import textwrap

from nla import sfx

from . import theme as T

_CLICK = {"up": "a", "right": "b", "middle": "c"}



def _a(name):
    return T.asset(name)


# --------------------------------------------------------------------------- numbers
def fmt_num(n):
    return str(int(n))


def fmt_signed(n):
    return ("+%d" % n) if n >= 0 else ("-%d" % -n)


def fmt_pct(p):
    return ("+%d%%" % p) if p >= 0 else ("-%d%%" % -p)


def fmt_hp(cur, mx):
    return "%d/%d" % (cur, mx)


def fmt_k(n):
    return str(n) if n < 1000 else ("%.1fk" % (n / 1000)).replace(".0k", "k")


# --------------------------------------------------------------------------- small geometry
def _minus(a, b):
    """Rects (x, y, w, h) of `a` not covered by `b`."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix0, iy0, ix1, iy1 = max(ax, bx), max(ay, by), min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if ix0 >= ix1 or iy0 >= iy1:
        return [a]
    out = []
    if ay < iy0:
        out.append((ax, ay, aw, iy0 - ay))
    if iy1 < ay + ah:
        out.append((ax, iy1, aw, ay + ah - iy1))
    if ax < ix0:
        out.append((ax, iy0, ix0 - ax, iy1 - iy0))
    if ix1 < ax + aw:
        out.append((ix1, iy0, ax + aw - ix1, iy1 - iy0))
    return out


def text_y(row_y, row_h, font=T.BODY):
    return row_y + (row_h - T.text_h(font)) // 2


def ground(scr, x, y, w, h):
    scr.fill_rect(x, y, w, h, T.GROUND)


def over_budget(scr, px=0, ops=1):
    """True when painting `px` slow pixels with `ops` draw ops would push this frame past the 45 ms idle limit while
    other work is already queued. Widgets then skip the redraw and stay dirty, so a big change spreads over several
    frames. A frame that holds no op yet always accepts (something has to go first)."""
    st = scr.stats()
    return st["ops"] > 0 and st["ms"] + px / 180.0 + 1.5 * ops > 45.0


def _run_jobs(scr, jobs, full):
    """Run queued paint steps (est_px, fn) in order; stop when the next one does not fit this frame. A frame that
    holds nothing yet always runs its first step. A step may push a follow-up step at the front of `jobs`.
    Returns True when the queue is empty."""
    while jobs:
        px, fn = jobs[0]
        if not full and over_budget(scr, px, 3):
            return False
        jobs.pop(0)
        fn(scr)
    return True


def panel(scr, x, y, w, h, fill=T.PANEL, edge=T.RULE, orn=True):
    """Boxed area; (x, y, w, h) is the inside+rule box. Corner flourishes overhang by 1 px."""
    if fill is not None:
        scr.fill_rect(x, y, w, h, fill)
    scr.rect(x, y, w, h, edge)
    if orn:
        corners(scr, x - 1, y - 1, w + 2, h + 2)


def corners(scr, x, y, w, h):
    c = _a("ui_corner")
    scr.blit(c, 0, x, y)
    scr.blit(c, 0, x + w - c.w, y, flip=True)
    scr.blit(c, 0, x, y + h - c.h, flip_y=True)
    scr.blit(c, 0, x + w - c.w, y + h - c.h, flip=True, flip_y=True)


def divider(scr, x0, x1, y, bg=T.GROUND, mid=True):
    scr.fill_rect(x0, y, x1 - x0 + 1, 1, T.RULE_DIM)
    if mid:
        cx = (x0 + x1) // 2
        scr.fill_rect(cx - 14, y, 29, 1, bg)
        scr.fill_rect(cx - 14, y, 10, 1, T.RULE)
        scr.fill_rect(cx + 5, y, 10, 1, T.RULE)
        scr.blit(_a("ui_diamond"), 0, cx - 2, y - 2, bg=bg)


# --------------------------------------------------------------------------- rich text
_GLYPHS = (("{.}", "\u00b7"), ("{>}", "\u2192"), ("{*}", "\u2605"), ("{v}", "\u25bc"))


def glyphs(s):
    """Map the markers {.} {>} {*} {v} to the font's separator glyphs (middle dot, arrow, star, down triangle)."""
    for token, ch in _GLYPHS:
        if token in s:
            s = s.replace(token, ch)
    return s


def rich_w(scr, s, font=T.BODY):
    """Width of text that may contain {.} {>} {*} {v} markers."""
    return scr.measure(glyphs(s), font)[0]


def rich(scr, x, y, s, color, bg, font=T.BODY):
    """One opaque text op with the markers {.} {>} {*} {v} turned into glyphs; y = top of the cell. Returns width.
    Every star (U+2605 or {*}) gets the gold ui_star icon painted over its glyph."""
    s = glyphs(s)
    scr.text(x, y, s, color, bg, font)
    star_icons(scr, x, y, s, font)
    return scr.measure(s, font)[0]


def star_icons(scr, x, y, s, font=T.BODY):
    """Paint the gold ui_star icon over every star glyph (U+2605) of text `s` that was drawn at (x, y)."""
    if "\u2605" not in s:
        return
    star = _a("ui_star")
    ty = y + T.text_ascent(font) - 8
    for k, ch in enumerate(s):
        if ch == "\u2605":
            scr.blit(star, 0, x + scr.measure(s[:k], font)[0] + 1, ty)


# --------------------------------------------------------------------------- Label
class Label:
    """Opaque text field. Redraws only when the text or color changes; clears just the leftover tail."""

    def __init__(self, x, y, w, font=T.BODY, color=T.TEXT, bg=T.GROUND, align="l"):
        self.x, self.y, self.w, self.font, self.color, self.bg = x, y, w, font, color, bg
        self.align = align
        self.msg = ""
        self._drawn = None       # (msg, color, width)

    def invalidate(self):
        self._drawn = None

    def set(self, msg, color=None):
        self.msg = msg
        if color is not None:
            self.color = color

    def draw(self, scr, full=False):
        look = (self.msg, self.color)
        if not full and self._drawn is not None and self._drawn[:2] == look:
            return
        th = T.text_h(self.font)
        text = glyphs(self.msg)
        w = scr.measure(text, self.font)[0]
        if not full and over_budget(scr, (w if self.align == "l" else self.w) * th, 2):
            return
        if self.align == "l":
            x = self.x
        elif self.align == "r":
            x = self.x + self.w - w
        else:
            x = self.x + (self.w - w) // 2
        prev = self._drawn[2] if (self._drawn is not None and not full) else None
        if prev is not None:
            if self.align == "l":
                if w < prev:
                    scr.fill_rect(x + w, self.y, prev - w, th, self.bg)
            else:
                scr.fill_rect(self.x, self.y, self.w, th, self.bg)
        if self.msg:
            scr.text(x, self.y, text, self.color, self.bg, self.font)
            star_icons(scr, x, self.y, text, self.font)
        self._drawn = (self.msg, self.color, w)


# --------------------------------------------------------------------------- TextRun
def _chunks(scr, text, font, band, limit=3200):
    """Split a long plain text at spaces into (x offset, piece) so no single op exceeds `limit` px."""
    if text is None or scr.measure(text, font)[0] * band <= limit:
        return [(0, text)]
    out, start, last = [], 0, 0
    for k, ch in enumerate(text):
        if ch == " ":
            if scr.measure(text[start:k], font)[0] * band > limit and last > start:
                out.append((scr.measure(text[:start], font)[0] if start else 0, text[start:last + 1]))
                start = last + 1
            last = k
    out.append((scr.measure(text[:start], font)[0] if start else 0, text[start:]))
    return out


class TextRun:
    """One text line built from segments, painted opaque, top-aligned at y (use for 'Title . subtitle' rows).

    set([("Fire Claw", T.LABEL, T.TITLE), 10, ("{.} Wands 4 {*}1", T.TEXT)])
    A segment is (text, color) or (text, color, font); an int is a gap in px. Markers {.} {>} {*} {v} become glyphs.
    Segments are painted one per step and steps that do not fit the frame budget wait for the next frame; a shorter
    new line clears only the leftover tail, a taller neighbor is padded so no old pixels survive."""

    def __init__(self, x, y, bg=T.GROUND):
        self.x, self.y, self.bg = x, y, bg
        self.segments = []
        self._shown = None
        self._jobs = None
        self._planned = None
        self._end = x            # right extent painted so far (including unfinished jobs)
        self._band = 0           # band height of the last finished paint

    def set(self, segments):
        self.segments = list(segments)

    def invalidate(self):
        self._shown = None
        self._jobs = None

    def _plan(self, scr, full):
        parts = []
        for s in self.segments:
            if isinstance(s, int):
                parts.append((s, None, None, None))
            else:
                font = s[2] if len(s) > 2 else T.BODY
                parts.append((rich_w(scr, s[0], font), glyphs(s[0]), s[1], font))
        band = max([T.text_h(p[3]) for p in parts if p[3] is not None] or [0])
        if full:
            self._end, self._band = self.x, band
        jobs = []
        x = self.x
        for w, text, color, font in parts:
            for off, chunk in _chunks(scr, text, font, band):
                cw = w if chunk is text else scr.measure(chunk, font)[0]
                jobs.append((cw * band, self._seg_job(x + off, cw, chunk, color, font, band)))
            x += w
        jobs.append((max(0, self._end - x) * max(band, self._band), self._tail_job(x, band)))
        self._jobs, self._planned = jobs, list(self.segments)

    def _seg_job(self, x, w, text, color, font, band):
        def job(scr):
            if text is None:
                scr.fill_rect(x, self.y, w, band, self.bg)
            else:
                rich(scr, x, self.y, text, color, self.bg, font)
                h = T.text_h(font)
                if h < band:
                    scr.fill_rect(x, self.y + h, w, band - h, self.bg)
            self._end = max(self._end, x + w)
        return job

    def _tail_job(self, end, band):
        def job(scr):
            h = max(band, self._band)
            if self._end > end:
                w = min(self._end - end, max(8, 3200 // h))
                scr.fill_rect(self._end - w, self.y, w, h, self.bg)
                self._end -= w
                if self._end > end:
                    self._jobs.insert(0, ((self._end - end) * h, job))
                    return
            if self._band > band and end > self.x:
                scr.fill_rect(self.x, self.y + band, end - self.x, self._band - band, self.bg)
            self._end, self._band = end, band
        return job

    def draw(self, scr, full=False):
        if self._jobs is None:
            if not full and self._shown == self.segments:
                return
            self._plan(scr, full)
        elif self._planned != self.segments:
            self._plan(scr, full)
        if _run_jobs(scr, self._jobs, full):
            self._jobs = None
            self._shown = list(self._planned)


# --------------------------------------------------------------------------- CardView
_MAJOR_FIRST = 40


class CardView:
    """One card slot (48x64, or 40x54 when small). Draws rim + baked face + stars + charm gem; empty slots are dotted.

    Attributes you may flip any time (the widget redraws on the next draw):
        dim     darkened face and rim (disabled / not selectable)
        ghost   the dotted "where it came from" outline of a picked-up card
        lift    px the card is raised (the exposed strip is repainted with bg)
        glow    gold outline around the card (the active card)
        flash   moon-white silhouette (hit flash)
        rim     override rim color (None = by charm rarity)
    """

    def __init__(self, x, y, small=False, bg=T.GROUND):
        self.x, self.y, self.small, self.bg = x, y, small, bg
        self.w, self.h = (T.CARD_SW, T.CARD_SH) if small else (T.CARD_W, T.CARD_H)
        self.dim = self.ghost = self.glow = self.flash = False
        self.lift = 0
        self.rim = None
        self._kind = ("empty",)
        self._drawn = None            # (look, outer rect)

    # -- content
    def set_empty(self):
        self._kind = ("empty",)

    def set_back(self):
        self._kind = ("back",)

    def set_curse(self):
        """The Droppings curse card (red rim)."""
        self._kind = ("curse",)

    def set_scrap(self, frame, number=None):
        """Rat scrap: frame = index in the scrap set (see docs/assets.md); number = text drawn on it."""
        self._kind = ("scrap", frame, None if number is None else str(number))

    def set_chewed(self, frame):
        self._kind = ("chewed", frame)

    def set_face(self, def_id, reversed=False, star=0, charm=0, rarity=None):
        if def_id == _DROPPINGS:
            self._kind = ("curse",)
            return
        self._kind = ("face", def_id, bool(reversed), star, charm, rarity)

    def set_enemy_card(self, c):
        """An entry of EnemyDef.spread: rules Scrap (scrap art + X) or Card (chewed Major or a plain card)."""
        from nla.rules import cards
        if isinstance(c, cards.Scrap):
            self.set_scrap(cards.SCRAP_KINDS.index(c.kind), c.value if c.value else None)
        elif c.def_id in _CHEWED:
            self.set_chewed(_CHEWED[c.def_id])
        else:
            self.set_card(c)

    def set_card(self, card):
        """rules.cards.Card (or None for an empty slot). Rim color comes from the charm's rarity."""
        if card is None:
            self._kind = ("empty",)
            return
        rarity = None
        if card.charm:
            from nla.rules import cards
            rarity = cards.CHARMS[card.charm].rarity
        self.set_face(card.def_id, card.reversed, card.star, card.charm, rarity)

    @property
    def rect(self):
        return (self.x, self.y - self.lift, self.w, self.h)

    def _look(self):
        return (self._kind, self.dim, self.ghost, self.glow, self.flash, self.rim, self.x, self.y, self.lift)

    def invalidate(self):
        self._drawn = None

    def draw(self, scr, full=False):
        look = self._look()
        if not full and ((self._drawn is not None and self._drawn[0] == look) or over_budget(scr, 3200, 4)):
            return
        x, y = self.x, self.y - self.lift
        outer = (x - 2, y - 2, self.w + 4, self.h + 4) if self.glow else (x, y, self.w, self.h)
        if self._drawn is not None and not full:
            for part in _minus(self._drawn[1], outer):
                scr.fill_rect(*part, self.bg)
        kind = self._kind[0]
        if self.ghost or kind == "empty":
            self._paint_empty(scr, x, y)
        elif kind == "back":
            scr.blit(_a("card_back_s" if self.small else "card_back"), 0, x, y, bg=self.bg, dim=self.dim)
        else:
            self._paint_face(scr, x, y)
        if self.glow:
            scr.rect(x - 2, y - 2, self.w + 4, self.h + 4, T.GOLD4)
        self._drawn = (look, outer)

    def _paint_empty(self, scr, x, y):
        scr.fill_rect(x, y, self.w, self.h, self.bg)
        scr.dotted_rect(x, y, self.w, self.h, T.NIGHT4 if self.ghost else T.NIGHT3)
        scr.blit(_a("ui_sparkle"), 1, x + self.w // 2 - 2, y + self.h // 2 - 2, bg=self.bg)

    def draw_scaled(self, scr, x, y, s=2):
        """One-off enlarged paint (Card Info): faces, rim, stars and gem at integer scale s. Not dirty-tracked."""
        if self._kind[0] in ("empty", "back"):
            return
        self._paint_face(scr, x, y, s)

    def _paint_face(self, scr, x, y, s=1):
        w, h, sm = self.w * s, self.h * s, self.small
        kind = self._kind
        sfx = "_s" if sm else ""
        body = T.NIGHT0
        rim = self.rim
        stars = charm = 0
        elem = None
        reversed_ = False
        if kind[0] == "face":
            _, def_id, reversed_, star, charm, rarity = kind
            asset = _a(("card_s_r" if reversed_ else "card_s_u") if sm else ("card_r" if reversed_ else "card_u"))
            frame = def_id
            if rim is None:
                rim = T.rarity_color(rarity)
            if def_id < _MAJOR_FIRST:
                stars = star + 1
                elem = def_id // 10
        elif kind[0] == "scrap":
            asset, frame = _a("scrap" + sfx), kind[1]
            rim = rim if rim is not None else T.RAT2
        elif kind[0] == "chewed":
            asset, frame = _a("card_chewed_s"), kind[1]
            rim = rim if rim is not None else T.RAT2
        else:
            asset, frame = _a("card_droppings" + sfx), 0
            rim = rim if rim is not None else T.RED
        if elem is None:
            elem = 0 if kind[0] == "face" else None       # Majors use the Fire body color
            if elem is None:
                field = T.NIGHT0
        if elem is not None:
            field = T.elem_body(elem, reversed_)
        scr.card(asset, frame, x, y, rim, self.bg, field, stars, _a("ui_star"), charm, _a("ui_gem"),
                 dim=self.dim, tint=T.MOON if self.flash else None, scale=s)
        if kind[0] == "scrap" and kind[2] is not None and not self.flash:
            asc = T.text_ascent(T.BODY)
            ty = y + 2 * s + ((10 if sm else 11) * s - asc * s)
            scr.text(x + 5 * s, ty, kind[2], T.RAT3, T.RAT1, T.BODY, s)


# --------------------------------------------------------------------------- Cursor
class Cursor:
    """Four amber corner brackets 4 px outside a rect, plus the paw under it. Erases its own ring on move."""

    def __init__(self, bg=T.GROUND):
        self.bg = bg
        self._want = None
        self._drawn = None

    def to(self, x, y, w, h, paw=True):
        self._want = (x, y, w, h, paw)

    def hide(self):
        self._want = None

    def invalidate(self):
        self._drawn = None

    def draw(self, scr, full=False):
        want = self._want
        if full:
            self._drawn = None
            old = None
        else:
            old = self._drawn
            if old == want or over_budget(scr, 600, 7):
                return
        if old is not None:
            x, y, w, h, paw = old
            scr.fill_rect(x - 4, y - 4, w + 8, 2, self.bg)
            scr.fill_rect(x - 4, y + h + 2, w + 8, 2, self.bg)
            scr.fill_rect(x - 4, y - 4, 2, h + 8, self.bg)
            scr.fill_rect(x + w + 2, y - 4, 2, h + 8, self.bg)
            if paw:
                scr.fill_rect(x + w // 2 - 7, y + h + 3, 15, 11, self.bg)
        if want is not None:
            x, y, w, h, paw = want
            b = _a("ui_bracket")
            scr.blit(b, 0, x - 4, y - 4)
            scr.blit(b, 0, x + w - 3, y - 4, flip=True)
            scr.blit(b, 0, x - 4, y + h - 3, flip_y=True)
            scr.blit(b, 0, x + w - 3, y + h - 3, flip=True, flip_y=True)
            if paw:
                scr.blit(_a("ui_paw"), 0, x + w // 2 - 7, y + h + 3, bg=self.bg)
        self._drawn = want


# --------------------------------------------------------------------------- Button / plaque
class Button:
    """Small plate button (Yes / No / Leave / Cancel). Focused = amber text and rim."""

    def __init__(self, x, y, w, h, label="", bg=T.GROUND, font=T.BODY):
        self.x, self.y, self.w, self.h, self.bg, self.font = x, y, w, h, bg, font
        self.label, self.focused, self.disabled = label, False, False
        self._drawn = None

    def set(self, label=None, focused=None, disabled=None):
        if label is not None:
            self.label = label
        if focused is not None:
            self.focused = focused
        if disabled is not None:
            self.disabled = disabled

    def invalidate(self):
        self._drawn = None

    def draw(self, scr, full=False):
        look = (self.label, self.focused, self.disabled)
        if not full and (self._drawn == look or over_budget(scr, self.w * self.h, 4)):
            return
        edge = T.AMBER3 if self.focused else (T.NIGHT3 if self.disabled else T.RULE)
        color = T.ACCENT if self.focused else (T.NIGHT4 if self.disabled else T.TEXT)
        fill = T.NIGHT2 if self.focused else T.PANEL
        scr.fill_rect(self.x, self.y, self.w, self.h, fill)
        scr.rect(self.x, self.y, self.w, self.h, edge)
        if self.focused:
            scr.rect(self.x + 1, self.y + 1, self.w - 2, self.h - 2, T.AMBER1)
        tw, th = scr.measure(self.label, self.font)
        scr.text(self.x + (self.w - tw) // 2, self.y + (self.h - th) // 2, self.label, color, fill, self.font)
        self._drawn = look


class FightPlaque:
    """The baked 92x64 Fight plaque; focused = amber rim, disabled = dimmed.

    A change repaints the plaque as two half-height regions on two consecutive frames (one op of 5888 px would
    alone exceed the 45 ms idle budget); a full redraw paints it at once."""

    def __init__(self, x=T.SPREAD_FIGHT[0], y=T.SPREAD_FIGHT[1]):
        self.x, self.y = x, y
        self.focused = False
        self.disabled = False
        self._drawn = None        # painted look once complete
        self._half = 0            # 1 = top half of the pending look painted
        self._half_look = None

    def set(self, focused=None, disabled=None):
        if focused is not None:
            self.focused = focused
        if disabled is not None:
            self.disabled = disabled

    def invalidate(self):
        self._drawn = None
        self._half = 0

    def draw(self, scr, full=False):
        look = (self.focused, self.disabled)
        if not full and self._drawn == look:
            return
        a = _a("ui_plaque_fight")
        frame = 1 if self.focused else 0
        top = a.h // 2
        if full:
            scr.blit(a, frame, self.x, self.y, bg=T.GROUND, dim=self.disabled)
        elif self._half == 0 or self._half_look != look:
            scr.asset_region(a, frame, self.x, self.y, 0, 0, a.w, top, bg=T.GROUND, dim=self.disabled)
            self._half, self._half_look = 1, look
            return
        else:
            scr.asset_region(a, frame, self.x, self.y + top, 0, top, a.w, a.h - top, bg=T.GROUND,
                             dim=self.disabled)
        self._half = 0
        self._drawn = look


# --------------------------------------------------------------------------- HP bar
class HpBar:
    """Outlined bar with fill + highlight row. set(cur, mx) repaints only the changed segment.

    hero=True uses the green heal ramp; otherwise the enemy fire ramp. `tick` (0..1) marks a threshold
    (Chubbs' Still Hungry at 0.5) with two moon pixels. flash() paints the fill red for a few frames."""

    def __init__(self, x, y, w, h=9, hero=False, tick=None, bg=T.GROUND):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.fill, self.hi = (T.BAR_HP_HERO, T.BAR_HP_HERO_HI) if hero else (T.BAR_HP_ENEMY, T.BAR_HP_ENEMY_HI)
        self.tick, self.bg = tick, bg
        self.cur = self.mx = 1
        self._flash = 0
        self._drawn = None      # (fill width, flashing)

    def set(self, cur, mx=None):
        self.cur = max(0, cur)
        if mx is not None:
            self.mx = max(1, mx)

    def flash(self, frames=2):
        self._flash = frames

    def invalidate(self):
        self._drawn = None

    def _fill_w(self):
        return (self.w - 2) * min(self.cur, self.mx) // self.mx

    def update(self):
        """Call once per frame to run the flash timer."""
        if self._flash:
            self._flash -= 1

    def draw(self, scr, full=False):
        fw = self._fill_w()
        flashing = self._flash > 0
        look = (fw, flashing)
        if not full and self._drawn == look:
            return
        x, y, h = self.x, self.y, self.h
        fill, hi = (T.RED, T.AMBER3) if flashing else (self.fill, self.hi)
        old = self._drawn
        if full or old is None or old[1] != flashing:
            scr.rect(x, y, self.w, h, T.RULE)
            scr.fill_rect(x + 1, y + 1, self.w - 2, h - 2, T.PANEL)
            if fw:
                scr.fill_rect(x + 1, y + 1, fw, h - 2, fill)
                scr.fill_rect(x + 1, y + 1, fw, 1, hi)
        elif fw < old[0]:
            scr.fill_rect(x + 1 + fw, y + 1, old[0] - fw, h - 2, T.PANEL)
        else:
            scr.fill_rect(x + 1 + old[0], y + 1, fw - old[0], h - 2, fill)
            scr.fill_rect(x + 1 + old[0], y + 1, fw - old[0], 1, hi)
        if self.tick is not None:
            tx = x + 1 + int((self.w - 2) * self.tick)
            scr.fill_rect(tx, y + 1, 1, 1, T.MOON)
            scr.fill_rect(tx, y + h - 2, 1, 1, T.MOON)
        self._drawn = look


# --------------------------------------------------------------------------- chips
def chip(label, color=T.TEXT, icon=None):
    """icon = (asset name, frame) or None."""
    return (icon, label, color)


_STATUS_FRAME = {"singe": 0, "puff": 1, "drowsy": 2, "curl": 3, "leap": 4}
_STATUS_COLOR = {"singe": T.SINGE, "puff": T.TEXT, "drowsy": T.WATER2, "curl": T.TEXT, "leap": T.HEAL}


def status_chip(name, count=None):
    """Status icon plus 'Name n' (small 9x9 icon). name in singe/puff/drowsy/curl/leap."""
    label = name.capitalize() if count is None else "%s %d" % (name.capitalize(), count)
    return (("ui_status_s", _STATUS_FRAME[name]), label, _STATUS_COLOR[name])


class ChipRow:
    """A row of icon + label chips (status chips, per-round stats). Chips are painted one per step; steps that do
    not fit the frame budget wait for the next frame. Each chip cell is cleared in place and the leftover head or
    tail of the old row is cleared at the end, so there is no blank flash."""

    def __init__(self, x, y, w, align="l", bg=T.GROUND, gap=14, font=T.BODY):
        self.x, self.y, self.w, self.align, self.bg, self.gap, self.font = x, y, w, align, bg, gap, font
        self.items = []
        self._shown = None
        self._jobs = None
        self._planned = None
        self._lo = self._hi = x      # painted extent on screen (including unfinished jobs)

    def set(self, items):
        self.items = list(items)

    def invalidate(self):
        self._shown = None
        self._jobs = None

    def _plan(self, scr, full):
        th = T.text_h(self.font)
        cells = []
        for icon, label, color in self.items:
            iw = _a(icon[0]).w + 3 if icon else 0
            cells.append((iw + scr.measure(label, self.font)[0], icon, label, color))
        total = sum(c[0] for c in cells) + self.gap * max(0, len(cells) - 1)
        x0 = self.x if self.align == "l" else self.x + self.w - total
        if full:
            self._lo = self._hi = x0
        jobs = []
        x = x0
        for cw, icon, label, color in cells:
            jobs.append((cw * th, self._chip_job(x, cw, icon, label, color, th)))
            x += cw + self.gap
        end = x0 + total
        jobs.append(((max(0, x0 - self._lo) + max(0, self._hi - end)) * th, self._edge_job(x0, end, th)))
        self._jobs, self._planned = jobs, list(self.items)

    def _chip_job(self, x, cw, icon, label, color, th):
        def job(scr):
            scr.fill_rect(x, self.y, cw + self.gap, th, self.bg)
            tx = x
            if icon:
                a = _a(icon[0])
                scr.blit(a, icon[1], x, self.y + (th - a.h) // 2, bg=self.bg)
                tx = x + a.w + 3
            scr.text(tx, self.y, label, color, self.bg, self.font)
            self._lo, self._hi = min(self._lo, x), max(self._hi, x + cw + self.gap)
        return job

    def _edge_job(self, x0, end, th):
        def job(scr):
            if x0 > self._lo:
                scr.fill_rect(self._lo, self.y, x0 - self._lo, th, self.bg)
            if self._hi > end + self.gap:
                scr.fill_rect(end + self.gap, self.y, self._hi - end - self.gap, th, self.bg)
            self._lo, self._hi = x0, max(end, x0)
        return job

    def draw(self, scr, full=False):
        if self._jobs is None:
            if not full and self._shown == self.items:
                return
            self._plan(scr, full)
        elif self._planned != self.items:
            self._plan(scr, full)
        if _run_jobs(scr, self._jobs, full):
            self._jobs = None
            self._shown = list(self._planned)


# --------------------------------------------------------------------------- Footer
_BTN = {"A": 0, "B": 1, "C": 2}


class Footer:
    """Bottom rule + status on the left + A/B/C hints on the right. Left and hints repaint independently.
    The most recently painted footer is `Footer.active`; the App turns clicks on its gems into A/B/C inputs."""

    active = None

    def __init__(self, left=None, hints=None, gap=10, y=T.FOOTER_Y, h=T.FOOTER_H, bg=T.GROUND, divider_line=True):
        self.left = list(left or [])
        self.hints = list(hints or [])
        self.gap, self.y, self.h, self.bg, self.divider_line = gap, y, h, bg, divider_line
        self._left_drawn = None
        self._hints_drawn = None
        self._left_end = T.INNER_L
        self._hints_x = T.INNER_R + 1
        self._gems = []

    def set_left(self, items):
        self.left = list(items)

    def set_hints(self, hints):
        self.hints = list(hints)

    @property
    def left_end(self):
        """x just after the left status (valid after the first draw)."""
        return self._left_end

    def invalidate(self):
        self._left_drawn = self._hints_drawn = None

    def draw(self, scr, full=False):
        if full and self.divider_line:
            divider(scr, T.INNER_L, T.INNER_R, T.FOOTER_DIV_Y, bg=self.bg, mid=False)
        if full or (self._left_drawn != self.left and not over_budget(scr, 240 * 15, 10)):
            self._draw_left(scr)
        if full or (self._hints_drawn != self.hints and not over_budget(scr, 160 * 15, 8)):
            self._draw_hints(scr)

    def _draw_left(self, scr):
        th = T.text_h(T.BODY)
        ty = self.y + (self.h - th) // 2
        old_end = self._left_end
        x = T.INNER_L
        parts = []
        for item in self.left:
            kind = item[0]
            if kind == "name":
                parts.append(("t", item[1], T.LABEL))
            elif kind == "txt":
                parts.append(("t", item[1], T.MUTED))
            elif kind in ("hp", "treat"):
                parts.append(("i", "ui_heart" if kind == "hp" else "ui_treat", item[1],
                              T.TEXT))
            elif kind == "bar":
                parts.append(("b", item[1:]))
        # measure first so the block is repainted in one clear
        width = 0
        for p in parts:
            if p[0] == "t":
                width += scr.measure(p[1], T.BODY)[0] + 10
            elif p[0] == "i":
                width += 12 + scr.measure(p[2], T.BODY)[0] + 12
            else:
                width += 88
        end = x + width
        scr.fill_rect(x, self.y, max(end, old_end) - x, self.h, self.bg)
        for p in parts:
            if p[0] == "t":
                scr.text(x, ty, p[1], p[2], self.bg)
                x += scr.measure(p[1], T.BODY)[0] + 10
            elif p[0] == "i":
                a = _a(p[1])
                scr.blit(a, 0, x, self.y + (self.h - a.h) // 2, bg=self.bg)
                scr.text(x + 12, ty, p[2], p[3], self.bg)
                x += 12 + scr.measure(p[2], T.BODY)[0] + 12
            else:
                cur, mx, flashing = (tuple(p[1]) + (False,))[:3]
                by = self.y + (self.h - 9) // 2
                bar = HpBar(x, by, 80, 9, hero=True, bg=self.bg)
                bar.set(cur, mx)
                if flashing:
                    bar.flash(1)
                bar.draw(scr, True)
                x += 88
        self._left_end = end
        self._left_drawn = list(self.left)

    def _draw_hints(self, scr):
        ty = self.y + (self.h - T.text_h(T.BODY)) // 2
        widths = [14 + scr.measure(label, T.BODY)[0] + 2 for _, label in self.hints]
        total = sum(widths) + self.gap * max(0, len(widths) - 1)
        x0 = T.INNER_R + 1 - total
        clear_x = min(x0, self._hints_x)
        scr.fill_rect(clear_x, self.y, T.INNER_R + 1 - clear_x, self.h, self.bg)
        x = x0
        self._gems = []
        for (letter, label), w in zip(self.hints, widths):
            scr.blit(_a("ui_btn"), _BTN[letter], x, self.y + (self.h - 13) // 2, bg=self.bg)
            scr.text(x + 16, ty, label, T.TEXT, self.bg)
            self._gems.append((letter, label, (x - 2, self.y, w + 4, self.h)))
            x += w + self.gap
        self._hints_x = x0
        self._hints_drawn = list(self.hints)
        Footer.active = self

    def hit(self, x, y):
        """(letter, label) of the gem + label under game point (x, y), or None (PC pointer)."""
        for letter, label, (rx, ry, rw, rh) in self._gems:
            if rx <= x < rx + rw and ry <= y < ry + rh:
                return letter, label
        return None


# --------------------------------------------------------------------------- Toast
class Toast:
    """One-line message plate centered in the strip (x, y, w, h) the scene owns; the plate is only as wide as the
    text (cheap). show() it, update(dt) it, draw() it every frame; it erases itself with bg when it expires."""

    def __init__(self, x, y, w, h=20, bg=T.GROUND):
        self.x, self.y, self.w, self.h, self.bg = x, y, w, h, bg
        self.msg = None
        self.color = T.ACCENT
        self._left = 0.0
        self._drawn = None        # (msg, color, plate rect) while the plate is on screen

    def show(self, msg, seconds=1.5, color=T.ACCENT):
        self.msg, self.color, self._left = msg, color, seconds

    def pointer(self, x, y, kind):
        """PC pointer: True when a click landed on the plate (it is dismissed). Scenes that own a Toast may call it."""
        if kind == "up" and self._drawn is not None and self._left > 0:
            rx, ry, rw, rh = self._drawn[2]
            if rx <= x < rx + rw and ry <= y < ry + rh:
                self._left = 0
                return True
        return False

    def hide(self):
        self._left = 0

    @property
    def active(self):
        return self._left > 0

    def update(self, dt):
        if self._left > 0:
            self._left -= dt

    def invalidate(self):
        self._drawn = None

    def draw(self, scr, full=False):
        if self._left > 0:
            look = (self.msg, self.color)
            if self._drawn is not None and self._drawn[:2] == look and not full:
                return
            tw, th = scr.measure(self.msg, T.BODY)
            pw = tw + 20
            rect = (self.x + (self.w - pw) // 2, self.y, pw, self.h)
            if self._drawn is not None and not full and self._drawn[2] != rect:
                for part in _minus(self._drawn[2], rect):
                    scr.fill_rect(*part, self.bg)
            panel(scr, *rect, orn=False, edge=T.RULE_BRIGHT)
            scr.text(rect[0] + 10, rect[1] + (self.h - th) // 2, self.msg, self.color, T.PANEL)
            self._drawn = (self.msg, self.color, rect)
        elif self._drawn is not None:
            scr.fill_rect(*self._drawn[2], self.bg)
            self._drawn = None


# --------------------------------------------------------------------------- Chain popup
class ChainPopup:
    """Battle chain panel (187x45) with a tier-colored 'CHAIN xN' tab, one reading line and a big title.

    show(tier, line, title, chain=None) sets the content (tier 0..4 colors the tab), hide() removes it.
    The first draw paints the panel; later changes repaint only the text fields. `restore(scr, rect)` repaints the
    backdrop under the popup when it hides (default: flat ground fill)."""

    def __init__(self, rect=T.BATTLE_POPUP, restore=None):
        self.rect = rect
        self.restore = restore
        x, y, w, h = rect
        self._line = Label(x + 4, y + 9, w - 8, color=T.TEXT, bg=T.PANEL, align="c")
        self._title = Label(x + 4, y + 25, w - 8, font=T.TITLE, color=T.FOCUS, bg=T.PANEL, align="c")
        self._want = None
        self._tab = None          # (tier, chain) painted
        self._up = False          # panel on screen

    def show(self, tier, line, title, chain=None):
        self._want = (tier, chain if chain is not None else tier + 1)
        self._line.set(line)
        self._title.set(title)

    def hide(self):
        self._want = None

    def invalidate(self):
        self._line.invalidate()
        self._title.invalidate()
        self._tab = None
        self._up = False

    def draw(self, scr, full=False):
        x, y, w, h = self.rect
        if self._want is None:
            if self._up:
                r = (x - 1, y - 8, w + 2, h + 9)
                if self.restore:
                    self.restore(scr, r)
                else:
                    scr.fill_rect(*r, T.GROUND)
                self.invalidate()
            return
        if full or not self._up:
            panel(scr, x, y, w, h, edge=T.RULE_BRIGHT, orn=False)
            scr.rect(x + 2, y + 2, w - 4, h - 4, T.RULE_DIM)
            corners(scr, x, y, w, h)
            self._line.invalidate()
            self._title.invalidate()
            self._tab = None
            self._up = True
            full = True
        if self._tab != self._want and (full or not over_budget(scr, 90 * 13, 3)):
            tier, chain = self._want
            tab = "CHAIN x%d" % chain
            tw = scr.measure("CHAIN x0", T.BODY)[0] + 16
            tx = x + (w - tw) // 2
            scr.fill_rect(tx, y - 7, tw, 13, T.PANEL)
            scr.rect(tx, y - 7, tw, 13, T.AMBER1)
            th = T.text_h(T.BODY)
            scr.text(tx + 8, y - 7 + (13 - th) // 2, tab, T.tier_color(tier), T.PANEL)
            self._tab = self._want
        self._line.draw(scr, full)
        self._title.draw(scr, full)

# --------------------------------------------------------------------------- Overlays
class _Build:
    """Progressive panel paint: fills in row slices of at most STEP_PX pixels per frame (a big non-fast fill in one
    frame would blow the frame budget), then draws the rule and corners. Overlays report busy while building."""

    STEP_PX = 6500

    def __init__(self, rect, edge=T.RULE, fill=T.PANEL, orn=True):
        self.rect, self.edge, self.fill, self.orn = rect, edge, fill, orn
        self.rows = 0
        self.done = False

    def reset(self):
        self.rows = 0
        self.done = False

    def step(self, scr):
        x, y, w, h = self.rect
        n = min(h - self.rows, max(1, self.STEP_PX // w))
        scr.fill_rect(x, y + self.rows, w, n, self.fill)
        self.rows += n
        if self.rows >= h:
            scr.rect(x, y, w, h, self.edge)
            if self.orn:
                corners(scr, x - 1, y - 1, w + 2, h + 2)
            self.done = True


class Overlay:
    """Base for modal layers opened with app.open(). Subclasses set `rect` (what they cover) and
    implement update(ctl, dt) / draw(scr, full). Call self.close(result) to finish. `busy` is True on frames
    that paint a lot (the App passes it on to the cost model)."""

    rect = (0, 0, T.SCREEN_W, T.SCREEN_H)
    full_screen = False
    busy = False

    def __init__(self):
        self.closed = False
        self.result = None
        self._app = None

    def pointer(self, x, y, kind):
        """PC pointer: a click anywhere is the matching button (left = A, right = B, middle = C)."""
        return _CLICK.get(kind)

    def attach(self, app):
        self._app = app

    def close(self, result=None):
        self.closed = True
        self.result = result

    def update(self, ctl, dt):
        pass

    def draw(self, scr, full=False):
        pass


def portrait(key):
    """Baked 48x48 portrait asset for a story portrait key ('zero', 'domino', ...) or None."""
    if not key:
        return None
    alias = {"oriel": "granny_oriel", "young_oriel": "granny_oriel"}.get(key, key)
    try:
        return _a(alias + "_portrait")
    except AttributeError:
        return None


class Dialogue(Overlay):
    """Typewriter dialogue box at the bottom of the screen.

    lines: iterable of story.Line-like objects (speaker, text, portrait) or plain strings. Text may contain
    "\\n" (max 2 lines of 46 chars). A finishes the reveal, then advances; B skips the whole dialogue.
    on_done() is called when the last box closes. Reveal speed: 60 chars/s."""

    CPS = 60
    RECT = (16, 228, 448, 60)

    def __init__(self, lines, on_done=None):
        super().__init__()
        self.rect = self.RECT
        self.pages = [(getattr(l, "speaker", ""), getattr(l, "text", l), getattr(l, "portrait", None))
                      if not isinstance(l, str) else ("", l, None) for l in lines]
        self.on_done = on_done
        self.i = 0
        self.shown = 0.0
        self._clock = 0.0
        self._build = _Build(self.rect)
        self._jobs = []            # page repaint steps, one per frame
        self._page = None          # index of the page whose chrome is painted
        self._typed = 0            # characters painted of the current page
        self._row_w = [0, 0]       # painted widths of the two text rows
        self._name_w = 0
        self._has_portrait = False
        self._blink_on = None
        self._rx = self._name_x = 0   # x where the text rows / the speaker name were painted
        self._blip_page, self._blip_at = None, 0
        self.busy = True

    @property
    def text(self):
        return self.pages[self.i][1]

    @property
    def complete(self):
        return int(self.shown) >= len(self.text)

    def update(self, ctl, dt):
        self._clock += dt
        self._blip()
        if ctl.b:
            self.close()
            if self.on_done:
                self.on_done()
            return
        if self._jobs or not self._build.done:
            return
        if not self.complete:
            self.shown += self.CPS * dt
            if ctl.a:
                self.shown = len(self.text)
            return
        if ctl.a:
            if self.i + 1 < len(self.pages):
                self.i += 1
                self.shown = 0.0
            else:
                self.close()
                if self.on_done:
                    self.on_done()

    def _blip(self):
        """Typewriter tick: one soft `type` sound per four revealed letters (never on a space)."""
        if self._blip_page != self.i:
            self._blip_page, self._blip_at = self.i, 0
        n = min(len(self.text), int(self.shown))
        if n - self._blip_at >= 4:
            self._blip_at = n
            if not self.text[n - 1].isspace():
                sfx.play("type")

    def _text_x(self, key):
        return self.rect[0] + (68 if key else 14)

    def draw(self, scr, full=False):
        if full:
            self._build.reset()
            self._page = None
            self._jobs = []
            self._blink_on = None
            self._row_w = [0, 0]
            self._name_w = 0
            self._has_portrait = False
        if not self._build.done:
            self.busy = True
            self._build.step(scr)
            return
        if self._page != self.i:
            self._begin_page(scr)
        if self._jobs:
            self.busy = True
            self._jobs.pop(0)(scr)
            return
        self.busy = False
        self._type(scr)
        self._blink(scr)

    def _begin_page(self, scr):
        x, y, w, h = self.rect
        speaker, text, key = self.pages[self.i]
        art = portrait(key)
        tx, th = self._text_x(key), T.text_h(T.BODY)
        self._page = self.i
        self._typed = 0
        px, py = x + 8, y + (h - 52) // 2

        def chrome(scr):
            if key:
                scr.fill_rect(px, py, 52, 52, T.NIGHT1)
                scr.rect(px, py, 52, 52, T.RULE)
                if art is not None:
                    scr.blit(art, 0, px + 2, py + 2, bg=T.NIGHT1)
            elif self._has_portrait:
                scr.fill_rect(px, py, 52, 52, T.PANEL)
            self._has_portrait = bool(key)
            if self._name_w:
                scr.fill_rect(self._name_x, y + 5, self._name_w, th, T.PANEL)
            self._name_w = 0
            if speaker:
                scr.text(tx, y + 5, speaker, T.LABEL, T.PANEL)
                self._name_w = scr.measure(speaker, T.BODY)[0]
                self._name_x = tx

        def clear_row(i):
            def job(scr):
                if self._row_w[i]:
                    scr.fill_rect(self._rx, y + 5 + th + 3 + i * (th + 1), self._row_w[i], th, T.PANEL)
                self._row_w[i] = 0
                if i == 1:
                    self._rx = tx
            return job

        # Clear the previous page's rows first: after a narration page they start at x+14 and would
        # otherwise erase the portrait that chrome() paints.
        self._jobs = [clear_row(0), clear_row(1), chrome]

    def _type(self, scr):
        speaker, text, key = self.pages[self.i]
        n = min(len(text), int(self.shown))
        if n <= self._typed:
            return
        th = T.text_h(T.BODY)
        tx, ty0 = self._text_x(key), self.rect[1] + 5 + th + 3
        pos = 0
        for row, line in enumerate(text.split("\n")):
            lo, hi = max(self._typed - pos, 0), min(n - pos, len(line))
            if hi > lo:
                x = tx + scr.measure(line[:lo], T.BODY)[0] if lo else tx
                scr.text(x, ty0 + row * (th + 1), line[lo:hi], T.TEXT, T.PANEL)
                self._row_w[row] = scr.measure(line[:hi], T.BODY)[0]
            pos += len(line) + 1
        self._typed = n

    def _blink(self, scr):
        if not self.complete:
            self._blink_on = None if self._blink_on is None else False
            return
        on = int(self._clock * 2) % 2 == 0
        if on != self._blink_on:
            x, y, w, h = self.rect
            gx, gy = x + w - 22, y + h - 20
            scr.fill_rect(gx, gy, 13, 13, T.PANEL)
            if on:
                scr.blit(_a("ui_btn"), 0, gx, gy, bg=T.PANEL)
            self._blink_on = on


class Confirm(Overlay):
    """Modal question with [No] [Yes]; the cursor starts on No (GDD 6.4). A confirms the focused button,
    B = No. on_yes() / on_no() are called after the box closes."""

    def __init__(self, question, on_yes, on_no=None, yes="Yes", no="No"):
        super().__init__()
        self.on_yes, self.on_no = on_yes, on_no
        self.lines = question.split("\n")
        self.rect = (110, 116, 260, 84)
        x, y, w, h = self.rect
        self.focus = 0
        self._build = _Build(self.rect, edge=T.RULE_BRIGHT)
        self.no_btn = Button(x + 28, y + h - 34, 90, 26, no, bg=T.PANEL)
        self.yes_btn = Button(x + w - 28 - 90, y + h - 34, 90, 26, yes, bg=T.PANEL)
        self._text_done = False
        self.busy = True

    def pointer(self, x, y, kind):
        """Hover focuses the Yes/No button under the pointer; a click on one confirms it, outside does nothing."""
        for focus, btn in ((0, self.no_btn), (1, self.yes_btn)):
            if btn.x <= x < btn.x + btn.w and btn.y <= y < btn.y + btn.h:
                if kind in ("move", "down", "up"):
                    self.focus = focus
                return "a" if kind == "up" else None
        return "b" if kind == "right" else None

    def update(self, ctl, dt):
        if ctl.dx:
            self.focus = 1 - self.focus
        if ctl.b:
            self._finish(False)
        elif ctl.a:
            self._finish(self.focus == 1)

    def _finish(self, yes):
        self.close(yes)
        cb = self.on_yes if yes else self.on_no
        if cb:
            cb()

    def draw(self, scr, full=False):
        x, y, w, h = self.rect
        if full:
            self._build.reset()
            self._text_done = False
            self.no_btn.invalidate()
            self.yes_btn.invalidate()
        if not self._build.done:
            self.busy = True
            self._build.step(scr)
            return
        if not self._text_done:
            self.busy = True
            th = T.text_h(T.BODY)
            for i, line in enumerate(self.lines):
                lw = scr.measure(line, T.BODY)[0]
                scr.text(x + (w - lw) // 2, y + 9 + i * (th + 1), line, T.TEXT, T.PANEL)
            self._text_done = True
            return
        self.busy = False
        self.no_btn.set(focused=self.focus == 0)
        self.yes_btn.set(focused=self.focus == 1)
        self.no_btn.draw(scr, full)
        self.yes_btn.draw(scr, full)



class InfoOverlay(Overlay):
    """Full-screen Card Info / explanation page. B or C closes.

    title      name in the TITLE font (gold), right of the big card
    subtitle   one line under it (rich text: "Wands 4 {.} {*}1 {.} Upright")
    side       extra lines in MUTED beside the card (flavor text), max 5
    body       rules lines (max ~7 of 56 chars), full width under a divider
    card       an already configured CardView; it is painted at 2x (96x128) at the top left
    notes      rows (icon, heading, text): icon = (asset name, frame) or None; heading in amber, text in muted;
               use for the Charm and for glossary terms"""

    def __init__(self, title, subtitle="", body=(), card=None, notes=(), side=()):
        super().__init__()
        self.full_screen = True
        self.title, self.subtitle, self.body = title, subtitle, list(body)
        self.card, self.notes, self.side = card, list(notes), list(side)
        self._built = False

    def pointer(self, x, y, kind):
        if kind in ("up", "right", "middle"):
            return "b"                     # any click closes the page
        return None

    def update(self, ctl, dt):
        if ctl.b or ctl.c:
            self.close()

    def draw(self, scr, full=False):
        if self._built and not full:
            self.busy = False
            return
        self._built = True
        self.busy = True
        scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
        scr.rect(2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4, T.RULE_DIM)
        corners(scr, 2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4)
        th = T.text_h(T.BODY)
        has_card = self.card is not None
        tx = T.INNER_L + 8 + 96 + 20 if has_card else T.INNER_L
        title_h = T.text_h(T.TITLE)
        head_h = title_h + 10 + ((th + 12) if self.subtitle else 0) + len(self.side) * (th + 4)
        top_h = max(128 if has_card else 0, head_h)
        note_rows = []
        for icon, heading, text in self.notes:
            note_rows.append((icon, heading, textwrap.wrap(text, 54) if text else []))
        body_h = len(self.body) * (th + 4)
        notes_h = sum(th + 2 + len(rows) * (th + 1) + 4 for _, _, rows in note_rows)
        total = top_h + 20 + body_h + ((8 + notes_h) if note_rows else 0)
        avail_top, avail_bot = 10, T.FOOTER_DIV_Y - 6
        y0 = max(avail_top, avail_top + (avail_bot - avail_top - total) // 2)
        if has_card:
            self.card.bg = T.GROUND
            self.card.draw_scaled(scr, T.INNER_L + 8, y0 + (top_h - 128) // 2, 2)
        y = y0 + (top_h - head_h) // 2
        scr.text(tx, y, self.title, T.LABEL, T.GROUND, T.TITLE)
        y += title_h + 10
        if self.subtitle:
            rich(scr, tx, y, self.subtitle, T.TEXT, T.GROUND)
            y += th + 12
        for line in self.side:
            rich(scr, tx, y, line, T.MUTED, T.GROUND)
            y += th + 4
        y = y0 + top_h + 8
        divider(scr, T.INNER_L, T.INNER_R, y)
        y += 12
        for line in self.body:
            rich(scr, T.INNER_L, y, line, T.TEXT, T.GROUND)
            y += th + 4
        y += 8
        for icon, heading, rows in note_rows:
            x = T.INNER_L
            if icon:
                a = _a(icon[0])
                scr.blit(a, icon[1], x, y + (th - a.h) // 2, bg=T.GROUND)
                x += a.w + 4
            scr.text(x, y, heading, T.ACCENT, T.GROUND)
            y += th + 2
            for row in rows:
                rich(scr, T.INNER_L + 12, y, row, T.MUTED, T.GROUND)
                y += th + 1
            y += 4
        Footer(hints=[("B", "Close")]).draw(scr, True)


def card_info(card):
    """InfoOverlay for a rules Card: name, subtitle, flavor, full rules text, and its Charm."""
    from nla.rules import cards
    cv = CardView(0, 0)
    cv.set_card(card)
    notes = []
    if card.charm:
        ch = cards.CHARMS[card.charm]
        notes.append((("ui_charm", card.charm - 1), "Charm: %s (%s)" % (ch.name, ch.rarity.capitalize()), ""))
    flavor = cards.card_flavor(card)
    return InfoOverlay(cards.card_title(card), cards.card_subtitle(card), cards.card_text_full(card), cv, notes,
                       side=cards.wrap_lines(flavor, 34) if flavor else ())


_DROPPINGS = 48
_CHEWED = {44: 0, 41: 1, 45: 2}   # Chariot, Magician, Strength -> card_chewed_s frame
