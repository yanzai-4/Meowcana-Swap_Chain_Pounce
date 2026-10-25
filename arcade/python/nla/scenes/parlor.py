"""Moonnap Parlor: Granny asleep, the Nine Bells rail, Start Night.

    ParlorScene(services, done, dying=False, lines=None, quip="")

done("start") | done("title"). `dying=True` plays the newest dark bell going out (a short flicker), then `lines`
(story.SCENES first_death / parlor_return) play over the room, then the menu opens. Bells lit = profile.bells,
counted from the left; the bell that just went dark is index profile.bells.
"""

from nla import sfx
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene

BELLS = tuple((292 + 20 * i, 66) for i in range(9))      # top-left of each 14x16 ui_bell (see docs/assets.md)
CANDLE = (146, 175)
FLICKER = (1, 0, 1, 0)                                   # lit/dark steps of the bell that just went out
FLICKER_STEP = 0.35
BAND_Y = 232
BTN = (140, 262, 200, 20)


class ParlorScene(Scene):
    def __init__(self, services, done=None, dying=False, lines=None, quip=""):
        super().__init__(done)
        self.svc = services
        self.dying = dying
        self.lines = lines
        self.quip = quip
        self.lit = services.profile.bells
        self.sel = 0
        self.buttons = [W.Button(140, 254, 200, 20, label="Start Night", bg=T.PANEL),
                        W.Button(140, 276, 200, 18, label="Learn to Play", bg=T.PANEL)]
        self.footer = W.Footer(bg=T.PANEL, divider_line=False)
        self._focus()
        self.clock = 0.0
        self.ready = not dying
        self._said = not (dying and lines)
        self._candle = None
        self._bell_state = None
        self._belled = False

    def _focus(self):
        for i, b in enumerate(self.buttons):
            b.set(focused=i == self.sel)
        self.footer.set_hints([("A", ("Start Night", "Learn")[self.sel]), ("B", "Title"), ("C", "Bells")])

    def region(self, key):
        return None

    # ------------------------------------------------------------------ input
    def update(self, ctl, dt):
        self.clock += dt
        if not self.ready:
            if not self._belled and self.clock >= FLICKER_STEP:
                self._belled = True
                sfx.play("bell")                          # the newest bell goes dark
            if self.clock >= FLICKER_STEP * len(FLICKER) + 0.4:
                self.ready = True
                if self.lines and not self._said:
                    self._said = True
                    self.app.say(self.lines)
            return
        if ctl.dy:
            self.sel = 1 - self.sel
            self._focus()
        elif ctl.a:
            self.finish(("start", "learn")[self.sel])
        elif ctl.b:
            self.finish("title")
        elif ctl.c:
            self.app.open(W.InfoOverlay("Nine Bells", "%d still lit" % self.lit,
                                        ["Every night that ends in a nap dims", "one bell.", "",
                                         "The Parlor is always open.", "Start Night begins a new one."]))

    def pointer(self, x, y, kind):
        """Hover/click the two plates; clicking the Nine Bells rail shows the bells info (like C); right = B."""
        if not self.ready:
            return None
        if kind == "right":
            return "b"
        if kind in ("wheel_up", "wheel_down"):
            return "up" if kind == "wheel_up" else "down"
        bx0, by0 = BELLS[0]
        if bx0 <= x < BELLS[-1][0] + 14 and by0 <= y < by0 + 16:
            return "c" if kind in ("up", "middle") else None
        for i, b in enumerate(self.buttons):
            if b.x <= x < b.x + b.w and b.y <= y < b.y + b.h:
                if kind in ("move", "up", "middle") and self.sel != i:
                    self.sel = i
                    self._focus()
                if kind == "up":
                    return "a"
                return "c" if kind == "middle" else None
        return None

    # ------------------------------------------------------------------ drawing
    def draw(self, scr, full):
        if full:
            scr.blit(T.asset("bg_parlor"), 0, 0, 0)
            scr.fill_rect(0, BAND_Y, T.SCREEN_W, T.SCREEN_H - BAND_Y, T.PANEL)
            scr.text_center(240, self.quip, T.MUTED, T.PANEL)
            for b in self.buttons:
                b.invalidate()
            self.footer.invalidate()
            self._candle = None
            self._bell_state = None
            for i, (x, y) in enumerate(BELLS):
                glow = i < self.lit or (not self.ready and i == self.lit)
                scr.blit(T.asset("ui_bell"), 1 if glow else 0, x, y)
        for b in self.buttons:
            b.draw(scr, False)
        self.footer.draw(scr, False)
        self._flicker(scr)

    def _flicker(self, scr):
        frame = int(self.app.time * 4) % 2
        if self._candle != frame:
            self._candle = frame
            x, y = CANDLE
            scr.asset_region(T.asset("bg_parlor"), 0, x, y, x, y, 5, 20)
            scr.blit(T.asset("ui_candle"), frame, x, y)
        if not self.ready:
            step = min(len(FLICKER) - 1, int(self.clock / FLICKER_STEP))
            if self._bell_state != step:
                self._bell_state = step
                x, y = BELLS[min(self.lit, len(BELLS) - 1)]
                scr.asset_region(T.asset("bg_parlor"), 0, x, y, x, y, 14, 16)
                scr.blit(T.asset("ui_bell"), FLICKER[step], x, y)
