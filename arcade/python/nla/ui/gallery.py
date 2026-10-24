"""Dev-only gallery: every widget and effect in its states, for screenshots in the simulator.

    python tools/sim.py --game nla.ui.gallery:make --keys "0.5s,SHOT:p0,C,0.5s,SHOT:p1,C,0.5s,SHOT:p2,..." --shots build/shots/ui/

Keys: C = next page (all pages). Page 0 (Spread look): stick moves the cursor, A lifts/drops the card under it
(opens Card Info on a Box card), B toggles the ghost outline. Page 1 (chrome): A damages the HP bars, B shows
a toast, L/R cycles the chain tier, U/D cycles statuses. Page 2 (overlays): A dialogue, B confirm, U card info.
Page 3 (fx): A damage numbers, B shake, U slash, D sparks + element burst, L hit flash, R hit-stop.
"""

from nla.rules import cards
from nla.rules.cards import Card, Scrap

from . import theme as T
from . import widgets as W
from .app import App, Scene
from .fx import Effects, HitStop, Shake, TintFlash
from .input import Nav

PAGES = 4


def make(page=0):
    return App(Gallery(page))


def make_chrome():
    return make(1)


def make_overlays():
    return make(2)


def make_fx():
    return make(3)


def _frame(scr):
    scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
    scr.rect(2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4, T.RULE_DIM)
    W.corners(scr, 2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4)


class Gallery(Scene):
    def __init__(self, page=0):
        super().__init__()
        self.page = page
        self.pages = [SpreadPage(), ChromePage(), OverlayPage(), FxPage()]

    def enter(self, app):
        super().enter(app)
        for p in self.pages:
            p.app = app

    def update(self, ctl, dt):
        if ctl.c:
            self.page = (self.page + 1) % PAGES
            self.app.switch(self.__class__(self.page).adopt(self.pages))
            return
        self.pages[self.page].update(ctl, dt)

    def adopt(self, pages):
        self.pages = pages
        return self

    def draw(self, scr, full):
        page = self.pages[self.page]
        if full:
            page.invalidate()
        page.draw(scr, full)

    def restore(self, scr, rect):
        self.pages[self.page].invalidate()
        self.draw(scr, True)

    @property
    def busy(self):
        return self.pages[self.page].busy


class Page:
    busy = False
    app = None

    def invalidate(self):
        pass

    def update(self, ctl, dt):
        pass

    def draw(self, scr, full):
        pass


