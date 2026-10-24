"""Encounters (GDD 13.7). EncounterScene(services, done) -> done(None) after the outcome page.

An illustrated header (Domino on the left, the encounter's subject on the right), the story prompt, and two option
plates with their hints. Left/Right pick, A chooses, C explains the highlighted option. Options that need a card
(Granny's Dream) open the Card Picker first. The outcome page shows the story text, what changed (HP, max HP), the
card you received for the Major/page encounters, and a Continue button. A gained card that is a duplicate or does not
fit the Box goes through the Reward flow when you press Continue.
"""

from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.input import step

from . import path_art
from .path_common import CENTER_W, CENTER_X, NodeScene, Sprite, Tile, enc_story, place_card, wrap

ART_Y = 50                  # top of the 64 px sprites; feet on the floor strip at y 114
FLOOR = (16, 114, 448, 6)
PROMPT_Y = 134
TILE_Y, TILE_W, TILE_H = 186, 216, 70
TILE_X = (16, 248)
ZONE = (16, 124, 448, 168)
CARD_XY = (216, 176)

# which sprite stands opposite Domino: (asset, x, flip) and optional code art
_SUBJECT = {
    "lost_mouse": ("practice_mouse_idle", 304, False),
    "zero_booth": ("zero_idle", 330, True),
    "granny_dream": ("granny_oriel_idle", 304, True),
}


