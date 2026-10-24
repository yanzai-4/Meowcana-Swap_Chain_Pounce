"""Battle HUD: everything of the Battle screen that is not the attic stage.

    top plate        enemy name (TITLE), enemy HP bar with lag segment (+ 50% tick for the boss), HP text
    enemy chips      statuses under the scrap row, right aligned
    scrap row        enemy cards (40x54), the active one lifted with a gold bracket
    hand row         Domino's cards (40x54), the active one lifted 4 px with a gold bracket; eaten slots show a bite
    seam icons       ui_link glyphs between the cards of a reading, just above the row
    reading panel    "READING", round number and one line (chain text / last card)
    footer           Domino name, HP bar, HP text, compact status chips, A/B/C hints

All pieces repaint only what changed and defer when the frame budget is used up (widgets' own check), the static
chrome is built in slices (jobs) so a scene entry never sends one huge op.
"""

from nla.ui import theme as T
from nla.ui import widgets as W

HAND_Y = T.BATTLE_HAND_Y            # 238
FOE_Y = T.BATTLE_SCRAP_Y            # 34
READING_Y, READING_H = 240, 51
LINK_Y = HAND_Y + 18                # seam icons sit on the middle of the gap between two cards (9 px)
BAR_FOE = (316, 3, 148, 9)
BAR_HERO = (66, 304, 80, 9)

STATUS_FRAME = {"singe": 0, "puff": 1, "drowsy": 2, "curl": 3, "leap": 4}
STATUS_COLOR = {"singe": T.SINGE, "puff": T.TEXT, "drowsy": T.WATER2, "curl": T.SILVER2, "leap": T.HEAL}
STATUS_ORDER = ("curl", "puff", "singe", "drowsy", "leap")


def run_jobs(scr, jobs, limit_ms=62.0):
    """Run queued paint steps (est_px, fn) in order while they fit the frame; the first step of a frame always runs."""
    while jobs:
        px, fn = jobs[0]
        st = scr.stats()
        if st["ops"] > 0 and st["ms"] + px / 180.0 + 3.0 > limit_ms:
            return False
        fn(scr)
        jobs.pop(0)
    return True


class LagBar:
    """HP bar: fill = current HP, a trailing segment drains toward it after a hit (the lag), red flash on damage."""

    def __init__(self, x, y, w, h=9, hero=False, tick=None, bg=T.GROUND):
        self.x, self.y, self.w, self.h, self.bg, self.tick = x, y, w, h, bg, tick
        self.fill, self.hi = (T.BAR_HP_HERO, T.BAR_HP_HERO_HI) if hero else (T.BAR_HP_ENEMY, T.BAR_HP_ENEMY_HI)
        self.lag_color = T.RED if hero else T.AMBER2
        self.cur = self.mx = 1
        self.lag = 0.0
        self._hold = 0
        self._flash = 0
        self._drawn = None

    def snap(self, cur, mx=None):
        if mx is not None:
            self.mx = max(1, mx)
        self.cur = max(0, cur)
        self.lag = float(self._px(self.cur))
        self._hold = 0

    def set(self, cur):
        cur = max(0, cur)
        if cur > self.cur:
            self.lag = float(self._px(cur))
        elif cur < self.cur:
            self._hold = 5
        self.cur = cur

    def flash(self, frames=2):
        self._flash = frames

    def _px(self, v):
        return (self.w - 2) * min(v, self.mx) // self.mx

    def update(self):
        if self._flash:
            self._flash -= 1
        target = self._px(self.cur)
        if self.lag > target:
            if self._hold:
                self._hold -= 1
            else:
                self.lag = max(float(target), self.lag - max(1.0, (self.lag - target) * 0.14))
        else:
            self.lag = float(target)

    def invalidate(self):
        self._drawn = None

    def draw(self, scr, full=False):
        fc, fl = self._px(self.cur), int(self.lag)
        fl = max(fl, fc)
        flashing = self._flash > 0
        look = (fc, fl, flashing)
        if not full and look == self._drawn:
            return
        inner, x0, y0, ih = self.w - 2, self.x + 1, self.y + 1, self.h - 2
        old = self._drawn
        fill, hi = (T.RED, T.AMBER3) if flashing else (self.fill, self.hi)
        if full or old is None or old[2] != flashing:
            lo, up = 0, inner
            scr.rect(self.x, self.y, self.w, self.h, T.RULE)
        else:
            lo, up = min(old[0], fc), max(old[1], fl)
            lo = min(lo, old[1], fl)
        for a, b, color, hl in ((0, fc, fill, hi), (fc, fl, self.lag_color, None), (fl, inner, T.PANEL, None)):
            a, b = max(a, lo), min(b, up)
            if a < b:
                scr.fill_rect(x0 + a, y0, b - a, ih, color)
                if hl is not None:
                    scr.fill_rect(x0 + a, y0, b - a, 1, hl)
        if self.tick is not None:
            tx = self.x + 1 + int((self.w - 2) * self.tick)
            scr.fill_rect(tx, y0, 1, 1, T.MOON)
            scr.fill_rect(tx, y0 + ih - 1, 1, 1, T.MOON)
        self._drawn = look