# =========================================================================== page 0: the Spread look
class SpreadPage(Page):
    def __init__(self):
        spread = [Card(2, False, 0, 1), Card(3, False, 0, 1), Card(14, True, 0, 0), Card(22, False, 0, 5)]
        self.spread = spread + [None, None]
        self.box = [Card(47, False, 0, 7), Card(36, False, 1, 0)] + [None] * 4
        self.enemy = [Scrap("broken_sword", 3), Scrap("broken_sword", 3), Scrap("cracked_coin", 4)]
        self.slots = [W.CardView(T.SPREAD_SLOT_X0 + T.SPREAD_SLOT_PITCH * i, T.SPREAD_CARD_Y) for i in range(6)]
        self.boxv = [W.CardView(T.SPREAD_BOX_X0 + T.SPREAD_BOX_PITCH * i, T.SPREAD_BOX_Y, small=True)
                     for i in range(6)]
        self.scraps = [W.CardView(T.ENEMY_SCRAP_X0 + T.ENEMY_SCRAP_PITCH * i, T.ENEMY_SCRAP_Y, small=True)
                       for i in range(3)]
        for v, c in zip(self.slots, self.spread):
            v.set_card(c)
        for v, c in zip(self.boxv, self.box):
            v.set_card(c)
        for v, c in zip(self.scraps, self.enemy):
            v.set_enemy_card(c)
        self.fight = W.FightPlaque()
        self.cursor = W.Cursor()
        xs = [[v.x + 24 for v in self.slots] + [T.SPREAD_FIGHT[0] + 46], [v.x + 20 for v in self.boxv]]
        self.nav = Nav([7, 6], xs=xs, row=0, col=6)
        self.hp = W.HpBar(88, 44, 101)
        self.hp.set(18, 18)
        self.spread_label = W.Label(16, 89, 100, color=T.LABEL)
        self.spread_label.set("SPREAD 4/6")
        self.chips = W.ChipRow(160, 89, T.INNER_R - 160 + 1, align="r", gap=14)
        self.chips.set([W.chip("PER ROUND", T.CAPTION), W.chip("DMG 38", T.ACCENT),
                        W.status_chip("singe", 2), W.chip("HEAL 3", T.HEAL, ("ui_heart", 0)),
                        W.status_chip("curl", 0)])
        self.footer = W.Footer([("name", "Domino"), ("hp", "HP 30/36"), ("treat", "Treats 14")],
                               [("A", "Pick up"), ("B", "Menu"), ("C", "Info")])
        self.lifted = None
        self.ghosted = None
        self._detail = None
        self._detail_fresh = True
        self.detail1 = W.TextRun(30, 255, bg=T.PANEL)
        self.detail2 = W.TextRun(30, 273, bg=T.PANEL)
        self._candle = None

    def invalidate(self):
        for w in self.slots + self.boxv + self.scraps + [self.fight, self.cursor, self.hp, self.chips, self.footer]:
            w.invalidate()
        self.detail1.invalidate()
        self.detail2.invalidate()
        self._candle = None

    def _selected(self):
        r, c = self.nav.row, self.nav.col
        if r == 0:
            return None if c >= 6 else self.spread[c]
        return self.box[c]

    def update(self, ctl, dt):
        self.nav.move(ctl.dx, ctl.dy)
        r, c = self.nav.row, self.nav.col
        views = self.slots if r == 0 else self.boxv
        if ctl.a:
            if r == 1 and self.box[c] is not None and self.lifted is None:
                self.app.open(W.card_info(self.box[c]))
            elif c < 6 and ((r == 0 and self.spread[c] is not None) or (r == 1 and self.box[c] is not None)):
                v = views[c]
                v.lift = 0 if v.lift else T.CARD_LIFT
                v.glow = bool(v.lift)
        if ctl.b and c < 6:
            v = views[c]
            v.ghost = not v.ghost

    def draw(self, scr, full):
        if full:
            _frame(scr)
            W.panel(scr, 16, 9, 59, 53, orn=False)
            p = W.portrait("gray_rat")
            if p is not None:
                scr.blit(p, 0, 22, 13, bg=T.PANEL)
            scr.text(88, 21, "Gray Rat", T.LABEL, T.GROUND, T.TITLE)
            scr.text(196, 41, "HP 18", T.TEXT, T.GROUND)
            W.divider(scr, T.INNER_L, T.INNER_R, T.SPREAD_DIV1_Y)
            scr.text(16, 70, "READING", T.LABEL, T.GROUND)
            x = 16 + scr.measure("READING")[0] + 12
            for i, (name, hot) in enumerate([("Nuzzle x2", 0), ("Tail Tap x2", 0), ("Step x2", 0), ("Catwalk", 1)]):
                if i:
                    x += W.rich(scr, x, 70, "{.}", T.RULE, T.GROUND) + 6
                scr.text(x, 70, name, T.FOCUS if hot else T.TEXT, T.GROUND)
                x += scr.measure(name)[0] + 6
            W.divider(scr, T.INNER_L, T.INNER_R, T.SPREAD_DIV2_Y)
            scr.text(16, 185, "BOX 2/6", T.LABEL, T.GROUND)
            scr.text(16, 199, "spare cards", T.CAPTION, T.GROUND)
            for sx, sy in ((396, 190), (440, 192), (407, 232), (428, 230)):
                scr.blit(T.asset("ui_sparkle"), 1, sx - 2, sy - 2, bg=T.GROUND)
            scr.blit(T.asset("ui_moon_eye_s"), 0, 410, 204, bg=T.GROUND)
            W.divider(scr, T.INNER_L, T.INNER_R, T.SPREAD_DIV3_Y)
            W.panel(scr, *T.SPREAD_DETAIL)
        r, c = self.nav.row, self.nav.col
        if r == 0 and c < 6:
            v = self.slots[c]
            self.cursor.to(v.x, v.y, v.w, v.h, paw=True)
        elif r == 1:
            v = self.boxv[c]
            self.cursor.to(v.x, v.y, v.w, v.h, paw=False)
        else:
            self.cursor.hide()
        self.cursor.draw(scr, full)              # the cursor goes first: it is the immediate feedback
        self.hp.draw(scr, full)
        for v in self.slots + self.boxv + self.scraps:
            v.draw(scr, full)
        self.fight.set(focused=(r == 0 and c == 6))
        self.fight.draw(scr, full)
        self.spread_label.draw(scr, full)
        self.chips.draw(scr, full)
        self._draw_candles(scr, full)
        self._draw_detail(scr, full)
        self.footer.draw(scr, full)

    def _draw_candles(self, scr, full):
        frame = int(self.app.time * 3) % 2
        if full or (frame != self._candle and not W.over_budget(scr, 200, 2)):
            c = T.asset("ui_candle")
            scr.blit(c, frame, 384, 219, bg=T.GROUND)
            scr.blit(c, (frame + 1) % 2, 450, 221, bg=T.GROUND)
            self._candle = frame

    def _draw_detail(self, scr, full):
        card = self._selected()
        key = card if card is None else (card.def_id, card.reversed, card.star, card.charm)
        if key != self._detail or self._detail_fresh:
            self._detail, self._detail_fresh = key, False
            if card is None:
                msg = "Press A to fight" if self.nav.col == 6 and self.nav.row == 0 else "Empty slot"
                self.detail1.set([(msg, T.CAPTION)])
                self.detail2.set([])
            else:
                self.detail1.set([(cards.card_title(card), T.LABEL, T.TITLE), 10,
                                  ("{.} " + cards.card_subtitle(card), T.TEXT)])
                self.detail2.set([(cards.card_text(card)[0], T.MUTED)])
        self.detail1.draw(scr, full)
        self.detail2.draw(scr, full)


