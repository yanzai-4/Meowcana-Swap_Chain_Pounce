"""Shared Spread/Box board for the Spread and Card Picker screens (GDD 6.5, 6.6).

Owns the Spread row (48x64 cards), the Box row (40x54), their header labels, the cursor, the per-slot Power numbers
(they count up/down and flash amber when a Reading changes them) and the Reading link glyphs drawn between cards.

    board = Board(ns, nb, power=True)
    board.show(spread, box, origin=None, hover=None, dim=())     # what the rows look like right now
    board.set_report(report, spread)                              # Power numbers + link glyphs (Spread screen only)
    board.cursor_to("s" | "b", index, lifted=False)               # cursor first in draw(): immediate feedback
    board.tick(dt) -> bool                                        # advance number animation; True while animating
    board.draw(scr, full)                                         # cursor, cards, labels, numbers, links
    board.invalidate(rect=None)                                   # repaint what overlaps rect (or everything)

`spread`/`box` are lists of Card|None. `origin` = ("s"|"b", index) of a card in the hand, `hover` = where the hand
card currently hovers: that slot shows the held card (lifted, gold rim); the origin shows the card that would be
swapped back (dimmed) or a dotted ghost outline. `dim` = set of (zone, index) drawn dimmed (Picker: not selectable).
"""

from nla.ui import theme as T
from nla.ui import widgets as W

SLOT_Y = T.SPREAD_CARD_Y
POWER_Y = SLOT_Y + T.CARD_H + 1              # number row under a Spread card (y 171..185)
GAP_W = T.SPREAD_SLOT_PITCH - T.CARD_W       # 10 px between Spread cards
LINK_FRAME = {"nuzzle": 0, "tail_tap": 1, "hiss": 2, "step": 3, "mirror": 4, "litter": 5, "journey": 6}
FLASH_S = 0.7                                # amber flash after a Power change
COUNT_S = 0.045                              # seconds per count step
HOLD_RIM = T.GOLD4


def slot_x(i):
    return T.SPREAD_SLOT_X0 + T.SPREAD_SLOT_PITCH * i


def box_x(i):
    return T.SPREAD_BOX_X0 + T.SPREAD_BOX_PITCH * i


def hit(a, b):
    """True when rects (x, y, w, h) overlap."""
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


