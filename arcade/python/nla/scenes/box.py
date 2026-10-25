"""Cardboard Box node. BoxScene(services, done) -> done(None) after the card is placed.

Zero's first-time tip, then a taped box waits (A Open). A: the box shakes, the flaps spring open, a card back rises
out of the mouth, flips over, and the card is revealed with its name and rules (C = Card Info). A on the revealed
card takes it: the Rules decide Spread / Box / duplicate / box full, and duplicates and a full Box go through the
Reward flow (nla.scenes.reward.place_card). `rules.run.open_box` is deterministic per step, so leaving and coming back
shows the same card.
"""

from nla import sfx, story
from nla.rules import cards
from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W

from . import path_art
from .path_common import NodeScene, detail_lines, place_card, wrap

CX, BASE = 240, 200
TOP = path_art.box_top(BASE)
CARD_X = CX - 24
CARD_FINAL_Y = TOP - 8 - 64
CARD_START_Y = TOP + 2
STAGE = (CX - 72, CARD_FINAL_Y - 2, 144, BASE - CARD_FINAL_Y + 6)
SHAKE_S, OPEN_S, RISE_S, FLIP_STEP_S = 0.75, 0.22, 0.55, 0.14
DETAIL_Y = 206


class _Stage:
    """The box and the card, drawn from a small state machine. Every animated frame touches only what changed."""

    def __init__(self, scene):
        self.scene = scene
        self.phase = "ready"        # ready shake open rise flip reveal
        self.t = 0.0
        self.card = None
        self.view = W.CardView(CARD_X, CARD_FINAL_Y)
        self._look = None
        self._rise_y = None         # card top y during the rise
        self._shake_dx = 0
        self._sparks = False

    rect = STAGE

    def invalidate(self):
        self._look = None
        self._rise_y = None
        self.view.invalidate()

    def start(self, card):
        self.card = card
        self.view.set_card(card)
        self.phase, self.t = "shake", 0.0

    def tick(self, dt):
        """Advance the state machine; returns True when the phase just became 'reveal'."""
        self.t += dt
        if self.phase == "shake" and self.t >= SHAKE_S:
            self.phase, self.t = "open", 0.0
        elif self.phase == "open" and self.t >= OPEN_S:
            self.phase, self.t = "rise", 0.0
        elif self.phase == "rise" and self.t >= RISE_S:
            self.phase, self.t = "flip", 0.0
        elif self.phase == "flip" and self.t >= FLIP_STEP_S * 3:
            self.phase, self.t = "reveal", 0.0
            return True
        return False

    @property
    def animating(self):
        return self.phase in ("shake", "open", "rise", "flip")

    # ------------------------------------------------------------------ drawing
    def _flip_step(self):
        return min(2, int(self.t / FLIP_STEP_S))

    def look(self):
        p = self.phase
        if p == "ready":
            return ("closed", 0)
        if p == "shake":
            return ("shake", 3 if int(self.t * 22) % 2 else -3)
        if p == "open":
            return ("open", 0 if self.t < OPEN_S / 2 else 1)
        if p == "rise":
            k = min(1.0, self.t / RISE_S)
            return ("rise", CARD_START_Y - int((CARD_START_Y - CARD_FINAL_Y) * (1 - (1 - k) * (1 - k))))
        if p == "flip":
            return ("flip", self._flip_step())
        return ("reveal",)

    def draw(self, scr, full=False):
        look = self.look()
        if not full and look == self._look:
            return
        kind = look[0]
        fresh = full or self._look is None         # the scene just repainted the ground under us
        if kind == "closed":
            path_art.box_closed(scr, CX, BASE)
        elif kind == "shake":
            if not fresh:
                self._erase_edges(scr)
            path_art.box_closed(scr, CX + look[1], BASE)
        elif kind == "open":
            self._open_box(scr, fresh, None if fresh else look[1])
        elif kind == "rise":
            self._draw_rise(scr, look[1], fresh)
        elif kind == "flip":
            self._draw_flip(scr, look[1], fresh)
        else:
            self._draw_reveal(scr, fresh)
        self._look = look

    @staticmethod
    def _erase_edges(scr):
        """The shaken box moved at most 3 px: clear the sliver it leaves on each side, then it is redrawn."""
        scr.fill_rect(CX - 52, TOP - 10, 8, BASE - TOP + 10, T.GROUND)
        scr.fill_rect(CX + 44, TOP - 10, 8, BASE - TOP + 10, T.GROUND)

    def _open_box(self, scr, fresh, part=None):
        """Opened box on the spot of the closed one, in two halves over two frames: the back (flaps and mouth), then
        the front (wall and folded flaps). part=None draws both. `fresh` means the ground was just repainted."""
        if part in (None, 0):
            if not fresh:
                self._erase_edges(scr)
                scr.fill_rect(CX - 52, TOP - 10, 104, 10, T.GROUND)     # the lid band and tape
            path_art.box_open_back(scr, CX, BASE)
        if part in (None, 1):
            path_art.box_open_front(scr, CX, BASE)

    def _draw_rise(self, scr, y, fresh):
        if fresh:
            self._open_box(scr, True)
            old = None
        else:
            old = self._rise_y
        if old is not None and old != y:
            bottom_old, bottom_new = old + 64, y + 64
            if bottom_new < TOP - 3:                # card fully above the mouth: strip it leaves behind
                scr.fill_rect(CARD_X, bottom_new, 48, min(bottom_old, TOP - 3) - bottom_new, T.GROUND)
                path_art.box_mouth(scr, CX, BASE)
        vis = min(64, TOP - 3 - y)
        if vis > 0:
            scr.asset_region(T.asset("card_back"), 0, CARD_X, y, 0, 0, 48, vis, bg=T.GROUND)
        self._rise_y = y

    def _draw_flip(self, scr, step, fresh):
        if fresh:
            self._open_box(scr, True)
        scr.fill_rect(CARD_X - 2, CARD_FINAL_Y, 52, 64, T.GROUND)
        if step == 0:
            scr.blit(T.asset("card_back"), 0, CARD_X, CARD_FINAL_Y, bg=T.GROUND)
        elif step == 1:                             # edge-on: a thin gold sliver
            scr.fill_rect(CX - 3, CARD_FINAL_Y, 6, 64, T.GOLD3)
            scr.fill_rect(CX - 1, CARD_FINAL_Y, 2, 64, T.GOLD4)
        else:
            self.view.draw(scr, True)
            spark = T.asset("ui_sparkle")
            for dx, dy, f in ((-40, 6, 0), (38, 18, 1), (-32, 50, 1), (44, 54, 0)):
                scr.blit(spark, f, CX + dx - 2, CARD_FINAL_Y + dy, bg=T.GROUND)

    def _draw_reveal(self, scr, fresh):
        if fresh:
            self._open_box(scr, True)
            self.view.draw(scr, True)
        else:
            self.view.draw(scr, False)


