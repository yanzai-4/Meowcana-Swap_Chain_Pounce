"""Cat Bed (GDD 13.6). CatBedScene(services, done) -> done(None) after one choice is resolved.

Domino sleeps curled on a cushion (code-drawn, Zzz drifting up, a candle beside him). Left/Right pick Nap (heal 30%
max HP), Sharpen (a card gets +1 Star, via the Card Picker) or Groom (wash a Curse off a card, or flip a card for good
when nothing is cursed). A chooses, C explains the highlighted option. There is nothing to back out of, so B does
nothing; after the choice a result line and a Continue button end the visit.
"""

from nla import sfx, story
from nla.rules import cards
from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.input import step

from . import path_art
from .path_common import CENTER_W, CENTER_X, NodeScene, Tile, hit

BED_XY = (140, 90)
TILE_Y, TILE_W, TILE_H = 178, 144, 66
TILE_X = (16, 168, 320)
ZONE = (16, 170, 448, 102)
CONTINUE = (180, 240, 120, 30)


class _Zzz:
    """Three letters that appear one after another above the sleeper, then start over."""

    RECT = (210, 62, 64, 44)

    def __init__(self, clock):
        self.clock = clock
        self._step = None

    @property
    def rect(self):
        return self.RECT

    def invalidate(self):
        self._step = None

    def draw(self, scr, full=False):
        n = int(self.clock() / 0.9) % 4
        if not full and n == self._step:
            return
        x, y, w, h = self.RECT
        scr.fill_rect(x, y, w, h, T.GROUND)
        if n >= 1:
            scr.text(x + 2, y + 28, "z", T.SILVER1, None)
        if n >= 2:
            scr.text(x + 16, y + 14, "Z", T.SILVER2, None)
        if n >= 3:
            scr.text(x + 30, y, "Z", T.MOON, None, T.BODY, 2)
        self._step = n


class _Candle:
    """ui_candle (2-frame flicker) on a flat ground fill."""

    def __init__(self, x, y, clock):
        self.x, self.y, self.clock = x, y, clock
        self._frame = None

    @property
    def rect(self):
        return (self.x, self.y, 5, 20)

    def invalidate(self):
        self._frame = None

    def draw(self, scr, full=False):
        f = int(self.clock() * 4) % 2
        if not full and f == self._frame:
            return
        scr.blit(T.asset("ui_candle"), f, self.x, self.y, bg=T.GROUND)
        self._frame = f