# =========================================================================== page 1: chrome
class ChromePage(Page):
    def __init__(self):
        self.enemy_hp = W.HpBar(24, 42, 150, tick=0.5)
        self.hero_hp = W.HpBar(24, 58, 150, hero=True)
        self.hp_val = 62
        self.enemy_hp.set(self.hp_val, 90)
        self.hero_hp.set(33, 36)
        self.statuses = ["singe", "puff", "drowsy", "curl", "leap"]
        self.status_i = 0
        self.chips = W.ChipRow(24, 88, 430)
        self.toast = W.Toast(320, 112, 140, 20)
        self.popup = W.ChainPopup((266, 168, 187, 45))
        self.tier = 2
        self.btns = [W.Button(24 + 100 * i, 112, 90, 24, label) for i, label in enumerate(("Fight", "Leave", "Skip"))]
        self.btns[2].set(disabled=True)
        self.footer = W.Footer([("name", "Domino"), ("bar", 33, 36, False)], [("A", "2x"), ("B", "Skip")], gap=12)
        self.label = W.Label(24, 146, 200, color=T.ACCENT)
        self.big = []
        x = 24
        for st in (dict(), dict(dim=True), dict(ghost=True), dict(glow=True, lift=4), dict(flash=True)):
            v = W.CardView(x, 228)
            v.set_face(3, False, 1, 1, "common")
            for k, val in st.items():
                setattr(v, k, val)
            self.big.append(v)
            x += 58
        v = W.CardView(x, 228)
        v.set_back()
        self.big.append(v)
        self.small = []
        for i, (kind, arg) in enumerate((("rare", True), ("legendary", False), ("curse", False), ("drop", 0),
                                         ("scrap", 0))):
            v = W.CardView(24 + 46 * i, 168, small=True)
            if kind == "drop":
                v.set_curse()
            elif kind == "scrap":
                v.set_scrap(1, 7)
            else:
                v.set_face(14 if arg else 33, arg, 2, 0, kind)
            self.small.append(v)
        self._refresh()

    def _refresh(self):
        s = self.statuses[self.status_i]
        self.chips.set([W.status_chip(s, 2), W.status_chip(self.statuses[(self.status_i + 1) % 5], 0),
                        W.chip("Power %s" % W.fmt_signed(self.tier * 2), T.ACCENT, ("ui_treat", 0))])
        self.label.set("Chain tier %d (L/R)" % self.tier, T.tier_color(self.tier))
        self.popup.show(self.tier, "Nuzzle +2 {>} Step +2 {>}", "Catwalk!", self.tier + 1)

    def invalidate(self):
        for w in (self.enemy_hp, self.hero_hp, self.chips, self.footer, self.toast, self.popup, self.label,
                  *self.btns, *self.big, *self.small):
            w.invalidate()

    def update(self, ctl, dt):
        self.toast.update(dt)
        self.enemy_hp.update()
        self.hero_hp.update()
        if ctl.a:
            self.hp_val = (self.hp_val - 17) % 91
            self.enemy_hp.set(self.hp_val)
            self.enemy_hp.flash(2)
            self.hero_hp.flash(2)
        if ctl.b:
            self.toast.show("Not enough Treats", 1.5, T.AMBER3)
        if ctl.dx:
            self.tier = (self.tier + ctl.dx) % 5
            self._refresh()
        if ctl.dy:
            self.status_i = (self.status_i + ctl.dy) % 5
            self._refresh()
        for i, b in enumerate(self.btns):
            b.set(focused=(i == self.tier % 2))

    def draw(self, scr, full):
        if full:
            _frame(scr)
            scr.text(24, 14, "Chrome", T.LABEL, T.GROUND, T.TITLE)
            W.panel(scr, 200, 38, 256, 40)
            scr.text(210, 42, "Panel with flourish corners", T.TEXT, T.PANEL)
            scr.text(210, 58, "Muted and faint captions", T.MUTED, T.PANEL)
            W.divider(scr, 24, 456, 160)
            W.divider(scr, 24, 456, 222, mid=False)
        self.enemy_hp.draw(scr, full)
        self.hero_hp.draw(scr, full)
        for v in self.big + self.small:
            v.draw(scr, full)
        self.chips.draw(scr, full)
        self.label.draw(scr, full)
        for b in self.btns:
            b.draw(scr, full)
        self.popup.draw(scr, full)
        self.toast.draw(scr, full)
        self.footer.draw(scr, full)

    @property
    def busy(self):
        return self.enemy_hp._flash > 0 or self.hero_hp._flash > 0


