"""Pick 1 of 3 (GDD 6.4): rewards, tutorial prizes and Fate's Draft.

    RewardScene(services, options, done, title="Pick 1 of 3", skip_treats=3)        done(Card | None)
    place_card(services, card, status, done)                                         for scenes that gain a card

Three big cards are dealt face-down, then flipped one after another. Left/right moves over the cards and the Skip button
(Skip gives `skip_treats` Treats; 0 hides it), up/down hops between the cards and Skip, A takes, B jumps to Skip, C is Card
Info. The pick goes through Rules `take_card`: a Duplicate asks Merge / Keep Both (B = Keep Both), a full Box opens the Card
Picker with "Skip New Card", and the card then flies to the Spread or Box slot it landed in. Reports `pick_reward` once
the choice is final and answers region("reward"). Dev harnesses: `dev_reward()` (a duplicate in the Spread),
`dev_reward_full()` (full Box). `place_card` is the same duplicate / box-full logic without the animation.
"""

from nla import sfx
from nla.rules import cards, run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene

from .spread_board import Board, DetailPanel, PANEL_RECT, box_x, hit, hover_allowed, inside, slot_x, text_rows

BIG = 2
BIG_W, BIG_H = (T.CARD_W - 4 + 4) * BIG, T.CARD_H * BIG        # 96 x 128
CARD_Y = 50
CARD_GAP = 40
SHAKE_S = 0.25
DEAL_T = (0.15, 0.30, 0.45)           # when card i appears face-down
FLIP_T0, FLIP_STEP, FLIP_MID = 0.75, 0.30, 0.10
FLY_FRAMES = 10
FLY_DT = 0.05
LAND_S = 1.8
PANEL_A = (16, 204, 448, 48)
SKIP_Y = 258
SKIP_RECT = (180, SKIP_Y, 120, 28)


def _card_x(i, n):
    total = n * BIG_W + (n - 1) * CARD_GAP
    return (T.SCREEN_W - total) // 2 + i * (BIG_W + CARD_GAP)


def _sub(card):
    s = cards.card_subtitle(card)
    if card.charm:
        s += " {.} " + cards.CHARMS[card.charm].name
    return s


