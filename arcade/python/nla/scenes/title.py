"""Title screen: bg_title, the menu band, a calm candle flicker and a few twinkling stars.

    TitleScene(services, done, can_continue=False, tutorial_done=False)

done("learn") | done("skip") | done("continue"). Menu: Begin the Night (then Learn to Play / Skip Tutorial, with the
default on Learn to Play until the profile shows the tutorial was finished) · Continue (only with a saved night) ·
Records. A explains nothing it does not do, C explains the highlighted row, B backs out of a sub-menu.
"""

from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene
from nla.ui.input import step

BAND = (0, 232, T.SCREEN_W, 64)
BTN_W, BTN_H, BTN_PITCH, BTN_Y0 = 200, 18, 20, 236
BTN_X = (T.SCREEN_W - BTN_W) // 2

CANDLE = (100, 182)                      # top-left of the 5x20 flame sprite over the baked candle
STARS = ((96, 66, 0.0), (150, 96, 1.1), (330, 74, 0.5), (384, 106, 1.7), (88, 28, 0.9), (410, 30, 1.4))
STAR_CYCLE = (None, 1, 0, 1)             # sparkle frame per quarter of the cycle (None = hidden)

HELP = {
    "begin": ("Begin the Night", "A new night", ["Start a new night in the Dusty Attic.", "",
                                                  "You can learn the basics first,", "or jump right in."]),
    "continue": ("Continue", "Your saved night", ["Pick up where you left off,", "at the last stop on the Night Path."]),
    "records": ("Records", "Your best nights", ["Wins, your biggest hit and your", "fastest night so far."]),
    "learn": ("Learn to Play", "The Reading Table", ["Zero shows you the cards in three", "tiny battles. Takes a few minutes."]),
    "skip": ("Skip Tutorial", "Fate's Draft", ["Pick three cards and go.", "You can read How to Play any time."]),
}


def _fmt_time(secs):
    secs = int(secs)
    return "--:--" if secs <= 0 else "%d:%02d" % (secs // 60, secs % 60)


class TitleScene(Scene):
    def __init__(self, services, done=None, can_continue=False, tutorial_done=False):
        super().__init__(done)
        self.svc = services
        self.can_continue = can_continue
        self.tutorial_done = tutorial_done
        self.mode = "main"
        self.items = []
        self.sel = 0
        self.buttons = [W.Button(BTN_X, BTN_Y0 + i * BTN_PITCH, BTN_W, BTN_H) for i in range(3)]
        self.footer = W.Footer(left=[("txt", "Demo")], hints=[], divider_line=False)
        self._band_dirty = True
        self._records_drawn = False
        self._candle = None
        self._stars = [None] * len(STARS)
        self._full_done = False
        self._set_mode("main")

    def region(self, key):
        return None

    # ------------------------------------------------------------------ modes
    def _set_mode(self, mode):
        self.mode = mode
        if mode == "main":
            self.items = [("Begin the Night", "begin")]
            if self.can_continue:
                self.items.append(("Continue", "continue"))
            self.items.append(("Records", "records"))
            self.sel = 1 if self.can_continue else 0
            hints = [("A", "Select"), ("C", "Info")]
        elif mode == "choice":
            self.items = [("Learn to Play", "learn"), ("Skip Tutorial", "skip")]
            self.sel = 1 if self.tutorial_done else 0
            hints = [("A", "Go"), ("B", "Back"), ("C", "Info")]
        else:
            self.items = []
            hints = [("A", "Back")]
        self.footer.set_hints(hints)
        self._band_dirty = True

    # ------------------------------------------------------------------ input
    def update(self, ctl, dt):
        if self.mode == "records":
            if ctl.a or ctl.b:
                self._set_mode("main")
            return
        n = len(self.items)
        if ctl.dy:
            self.sel = step(self.sel, ctl.dy, n)
        if ctl.c:
            self.app.open(W.InfoOverlay(*HELP[self.items[self.sel][1]]))
            return
        if ctl.b and self.mode == "choice":
            self._set_mode("main")
            self.sel = 0
            return
        if ctl.a:
            key = self.items[self.sel][1]
            if key == "begin":
                if self.can_continue:
                    self.app.confirm("Start a new night?\nYour saved night will be lost.",
                                     lambda: self._set_mode("choice"), yes="Start over", no="Keep it")
                else:
                    self._set_mode("choice")
            elif key == "records":
                self._set_mode("records")
            else:
                self.finish(key)

    # ------------------------------------------------------------------ drawing
    def draw(self, scr, full):
        if full:
            scr.blit(T.asset("bg_title"), 0, 0, 0)
            self._band_dirty = True
            self._candle = None
            self._stars = [None] * len(STARS)
            self._records_drawn = False
        self._animate(scr)
        if self._band_dirty:
            self._band_dirty = False
            self._records_drawn = False
            scr.fill_rect(*BAND, T.GROUND)
            for b in self.buttons:
                b.invalidate()
            self.footer.invalidate()
        if self.mode == "records":
            self._draw_records(scr)
        else:
            for i, b in enumerate(self.buttons):
                if i < len(self.items):
                    b.set(self.items[i][0], focused=i == self.sel)
                    b.draw(scr, False)
        self.footer.draw(scr, False)
        self._full_done = True

    def _draw_records(self, scr):
        if self._records_drawn:
            return
        self._records_drawn = True
        p = self.svc.profile
        W.panel(scr, 100, 238, 280, 52)
        rows = (("Wins", str(p.wins)), ("Best hit", str(p.best_hit)),
                ("Fastest", _fmt_time(p.fastest)), ("Nights lost", str(p.deaths)))
        for i, (label, value) in enumerate(rows):
            x = 116 + (i % 2) * 136
            y = 244 + (i // 2) * 20
            scr.text(x, y, label, T.MUTED, T.PANEL)
            scr.text(x + 76, y, value, T.ACCENT, T.PANEL)

    def _animate(self, scr):
        t = self.app.time
        frame = int(t * 4) % 2
        if self._candle != frame:
            self._candle = frame
            x, y = CANDLE
            scr.asset_region(T.asset("bg_title"), 0, x, y, x, y, 5, 20)
            scr.blit(T.asset("ui_candle"), frame, x, y)
        sparkle = T.asset("ui_sparkle")
        for i, (x, y, off) in enumerate(STARS):
            state = STAR_CYCLE[int((t + off) * 1.5) % len(STAR_CYCLE)]
            if state != self._stars[i]:
                self._stars[i] = state
                scr.asset_region(T.asset("bg_title"), 0, x, y, x, y, 5, 5)
                if state is not None:
                    scr.blit(sparkle, state, x, y)