# =========================================================================== page 2: overlays
class OverlayPage(Page):
    def __init__(self):
        self.msg = W.Label(24, 60, 430, color=T.MUTED)
        self.msg.set("A dialogue   B confirm   U card info   C next page")
        self.result = W.Label(24, 90, 430, color=T.ACCENT)
        self.footer = W.Footer(hints=[("A", "Talk"), ("B", "Ask"), ("C", "Next")])

    def invalidate(self):
        self.msg.invalidate()
        self.result.invalidate()
        self.footer.invalidate()

    def update(self, ctl, dt):
        if ctl.a:
            from nla.story import Line
            self.app.say([Line("Zero", "Cards go from left to right.\nThe Paw plays them one by one.", "zero"),
                          Line("Domino", "Then the rat plays one.", "domino"),
                          Line("", "A cold wind rattles the attic window.")],
                         lambda: self.result.set("dialogue done"))
        elif ctl.b:
            self.app.confirm("Throw away the Sun?\nThis cannot be undone.",
                             lambda: self.result.set("answer: Yes"), lambda: self.result.set("answer: No"),
                             yes="Throw away", no="Keep")
        elif ctl.dy < 0:
            self.app.open(W.card_info(Card(47, False, 0, 7)))

    def draw(self, scr, full):
        if full:
            _frame(scr)
            scr.text(24, 14, "Overlays", T.LABEL, T.GROUND, T.TITLE)
            scr.text_center(150, "(scene content under the overlays)", T.CAPTION, T.GROUND)
        self.msg.draw(scr, full)
        self.result.draw(scr, full)
        self.footer.draw(scr, full)