class SlotView:
    """One card slot of a row: a small CardView plus the eaten marker and the hiss lean."""

    def __init__(self, x, y, bg):
        self.x0, self.y = x, y
        self.cv = W.CardView(x, y, small=True, bg=bg)
        self.bg = bg
        self.gone = False
        self.empty = True
        self.flash_left = 0
        self.dx = 0
        self._gone_drawn = False
        self._card = None
        self.flip_steps = []
        self._flip_i = 0
        self._flip_drawn = None
        self.mark = 0

    def set_card(self, card):
        self._card = card
        self.empty = card is None
        self.gone = False
        self.cv.set_card(card)

    def set_enemy_card(self, c):
        self._card = c
        self.empty = False
        self.gone = False
        self.cv.set_enemy_card(c)

    def set_gone(self):
        self.gone = True
        self.cv.lift = 0
        self.cv.glow = False
        self.cv.flash = False
        self.flash_left = 0

    def set_active(self, on):
        self.cv.lift = T.CARD_LIFT if on else 0
        self.cv.glow = on

    def flash(self, ticks=2):
        self.flash_left = ticks
        self.cv.flash = True

    def flip_to(self, card):
        """Squash flip to the new face: field-colored slivers shrink around the old face, then grow into the new."""
        old = self._card
        self.set_card(card)
        c_old = T.elem_body((old.def_id // 10) if old is not None and old.def_id < 40 else 0,
                            bool(old.reversed) if old is not None else False)
        c_new = T.elem_body((card.def_id // 10) if card.def_id < 40 else 0, bool(card.reversed))
        self.flip_steps = [(28, c_old), (12, c_old), (4, T.NIGHT0), (12, c_new), (28, c_new)]
        self.mark = 12
        self._flip_i = 0

    def tick(self):
        if self.flash_left:
            self.flash_left -= 1
            if not self.flash_left:
                self.cv.flash = False
        if self.flip_steps:
            self._flip_i += 1
            if self._flip_i >= len(self.flip_steps):
                self.flip_steps = []
                self.invalidate()
        elif self.mark:
            self.mark -= 1
            if self.mark == 0:
                self.invalidate()
        self.cv.x = self.x0 + self.dx

    @property
    def rect(self):
        return (self.x0 - 3, self.y - T.CARD_LIFT - 3, T.CARD_SW + 6, T.CARD_SH + T.CARD_LIFT + 6)

    def invalidate(self):
        d = self.cv._drawn
        self.cv._drawn = (None, d[1]) if d is not None else None     # repaint, but remember what to erase
        self._gone_drawn = False
        self._flip_drawn = None

    def _stamp(self, scr):
        bite = T.asset("fx_bite")
        scr.blit(bite, 0, self.cv.x + T.CARD_SW - bite.w - 2, self.y - self.cv.lift + 2)

    def draw(self, scr, full=False):
        if self.gone:
            if full or not self._gone_drawn:
                x, y = self.x0, self.y
                scr.fill_rect(x - 3, y - 6, T.CARD_SW + 6, T.CARD_SH + 8, self.bg)
                scr.dotted_rect(x, y, T.CARD_SW, T.CARD_SH, T.NIGHT3)
                bite = T.asset("fx_bite")
                scr.blit(bite, 0, x + (T.CARD_SW - bite.w) // 2, y + (T.CARD_SH - bite.h) // 2, bg=self.bg)
                self._gone_drawn = True
            return
        self._gone_drawn = False
        if self.flip_steps:
            w, color = self.flip_steps[min(self._flip_i, len(self.flip_steps) - 1)]
            if self._flip_drawn != self._flip_i:
                x, y = self.x0, self.y - self.cv.lift
                scr.fill_rect(x, y, T.CARD_SW, T.CARD_SH, self.bg)
                scr.fill_rect(x + (T.CARD_SW - w) // 2, y, w, T.CARD_SH, color)
                scr.rect(x + (T.CARD_SW - w) // 2, y, w, T.CARD_SH, T.RULE)
                self._flip_drawn = self._flip_i
            return
        before = self.cv._drawn
        self.cv.draw(scr, full)
        if self.mark and self.cv._drawn is not before:
            self._stamp(scr)


class Hud:
    def __init__(self, enemy, hand_cards, foe_cards, foe_slots, hero_max, boss):
        self.n_hand = max(1, len(hand_cards))
        self.hand_pitch = 46 if self.n_hand <= 4 else 42
        self.foe_n = max(1, foe_slots)
        self.foe_pitch = 44
        self.foe_x0 = 464 - T.CARD_SW - (self.foe_n - 1) * self.foe_pitch
        hand_right = 16 + (self.n_hand - 1) * self.hand_pitch + T.CARD_SW
        self.rx = max(212, hand_right + 12)
        self.rw = 464 - self.rx

        # plate
        self.name = W.Label(16, 3, 220, font=T.TITLE, color=T.LABEL, bg=T.GROUND)
        self.name.set(enemy.name)
        self.foe_bar = LagBar(*BAR_FOE, hero=False, tick=0.5 if boss else None)
        self.foe_hp = W.Label(BAR_FOE[0], 14, BAR_FOE[2], color=T.TEXT, bg=T.GROUND, align="r")
        self.foe_chips = W.ChipRow(236, 14, 168, align="r", gap=10)
        self._foe_status = {}

        # rows
        self.hand = [SlotView(16 + i * self.hand_pitch, HAND_Y, T.GROUND) for i in range(self.n_hand)]
        for sv, c in zip(self.hand, hand_cards):
            sv.set_card(c)
        for sv in self.hand[len(hand_cards):]:
            sv.set_card(None)
        self.foe = [SlotView(self.foe_x0 + i * self.foe_pitch, FOE_Y, T.GROUND) for i in range(self.foe_n)]
        self.foe_shown = len(foe_cards)
        for sv, c in zip(self.foe, foe_cards):
            sv.set_enemy_card(c)
        self.active = [None, None]

        # reading panel
        self.round_label = W.Label(self.rx + self.rw - 8 - 72, READING_Y + 5, 72, color=T.MUTED, bg=T.PANEL, align="r")
        self.round_label.set("Round 1")
        self.head_label = W.Label(self.rx + 8, READING_Y + 5, 80, color=T.LABEL, bg=T.PANEL)
        self.head_label.set("READING")
        self.line_label = W.Label(self.rx + 8, READING_Y + 26, self.rw - 16, color=T.TEXT, bg=T.PANEL, align="c")
        self.line_label.set("")
        self.line_color = T.TEXT

        # footer
        self.hero_name = W.Label(T.INNER_L, 301, 48, color=T.LABEL, bg=T.GROUND)
        self.hero_name.set("Domino")
        self.hero_bar = LagBar(*BAR_HERO, hero=True)
        self.hero_hp = W.Label(BAR_HERO[0] + BAR_HERO[2] + 6, 301, 70, color=T.TEXT, bg=T.GROUND)
        self.hero_chips = W.ChipRow(206, 301, 104, gap=6)
        self._hero_status = {}
        self.footer = W.Footer(left=[], hints=[("A", "2x"), ("B", "Skip"), ("C", "Info")])

        # links
        self.links = []          # (center x, frame) wanted
        self._links_drawn = []
        self._lean = {}
        self._jobs = []
        self._full_pending = False
        self.hint_speed = "2x"
        self._pops = {}

    # ------------------------------------------------------------------ state
    def set_hp(self, side, cur, mx=None, snap=False):
        bar, label = (self.hero_bar, self.hero_hp) if side == 0 else (self.foe_bar, self.foe_hp)
        if snap:
            bar.snap(cur, mx)
        else:
            bar.set(cur)
        if mx is not None:
            bar.mx = max(1, mx)
        label.set("HP %d/%d" % (max(0, cur), bar.mx))

    def hurt_bar(self, side):
        (self.hero_bar if side == 0 else self.foe_bar).flash(2)

    def _chips(self, side):
        st = self._hero_status if side == 0 else self._foe_status
        items = []
        for k in STATUS_ORDER:
            n = st.get(k)
            if not n:
                continue
            popping = self._pops.get((side, k), 0) > 0
            color = T.MOON if popping else STATUS_COLOR[k]
            if side == 0:
                items.append(W.chip(str(n), color, ("ui_status_s", STATUS_FRAME[k])))
            else:
                items.append(W.chip("%s %d" % (k.capitalize(), n), color, ("ui_status_s", STATUS_FRAME[k])))
        return items

    def set_status(self, side, st):
        if side == 0:
            self._hero_status = dict(st)
            self.hero_chips.set(self._chips(0))
        else:
            self._foe_status = dict(st)
            self.foe_chips.set(self._chips(1))

    def pop_status(self, side, key):
        """A status chip just grew: paint it moon-white for 4 ticks (pop)."""
        self._pops[(side, key)] = 4
        (self.hero_chips if side == 0 else self.foe_chips).set(self._chips(side))

    def tick_pops(self):
        for k in list(self._pops):
            self._pops[k] -= 1
            if self._pops[k] <= 0:
                del self._pops[k]
                (self.hero_chips if k[0] == 0 else self.foe_chips).set(self._chips(k[0]))

    def settle_slots(self):
        for row in (self.hand, self.foe):
            for sv in row:
                sv.set_active(False)
                sv.flash_left = 0
                sv.cv.flash = False
                sv.flip_steps = []
                sv.mark = 0
        self.active = [None, None]

    def set_round(self, n):
        self.round_label.set("Round %d" % n)

    def set_line(self, text, color=T.TEXT):
        self.line_label.set(text, color)

    def set_hints(self, speed_label):
        self.hint_speed = speed_label
        self.footer.set_hints([("A", speed_label), ("B", "Skip"), ("C", "Info")])

    def set_result_hints(self):
        self.footer.set_hints([("A", "Continue")])

    def row(self, side):
        return self.hand if side == 0 else self.foe

    def activate(self, side, i):
        row = self.row(side)
        prev = self.active[side]
        if prev is not None and prev != i and prev < len(row):
            row[prev].set_active(False)
        if i is not None and 0 <= i < len(row) and not row[i].gone:
            row[i].set_active(True)
            self.active[side] = i
        else:
            self.active[side] = None

    def deactivate(self, side):
        self.activate(side, None)

    def slot_center_x(self, side, i):
        row = self.row(side)
        return row[i].x0 + T.CARD_SW // 2

    def add_foe_card(self, i, c):
        if i >= len(self.foe):
            return
        self.foe[i].set_enemy_card(c)
        self.foe[i].flash(2)
        self.foe_shown = max(self.foe_shown, i + 1)

    def set_links(self, pairs):
        """pairs: [(slot a, slot b, ui_link frame)] drawn at the seam between the cards."""
        self.links = [(self._seam_x(a, b), f) for a, b, f in pairs]

    def _seam_x(self, a, b):
        lo, hi = min(a, b), max(a, b)
        if hi == lo + 1:
            return self.hand[lo].x0 + T.CARD_SW + (self.hand_pitch - T.CARD_SW) // 2
        return (self.slot_center_x(0, lo) + self.slot_center_x(0, hi)) // 2

    def clear_links(self):
        self.links = []

    def lean(self, a, b, amount=3):
        """Hiss: the two cards lean away from each other."""
        self._lean = {min(a, b): -amount, max(a, b): amount}

    def unlean(self):
        self._lean = {}

    # ------------------------------------------------------------------ per tick
    def update(self):
        self.foe_bar.update()
        self.hero_bar.update()
        for i, sv in enumerate(self.hand):
            sv.dx = self._lean.get(i, 0)
            sv.tick()
        for sv in self.foe:
            sv.tick()

    # ------------------------------------------------------------------ static chrome
    def invalidate(self):
        for w in (self.name, self.foe_hp, self.foe_chips, self.foe_bar, self.round_label, self.head_label,
                  self.line_label, self.hero_name, self.hero_bar, self.hero_hp, self.hero_chips, self.footer):
            w.invalidate()
        for sv in self.hand + self.foe:
            sv.invalidate()
        self._links_drawn = []
        self._full_pending = True
        self._build_jobs()

    def _build_jobs(self):
        rx, rw, ry, rh = self.rx, self.rw, READING_Y, READING_H

        def panel_rows(r0, r1):
            def job(scr):
                scr.fill_rect(rx, ry + r0, rw, r1 - r0, T.PANEL)
            return job

        def panel_rule(scr):
            scr.rect(rx, ry, rw, rh, T.RULE)
            W.corners(scr, rx - 1, ry - 1, rw + 2, rh + 2)
            scr.fill_rect(rx + 8, ry + 22, rw - 16, 1, T.RULE_DIM)

        jobs = []
        step = max(1, 6000 // rw)
        for r0 in range(0, rh, step):
            jobs.append((rw * min(step, rh - r0), panel_rows(r0, min(rh, r0 + step))))
        jobs.append((600, panel_rule))
        self._jobs = jobs

    def draw(self, scr, full=False):
        if full:
            self.invalidate()
        if self._jobs:
            if not run_jobs(scr, self._jobs):
                return
            for w in (self.round_label, self.head_label, self.line_label):
                w.invalidate()
        if scr.stats()["ms"] < 56.0 or scr.stats()["ops"] == 0:
            self.foe_bar.draw(scr)
            self.hero_bar.draw(scr)
        painted = False
        for sv in self.hand:
            before = sv.cv._drawn
            self._draw_slot(scr, sv)
            painted = painted or sv.cv._drawn is not before
        for sv in self.foe[:self.foe_shown]:
            self._draw_slot(scr, sv)
        self._draw_links(scr, painted)
        self.foe_hp.draw(scr)
        self.name.draw(scr)
        self.round_label.draw(scr)
        self.head_label.draw(scr)
        self.line_label.draw(scr)
        self.hero_name.draw(scr)
        self.hero_hp.draw(scr)
        self.foe_chips.draw(scr)
        self.hero_chips.draw(scr)
        st = scr.stats()
        if st["ops"] == 0 or st["ms"] < 34.0:
            self.footer.draw(scr, self._full_pending)
            self._full_pending = False

    @staticmethod
    def _draw_slot(scr, sv):
        """A card that was never painted goes out as soon as the frame has room (the widget's own 45 ms check would
        paint one card per frame and the screen would take seconds to fill in)."""
        if sv.cv._drawn is None and not sv.gone and not sv.flip_steps:
            st = scr.stats()
            if st["ops"] == 0 or st["ms"] < 54.0:
                sv.cv.draw(scr, True)
            return
        sv.draw(scr)

    def settled(self):
        """True when every widget has been painted at least once since the last invalidate (nothing is deferred)."""
        if self._jobs or self._full_pending:
            return False
        if self.foe_bar._drawn is None or self.hero_bar._drawn is None:
            return False
        for lab in (self.name, self.foe_hp, self.hero_name, self.hero_hp, self.round_label, self.head_label):
            if lab._drawn is None:
                return False
        for sv in self.hand + self.foe[:self.foe_shown]:
            if not sv.gone and sv.cv._drawn is None:
                return False
        return not (self.foe_chips._jobs or self.hero_chips._jobs)

    def _draw_links(self, scr, repaint):
        if self.links == self._links_drawn and not (repaint and self.links):
            return
        if W.over_budget(scr, 400, 4):
            return
        icon = T.asset("ui_link")
        if self.links != self._links_drawn:
            for cx, _f in self._links_drawn:
                if (cx, _f) in self.links:
                    continue
                x = cx - icon.w // 2
                scr.fill_rect(x, LINK_Y, icon.w, icon.h, T.GROUND)
                for sv in self.hand:
                    r = sv.rect
                    if x < r[0] + r[2] and r[0] < x + icon.w and LINK_Y < r[1] + r[3] and r[1] < LINK_Y + icon.h:
                        sv.invalidate()
        for cx, f in self.links:
            scr.blit(icon, f, cx - icon.w // 2, LINK_Y)
        self._links_drawn = list(self.links)

    def invalidate_rect(self, rect):
        """Something painted over `rect` and went away (the stage side is the scene's job): repaint what lives there."""
        x, y, w, h = rect

        def hit(r):
            return x < r[0] + r[2] and r[0] < x + w and y < r[1] + r[3] and r[1] < y + h

        for sv in self.hand + self.foe:
            if hit(sv.rect):
                sv.invalidate()
        if hit((0, 0, 480, 30)):
            for wd in (self.name, self.foe_hp, self.foe_bar, self.foe_chips):
                wd.invalidate()
        if hit((self.rx, READING_Y, self.rw, READING_H)):
            self._build_jobs()
        if hit((0, 296, 480, 24)):
            for wd in (self.hero_name, self.hero_bar, self.hero_hp, self.hero_chips, self.footer):
                wd.invalidate()
        if self.links and hit((0, LINK_Y - 2, 480, 14)):
            self._links_drawn = []

    # ------------------------------------------------------------------ geometry for tutorial regions / restore
    def hint_width(self, scr_measure):
        total = 0
        for _l, label in self.footer.hints:
            total += 14 + scr_measure(label)[0] + 2 + self.footer.gap
        return total - self.footer.gap

    def region(self, key, scr_measure):
        if key == "hp_bar":
            return (BAR_HERO[0] - 4, BAR_HERO[1] - 4, BAR_HERO[2] + 8, BAR_HERO[3] + 8)
        if key == "enemy_row":
            return (self.foe_x0 - 4, FOE_Y - 6, 464 - self.foe_x0 + 8, T.CARD_SH + 10)
        if key == "spread":
            return (12, HAND_Y - 8, self.rx - 16, T.CARD_SH + 12)
        if key == "reading_bar":
            return (self.rx, READING_Y, self.rw, READING_H)
        if key == "footer":
            w = self.hint_width(scr_measure)
            return (T.INNER_R + 1 - w - 4, T.FOOTER_Y, w + 8, T.FOOTER_H)
        if key.startswith("slot:"):
            try:
                n = int(key[5:]) - 1
            except ValueError:
                return None
            if 0 <= n < len(self.hand):
                return self.hand[n].rect
        return None

    def rects(self):
        """(rect, widget list) for restore(): which widgets cover which area."""
        out = [((0, 0, 480, 30), [self.name, self.foe_hp, self.foe_bar]),
               ((self.rx, READING_Y, self.rw, READING_H), [self.round_label, self.head_label, self.line_label]),
               ((0, 296, 480, 24), [self.hero_name, self.hero_bar, self.hero_hp, self.hero_chips, self.footer])]
        return out


class ChainPanel:
    """Chain popup (187x45) with a tier-colored `CHAIN xN` tab, the readings so far and the newest reading as a big
    title. Painted in slices over a few frames (the whole panel is 8k slow pixels); hiding queues the backdrop
    restore with `restore(rect)` (the stage cuts it into strips)."""

    def __init__(self, restore, rect=T.BATTLE_POPUP):
        self.rect = rect
        self.restore = restore
        x, y, w, h = rect
        self.line = W.Label(x + 4, y + 7, w - 8, color=T.TEXT, bg=T.PANEL, align="c")
        self.title = W.Label(x + 4, y + 22, w - 8, font=T.TITLE, color=T.FOCUS, bg=T.PANEL, align="c")
        self.want = None            # (tier, chain)
        self.up = False
        self.jobs = []
        self._tab = None
        self._building = False

    def show(self, tier, line, title, chain):
        self.want = (tier, chain)
        self.line.set(line)
        self.title.set(title, T.tier_color(tier) if tier >= 1 else T.FOCUS)

    def hide(self):
        self.want = None

    def invalidate(self):
        self.up = False
        self.jobs = []
        self._tab = None
        self._building = False
        self.line.invalidate()
        self.title.invalidate()

    def tab_rect(self):
        x, y, w, h = self.rect
        tw = 72
        return (x + (w - tw) // 2, y - 7, tw, 13)

    def _build(self):
        x, y, w, h = self.rect
        jobs = []
        split = 22
        jobs.append((w * split, lambda scr: scr.fill_rect(x, y, w, split, T.PANEL)))
        jobs.append((w * (h - split), lambda scr: scr.fill_rect(x, y + split, w, h - split, T.PANEL)))

        def rule(scr):
            scr.rect(x, y, w, h, T.RULE_BRIGHT)
            scr.rect(x + 2, y + 2, w - 4, h - 4, T.RULE_DIM)
            W.corners(scr, x, y, w, h)

        jobs.append((700, rule))
        self.jobs = jobs
        self._building = True

    def _draw_tab(self, scr):
        tier, chain = self.want
        tx, ty, tw, th = self.tab_rect()
        scr.fill_rect(tx, ty, tw, th, T.PANEL)
        scr.rect(tx, ty, tw, th, T.AMBER1)
        scr.text_center(ty + (th - T.text_h(T.BODY)) // 2, "CHAIN x%d" % chain, T.tier_color(tier), T.PANEL,
                        cx=tx + tw // 2)
        self._tab = self.want

    def draw(self, scr):
        if self.want is None:
            if self.up or self._building:
                self.up = False
                self._building = False
                self.jobs = []
                x, y, w, h = self.rect
                self.restore((x - 1, y - 8, w + 2, h + 9))
                self.invalidate()
            return
        if not self.up:
            if not self._building:
                self._build()
            if not run_jobs(scr, self.jobs):
                return
            self.up = True
            self._building = False
            self._tab = None
            self.line.invalidate()
            self.title.invalidate()
        if self._tab != self.want and not W.over_budget(scr, 90 * 13, 3):
            self._draw_tab(scr)
        self.line.draw(scr)
        self.title.draw(scr)