class BoxScene(NodeScene):
    def __init__(self, services, done=None):
        super().__init__(services, done)
        self.stage = _Stage(self)
        self._card = None
        self._end = None            # seconds until done() after the card is placed
        self.add_frame()
        self.add_title("Cardboard Box", y=6)
        for i, line in enumerate(story.NODE_TEXT["box"].desc.split("\n")):
            self.add_text(T.INNER_L, 34 + 15 * i, line, T.MUTED, w=T.INNER_W, align="c")
        self.add_widget(self.stage, STAGE)
        self.head = W.TextRun(T.INNER_L, DETAIL_Y)
        self.add_widget(self.head, (T.INNER_L, DETAIL_Y, T.INNER_W, 26), "reveal")
        self.lines = [W.Label(T.INNER_L, DETAIL_Y + 27 + 15 * i, T.INNER_W) for i in range(3)]
        for lab in self.lines:
            self.add_widget(lab, (T.INNER_L, lab.y, T.INNER_W, 15), "reveal")
        self.set_hints([("A", "Open"), ("C", "Info")])
        self.tip("first_box")

    def click_anywhere(self):
        return True             # one big target: click opens the box, then takes the card (right/middle = B/C as usual)

    def animating(self):
        return self.stage.animating

    def update(self, ctl, dt):
        if self.pump_tip():
            return
        if self._end is not None:
            self._end -= dt
            if self._end <= 0:
                self._end = None
                self.sv.save()
                self.finish(None)
            return
        if self.stage.animating:
            if self.stage.tick(dt):
                self._revealed()
            return
        if self._card is None:
            if ctl.a:
                self._open()
            elif ctl.c:
                self.sv.app.open(W.InfoOverlay("Cardboard Box", "Night Path", wrap(story.NODE_TEXT["box"].desc, 56)))
        elif ctl.a:
            self._take()
        elif ctl.c:
            self.sv.card_info(self._card)

    def _open(self):
        self._card = R.open_box(self.run)
        sfx.play("box_open")
        self.stage.start(self._card)
        self.set_hints([])

    def _revealed(self):
        sfx.play("reward")
        c = self._card
        self.head.set([(cards.card_title(c), T.LABEL, T.TITLE), 10, (cards.card_subtitle(c), T.TEXT)])
        text = cards.card_text(c)[:2]
        if c.charm:
            ch = cards.CHARMS[c.charm]
            text = text[:2] + ["%s: %s" % (ch.name, wrap(ch.text, 44)[0])]
        text = detail_lines(text)
        for k, lab in enumerate(self.lines):
            lab.set(text[k] if k < len(text) else "")
        self.set_hints([("A", "Take card"), ("C", "Info")])
        self.set_mode("reveal", (T.INNER_L, DETAIL_Y, T.INNER_W, 86))

    def _take(self):
        card = self._card
        status = R.take_card(self.run, card)
        self.set_hints([])
        place_card(self.sv, card, status, self._placed)

    def _placed(self, final):
        where = {"spread": "Added to your Spread.", "box": "Added to your Box.", "merged": "Merged! One more Star.",
                 "replaced": "Swapped in. +1 Treat for the old card.", "discarded": "You left the card behind."}
        self.lines[2].set(where.get(final, ""), T.HEAL)
        self.refresh_status()
        self._end = 0.9


def dev_box():
    from . import path_dev
    return path_dev.dev_box()