class CatBedScene(NodeScene):
    TOAST = (T.INNER_L, 250, T.INNER_W, 20)

    def __init__(self, services, done=None):
        super().__init__(services, done)
        run = self.run
        clock = lambda: self.sv.app.time if self.sv.app else 0.0   # noqa: E731
        self.sel = 0
        self.mode = "choose"
        self._after = None          # seconds until the result button accepts input (None = not in result)

        self.add_frame()
        self.add_title("Cat Bed", y=6)
        desc = story.NODE_TEXT["cat_bed"].desc.split("\n")
        for i, line in enumerate(desc):
            self.add_text(T.INNER_L, 32 + 15 * i, line, T.MUTED, w=T.INNER_W, align="c")
        for rect, fn, est in path_art.bed_parts(*BED_XY):
            self.add_static(rect, fn, est=est)
        self.add_widget(_Zzz(clock), _Zzz.RECT)
        candle = _Candle(112, 134, clock)
        self.add_widget(candle, candle.rect)
        self.add_static((102, 152, 26, 5), lambda scr: scr.fill_rect(102, 154, 26, 3, T.GOLD0))

        self.tiles = []
        for i in range(3):
            t = Tile(TILE_X[i], TILE_Y, TILE_W, TILE_H, fill=T.GROUND)
            self.tiles.append(t)
            self.add_widget(t, t.rect, "choose")
        self.res = [W.Label(CENTER_X, 180 + 17 * i, CENTER_W, T.BODY, T.TEXT, T.GROUND, "c") for i in range(2)]
        for lab in self.res:
            self.add_widget(lab, (T.INNER_L, lab.y, T.INNER_W, 15), "result")
        self.chips = W.Label(CENTER_X, 216, CENTER_W, T.BODY, T.HEAL, T.GROUND, "c")
        self.add_widget(self.chips, (T.INNER_L, 216, T.INNER_W, 15), "result")
        self.cont = Tile(*CONTINUE)
        self.cont.set(rows=[("Continue", T.ACCENT, T.BODY, 7, "c")], focused=True)
        self.add_widget(self.cont, self.cont.rect, "result")

        self._labels()
        self._focus()
        self.tip("first_catbed")

    # ------------------------------------------------------------------ content
    def _heal_amount(self):
        run = self.run
        return max(0, min(run.max_hp - run.hp, run.max_hp * 30 // 100))

    def _sharpen_targets(self):
        return [c for c in R.all_cards(self.run) if c.star < 2]

    def _cursed(self):
        return [c for c in R.all_cards(self.run) if cards.is_curse_charm(c.charm)]

    def _labels(self):
        gain = self._heal_amount()
        nap = [("Nap", T.LABEL, T.TITLE, 6, "c"), ("Heal %d HP" % gain, T.TEXT, T.BODY, 36, "c"),
               ("30% of max HP", T.MUTED, T.BODY, 51, "c")]
        sharp = [("Sharpen", T.LABEL, T.TITLE, 6, "c"), ("A card gets +1 {*}", T.TEXT, T.BODY, 36, "c"),
                 ("you pick which", T.MUTED, T.BODY, 51, "c")]
        if self._cursed():
            groom = [("Groom", T.LABEL, T.TITLE, 6, "c"), ("Remove a Curse", T.TEXT, T.BODY, 36, "c"),
                     ("from a card", T.MUTED, T.BODY, 51, "c")]
        else:
            groom = [("Groom", T.LABEL, T.TITLE, 6, "c"), ("Flip a card", T.TEXT, T.BODY, 36, "c"),
                     ("for good", T.MUTED, T.BODY, 51, "c")]
        self.tiles[0].set(rows=nap, dim=gain == 0)
        self.tiles[1].set(rows=sharp, dim=not self._sharpen_targets())
        self.tiles[2].set(rows=groom, dim=not R.all_cards(self.run))

    def _focus(self):
        for i, t in enumerate(self.tiles):
            t.set(focused=(i == self.sel))
        self.set_hints([("A", ("Nap", "Sharpen", "Groom")[self.sel]), ("C", "Info")])

    # ------------------------------------------------------------------ pointer
    WHEEL = ("left", "right")

    def click_anywhere(self):
        return self.mode == "result"

    def target_at(self, x, y):
        if self._locked:
            return None
        for i, t in enumerate(self.tiles):
            if hit(t.rect, x, y):
                return i
        return None

    def current_target(self):
        return self.sel

    def hover(self, target):
        self.sel = target
        self._focus()

    # ------------------------------------------------------------------ input
    def update(self, ctl, dt):
        self.toast.update(dt)
        if self.pump_tip():
            return
        if self.mode == "result":
            if ctl.a and (self._after is None or self._after <= 0):
                self.sv.save()
                self.finish(None)
            elif self._after is not None:
                self._after -= dt
            return
        if ctl.dx:
            self.sel = step(self.sel, ctl.dx, 3)
            self._focus()
        elif ctl.a:
            self._choose(self.sel)
        elif ctl.c:
            self._info()

    def _info(self):
        run = self.run
        gain = self._heal_amount()
        if self.sel == 0:
            body = ["Rest and restore 30% of your max HP.",
                    "HP %d/%d {>} %d/%d" % (run.hp, run.max_hp, run.hp + gain, run.max_hp)]
            title = "Nap"
        elif self.sel == 1:
            body = ["Pick a card. It gets +1 Star (up to 3 Stars).", "Stars make a card hit harder."]
            title = "Sharpen"
        elif self._cursed():
            body = ["Pick a Cursed card. The Curse is removed."]
            title = "Groom"
        else:
            body = ["No Curse to remove, so Groom flips a card for good:", "Upright becomes Reversed, and back."]
            title = "Groom"
        self.sv.app.open(W.InfoOverlay(title, "Cat Bed", body))

    def _choose(self, i):
        run = self.run
        if i == 0:
            gain = self._heal_amount()
            if gain == 0:
                self.toast.show("Already at full HP. Pick another!")
                return
            R.cat_bed(run, "nap")
            sfx.play("nap")
            sfx.play("heal")
            self._result(["Domino curls up and sleeps.", "Zzz... all rested."], "HP +%d" % gain, T.HEAL)
        elif i == 1:
            targets = self._sharpen_targets()
            if not targets:
                self.toast.show("Every card already has 3 Stars!")
                return
            self.sv.pick_card("SHARPEN: pick a card to add a Star", [c.uid for c in targets], self._sharpen_picked)
        else:
            targets = R.groom_targets(run)
            if not targets:
                self.toast.show("You have no cards to groom.")
                return
            prompt = "GROOM: pick a cursed card to clean" if self._cursed() else "GROOM: pick a card to flip"
            self.sv.pick_card(prompt, [c.uid for c in targets], self._groom_picked)

    def _sharpen_picked(self, uid):
        if uid is None:
            return
        c = R.find_card(self.run, uid)[2]
        name = cards.card_title(c) if c else "The card"
        if R.cat_bed(self.run, "sharpen", uid) == "ok":
            sfx.play("merge")
            self._result(["%s is sharper now." % name, "Claws out. One more Star."], "{*} %d" % (c.star + 1), T.ACCENT)
        else:
            self.toast.show("That card cannot get another Star.")

    def _groom_picked(self, uid):
        if uid is None:
            return
        c = R.find_card(self.run, uid)[2]
        if c is None:
            return
        was_curse = cards.is_curse_charm(c.charm)
        name = cards.card_title(c)
        if R.cat_bed(self.run, "groom", uid) != "ok":
            self.toast.show("Pick a cursed card.")
            return
        if was_curse:
            sfx.play("heal")
            self._result(["%s is clean again." % name, "The Curse washed right off."], "Curse removed", T.HEAL)
        else:
            sfx.play("flip")
            self._result(["%s is flipped for good." % name,
                          "Now %s." % ("Reversed" if c.reversed else "Upright")], "Flipped", T.ACCENT)

    def _result(self, lines, chip, color):
        for i, lab in enumerate(self.res):
            lab.set(lines[i] if i < len(lines) else "")
        self.chips.set(chip, color)
        self.refresh_status()
        self.set_hints([("A", "Continue")])
        self._after = 0.3
        self.set_mode("result", ZONE)


def dev_catbed():
    from . import path_dev
    return path_dev.dev_catbed()