class Board:
    def __init__(self, ns, nb, power=True):
        self.ns, self.nb, self.power = ns, nb, power
        self.slots = [W.CardView(slot_x(i), SLOT_Y) for i in range(ns)]
        self.box = [W.CardView(box_x(i), T.SPREAD_BOX_Y, small=True) for i in range(nb)]
        self.cursor = W.Cursor()
        self.spread_label = W.Label(16, 89, 100, color=T.LABEL)
        self.box_label = W.Label(16, 188, 70, color=T.LABEL)
        self.box_note = W.Label(16, 202, 70, color=T.CAPTION)
        self.box_note.set("spare cards")
        self.spread_cards = 0
        self.box_cards = 0
        # power numbers
        self._target = [None] * ns
        self._shown = [None] * ns
        self._base = [0] * ns
        self._flash = [0.0] * ns
        self._acc = 0.0
        self._num = [None] * ns           # (text, color, x, w) on screen
        # links
        self._gaps = {}                   # gap index -> tuple of link frames wanted
        self._gap_fill = set()            # gaps whose content changed (clear + blit)
        self._gap_blit = set(range(max(0, ns - 1)))   # gaps to blit again (cursor ring cut through them)
        # bite marker (Chubbs)
        self.bite = -1
        self._bite_seen = None
        self._cursor_slot = None
        self._last_dx = 0
        self._stamp = [None] * ns

    # ------------------------------------------------------------------ content
    def show(self, spread, box, origin=None, hover=None, dim=()):
        for zone, cards, views in (("s", spread, self.slots), ("b", box, self.box)):
            for i, v in enumerate(views):
                c = cards[i] if i < len(cards) else None
                v.set_card(c)
                key = (zone, i)
                held = origin is not None and key == hover
                swapped_back = origin is not None and key == origin and not held
                v.lift = T.CARD_LIFT if held else 0
                v.rim = HOLD_RIM if held else None
                v.ghost = swapped_back and c is None
                v.dim = key in dim or (swapped_back and c is not None)
                v.glow = False
        self.spread_cards = sum(1 for c in spread if c is not None)
        self.box_cards = sum(1 for c in box if c is not None)
        self.spread_label.set("SPREAD %d/%d" % (self.spread_cards, self.ns))
        self.box_label.set("BOX %d/%d" % (self.box_cards, self.nb))

    def set_report(self, report, spread):
        """Power numbers and link glyphs for the arrangement last passed to show()."""
        for i in range(self.ns):
            info = report.slots[i] if i < len(report.slots) else None
            new = info.power if (info is not None and spread[i] is not None) else None
            self._base[i] = info.base if info is not None else 0
            if new != self._target[i]:
                if self._shown[i] is None or new is None:
                    self._shown[i] = new
                    self._flash[i] = 0.0
                else:
                    self._flash[i] = FLASH_S
                self._target[i] = new
        gaps = {}
        for lk in report.links:
            f = LINK_FRAME.get(lk.kind)
            if f is None or lk.a == lk.b:
                continue
            a, b = min(lk.a, lk.b), max(lk.a, lk.b)
            for g in ([a] if b == a + 1 else [a, b - 1]):
                if 0 <= g < self.ns - 1:
                    lst = gaps.setdefault(g, [])
                    if f not in lst and len(lst) < 4:
                        lst.append(f)
        gaps = {g: tuple(v) for g, v in gaps.items()}
        for g in set(gaps) | set(self._gaps):
            old, new = self._gaps.get(g, ()), gaps.get(g, ())
            if new != old:
                self._gap_fill.add(g)
                if 2 in old and 2 not in new:        # the Hiss sticker overlapped both cards: repaint them
                    self.slots[g].invalidate()
                    self.slots[g + 1].invalidate()
        self._gaps = gaps

    def set_bite(self, i):
        """Slot Chubbs would eat (-1 = none). The old card repaints to lose the marker."""
        if i != self.bite:
            if 0 <= self.bite < self.ns:
                self.slots[self.bite].invalidate()
            self.bite = i
            self._bite_seen = None

    # ------------------------------------------------------------------ cursor
    def cursor_to(self, zone, i, lifted=False, dx=0):
        if zone == "s":
            v = self.slots[i]
            self.cursor.to(v.x + dx, v.y - (T.CARD_LIFT if lifted else 0), v.w, v.h, paw=False)
            slot = i
        else:
            v = self.box[i]
            self.cursor.to(v.x + dx, v.y - (T.CARD_LIFT if lifted else 0), v.w, v.h, paw=False)
            slot = None
        if slot is not None and (dx or self._last_dx):
            self._num[slot] = None
            self._gap_blit.update(g for g in (slot - 1, slot) if 0 <= g < self.ns - 1)
        self._last_dx = dx
        self._moved_cursor(slot)

    def cursor_rect(self, x, y, w, h, paw=False):
        self.cursor.to(x, y, w, h, paw=paw)
        self._moved_cursor(None)

    def cursor_hide(self):
        self.cursor.hide()
        self._moved_cursor(None)

    def _moved_cursor(self, slot):
        """The old ring erase cuts through the neighbors' number and link glyphs: repaint them."""
        old = self._cursor_slot
        if old == slot:
            return
        for s in (old, slot):
            if s is None:
                continue
            self._num[s] = None
            for g in (s - 1, s):
                if 0 <= g < self.ns - 1:
                    self._gap_blit.add(g)
        self._cursor_slot = slot

    # ------------------------------------------------------------------ animation
    def tick(self, dt):
        """Advance the count-up/down and the flash timers; True while something still animates."""
        busy = False
        self._acc += dt
        steps = 0
        while self._acc >= COUNT_S:
            self._acc -= COUNT_S
            steps += 1
        steps = min(steps, 3)
        for i in range(self.ns):
            t, s = self._target[i], self._shown[i]
            if t is not None and s is not None and s != t:
                diff = t - s
                step = max(1, abs(diff) // 6) * (1 if diff > 0 else -1)
                if steps:
                    self._shown[i] = s + step if abs(step) < abs(diff) else t
                busy = True
            if self._flash[i] > 0:
                self._flash[i] = max(0.0, self._flash[i] - dt)
                busy = True
        return busy

    # ------------------------------------------------------------------ drawing
    def invalidate(self, rect=None):
        everything = rect is None
        for v in self.slots + self.box:
            if everything or hit(rect, (v.x - 4, v.y - 8, v.w + 8, v.h + 12)):
                v.invalidate()
        for lab in (self.spread_label, self.box_label, self.box_note):
            lab.invalidate()
        self.cursor.invalidate()
        for i in range(self.ns):
            if everything or hit(rect, (slot_x(i) - 4, POWER_Y, T.CARD_W + 8, 15)):
                self._num[i] = None
        self._gap_blit.update(range(max(0, self.ns - 1)))
        self._bite_seen = None


    def draw(self, scr, full=False):
        self.cursor.draw(scr, full)
        for v in self.slots + self.box:
            v.draw(scr, full)
        self.spread_label.draw(scr, full)
        self.box_label.draw(scr, full)
        self.box_note.draw(scr, full)
        if self.power:
            self._draw_numbers(scr, full)
            self._draw_links(scr, full)
            self._draw_bite(scr, full)

    def _num_look(self, i):
        val = self._shown[i]
        if val is None:
            return None
        if self._flash[i] > 0:
            color = T.FOCUS if int(self._flash[i] * 10) % 2 == 0 else T.AMBER2
        elif val > self._base[i]:
            color = T.ACCENT
        elif val < self._base[i]:
            color = T.CURSE
        else:
            color = T.TEXT
        return (str(val), color)

    def _draw_numbers(self, scr, full):
        for i in range(self.ns):
            look = self._num_look(i)
            drawn = self._num[i]
            if look is None:
                if drawn is not None and drawn != "blank":
                    scr.fill_rect(slot_x(i), POWER_Y, T.CARD_W, 15, T.GROUND)
                    self._num[i] = "blank"
                continue
            if not full and drawn is not None and drawn != "blank" and drawn[:2] == look:
                continue
            if not full and W.over_budget(scr, 300, 2):
                continue
            tw = scr.measure(look[0], T.NUM)[0]
            x = slot_x(i) + (T.CARD_W - tw) // 2
            if drawn not in (None, "blank") and (drawn[2] < x or drawn[2] + drawn[3] > x + tw):
                scr.fill_rect(drawn[2], POWER_Y, drawn[3], 15, T.GROUND)
            scr.text(x, POWER_Y, look[0], look[1], T.GROUND, T.NUM)
            self._num[i] = (look[0], look[1], x, tw)

    def _draw_links(self, scr, full):
        for i, v in enumerate(self.slots):           # a repainted card can have covered a Hiss sticker
            if v._drawn is not self._stamp[i]:
                self._stamp[i] = v._drawn
                self._gap_blit.update(g for g in (i - 1, i) if 2 in self._gaps.get(g, ()))
        if not full and not (self._gap_fill or self._gap_blit):
            return
        icons = T.asset("ui_link")
        for g in (range(max(0, self.ns - 1)) if full else sorted(self._gap_fill | self._gap_blit)):
            if not full and W.over_budget(scr, 80 * 4, 6):
                return
            x = slot_x(g) + T.CARD_W
            frames = self._gaps.get(g, ())
            hiss = 2 in frames
            if g in self._gap_fill and not full:
                scr.fill_rect(x, SLOT_Y, GAP_W, T.CARD_H, T.GROUND)
            if hiss:
                others = [f for f in frames if f != 2][:2]
                for k, f in enumerate(others):
                    scr.blit(icons, f, x + 1, SLOT_Y + 4 + k * 43, bg=T.GROUND)
                scr.blit(T.asset("fx_hiss"), 0, x + GAP_W // 2 - 12, SLOT_Y + 20)
            elif frames:
                n = len(frames)
                y0 = SLOT_Y + (T.CARD_H - (n * 9 + (n - 1) * 3)) // 2
                for k, f in enumerate(frames):
                    scr.blit(icons, f, x + 1, y0 + k * 12, bg=T.GROUND)
            self._gap_fill.discard(g)
            self._gap_blit.discard(g)

    def _draw_bite(self, scr, full):
        """Chubbs' next meal: a bite glyph on the card he would eat. Repainted whenever that card repainted."""
        if self.bite < 0 or self.bite >= self.ns:
            self._bite_seen = None
            return
        v = self.slots[self.bite]
        if v._drawn is None or (not full and self._bite_seen is not None and self._bite_seen[0] is v._drawn):
            return
        scr.blit(T.asset("fx_bite"), 0, v.x + v.w - 16, v.y - v.lift + 22)
        self._bite_seen = (v._drawn,)