class DuplicateOverlay(W.Overlay):
    """Merge / Keep Both. Cursor starts on Merge; B (or A on the second button) keeps both; C shows Card Info."""

    def __init__(self, new, owned, owned_zone):
        super().__init__()
        self.new, self.owned, self.zone = new, owned, owned_zone
        self.rect = (60, 54, 360, 176)
        x, y, w, h = self.rect
        self.focus = 0
        self.rows = 0
        self._text_done = False
        self.merge_btn = W.Button(x + 50, y + h - 38, 110, 26, "Merge", bg=T.PANEL)
        self.keep_btn = W.Button(x + w - 50 - 110, y + h - 38, 110, 26, "Keep Both", bg=T.PANEL)
        self.new_view = W.CardView(x + 62, y + 36, bg=T.PANEL)
        self.new_view.set_card(new)
        self.old_view = W.CardView(x + w - 62 - T.CARD_W, y + 36, bg=T.PANEL)
        self.old_view.set_card(owned)
        self._c = 0
        self.busy = True

    def update(self, ctl, dt):
        if ctl.dx:
            self.focus = 1 - self.focus
        if ctl.c:
            self._c += 1
            self._app.card_info(self.new if self._c % 2 else self.owned)
        elif ctl.b:
            self.focus = 1
            self.close("keep")
        elif ctl.a:
            self.close("merge" if self.focus == 0 else "keep")

    def pointer(self, x, y, kind):
        """Mouse: hovering a button focuses it, clicking one presses it, right = B, middle = C."""
        if kind == "right":
            return "b"
        if kind == "middle":
            return "c"
        if kind not in ("move", "up"):
            return None
        for i, btn in enumerate((self.merge_btn, self.keep_btn)):
            if inside(x, y, (btn.x, btn.y, btn.w, btn.h)):
                if hover_allowed(self._app):
                    self.focus = i
                return "a" if kind == "up" and self.focus == i else None
        return None

    def draw(self, scr, full=False):
        x, y, w, h = self.rect
        if full:
            self.rows = 0
            self._text_done = False
            for wd in (self.merge_btn, self.keep_btn, self.new_view, self.old_view):
                wd.invalidate()
        if self.rows < h:
            n = min(h - self.rows, max(1, 6500 // w))
            scr.fill_rect(x, y + self.rows, w, n, T.PANEL)
            self.rows += n
            if self.rows >= h:
                scr.rect(x, y, w, h, T.RULE_BRIGHT)
                W.corners(scr, x - 1, y - 1, w + 2, h + 2)
            return
        if not self._text_done:
            scr.text_center(y + 10, "Duplicate", T.LABEL, T.PANEL, T.TITLE, cx=x + w // 2)
            lab = "In your Spread" if self.zone == "s" else "In your Box"
            scr.text_center(y + 104, "New", T.TEXT, T.PANEL, cx=self.new_view.x + T.CARD_W // 2)
            scr.text_center(y + 104, lab, T.TEXT, T.PANEL, cx=self.old_view.x + T.CARD_W // 2)
            stars = min(self.owned.star + 2, 3)
            W.rich(scr, x + w // 2 - W.rich_w(scr, "Merge: {*}%d" % stars) // 2, y + 66, "Merge: {*}%d" % stars,
                   T.ACCENT, T.PANEL)
            scr.blit(T.asset("ui_arrow"), 1, x + w // 2 - 3, y + 54, bg=T.PANEL)
            self._text_done = True
            return
        self.new_view.draw(scr, full)
        self.old_view.draw(scr, full)
        self.merge_btn.set(focused=self.focus == 0)
        self.keep_btn.set(focused=self.focus == 1)
        self.merge_btn.draw(scr, full)
        self.keep_btn.draw(scr, full)
        self.busy = False


class RewardScene(Scene):
    def __init__(self, services, options, done, title="Pick 1 of 3", skip_treats=3):
        super().__init__(done)
        self.sv = services
        self.options = list(options)
        self.title = title
        self.skip_treats = skip_treats
        n = len(self.options)
        self.n = n
        self.views = [W.CardView(_card_x(i, n), CARD_Y) for i in range(n)]
        for v, c in zip(self.views, self.options):
            v.set_card(c)
        self.cursor = W.Cursor()
        self.skip_btn = W.Button(*SKIP_RECT, "Skip +%d Treats" % skip_treats)
        self.detail = DetailPanel(PANEL_A)
        self.footer = W.Footer()
        self.board = Board(len(self.run.spread), len(self.run.box), power=False)
        self.fly = {False: W.CardView(0, 0), True: W.CardView(0, 0, small=True)}
        # state
        self.state = "deal"
        self.t = 0.0
        self.pos = 0                       # 0..n-1 cards, n = Skip
        self.last_card = 0
        self.want = ["none"] * n
        self.drawn = [None] * n
        self.phase = "A"
        self._phase_drawn = None
        self._note = None
        self._note_t = 0.0
        self._detail_key = None
        self._footer_key = None
        self._shake_t = 0.0
        self._later = None
        self._result = None
        self._fly_plan = None
        self._override = {}
        self._land_t = 0.0
        self._title_now = title
        self._caption = None
        self._glow = None

    # ------------------------------------------------------------------ helpers
    @property
    def run(self):
        return self.sv.run

    @property
    def has_skip(self):
        return self.skip_treats > 0

    def region(self, key):
        if key == "reward":
            first, last = self.views[0], self.views[-1]
            return (first.x - 6, CARD_Y - 6, last.x + BIG_W + 6 - (first.x - 6), BIG_H + 28)
        return None

    def shake(self):
        """A blocked input: a gentle shake of the cursor (Flow may call this when it masks a key)."""
        self._shake_t = SHAKE_S
        sfx.play("blocked")

    def _queue(self, fn):
        self._later = fn

    # ------------------------------------------------------------------ pointer (mouse)
    def _target(self, x, y):
        """Cursor position (0..n-1 = card, n = Skip) of what is drawn under the pointer, else None."""
        for i, v in enumerate(self.views):
            if inside(x, y, (v.x, CARD_Y, BIG_W, BIG_H)):
                return i
        if self.has_skip and inside(x, y, SKIP_RECT):
            return self.n
        return None

    def pointer(self, x, y, kind):
        """Mouse: hover = cursor, left click = A (take / Skip), right = B, middle = C."""
        if kind == "right":
            return "b"
        if kind not in ("move", "up", "middle"):
            return None
        if self.state != "choose":
            return "a" if kind == "up" else None          # skip the deal / landing animation like A does
        tgt = self._target(x, y)
        if tgt is not None and tgt != self.pos and hover_allowed(self.app):
            self.pos = tgt
            self._moved()
            sfx.play("move")
        if kind == "move" or tgt is None or tgt != self.pos:
            return None
        return "c" if kind == "middle" else "a"

    # ------------------------------------------------------------------ update
    def update(self, ctl, dt):
        if self._later is not None and not self.app.overlays:
            fn, self._later = self._later, None
            fn()
            return
        if self._shake_t > 0:
            self._shake_t = max(0.0, self._shake_t - dt)
        if self._note_t > 0:
            self._note_t -= dt
            if self._note_t <= 0:
                self._note = None
                self._detail_key = None
        self.busy = self._shake_t > 0
        st = self.state
        if st == "deal":
            self._update_deal(ctl, dt)
        elif st == "choose":
            self._update_choose(ctl)
        elif st == "fly":
            self._update_fly(dt)
        elif st == "landed":
            self._land_t -= dt
            self.busy = False
            if ctl.a or ctl.b or self._land_t <= 0:
                self._finish_pick()
        elif st == "skipped":
            self._land_t -= dt
            if ctl.a or ctl.b or self._land_t <= 0:
                self._finish_pick()

    def _update_deal(self, ctl, dt):
        self.t += dt
        n = self.n
        if ctl.a or ctl.b:
            self.t = 9.0
        for i in range(n):
            t0 = FLIP_T0 + FLIP_STEP * i
            was = self.want[i]
            if self.t >= t0 + FLIP_MID:
                self.want[i] = "face"
            elif self.t >= t0:
                self.want[i] = "sliver"
            elif self.t >= DEAL_T[min(i, 2)]:
                self.want[i] = "back"
            if self.want[i] != was:
                if self.want[i] != "face":
                    sfx.play("deal" if self.want[i] == "back" else "flip")
        self.busy = True
        if self.want == ["face"] * n:
            self.state = "choose"
            self._detail_key = None
            self.busy = False

    def _update_choose(self, ctl):
        n = self.n
        if ctl.dx:
            slots = n + (1 if self.has_skip else 0)
            self.pos = (self.pos + ctl.dx) % slots
            self._moved()
        elif ctl.dy:
            if self.has_skip:
                self.pos = n if self.pos < n else self.last_card
                self._moved()
        if ctl.a:
            if self.pos == n:
                self._skip()
            else:
                self._take(self.pos)
        elif ctl.b:
            if self.has_skip and self.pos != n:
                self.pos = n
                self._moved()
            else:
                self.shake()
        elif ctl.c:
            if self.pos < n:
                self.sv.card_info(self.options[self.pos])
            else:
                self._note = "Skip the cards and take %d Treats instead." % self.skip_treats
                self._note_t = 3.0
                self._detail_key = None

    def _moved(self):
        if self.pos < self.n:
            self.last_card = self.pos
        self._note = None
        self._detail_key = None

    # ------------------------------------------------------------------ taking a card
    def _skip(self):
        self.run.treats += self.skip_treats
        sfx.play("coin")
        self.sv.report("pick_reward")
        self.state = "skipped"
        self._result = None
        self._land_t = 1.0
        self._note = "Skipped. +%d Treats!" % self.skip_treats
        self._note_t = 99.0
        self._detail_key = None

    def _take(self, i):
        card = self.options[i]
        self._card = card
        self._resolve(card, R.take_card(self.run, card))

    def _resolve(self, card, status):
        if status in ("spread", "box"):
            zone, idx = self._locate(card)
            self._start_fly(card, zone, idx, "add")
        elif status == "duplicate":
            self.state = "wait"
            R.arm_tip(self.run, "first_merge")
            self.sv.tip("first_merge", lambda: self._queue(lambda: self._open_duplicate(card)))
        else:                                                      # "box_full"
            self.state = "wait"
            R.arm_tip(self.run, "first_box_full")
            self.sv.tip("first_box_full", lambda: self._queue(lambda: self._open_picker(card)))

    def _locate(self, card):
        zone, idx, _ = R.find_card(self.run, card.uid)
        return ("s" if zone == "spread" else "b"), idx

    def _open_duplicate(self, card):
        target = R.duplicate_targets(self.run, card)[0]
        zone = R.find_card(self.run, target.uid)[0]
        ov = DuplicateOverlay(card, target, "s" if zone == "spread" else "b")
        self.app.open(ov, lambda res: self._queue(lambda: self._dup_choice(card, target, res)))

    def _dup_choice(self, card, target, res):
        if res == "merge":
            old = cards.Card(target.def_id, target.reversed, target.star, target.charm, target.uid)
            R.merge(self.run, card, target.uid)
            zone, idx = self._locate(target)
            self._start_fly(card, zone, idx, "merge", before=old)
        else:
            status = R.keep_both(self.run, card)
            if status == "box_full":
                self._resolve(card, status)
            else:
                zone, idx = self._locate(card)
                self._start_fly(card, zone, idx, "add")

    def _open_picker(self, card):
        sel = [c.uid for c in self.run.spread + self.run.box if c is not None]
        self.sv.pick_card("Box full: drop a card (+1 Treat)", sel, lambda uid: self._picked(card, uid),
                          "Skip New Card")

    def _picked(self, card, uid):
        if uid is None:
            self.sv.report("pick_reward")
            self.state = "skipped"
            self._result = None
            self._land_t = 1.2
            self._note = "You left the new card behind."
            self._note_t = 99.0
            self._detail_key = None
            return
        old = R.find_card(self.run, uid)[2]
        if R.needs_confirm(old):
            self.app.open(W.Confirm("Drop %s?\nIt is gone for good." % cards.card_title(old), None, None,
                                    yes="Drop", no="Keep"),
                          lambda yes: self._queue(lambda: self._drop(card, old) if yes else self._open_picker(card)))
        else:
            self._drop(card, old)

    def _drop(self, card, old):
        zone, idx, _ = R.find_card(self.run, old.uid)
        R.replace_card(self.run, card, old.uid)
        self._start_fly(card, "s" if zone == "spread" else "b", idx, "replace", before=old)

    # ------------------------------------------------------------------ fly
    def _start_fly(self, card, zone, idx, kind, before=None):
        """Switch to the Spread/Box strip and fly `card` into slot (zone, idx)."""
        self._override = {}
        if kind == "add":
            self._override[(zone, idx)] = None
        elif before is not None:
            self._override[(zone, idx)] = before
        self.board.show(*self._lists(), dim=())
        small = zone == "b"
        self.fly[small].set_card(card)
        v = (self.board.box if small else self.board.slots)[idx]
        self._fly_plan = dict(card=card, zone=zone, idx=idx, kind=kind, small=small, step=0, acc=0.0,
                              sx=(T.SCREEN_W - v.w) // 2, sy=34, dx=v.x, dy=v.y)
        self._fly_old = None
        self.state = "fly"
        self.phase = "B"
        self._title_now = {"add": "Card added", "merge": "Cards merged", "replace": "Card swapped"}[kind]
        self.sv.report("pick_reward")
        sfx.play("merge" if kind == "merge" else "reward")
        self.busy = True

    def _lists(self):
        sp, bx = list(self.run.spread), list(self.run.box)
        for (zone, idx), c in self._override.items():
            (sp if zone == "s" else bx)[idx] = c
        return sp, bx

    def _update_fly(self, dt):
        p = self._fly_plan
        self.busy = True
        if self._phase_drawn != "B":
            return                                   # wait for the strip to be painted
        p["acc"] += dt
        if p["acc"] >= FLY_DT and p["step"] < FLY_FRAMES:
            p["acc"] = 0.0
            p["step"] += 1
        if p["step"] >= FLY_FRAMES and p["acc"] >= 0:
            p["done"] = True

    def _land(self):
        p = self._fly_plan
        self._override = {}
        self.board.show(*self._lists())
        v = (self.board.box if p["small"] else self.board.slots)[p["idx"]]
        v.glow = True
        self._glow = v
        self._caption = p
        self._detail_key = None
        self.state = "landed"
        self._land_t = LAND_S
        self._result = p["card"]

    def _finish_pick(self):
        if self._glow is not None:
            self._glow.glow = False
        self.state = "done"
        self.finish(self._result)

    # ------------------------------------------------------------------ drawing
    def resume(self, result):
        self._phase_drawn = None

    def draw(self, scr, full):
        if full or self._phase_drawn != self.phase:
            self._paint_phase(scr)
        if self.phase == "A":
            self._draw_a(scr, full)
        else:
            self._draw_b(scr, full)
        if scr.stats()["ms"] > 45.0:
            self.busy = True

    def _panel_rect(self):
        return PANEL_A if self.phase == "A" else PANEL_RECT

    def _statics(self):
        """(rect, paint(scr)) for every static piece of the current phase."""
        panel = self._panel_rect()
        return [
            ((100, 10, 280, 24), lambda scr: scr.text_center(12, self._title_now, T.LABEL, T.GROUND, T.TITLE)),
            ((T.INNER_L, 36, T.INNER_W, 5), lambda scr: W.divider(scr, T.INNER_L, T.INNER_R, 38)),
            ((T.INNER_L, T.FOOTER_DIV_Y - 2, T.INNER_W, 5),
             lambda scr: W.divider(scr, T.INNER_L, T.INNER_R, T.FOOTER_DIV_Y, mid=False)),
            ((panel[0] - 1, panel[1] - 1, panel[2] + 2, panel[3] + 2), lambda scr: W.panel(scr, *panel)),
        ]

    def _frame(self, scr):
        scr.rect(2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4, T.RULE_DIM)
        W.corners(scr, 2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4)

    def _paint_phase(self, scr):
        scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
        self._frame(scr)
        for _, paint in self._statics():
            paint(scr)
        self.detail = DetailPanel(self._panel_rect())
        self._phase_drawn = self.phase
        self._invalidate_all()

    def _invalidate_all(self):
        self._detail_key = None
        self._footer_key = None
        for wd in (self.cursor, self.skip_btn, self.detail, self.footer, self.board):
            wd.invalidate()
        self.drawn = [None] * self.n
        for v in self.fly.values():
            v.invalidate()
        self._fly_old = None

    def restore(self, scr, rect):
        """An overlay closed over `rect`: repaint just what lay under it (cheap for the tutorial arrow)."""
        x, y, w, h = rect
        x, y = max(0, x - 2), max(0, y - 2)
        w, h = min(T.SCREEN_W - x, w + 4), min(T.SCREEN_H - y, h + 4)
        rect = (x, y, w, h)
        if w * h > 20000 or self._phase_drawn != self.phase:
            self.draw(scr, True)
            return
        scr.fill_rect(x, y, w, h, T.GROUND)
        if not (8 <= x and 8 <= y and x + w <= 472 and y + h <= 312):
            self._frame(scr)
        parts = [rect]
        for r, paint in self._statics():
            if hit(rect, r):
                paint(scr)
                parts.append(r)
        for r in parts:
            for i, v in enumerate(self.views):
                if hit(r, (v.x - 4, v.y - 4, BIG_W + 8, BIG_H + 22)):
                    self.drawn[i] = None
            if hit(r, SKIP_RECT):
                self.skip_btn.invalidate()
            if hit(r, (30, 204, 420, 48)) or hit(r, (30, 246, 420, 48)):
                self.detail.invalidate()
            if hit(r, (0, T.FOOTER_DIV_Y, T.SCREEN_W, 24)):
                self.footer.invalidate()
            self.cursor.invalidate()
            self.board.invalidate(r)
        self._detail_key = None
        self.draw(scr, False)

    # -- phase A: the three big cards
    def _draw_a(self, scr, full):
        n = self.n
        dx = (-2, 2, -1, 1)[int(self._shake_t * 40) % 4] if self._shake_t > 0 else 0
        if self.state == "choose" and self.pos < n:
            v = self.views[self.pos]
            self.cursor.to(v.x + dx, CARD_Y, BIG_W, BIG_H, paw=True)
        else:
            self.cursor.hide()
        self.cursor.draw(scr, full)
        for i, v in enumerate(self.views):
            want = self.want[i]
            if self.drawn[i] == want and not full:
                continue
            if want == "none":
                self.drawn[i] = want
                continue
            if not full and W.over_budget(scr, BIG_W * BIG_H, 2):
                break
            if want == "back":
                scr.blit(T.asset("card_back"), 0, v.x, v.y, scale=BIG, bg=T.GROUND)
            elif want == "sliver":
                scr.fill_rect(v.x, v.y, BIG_W, BIG_H, T.GROUND)
                scr.fill_rect(v.x + 38, v.y + 2, 20, BIG_H - 4, T.NIGHT3)
                scr.rect(v.x + 38, v.y + 2, 20, BIG_H - 4, T.GOLD2)
            else:
                v.draw_scaled(scr, v.x, v.y, BIG)
            self.drawn[i] = want
        if self.has_skip:
            self.skip_btn.set(focused=self.state == "choose" and self.pos == n, disabled=self.state != "choose")
            self.skip_btn.draw(scr, full)
        self._refresh_detail_a()
        self.detail.draw(scr, full)
        self._refresh_footer()
        self.footer.draw(scr, full)

    def _refresh_detail_a(self):
        key = (self.state, self.pos, self._note)
        if key == self._detail_key:
            return
        self._detail_key = key
        if self._note is not None:
            self.detail.set(None, "", [[(self._note, T.ACCENT)]])
        elif self.state == "choose" and self.pos < self.n:
            c = self.options[self.pos]
            self.detail.set(cards.card_title(c), _sub(c), text_rows(cards.card_text(c)))
        elif self.state == "choose":
            self.detail.set("Skip", "+%d Treats" % self.skip_treats,
                            [[("Treats buy cards and services at Spots' Stall.", T.MUTED)]])
        else:
            self.detail.set(None, "", [[]])

    # -- phase B: the Spread/Box strip
    def _draw_b(self, scr, full):
        if self.state == "fly" and self._phase_drawn == "B":
            self._draw_flight(scr, full)
        else:
            self.board.draw(scr, full)
        self._refresh_detail_b()
        self.detail.draw(scr, full)
        self._refresh_footer()
        self.footer.draw(scr, full)

    def _draw_flight(self, scr, full):
        p = self._fly_plan
        views = self.board.slots + self.board.box
        if full or p["step"] == 0 and self._fly_old is None:
            self.board.draw(scr, True)
        k = p["step"] / FLY_FRAMES
        e = 1 - (1 - k) * (1 - k)
        fv = self.fly[p["small"]]
        x = int(p["sx"] + (p["dx"] - p["sx"]) * e)
        y = int(p["sy"] + (p["dy"] - p["sy"]) * e)
        if (x, y) == self._fly_old and not full:
            if p.get("done"):
                self._fly_old = None
                self._land()
            return
        if self._fly_old is not None and not full:
            ox, oy = self._fly_old
            old = (ox, oy, fv.w, fv.h)
            scr.fill_rect(*old, T.GROUND)
            for v in views:
                covered = x <= v.x and y <= v.y and v.x + v.w <= x + fv.w and v.y + v.h <= y + fv.h
                if hit(old, (v.x, v.y, v.w, v.h)) and not covered:
                    v.draw(scr, True)
        fv.x, fv.y = x, y
        fv.draw(scr, True)
        self._fly_old = (x, y)
        if p["step"] >= FLY_FRAMES:
            p["done"] = True

    def _refresh_detail_b(self):
        key = (self.state, self._caption is not None and id(self._caption))
        if key == self._detail_key:
            return
        self._detail_key = key
        p = self._caption
        if self.state != "landed" or p is None:
            self.detail.set(None, "", [[]])
            return
        card = p["card"]
        where = "your Spread" if p["zone"] == "s" else "the Box"
        if p["kind"] == "merge":
            tgt = (self.run.spread if p["zone"] == "s" else self.run.box)[p["idx"]]
            self.detail.set(cards.card_title(tgt), "Merged! Now {*}%d" % (tgt.star + 1), text_rows(cards.card_text(tgt)))
        elif p["kind"] == "replace":
            self.detail.set(cards.card_title(card), "Swapped in. +1 Treat", text_rows(cards.card_text(card)))
        elif p["zone"] == "b" and not self.run.flags.get("to_box"):
            self.detail.set(cards.card_title(card), "Added to the Box",
                            [[("Your Spread is full, so it waits in the Box.", T.MUTED)]])
        else:
            self.detail.set(cards.card_title(card), "Added to " + where, text_rows(cards.card_text(card)))

    def _refresh_footer(self):
        run = self.run
        if self.phase == "B":
            hints = [("A", "Continue")] if self.state == "landed" else []
        elif self.state == "choose":
            hints = [("A", "Skip" if self.pos == self.n else "Take")]
            if self.has_skip and self.pos != self.n:
                hints.append(("B", "To Skip"))
            hints.append(("C", "Info"))
        elif self.state == "skipped":
            hints = [("A", "Continue")]
        else:
            hints = []
        left = [("name", "Domino"), ("treat", "Treats %d" % run.treats)]
        key = (tuple(hints), tuple(left))
        if key != self._footer_key:
            self._footer_key = key
            self.footer.set_hints(hints)
            self.footer.set_left(left)


# =========================================================================== shared logic for other scenes
def place_card(services, card, status, done):
    """Finish a card gain after `R.take_card(run, card)` returned `status` (no animation, no scene needed).

    "spread" / "box": nothing to do. "duplicate": Merge / Keep Both. "box_full": Card Picker with Skip New Card.
    `done(final)` gets "spread" | "box" | "merged" | "replaced" | "discarded"."""
    run = services.run
    app = services.app

    def keep():
        st = R.keep_both(run, card)
        if st == "box_full":
            full()
        else:
            done(st)

    def duplicate():
        target = R.duplicate_targets(run, card)[0]
        zone = R.find_card(run, target.uid)[0]

        def chosen(res):
            if res == "merge":
                R.merge(run, card, target.uid)
                done("merged")
            else:
                keep()

        R.arm_tip(run, "first_merge")
        services.tip("first_merge", lambda: app.open(DuplicateOverlay(card, target, "s" if zone == "spread" else "b"),
                                                      chosen))

    def full():
        def picked(uid):
            if uid is None:
                done("discarded")
                return
            old = R.find_card(run, uid)[2]

            def drop():
                R.replace_card(run, card, uid)
                done("replaced")

            if R.needs_confirm(old):
                app.open(W.Confirm("Drop %s?\nIt is gone for good." % cards.card_title(old), None, None,
                                   yes="Drop", no="Keep"), lambda yes: drop() if yes else full())
            else:
                drop()

        def open_picker():
            sel = [c.uid for c in run.spread + run.box if c is not None]
            services.pick_card("Box full: drop a card (+1 Treat)", sel, picked, "Skip New Card")

        R.arm_tip(run, "first_box_full")
        services.tip("first_box_full", open_picker)

    if status == "duplicate":
        duplicate()
    elif status == "box_full":
        full()
    else:
        done(status)


# =========================================================================== dev harnesses
def dev_reward():
    """Three options; the first is a copy of the Spread's Water 3 (Duplicate -> Merge / Keep Both)."""
    from .dev_spread import StubServices, dev_run, make_app
    run = dev_run()
    sv = StubServices(run)
    opts = [cards.Card(22, False, 0, 0), cards.Card(7, True, 0, 0), cards.Card(31, False, 0, 4)]
    return make_app(sv, lambda: RewardScene(sv, opts, lambda c: print("took", c)))


def dev_reward_full():
    """Spread and Box both full: any new card ends in the Card Picker with Skip New Card."""
    from .dev_spread import StubServices, dev_run, make_app
    run = dev_run()
    for k in range(len(run.box)):
        if run.box[k] is None:
            run.box[k] = cards.Card(10 + k, False, 0, 0, run.next_uid)
            run.next_uid += 1
    run.spread += [cards.Card(30, False, 0, 0, run.next_uid), cards.Card(33, False, 0, 0, run.next_uid + 1)]
    run.next_uid += 2
    sv = StubServices(run)
    opts = [cards.Card(5, False, 0, 0), cards.Card(26, True, 0, 0), cards.Card(38, False, 0, 0)]
    return make_app(sv, lambda: RewardScene(sv, opts, lambda c: print("took", c)))


def dev_reward_box():
    """Spread full, Box has room: the pick flies into the Box."""
    from .dev_spread import StubServices, dev_run, make_app
    run = dev_run()
    run.spread += [cards.Card(30, False, 0, 0, run.next_uid), cards.Card(33, False, 0, 0, run.next_uid + 1)]
    run.next_uid += 2
    sv = StubServices(run)
    opts = [cards.Card(5, False, 0, 0), cards.Card(26, True, 0, 0), cards.Card(38, False, 0, 0)]
    return make_app(sv, lambda: RewardScene(sv, opts, lambda c: print("took", c)))


def dev_place():
    """Exercises place_card with a Duplicate (a second Water 3) on a bare screen: A = go again."""
    from .dev_spread import StubServices, dev_run, make_app

    class Demo(Scene):
        def __init__(self, sv):
            super().__init__()
            self.sv, self.msg, self.fresh = sv, "press A", True

        def update(self, ctl, dt):
            if ctl.a and not self.app.overlays:
                card = cards.Card(22, False, 0, 0)
                status = R.take_card(self.sv.run, card)
                self.msg = "status: " + status
                self.fresh = True
                place_card(self.sv, card, status, self._done)

        def _done(self, final):
            self.msg = "final: " + final
            self.fresh = True

        def draw(self, scr, full):
            if full or self.fresh:
                scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
                scr.text_center(140, self.msg, T.LABEL, T.GROUND, T.TITLE)
                self.fresh = False

    sv = StubServices(dev_run())
    return make_app(sv, lambda: Demo(sv))
