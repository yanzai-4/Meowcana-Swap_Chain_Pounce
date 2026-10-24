"""Fate's Draft (the skip path) and the How to Play recap.

    Draft(services, done, first_pick=0).start()   three Pick 1 of 3 screens, then the recap, then done()
    HowToPlayScene(services, done, button="Continue")   one screen of story.HOW_TO_PLAY; A or B closes it

The picks are `rules.run.draft_options(run, i)`: the same pools the tutorial rewards use, so both paths enter the
attic with the same deck strength. Zero frames each pick with a line from story.SCENES (draft_intro, draft_pick2,
draft_pick3, draft_done). Starting at `first_pick > 0` finishes a skipped tutorial.
"""

from nla import story
from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene

PICKS = 3
_FRAMING = ("draft_intro", "draft_pick2", "draft_pick3")


class Draft:
    def __init__(self, services, done, first_pick=0):
        self.svc = services
        self.done = done
        self.i = first_pick

    def start(self):
        if self.i >= PICKS:
            self._recap()
        else:
            self._pick()

    def _pick(self):
        from nla.flow import scene_class, _after
        svc = self.svc
        svc.run.flags["draft_pick"] = self.i            # a saved night resumes at this pick
        scene = scene_class("RewardScene")(svc, R.draft_options(svc.run, self.i), self._picked,
                                           title="Fate's Draft: Card %d of %d" % (self.i + 1, PICKS),
                                           skip_treats=0)
        svc.app.switch(scene)
        lines = story.SCENES[_FRAMING[min(self.i, PICKS - 1)]]
        _after(svc.app, lambda: svc.say(lines))

    def _picked(self, card):
        self.i += 1
        self.start()

    def _recap(self):
        svc = self.svc
        svc.run.flags["draft_pick"] = PICKS
        svc.app.switch(HowToPlayScene(svc, self._recap_done))

    def _recap_done(self, _=None):
        self.svc.run.flags.pop("draft_pick", None)
        self.svc.say(story.SCENES["draft_done"], self.done)


class HowToPlayScene(Scene):
    """One static page; it is drawn once and then costs nothing."""

    def __init__(self, services, done=None, button="Continue"):
        super().__init__(done)
        self.svc = services
        self.page = story.HOW_TO_PLAY
        self.footer = W.Footer(left=[("txt", "How to Play")], hints=[("A", button)])

    def update(self, ctl, dt):
        if ctl.a or ctl.b:
            self.finish()

    def region(self, key):
        return None

    def draw(self, scr, full):
        if full:
            scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
            W.panel(scr, 8, 8, T.SCREEN_W - 16, 282)
            scr.text_center(14, self.page.title, T.LABEL, T.PANEL, T.TITLE)
            W.divider(scr, 40, T.SCREEN_W - 41, 46, bg=T.PANEL)
            y = 54
            for row in self.page.rows:
                if row:
                    head = len(row) > 2 and row[1] == " " and row[0] in "ABC"
                    if head:
                        letter = row[0]
                        scr.blit(T.asset("ui_btn"), W._BTN[letter], 28, y + 1, bg=T.PANEL)
                        scr.text(48, y, row[1:].strip(), T.TEXT, T.PANEL, T.BODY)
                    else:
                        scr.text(28, y, row, T.MUTED, T.PANEL, T.BODY)
                y += 19
        self.footer.draw(scr, full)
