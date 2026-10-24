"""Level Up (GDD 13.2). LevelUpScene(services, done) -> done(None) once every pending Level Up is spent.

Three prize plates from `rules.run.level_up_options`, each with an icon, a name, and a one-line effect preview. Left/Right
choose, A takes the prize, C explains it with the exact numbers. Sharpen Claws opens the Card Picker first; cancelling the
picker returns here with nothing spent. There is nothing to back out of, so B does nothing. If more Level Ups are pending
the next set of options follows after a short confirmation.
"""

from nla.rules import cards
from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.input import step

from . import path_art
from .path_common import NodeScene, Tile, wrap

TILE_Y, TILE_W, TILE_H = 82, 140, 150
TILE_X = (16, 170, 324)
ZONE = (16, 76, 448, 162)
NAMES = {key: info[0] for key, info in R.LEVEL_UP_INFO.items()}


def _stars_icon(scr, x, y, w, h, fill, dim):
    """Three Stars (the card rating Sharpen Claws raises)."""
    a = T.asset("ui_star")
    for k in range(3):
        scr.blit(a, 0, x + w // 2 - 33 + 24 * k, y + 22 - 4 * (k == 1), scale=4, bg=fill, dim=dim)


def _slot_icon(scr, x, y, w, h, fill, dim):
    """A card-sized dotted outline with a plus sign: one more Spread Slot."""
    cx, top = x + w // 2, y + 10
    scr.dotted_rect(cx - 15, top, 30, 44, T.NIGHT4 if not dim else T.NIGHT3)
    scr.fill_rect(cx - 6, top + 21, 12, 3, T.AMBER3)
    scr.fill_rect(cx - 1, top + 16, 3, 13, T.AMBER3)


def _box_icon(scr, x, y, w, h, fill, dim):
    path_art.box_closed(scr, x + w // 2, y + 56)


def _treat_icon(scr, x, y, w, h, fill, dim):
    a = T.asset("ui_treat")
    for k, dx in enumerate((-22, 0, 22)):
        scr.blit(a, 0, x + w // 2 + dx - a.w * 2 // 2, y + 24 - (k % 2) * 6, scale=2, bg=fill)


def _heart_icon(scr, x, y, w, h, fill, dim):
    a = T.asset("ui_heart")
    scr.blit(a, 0, x + w // 2 - a.w * 5 // 2, y + 14, scale=5, bg=fill)


ICONS = {"feast": _heart_icon, "wider_cloth": _slot_icon, "bigger_box": _box_icon, "lucky_cat": _treat_icon,
         "sharpen": _stars_icon}


class LevelUpScene(NodeScene):
    TOAST = (T.INNER_L, 248, T.INNER_W, 20)

    def __init__(self, services, done=None):
        super().__init__(services, done)
        self.sel = 0
        self.options = []
        self._end = None
        self.add_frame()
        self.level_label = W.Label(T.INNER_L, 36, T.INNER_W, T.BODY, T.MUTED, T.GROUND, "c")
        self.add_widget(self.level_label, (T.INNER_L, 36, T.INNER_W, 15))
        self.add_title("Level Up!", y=6)
        spark = T.asset("ui_sparkle")
        for k, (dx, dy) in enumerate(((-96, 14), (-70, 4), (82, 6), (104, 18))):
            self.add_static((240 + dx, dy, 5, 5), lambda scr, dx=dx, dy=dy, k=k: scr.blit(spark, k % 2, 240 + dx, dy, bg=T.GROUND))
        self.tiles = []
        for i in range(3):
            t = Tile(TILE_X[i], TILE_Y, TILE_W, TILE_H, fill=T.GROUND)
            self.tiles.append(t)
            self.add_widget(t, t.rect)
        self.result = W.Label(T.INNER_L, 244, T.INNER_W, T.BODY, T.HEAL, T.GROUND, "c")
        self.add_widget(self.result, (T.INNER_L, 244, T.INNER_W, 15))
        self._load()
        self.tip("first_levelup")

    # ------------------------------------------------------------------ content
    def _preview(self, key):
        run = self.run
        if key == "feast":
            return ["Max HP %d {>} %d" % (run.max_hp, run.max_hp + 8), "Heal 8 HP now"]
        if key == "wider_cloth":
            return ["Spread Slots %d {>} %d" % (run.spread_size, run.spread_size + 1), "A longer reading"]
        if key == "bigger_box":
            return ["Box Slots %d {>} %d" % (run.box_size, run.box_size + 2), "Room for spare cards"]
        if key == "lucky_cat":
            return ["Treats %d {>} %d" % (run.treats, run.treats + 15), "Spend them at Spots"]
        return ["A card gets +1 {*}", "You pick which one"]

    def _load(self):
        run = self.run
        self.options = R.level_up_options(run)
        if not self.options:
            self.sv.save()
            self.finish(None)
            return
        self.sel = min(self.sel, len(self.options) - 1)
        self.level_label.set("You reached level %d. Pick one prize." % run.pending_levels[0])
        for i, key in enumerate(self.options):
            rows = [(NAMES[key], T.LABEL, T.BODY, 68, "c")]
            for k, line in enumerate(self._preview(key)):
                rows.append((W.glyphs(line), T.TEXT if k == 0 else T.MUTED, T.BODY, 90 + 16 * k, "c"))
            self.tiles[i].set(rows=rows, icon=ICONS[key], icon_key=key)
        self._focus()

    def _focus(self):
        for i, t in enumerate(self.tiles):
            t.set(focused=(i == self.sel))
        self.set_hints([("A", "Take"), ("C", "Info")])

    # ------------------------------------------------------------------ input
    def update(self, ctl, dt):
        self.toast.update(dt)
        if self.pump_tip():
            return
        if self._end is not None:
            self._end -= dt
            if self._end <= 0:
                self._end = None
                self.result.set("")
                self._load()
            return
        if ctl.dx and self.options:
            self.sel = step(self.sel, ctl.dx, len(self.options))
            self._focus()
        elif ctl.a:
            self._take(self.options[self.sel])
        elif ctl.c:
            key = self.options[self.sel]
            self.sv.app.open(W.InfoOverlay(NAMES[key], "Level Up {.} level %d" % self.run.pending_levels[0],
                                           wrap(R.LEVEL_UP_INFO[key][1], 56) + [""] + [W.glyphs(p) for p in self._preview(key)]))

    def _take(self, key):
        run = self.run
        if key == "sharpen":
            targets = [c.uid for c in R.all_cards(run) if c.star < 2]
            self.sv.pick_card("SHARPEN CLAWS: pick a card (+1 Star)", targets, self._sharpened)
            return
        self._apply(key, None)

    def _sharpened(self, uid):
        if uid is not None:
            self._apply("sharpen", uid)

    def _apply(self, key, uid):
        run = self.run
        line = {"feast": "Feast! Max HP is now %d." % (run.max_hp + 8),
                "wider_cloth": "Wider Cloth! You have %d Spread Slots." % (run.spread_size + 1),
                "bigger_box": "Bigger Box! You have %d Box Slots." % (run.box_size + 2),
                "lucky_cat": "Lucky Cat! +15 Treats.",
                "sharpen": None}[key]
        if line is None:
            c = R.find_card(run, uid)[2]
            line = "%s now has %d Stars." % (cards.card_title(c), c.star + 2) if c else "Sharpened!"
        if R.apply_level_up(run, key, uid) != "ok":
            self.toast.show("That did not work. Pick another prize.")
            return
        self.result.set(line, T.HEAL)
        self.refresh_status()
        self.set_hints([])
        self._end = 1.1


def dev_levelup():
    from . import path_dev
    return path_dev.dev_levelup()
