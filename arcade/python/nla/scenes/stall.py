"""Spots' Stall (GDD 6.7, 13.5). StallScene(services, done) -> done(None) when the player leaves.

Row 1: four cards with prices. Row 2: [Service] [Tuna Can] [Reroll] [Sell] [Leave]. Up/Down switch rows, Left/Right
wrap inside a row, A buys / acts, B jumps the cursor to Leave (leaving cannot be undone, so B never leaves), C explains
the highlighted thing. Things you cannot afford are dimmed; A on one flashes its price red. Selling goes through the
Card Picker, and a Major or a 2-star-or-better card asks first. Buying a duplicate or into a full Box hands over to the
Reward flow (nla.scenes.reward.place_card).
"""

import random

from nla import story
from nla.rules import cards
from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.input import Nav

from .path_common import NodeScene, Sprite, Tile, detail_lines, place_card, wrap

CARD_X0, CARD_PITCH, CARD_Y = 28, 78, 62
PRICE_Y = 146
TILE_Y, TILE_W, TILE_H, TILE_GAP = 172, 84, 36, 7
SPOTS_XY = (372, 62)
LINE_Y = 34
DETAIL_Y = 222
LEAVE = 4          # column of Leave in row 2
SPEECH_X, SPEECH_W = 90, 300     # Spots' line, at most 46 characters (story LINE_CHARS)


class _PriceTag:
    """Treat icon + price centered under a card; red while flashing, dim when unaffordable, "Sold" when bought."""

    def __init__(self, x, w, y, clock):
        self.x, self.w, self.y, self.clock = x, w, y, clock
        self.price = None           # None = hidden
        self.state = "ok"           # ok | poor | sold
        self.flash_until = 0.0
        self._drawn = None

    def set(self, price, state):
        self.price, self.state = price, state

    def flash(self, seconds=0.6):
        self.flash_until = self.clock() + seconds

    def invalidate(self):
        self._drawn = None

    def _color(self):
        if self.state == "sold":
            return T.NIGHT4
        if self.clock() < self.flash_until and int(self.clock() * 8) % 2 == 0:
            return T.RED
        return T.NIGHT4 if self.state == "poor" else T.TEXT

    def draw(self, scr, full=False):
        look = (self.price, self.state, self._color())
        if not full and self._drawn == look:
            return
        if not full and W.over_budget(scr, self.w * 15, 3):
            return
        scr.fill_rect(self.x, self.y, self.w, 15, T.GROUND)
        if self.price is not None:
            label = "Sold" if self.state == "sold" else str(self.price)
            tw = scr.measure(label)[0]
            icon = 0 if self.state == "sold" else 12
            x = self.x + (self.w - tw - icon) // 2
            if icon:
                scr.blit(T.asset("ui_treat"), 0, x, self.y + 3, bg=T.GROUND, dim=self.state == "poor")
            scr.text(x + icon, self.y, label, self._color(), T.GROUND)
        self._drawn = look