# =========================================================================== page 3: fx
class FxPage(Page):
    STAGE = (16, 40, 448, 190)

    TX, TY = 340, 200          # target sprite: bottom center

    def __init__(self):
        self.fx = Effects(self._restore)
        self.shake = Shake()
        self.stop = HitStop()
        self.flash = TintFlash()
        self.footer = W.Footer(hints=[("A", "Hit"), ("B", "Shake"), ("C", "Next")])
        self.target = T.asset("gray_rat")
        self._rect = (0, 0, 0, 0)
        self._hits = 0

    def _restore(self, scr, r):
        """Repaint the ground, then the part of the target sprite that the rect covers."""
        x, y, w, h = r
        scr.fill_rect(x, y, w, h, T.GROUND)
        sx, sy, sw, sh = self._rect
        ix0, iy0, ix1, iy1 = max(x, sx), max(y, sy), min(x + w, sx + sw), min(y + h, sy + sh)
        if ix0 < ix1 and iy0 < iy1:
            scr.asset_region(self.target, 0, ix0, iy0, ix0 - sx, iy0 - sy, ix1 - ix0, iy1 - iy0, bg=T.GROUND)

    def invalidate(self):
        self.footer.invalidate()
        self.fx.items = []

    @property
    def busy(self):
        return self.fx.busy or self.shake.active or self.flash.active

    def update(self, ctl, dt):
        if self.stop.frozen():
            return
        if ctl.a:
            self._hits += 1
            big = self._hits % 2 == 0
            self.fx.damage(self.TX, self.TY - 80, 34 if big else 9, big=big)
            self.fx.slash(self.TX, self.TY - 32)
            self.fx.sparks(self.TX, self.TY - 32, (T.AMBER3, T.FIRE2, T.MOON))
            self.flash.triple() if big else self.flash.white()
            if big:
                self.shake.start()
                self.stop.start(3)
        if ctl.b:
            self.shake.start()
        if ctl.dy < 0:
            self.fx.slash(self.TX, self.TY - 32)
        if ctl.dy > 0:
            self.fx.sparks(120, 150, (T.AMBER3, T.GOLD4, T.SILVER2), n=6)
            self.fx.element_burst(120, 150, self._hits % 4)
            self.fx.chain_text(110, 100, "Catwalk!", self._hits % 5)
            self._hits += 1
        if ctl.dx < 0:
            self.flash.red()
        if ctl.dx > 0:
            self.stop.start()
        self.fx.update()
        self.shake.step()
        self.flash.step()

    def draw(self, scr, full):
        if full:
            _frame(scr)
            scr.text(24, 14, "Effects", T.LABEL, T.GROUND, T.TITLE)
            self.fx.items = []
            scr.hide("target", T.GROUND)
        dx, dy = self.shake.offset
        a = self.target
        self._rect = (self.TX - a.w // 2 + dx, self.TY - a.h + dy, a.w, a.h)
        scr.asset("target", a, 0, self._rect[0], self._rect[1], tint=self.flash.tint, bg=T.GROUND)
        self.fx.draw(scr)
        self.footer.draw(scr, full)
