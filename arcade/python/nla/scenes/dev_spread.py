"""Dev harness support for the Spread, Picker and Reward scenes: a stub `Services` that needs no Flow.

    sv = StubServices(run)            # run = nla.rules.run.RunState
    app = make_app(sv, lambda: SomeScene(sv, ...))      # a UIKit App showing the scene (sv.app is set)

Simulator: `python tools/sim.py --game nla.scenes.spread:dev_spread --keys "1.6s,..." --shots build/shots/spread/`.
"""

from nla.rules import cards, run as R
from nla import story
from nla.ui import theme as T
from nla.ui.app import App, Scene


class _StubMenu(Scene):
    """Stands in for the Menu scene: A or B closes it."""

    def __init__(self, sv):
        super().__init__()
        self.sv = sv

    def update(self, ctl, dt):
        if ctl.a or ctl.b:
            self.sv.app.pop(transition=False)

    def draw(self, scr, full):
        if full:
            scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
            scr.text_center(150, "Menu (stub)", T.LABEL, T.GROUND, T.TITLE)
            scr.text_center(180, "A or B to close", T.MUTED, T.GROUND)


class StubServices:
    def __init__(self, run, tutor=None):
        self.app = None
        self.run = run
        self.profile = None
        self.tutor = tutor
        self.reports = []
        self._tips = set()

    def report(self, key):
        self.reports.append(key)
        print("report:", key)

    def pick_card(self, purpose, selectable, on_pick, button="Cancel"):
        from .picker import PickerScene

        def done(uid):
            self.app.pop(transition=False)
            on_pick(uid)

        self.app.push(PickerScene(self, purpose, selectable, done, button))

    def menu(self):
        self.app.push(_StubMenu(self))

    def tip(self, key, then=None):
        lines = story.TIPS.get(key)
        if lines and key not in self._tips and self.tutor is None:
            self._tips.add(key)
            self.app.say(lines, then)
        elif then:
            then()

    def say(self, lines, then=None):
        self.app.say(lines, then)

    def card_info(self, card):
        self.app.card_info(card)

    def save(self):
        pass


def make_app(sv, factory):
    app = App()
    sv.app = app
    app.push(factory())
    return app


def dev_run(boss=False):
    """A run for screenshots. Normal: Lesson 2's Spread (Fire 3, Fire 4, Water 3, Air 5 reversed: one Hiss) and a
    Box holding a second Water 3 (merges), a Magician and a Water 6. Boss: six Minors for Chubbs' bite marker."""
    run = R.new_run(11, False)
    if boss:
        run.spread_size = 6
        faces = [(1, False), (12, False), (23, False), (4, False), (35, False), (6, True)]
    else:
        faces = [(2, False), (3, False), (22, False), (14, True)]
    run.spread = []
    for d, r in faces:
        run.spread.append(cards.Card(d, r, 0, 0, run.next_uid))
        run.next_uid += 1
    run.box = [None] * run.box_size
    for k, c in enumerate([cards.Card(22, False, 0, 2), cards.Card(41, False, 0, 0), cards.Card(25, False, 1, 0)]):
        c.uid = run.next_uid
        run.next_uid += 1
        run.box[k] = c
    return run