class StallScene(NodeScene):
    def __init__(self, services, done=None):
        super().__init__(services, done)
        run = self.run
        self.stock = R.stall_stock(run)
        self.nav = Nav([4, 5], xs=[[CARD_X0 + CARD_PITCH * i + 24 for i in range(4)],
                                   [16 + (TILE_W + TILE_GAP) * i + TILE_W // 2 for i in range(5)]], row=1, col=0)
        self._leaving = None
        self._desc_due = 0
        self._rng = random.Random(run.seed * 31 + run.step)
        clock = lambda: self.sv.app.time if self.sv.app else 0.0   # noqa: E731

        self.add_frame()
        self.add_title("Spots' Stall", y=6)
        self.add_divider(54)
        self.add_divider(216)

        self.cursor = W.Cursor()
        self.add_widget(self.cursor, (0, CARD_Y - 6, 350, 90))
        self.speech = W.Label(SPEECH_X, LINE_Y, SPEECH_W, T.BODY, T.TEXT, T.GROUND, "c")
        self.add_widget(self.speech, (SPEECH_X, LINE_Y, SPEECH_W, 15))
        self.views, self.prices = [], []
        for i in range(4):
            x = CARD_X0 + CARD_PITCH * i
            v = W.CardView(x, CARD_Y)
            self.views.append(v)
            self.add_widget(v, (x - 2, CARD_Y - 2, 52, 68))
            p = _PriceTag(x - 9, 66, PRICE_Y, clock)
            self.prices.append(p)
            self.add_widget(p, (x - 9, PRICE_Y, 66, 15))
        self.spots = Sprite("spots_idle", SPOTS_XY[0], SPOTS_XY[1], T.GROUND, clock)
        self.add_widget(self.spots, self.spots.rect)
        self.tiles = []
        for i in range(5):
            t = Tile(16 + (TILE_W + TILE_GAP) * i, TILE_Y, TILE_W, TILE_H, fill=T.GROUND)
            self.tiles.append(t)
            self.add_widget(t, t.rect)
        self.head = W.TextRun(T.INNER_L, DETAIL_Y)
        self.add_widget(self.head, (T.INNER_L, DETAIL_Y, T.INNER_W, 26))
        self.lines = [W.Label(T.INNER_L, DETAIL_Y + 27 + 15 * i, T.INNER_W) for i in range(3)]
        for lab in self.lines:
            self.add_widget(lab, (T.INNER_L, lab.y, T.INNER_W, 15))

        self.say_line("greeting")
        self.tip("first_stall")
        self._refresh()

    # ------------------------------------------------------------------ view state
    def say_line(self, situation, color=T.TEXT):
        self.speech.set(self._rng.choice(story.STALL_LINES[situation]), color)

    def message(self, text, color=T.ACCENT):
        self.speech.set(text, color)

    def _refresh(self):
        """Pull everything the screen shows from the run and the stock."""
        run, st = self.run, self.stock
        for i, item in enumerate(st.cards):
            v, p = self.views[i], self.prices[i]
            if item.sold:
                v.set_empty()
                v.dim = False
                p.set(item.price, "sold")
            else:
                v.set_card(item.card)
                v.dim = run.treats < item.price
                p.set(item.price, "poor" if v.dim else "ok")
        svc = st.service
        name = R.SERVICE_INFO[svc.service][0]
        self._tile(0, name, "Sold" if svc.sold else "%d Treats" % svc.price, svc.sold or run.treats < svc.price)
        self._tile(1, "Tuna Can", "%d Treats" % st.tuna.price, run.treats < st.tuna.price)
        self._tile(2, "Reroll", "%d Treats" % st.reroll_cost, run.treats < st.reroll_cost)
        self._tile(3, "Sell", "half price", False)
        self._tile(4, "Leave", "to the road", False)
        self.refresh_status()
        self._focus()

    def _tile(self, i, name, sub, dim):
        self.tiles[i].set(rows=[(name, T.LABEL, T.BODY, 4, "c"), (sub, T.TEXT, T.BODY, 19, "c")], dim=dim)

    def _item(self):
        """What the cursor is on: ("card", index) | ("tile", column)."""
        return ("card", self.nav.col) if self.nav.row == 0 else ("tile", self.nav.col)

    def _focus(self):
        kind, i = self._item()
        for k, t in enumerate(self.tiles):
            t.set(focused=(kind == "tile" and k == i))
        old = getattr(self, "_cur_card", None)
        self._cur_card = i if kind == "card" else None
        if old is not None and old != self._cur_card:
            self.views[old].invalidate()        # the old brackets overlapped its rim: repaint it
        if kind == "card":
            v = self.views[i]
            self.cursor.to(v.x, v.y, v.w, v.h)
        else:
            self.cursor.hide()
        self._desc_due = 2          # the detail text follows a frame after the cursor so no frame carries both
        a = {0: "Buy", 1: "Buy", 2: "Reroll", 3: "Sell", 4: "Leave"}[i] if kind == "tile" else "Buy"
        if kind == "tile" and i == LEAVE:
            self.set_hints([("A", "Leave"), ("C", "Info")])
        else:
            self.set_hints([("A", a), ("B", "To Leave"), ("C", "Info")])

    def _describe(self, kind, i):
        st = self.stock
        lines = []
        if kind == "card":
            item = st.cards[i]
            if item.sold:
                self.head.set([("Sold out", T.MUTED, T.TITLE)])
                lines = ["Spots already pocketed those Treats."]
            else:
                c = item.card
                self.head.set([(cards.card_title(c), T.LABEL, T.TITLE), 10,
                               (cards.card_subtitle(c), T.TEXT)])
                lines = cards.card_text(c)
                if c.charm:
                    ch = cards.CHARMS[c.charm]
                    lines = lines[:2] + wrap("%s: %s" % (ch.name, ch.text), 56)[:1]
                lines = detail_lines(lines)
        else:
            name, text = {0: self._service_info, 1: self._tuna_info, 2: self._reroll_info,
                          3: self._sell_info, 4: self._leave_info}[i]()
            self.head.set([(name, T.LABEL, T.TITLE)])
            lines = wrap(text, 50)
        for k, lab in enumerate(self.lines):
            lab.set(lines[k] if k < len(lines) else "")

    def _service_info(self):
        svc = self.stock.service
        name, text = R.SERVICE_INFO[svc.service]
        return name, text

    def _tuna_info(self):
        return "Tuna Can", "Restores %d HP." % R.TUNA_HEAL

    def _reroll_info(self):
        return "Reroll", "Swap all four cards for new ones. Each reroll costs 1 more Treat."

    def _sell_info(self):
        return "Sell", "Sell a card for half its price (at least 1 Treat)."

    def _leave_info(self):
        return "Leave", "Back to the Night Path. You cannot come back to this stall."

    # ------------------------------------------------------------------ input
    def update(self, ctl, dt):
        self.toast.update(dt)
        if self._desc_due:
            self._desc_due -= 1
            if not self._desc_due:
                self._describe(*self._item())
        if self.pump_tip():
            return
        if self._leaving is not None:
            self._leaving -= dt
            if self._leaving <= 0:
                self._leaving = None
                self.sv.save()
                self.finish(None)
            return
        if ctl.dx or ctl.dy:
            if self.nav.move(ctl.dx, ctl.dy):
                self._focus()
        elif ctl.a:
            self._act()
        elif ctl.b:
            if self.nav.row != 1 or self.nav.col != LEAVE:
                self.nav.jump(1, LEAVE)
                self._focus()
        elif ctl.c:
            self._info()

    def _info(self):
        kind, i = self._item()
        if kind == "card":
            item = self.stock.cards[i]
            if not item.sold:
                self.sv.card_info(item.card)
            return
        name, text = [self._service_info, self._tuna_info, self._reroll_info, self._sell_info, self._leave_info][i]()
        sub = {0: "Service {.} %d Treats" % self.stock.service.price, 1: "%d Treats" % self.stock.tuna.price,
               2: "%d Treats" % self.stock.reroll_cost, 3: "Spots' Stall", 4: "Spots' Stall"}[i]
        self.sv.app.open(W.InfoOverlay(name, sub, wrap(text, 56)))

    def _poor(self, price_tag=None):
        self.say_line("broke", T.CURSE)
        if price_tag is not None:
            price_tag.flash()
        else:
            self.tiles[self.nav.col].set(dim=True)

    def _act(self):
        kind, i = self._item()
        run, st = self.run, self.stock
        if kind == "card":
            self._buy_card(i)
        elif i == 0:
            self._buy_service()
        elif i == 1:
            if run.hp >= run.max_hp:
                self.message("HP is already full. Save the tuna!")
            elif R.buy(run, st.tuna) == "ok":
                self.say_line("tuna")
                self.message("Tuna! HP %d/%d" % (run.hp, run.max_hp), T.HEAL)
                self._refresh()
            else:
                self._poor()
        elif i == 2:
            if run.treats < st.reroll_cost:
                self._poor()
            else:
                R.reroll(run)
                self.stock = run.stall
                self.say_line("reroll")
                self._refresh()
        elif i == 3:
            self._sell()
        else:
            self.say_line("leave")
            self.set_hints([("A", "Leave")])
            self._leaving = 0.9

    # -- buying
    def _buy_card(self, i):
        run, item = self.run, self.stock.cards[i]
        if item.sold:
            self.message("That one is gone.")
        elif run.treats < item.price:
            self._poor(self.prices[i])
        else:
            card = item.card
            status = R.buy(run, item)
            self.say_line("buy")
            self._refresh()
            place_card(self.sv, card, status, lambda final: self._after_card(final))

    def _after_card(self, final):
        self._refresh()

    def _buy_service(self):
        run, item = self.run, self.stock.service
        svc = item.service
        if item.sold:
            self.message("Sold out.")
            return
        if run.treats < item.price:
            self._poor()
            return
        if svc in ("charm_up", "flea_bath", "flip"):
            if svc == "flea_bath":
                targets = [c for c in R.all_cards(run) if cards.is_curse_charm(c.charm)]
                prompt = "FLEA BATH: pick a cursed card"
            elif svc == "flip":
                targets = R.all_cards(run)
                prompt = "FLIP: pick a card to turn over for good"
            else:
                targets = R.all_cards(run)
                prompt = "CHARM UP: pick a card to get a Charm"
            if not targets:
                self.message("No card to use that on.")
                return
            self.say_line("service")
            self.sv.pick_card(prompt, [c.uid for c in targets], lambda uid: self._service_picked(uid))
        else:
            if R.buy(run, item) == "ok":
                self.say_line("service")
                self.message("%s! Spread %d, Box %d." % (R.SERVICE_INFO[svc][0], run.spread_size, run.box_size), T.HEAL)
                self._refresh()
            else:
                self.message("Spots shakes his head.")

    def _service_picked(self, uid):
        if uid is None:
            self._refresh()
            return
        item = self.stock.service
        if R.buy(self.run, item, uid) == "ok":
            c = R.find_card(self.run, uid)[2]
            self.say_line("buy")
            self.message("%s: %s" % (R.SERVICE_INFO[item.service][0], cards.card_title(c)), T.HEAL)
        else:
            self.message("That did nothing.")
        self._refresh()

    # -- selling
    def _sell(self):
        run = self.run
        owned = R.all_cards(run)
        if not owned:
            self.message("You have nothing to sell.")
            return
        self.say_line("sell")
        self.sv.pick_card("SELL: pick a card (half price)", [c.uid for c in owned],
                          lambda uid: self._sell_picked(uid))

    def _sell_picked(self, uid):
        if uid is None:
            self._refresh()
            return
        c = R.find_card(self.run, uid)[2]
        if c is None:
            self._refresh()
            return
        price = R.sell_price(c)
        if R.needs_confirm(c):
            self.sv.app.confirm("Sell %s for %d Treats?" % (cards.card_title(c), price),
                                lambda: self._do_sell(uid), self._refresh, yes="Sell", no="Keep")
        else:
            self._do_sell(uid)

    def _do_sell(self, uid):
        n = R.sell(self.run, uid)
        self.message("Sold for %d Treat%s." % (n, "" if n == 1 else "s"), T.HEAL)
        self._refresh()

    def animating(self):
        return False


def dev_stall():
    from . import path_dev
    return path_dev.dev_stall()