class EncounterScene(NodeScene):
    def __init__(self, services, done=None):
        super().__init__(services, done)
        run = self.run
        self.defn = R.encounter(run)
        self.text = enc_story(run.current.key)
        self.sel = 0
        self.mode = "choose"
        self._after = None
        self._gained = None         # (card, status) waiting for Continue
        clock = lambda: self.sv.app.time if self.sv.app else 0.0   # noqa: E731

        self.add_frame()
        self.add_title(self.text.title, y=6)
        self.add_static(FLOOR, lambda scr: scr.fill_rect(*FLOOR, T.NIGHT0))
        domino = Sprite("domino", 84, ART_Y, T.GROUND, clock, anim=False)
        self.add_widget(domino, domino.rect)
        self._subject(clock)

        for i, line in enumerate(self.text.prompt.split("\n")):
            self.add_text(T.INNER_L, PROMPT_Y + 16 * i, line, T.TEXT, w=T.INNER_W, align="c", group="choose")
        self.tiles = []
        for i in range(2):
            t = Tile(TILE_X[i], TILE_Y, TILE_W, TILE_H, fill=T.GROUND)
            self.tiles.append(t)
            self.add_widget(t, t.rect, "choose")
        self.out = [W.Label(CENTER_X, PROMPT_Y + 16 * i, CENTER_W, T.BODY, T.TEXT, T.GROUND, "c") for i in range(3)]
        for lab in self.out:
            self.add_widget(lab, ZONE, "result")
        self.detail = W.Label(CENTER_X, 0, CENTER_W, T.BODY, T.ACCENT, T.GROUND, "c")
        self.add_widget(self.detail, ZONE, "result")
        self.chips = W.Label(CENTER_X, 0, CENTER_W, T.BODY, T.HEAL, T.GROUND, "c")
        self.add_widget(self.chips, ZONE, "result")
        self.view = W.CardView(*CARD_XY)
        self.add_widget(self.view, ZONE, "result")
        self.cont = Tile(180, 0, 120, 30)
        self.cont.set(rows=[("Continue", T.ACCENT, T.BODY, 7, "c")], focused=True)
        self.add_widget(self.cont, ZONE, "result")

        for i, opt in enumerate(self.defn.options):
            label = self.text.options[i]
            hint = self.text.hints[i]
            rows = [(label, T.LABEL, T.TITLE, 6, "c")]
            for k, line in enumerate(wrap(hint, 34)[:2]):
                rows.append((line, T.TEXT, T.BODY, 36 + 15 * k, "c"))
            self.tiles[i].set(rows=rows)
        self._focus()
        self.tip("first_encounter")

    # ------------------------------------------------------------------ art
    def _subject(self, clock):
        key = self.run.current.key
        if key in _SUBJECT:
            name, x, flip = _SUBJECT[key]
            if key == "zero_booth":
                self.add_static((244, FLOOR[1] - 70, 74, 72), lambda scr: path_art.crate(scr, 246, FLOOR[1] - 68))
            sp = Sprite(name, x, ART_Y, T.GROUND, clock, flip=flip, anim=False)
            self.add_widget(sp, sp.rect)
        elif key == "catnip_patch":
            self.add_static((300, ART_Y, 80, 66), lambda scr: path_art.catnip(scr, 336, FLOOR[1]))
        elif key == "loose_page":
            self.add_static((300, ART_Y, 110, 70), self._page)
        elif key == "yarn_ball":
            self.add_static((298, FLOOR[1] - 44, 90, 46), lambda scr: path_art.yarn(scr, 318, FLOOR[1] - 16, 16))

    @staticmethod
    def _page(scr):
        path_art.page(scr, 322, ART_Y + 6)
        spark = T.asset("ui_sparkle")
        for dx, dy, f in ((-12, 4, 0), (62, 20, 1), (-4, 56, 1), (74, 0, 0)):
            scr.blit(spark, f, 322 + dx, ART_Y + 6 + dy, bg=T.GROUND)

    # ------------------------------------------------------------------ choosing
    def _focus(self):
        for i, t in enumerate(self.tiles):
            t.set(focused=(i == self.sel))
        self.set_hints([("A", self.text.options[self.sel]), ("C", "Info")])

    def update(self, ctl, dt):
        self.toast.update(dt)
        if self.pump_tip():
            return
        if self.mode == "result":
            if self._after is not None and self._after > 0:
                self._after -= dt
            elif ctl.a:
                self._continue()
            elif ctl.c and self._gained is not None:
                self.sv.card_info(self._gained[0])
            return
        if ctl.dx:
            self.sel = step(self.sel, ctl.dx, 2)
            self._focus()
        elif ctl.a:
            self._choose(self.sel)
        elif ctl.c:
            self.sv.app.open(W.InfoOverlay(self.text.options[self.sel], self.text.title,
                                           wrap(self.text.hints[self.sel], 56),
                                           side=self.text.prompt.split("\n")))

    def _choose(self, i):
        run = self.run
        if self.defn.options[i].needs_card:
            owned = R.all_cards(run)
            if not owned:
                self.toast.show("You have no cards to rework.")
                return
            self.sv.pick_card("REWORK: pick a card to flip and add a Star", [c.uid for c in owned],
                              lambda uid: self._picked(i, uid))
        else:
            self._resolve(i, None)

    def _picked(self, i, uid):
        if uid is not None:
            self._resolve(i, uid)

    def _outcome_key(self, i, res, hp_before):
        key = self.run.current.key
        if key == "zero_booth":
            return "b" if i == 1 else ("a_reversed" if res.card is not None and res.card.reversed else "a_upright")
        if key == "yarn_ball":
            if i == 1:
                return "b"
            return "a_ouch" if self.run.hp < hp_before else "a_yarn"
        return "a" if i == 0 else "b"

    def _resolve(self, i, uid):
        run = self.run
        before = (run.hp, run.max_hp)
        res = R.resolve_encounter(run, i, uid)
        if res.status == "need_card":
            self.toast.show("Pick a card first.")
            return
        okey = self._outcome_key(i, res, before[0])
        text = self.text.outcomes.get(okey) or res.text
        lines = text.split("\n")
        detail = res.text if " gets " in res.text else ""          # "Fire Claw gets Catnip!": which card
        if run.current.key == "catnip_patch" and i == 0 and not detail:
            lines = [res.text]                                      # nothing to sniff: say so
        dh, dm = run.hp - before[0], run.max_hp - before[1]
        chips = []
        if dm:
            chips.append("Max HP %+d" % dm)
        if dh:
            chips.append("HP %+d" % dh)
        color = T.CURSE if (dh < 0) else T.HEAL
        self._show_result(lines, detail, "   ".join(reversed(chips)) if chips else "", color, res)

    # ------------------------------------------------------------------ outcome page
    def _show_result(self, lines, detail, chips, color, res):
        for k, lab in enumerate(self.out):
            lab.set(lines[k] if k < len(lines) else "")
        y = PROMPT_Y + 16 * len(lines) + 6
        self._gained = None
        if res.card is not None:
            self._gained = (res.card, res.status)
            self.view.x, self.view.y = CARD_XY[0], y
            self.view.set_card(res.card)
            self.detail.y = y + 70
            where = {"spread": "Added to your Spread.", "box": "Added to your Box.",
                     "duplicate": "You already have one. Merge or keep both?",
                     "box_full": "Your Box is full. Swap one out?"}[res.status]
            self.detail.set(where, T.ACCENT)
            y += 70 + 20
        else:
            self.view.set_empty()
            self.view.x, self.view.y = -100, -100
            self.detail.y = y
            self.detail.set(detail, T.ACCENT)
            y += 20 if detail else 0
        self.chips.y = y
        self.chips.set(chips, color)
        y += 20 if chips else 4
        self.cont.y = min(y, 258)
        self.refresh_status()
        self.set_hints([("A", "Continue")] + ([("C", "Info")] if self._gained else []))
        self._after = 0.35
        self.set_mode("result", ZONE)

    def _continue(self):
        gained, self._gained = self._gained, None
        self._after = 9999
        if gained is not None and gained[1] in ("duplicate", "box_full"):
            place_card(self.sv, gained[0], gained[1], lambda final: self._finish())
        else:
            self._finish()

    def _finish(self):
        self.sv.save()
        self.finish(None)


def dev_encounter(key="lost_mouse"):
    from . import path_dev
    return path_dev.dev_encounter(key)
