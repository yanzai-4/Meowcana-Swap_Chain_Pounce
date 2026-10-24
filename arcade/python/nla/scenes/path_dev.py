"""Dev harness for the Path scenes: a stub Services, a plain card picker (used only when Spread's real picker is not
importable) and one factory per scene for the simulator, e.g.

    python tools/sim.py --game nla.scenes.path:dev_path --keys "3s,R,A" --shots build/shots/path/

Every factory returns an App whose first scene is the scene under test; when the scene calls done(result) the harness
shows a one-line DoneScene with the result so the screenshot proves the exit. `Services.dev()` from nla.flow is the
real thing; this stub only provides the same attribute names.
"""

from nla import story
from nla.rules import cards
from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import App, Scene


class DoneScene(Scene):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def draw(self, scr, full):
        if full:
            scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
            scr.text_center(150, "done: %s" % self.text, T.ACCENT, T.GROUND, T.TITLE)


class DevPicker(Scene):
    """Plain card picker: Spread row then Box row, A picks, B cancels."""

    def __init__(self, purpose, selectable, done, button="Cancel"):
        super().__init__(done)
        self.purpose, self.sel_uids, self.button = purpose, set(selectable), button
        self.items = []
        self.i = 0

    def enter(self, app):
        super().enter(app)
        self.run = app.services.run
        self.items = [c for c in self.run.spread + self.run.box if c is not None and c.uid in self.sel_uids]
        self.views = []
        for k, c in enumerate(self.items):
            v = W.CardView(24 + 58 * (k % 7), 70 + 80 * (k // 7))
            v.set_card(c)
            self.views.append(v)
        self.cursor = W.Cursor()
        self.drawn = None

    def update(self, ctl, dt):
        if ctl.dx and self.items:
            self.i = (self.i + ctl.dx) % len(self.items)
        if ctl.a and self.items:
            self.finish(self.items[self.i].uid)
        elif ctl.b:
            self.finish(None)

    def draw(self, scr, full):
        if full:
            scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
            scr.text(16, 16, self.purpose, T.LABEL, T.GROUND)
            for v in self.views:
                v.draw(scr, True)
            W.Footer(hints=[("A", "Pick"), ("B", self.button)]).draw(scr, True)
            self.cursor.invalidate()
        if self.views:
            v = self.views[self.i]
            self.cursor.to(v.x, v.y, v.w, v.h)
        self.cursor.draw(scr, full)


class StubServices:
    """Same names as nla.flow.Services (see the Flow contract)."""

    def __init__(self, app, run):
        self.app = app
        app.services = self
        self.run = run
        self.profile = None
        self.tutor = None
        self.seen = set()
        self.saves = 0
        self.reports = []

    def report(self, key):
        self.reports.append(key)

    def pick_card(self, purpose, selectable, on_pick, button="Cancel"):
        try:
            from nla.scenes.picker import PickerScene as Picker
        except ImportError:
            Picker = DevPicker

        def picked(uid):
            self.app.pop(transition=False)
            on_pick(uid)
        self.app.push(Picker(self, purpose, list(selectable), picked, button) if Picker is not DevPicker
                      else DevPicker(purpose, list(selectable), picked, button))

    def menu(self):
        from nla.scenes.menu import MenuScene

        def result(r):
            self.app.pop()
        self.app.push(MenuScene(self, result))

    def tip(self, key, then=None):
        lines = story.TIPS.get(key)
        if key in self.seen or not lines:
            if then:
                then()
            return
        self.seen.add(key)
        self.app.say(lines, then)

    def say(self, lines, then=None):
        self.app.say(lines, then)

    def card_info(self, card):
        self.app.card_info(card)

    def save(self):
        self.saves += 1


def make_run(seed=7, step=0, treats=None, hp=None, curse=False, trail=True):
    run = R.new_run(seed, False)
    run.step = step
    if treats is not None:
        run.treats = treats
    if hp is not None:
        run.hp = hp
    if trail:
        run.flags["trail"] = [0] * step
    if curse:
        run.spread[1].charm = cards.RAT_BITE
    return run


def boot(factory, run=None, **run_kw):
    app = App()
    sv = StubServices(app, run or make_run(**run_kw))

    def done(result=None):
        app.push(DoneScene(repr(getattr(result, "kind", result))))
    app.push(factory(sv, done))
    return app


# --------------------------------------------------------------------------- factories
def dev_path(step=0, treats=None):
    from nla.scenes.path import PathScene
    return boot(PathScene, step=step, treats=treats)


def dev_path_boss():
    return dev_path(step=R.STEPS)


def _node_run(kind, key="", step=2, **kw):
    run = make_run(step=step, **kw)
    node = R.Node(kind, key, kind)
    run.current = node
    return run


def dev_stall(treats=40, curse=True):
    from nla.scenes.stall import StallScene
    run = _node_run("stall", treats=treats, curse=curse)
    return boot(StallScene, run)


def dev_catbed(hp=18, curse=False):
    from nla.scenes.catbed import CatBedScene
    run = _node_run("bed", hp=hp, curse=curse)
    return boot(CatBedScene, run)


def dev_encounter(key="lost_mouse", hp=20):
    from nla.scenes.encounter import EncounterScene
    run = _node_run("encounter", key, hp=hp)
    return boot(EncounterScene, run)


def dev_box(full_box=False):
    from nla.scenes.box import BoxScene
    run = _node_run("box")
    if full_box:
        for i in range(run.box_size):
            run.box[i] = cards.Card(i + 1, False, 0, 0, 100 + i)
    return boot(BoxScene, run)


def dev_levelup(levels=1):
    from nla.scenes.levelup import LevelUpScene
    run = make_run(step=3)
    run.level = 1 + levels
    run.pending_levels = list(range(2, 2 + levels))
    return boot(LevelUpScene, run)


def dev_menu():
    from nla.scenes.menu import MenuScene
    return boot(MenuScene, step=3)


def _enc_factory(key):
    def factory():
        return dev_encounter(key)
    factory.__name__ = "dev_enc_" + key
    return factory


for _key in R.ENCOUNTERS:           # python tools/sim.py --game nla.scenes.path_dev:dev_enc_yarn_ball
    globals()["dev_enc_" + _key] = _enc_factory(_key)


def dev_stall_poor():
    return dev_stall(treats=1)


def dev_levelup2():
    return dev_levelup(levels=2)


def dev_box_full():
    return dev_box(full_box=True)
