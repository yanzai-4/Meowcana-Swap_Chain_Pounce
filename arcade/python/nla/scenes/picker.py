"""Card Picker (GDD 6.6): the shared "pick one card" screen. Spread row + Box row only.

    PickerScene(services, purpose, selectable, done, button="Cancel")      done(uid | None)

`purpose` is the title line on top ("Sell", "Sharpen", ...; any short text), `selectable` the uids that can be chosen
(the others are dimmed). The button sits at the FIGHT position at the end of the Spread row. With the default
"Cancel", B cancels at once (done(None)). With any other label (the Box-full "Skip New Card", which cannot be undone)
B only moves the cursor to the button and A on the button ends the picker. C = Card Info. Dev harness: `dev_picker()`.
"""

from nla.rules import cards
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene

from .spread_board import Board, DetailPanel, PANEL_RECT, box_x, slot_x, text_rows

SHAKE_S = 0.25
TITLE_Y = 18
CAPTION_Y = 70


class PickerScene(Scene):
    def __init__(self, services, purpose, selectable, done, button="Cancel"):
        super().__init__(done)
        self.sv = services
        self.purpose = purpose
        self.selectable = set(selectable)
        self.button_label = button
        self.hard_exit = button != "Cancel"
        run = services.run
        self.ns, self.nb = len(run.spread), len(run.box)
        self.board = Board(self.ns, self.nb, power=False)
        x, y, w, h = T.SPREAD_FIGHT
        self.button = W.Button(x, y, w, h, button)
        self.footer = W.Footer()
        self.detail = DetailPanel()
        self.row, self.col = 0, self.ns
        for i, c in enumerate(run.spread):
            if c is not None and c.uid in self.selectable:
                self.col = i
                break
        else:
            for i, c in enumerate(run.box):
                if c is not None and c.uid in self.selectable:
                    self.row, self.col = 1, i
                    break
        self._shake_t = 0.0
        self._detail_key = None
        self._footer_key = None
        self._refresh_board()

    # ------------------------------------------------------------------ helpers
    @property
    def run(self):
        return self.sv.run

    def _row_len(self, row):
        return self.ns + 1 if row == 0 else self.nb

    def _center_x(self, row, col):
        if row == 0:
            return slot_x(col) + 24 if col < self.ns else T.SPREAD_FIGHT[0] + 46
        return box_x(col) + 20

    def _card(self):
        """Card under the cursor (None on the button / an empty slot)."""
        if self.row == 0:
            return None if self.col >= self.ns else self.run.spread[self.col]
        return self.run.box[self.col]

    def _refresh_board(self):
        run = self.run
        dim = {("s", i) for i, c in enumerate(run.spread) if c is not None and c.uid not in self.selectable}
        dim |= {("b", i) for i, c in enumerate(run.box) if c is not None and c.uid not in self.selectable}
        self.board.show(run.spread, run.box, dim=dim)

    # ------------------------------------------------------------------ update
    def update(self, ctl, dt):
        if self._shake_t > 0:
            self._shake_t = max(0.0, self._shake_t - dt)
        self.busy = self._shake_t > 0
        if ctl.dx or ctl.dy:
            self._move(ctl.dx, ctl.dy)
        if ctl.a:
            self._press_a()
        elif ctl.b:
            if self.hard_exit:
                self.row, self.col = 0, self.ns
                self._detail_key = None
            else:
                self.finish(None)
        elif ctl.c:
            card = self._card()
            if card is not None:
                self.sv.card_info(card)
            else:
                self._shake_t = SHAKE_S

    def _move(self, dx, dy):
        row, col = self.row, self.col
        if dx:
            col = (col + dx) % self._row_len(row)
        if dy and self.nb:
            cx = self._center_x(row, col)
            row = 1 - row
            col = min(range(self._row_len(row)), key=lambda c: abs(self._center_x(row, c) - cx))
        if (row, col) != (self.row, self.col):
            self.row, self.col = row, col
            self._detail_key = None

    def _press_a(self):
        if self.row == 0 and self.col == self.ns:
            self.finish(None)
            return
        card = self._card()
        if card is not None and card.uid in self.selectable:
            self.finish(card.uid)
        else:
            self._shake_t = SHAKE_S

    # ------------------------------------------------------------------ drawing
    def draw(self, scr, full):
        if full:
            self._paint_static(scr)
            self._detail_key = None
        self._point_cursor()
        self.board.draw(scr, full)           # the cursor goes first: it is the immediate feedback
        self.button.set(focused=self.row == 0 and self.col == self.ns)
        self.button.draw(scr, full)
        self._refresh_detail()
        self.detail.draw(scr, full)
        self._refresh_footer()
        self.footer.draw(scr, full)
        if scr.stats()["ms"] > 45.0:
            self.busy = True

    def _paint_static(self, scr):
        scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
        scr.rect(2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4, T.RULE_DIM)
        W.corners(scr, 2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4)
        scr.text_center(TITLE_Y, self.purpose, T.LABEL, T.GROUND, T.TITLE)
        picks = sum(1 for c in self.run.spread + self.run.box if c is not None and c.uid in self.selectable)
        total = sum(1 for c in self.run.spread + self.run.box if c is not None)
        caption = "Dimmed cards can't be picked." if picks < total else "Pick one card."
        scr.text_center(CAPTION_Y, caption, T.MUTED, T.GROUND)
        W.divider(scr, T.INNER_L, T.INNER_R, T.SPREAD_DIV1_Y)
        W.divider(scr, T.INNER_L, T.INNER_R, T.SPREAD_DIV2_Y)
        W.divider(scr, T.INNER_L, T.INNER_R, T.SPREAD_DIV3_Y)
        W.divider(scr, T.INNER_L, T.INNER_R, T.FOOTER_DIV_Y, mid=False)
        W.panel(scr, *PANEL_RECT)

    def _point_cursor(self):
        dx = (-2, 2, -1, 1)[int(self._shake_t * 40) % 4] if self._shake_t > 0 else 0
        if self.row == 0 and self.col == self.ns:
            x, y, w, h = T.SPREAD_FIGHT
            self.board.cursor_rect(x + dx, y, w, h)
        else:
            self.board.cursor_to("s" if self.row == 0 else "b", self.col, False, dx)

    def _refresh_detail(self):
        key = (self.row, self.col)
        if key == self._detail_key:
            return
        self._detail_key = key
        card = self._card()
        if self.row == 0 and self.col == self.ns:
            self.detail.set(self.button_label, "", [[("Press A to leave without choosing.", T.TEXT)]])
        elif card is None:
            self.detail.set(None, "", [[("Empty slot", T.CAPTION)]])
        elif card.uid in self.selectable:
            self.detail.set(cards.card_title(card), cards.card_subtitle(card), text_rows(cards.card_text(card)))
        else:
            self.detail.set(cards.card_title(card), cards.card_subtitle(card),
                            [[("Can't pick this one.", T.CAPTION)]])

    def _refresh_footer(self):
        card = self._card()
        if self.row == 0 and self.col == self.ns:
            hints = [("A", self.button_label)] + ([] if self.hard_exit else [("B", "Cancel")])
        elif card is not None and card.uid in self.selectable:
            hints = [("A", "Choose"), ("B", self._b_label()), ("C", "Info")]
        elif card is not None:
            hints = [("B", self._b_label()), ("C", "Info")]
        else:
            hints = [("B", self._b_label())]
        run = self.run
        left = [("name", "Domino"), ("treat", "Treats %d" % run.treats)]
        key = (tuple(hints), tuple(left))
        if key != self._footer_key:
            self._footer_key = key
            self.footer.set_hints(hints)
            self.footer.set_left(left)

    def _b_label(self):
        return "To Skip" if self.hard_exit else "Cancel"


# =========================================================================== dev harness
def dev_picker():
    """Sell-style picker: only the Spread's reversed card and the Box's Magician can be chosen."""
    from .dev_spread import StubServices, dev_run, make_app
    run = dev_run()
    sv = StubServices(run)
    sel = [c.uid for c in run.spread + run.box if c is not None and (c.reversed is True or c.def_id >= 40)]
    return make_app(sv, lambda: PickerScene(sv, "Sell: pick a card (+2 Treats)", sel, lambda u: print("picked", u)))


def dev_picker_skip():
    """Box-full variant: the button is Skip New Card and B only moves the cursor."""
    from .dev_spread import StubServices, dev_run, make_app
    run = dev_run()
    sv = StubServices(run)
    sel = [c.uid for c in run.spread + run.box if c is not None]
    return make_app(sv, lambda: PickerScene(sv, "Box full: drop one card (+1 Treat)", sel,
                                            lambda u: print("picked", u), "Skip New Card"))
