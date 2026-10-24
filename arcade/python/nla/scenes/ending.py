"""Demo End: bg_end, Zero's goodbye (story.SCENES["demo_end"]), then the big-letter screen (DEMO_END_SCREEN).

    EndingScene(services, done)      done() on A

The art stays up while the goodbye plays; the title block is painted into the flat text band afterwards.
"""

from nla import story
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene

BAND_Y = 236


class EndingScene(Scene):
    def __init__(self, services, done=None):
        super().__init__(done)
        self.svc = services
        self.screen = story.DEMO_END_SCREEN
        self.phase = "art"            # art -> lines -> screen
        self.footer = W.Footer(hints=[("A", self.screen["footer"].split(":", 1)[-1].strip())], y=302, h=17,
                               divider_line=False)

    def region(self, key):
        return None

    def update(self, ctl, dt):
        if self.phase == "lines":
            return
        if self.phase == "art":
            self.phase = "lines"
            self.app.say(story.SCENES["demo_end"], self._goodbye_done)
        elif ctl.a:
            self.finish()

    def _goodbye_done(self):
        self.phase = "screen"

    def draw(self, scr, full):
        if full:
            scr.blit(T.asset("bg_end"), 0, 0, 0)
            scr.fill_rect(0, BAND_Y, T.SCREEN_W, T.SCREEN_H - BAND_Y, T.GROUND)
            self.footer.invalidate()
            if self.phase == "screen":
                self._paint_text(scr)
        elif self.phase == "screen" and not getattr(self, "_text", False):
            self._paint_text(scr)
        if self.phase == "screen":
            self.footer.draw(scr, False)

    def _paint_text(self, scr):
        self._text = True
        th = T.text_h(T.TITLE)
        y = BAND_Y + 1
        scr.text_center(y, self.screen["title"], T.FOCUS, T.GROUND, T.TITLE)
        y += th
        scr.text_center(y, self.screen["subtitle"], T.LABEL, T.GROUND)
        y += 17
        for line in self.screen["body"]:
            scr.text_center(y, line, T.MUTED, T.GROUND)
            y += 14
