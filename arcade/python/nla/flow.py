"""Run lifecycle: Services (what every scene talks to) and the Flow that wires the scenes together.

    app = make()                     # the UIKit App the engine Runner drives; starts at the Title

Graph (every arrow is a scene `done` callback; scenes never import each other):

    Title -> opening cutscene -> Tutorial (3 lessons) | Fate's Draft -> enter_attic cutscene -> Night Path
    Night Path -> node -> (fight/elite/boss: [intro] Spread -> Battle -> [defeated] Reward -> Level Ups)
                       -> (stall / cat bed / encounter / box scenes) -> finish_node + save -> Night Path
    Boss win -> chubbs_defeated -> Reward -> ending cutscene -> Demo End -> Parlor
    Defeat   -> Nine Bells -1 -> (first_death | dream | parlor_return) -> Parlor -> Start Night -> Fate's Draft

`Services` is the object handed to every scene as `services` (see docs/demo-plan.md section 6):
    app, run, profile, tutor, report(key), pick_card(...), menu(), tip(key, then), say(lines, then),
    card_info(card), save().  `Services.dev()` builds one without the Title for scene dev harnesses.

`FlowApp` is the UIKit App plus three tutorial hooks: a gated Input (the coach masks buttons per step), a pulsing
arrow drawn above the scene, and `after_change(fn)` (run fn once the pending scene change has been applied, so a
dialogue opened for the new scene is not wiped by the change).

Saves live in `<app root>/data/` (`run.json`, `profile.json`); NLA_DATA_DIR overrides it (simulator runs).
"""

import importlib
import os
import random

from nla import story
from nla.rules import run as R
from nla.rules import save as S
from nla.rules.battle import simulate
from nla.rules.enemies import ENEMIES
from nla.ui import theme as T
from nla.ui.app import App
from nla.ui.input import Input

_SCENE_MODULES = {
    "SpreadScene": "spread", "RewardScene": "reward", "PickerScene": "picker", "BattleScene": "battle",
    "PathScene": "path", "StallScene": "stall", "CatBedScene": "catbed", "EncounterScene": "encounter",
    "BoxScene": "box", "LevelUpScene": "levelup", "MenuScene": "menu",
}

NODE_SCENES = {"stall": "StallScene", "bed": "CatBedScene", "encounter": "EncounterScene", "box": "BoxScene"}


def scene_class(name):
    """Sibling scene classes are imported on first use (keeps start-up light, and Flow loadable on its own)."""
    return getattr(importlib.import_module("nla.scenes." + _SCENE_MODULES[name]), name)


def default_data_dir():
    env = os.environ.get("NLA_DATA_DIR")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))           # <root>/python/nla
    return os.path.join(os.path.dirname(os.path.dirname(here)), "data")


# =============================================================================================== app
class GatedInput(Input):
    """Input whose per-frame result can be masked (the tutorial coach blocks buttons that are off-topic)."""

    mask = None

    def update(self, ctl, dt):
        super().update(ctl, dt)
        if self.mask is not None:
            self.mask(self)


class FlowApp(App):
    def __init__(self):
        self._after = []
        self.tutor = None
        super().__init__(None)
        self.input = GatedInput()
        self.input.mask = self._mask

    def after_change(self, fn):
        """Run fn after the scene change that is pending now has been applied (now, if none is pending)."""
        if self._trans is not None:
            self._after.append(fn)
        else:
            fn()

    def _apply(self, fn):
        super()._apply(fn)
        after, self._after = self._after, []
        for f in after:
            f()

    def _mask(self, inp):
        if self.tutor is not None:
            self.tutor.gate(inp)

    def update(self, controls, dt):
        super().update(controls, dt)
        if self.tutor is not None:
            self.tutor.tick(dt)

    def draw(self, scr, full):
        super().draw(scr, full)
        if self.tutor is not None and self._trans is None:
            self.tutor.draw_over(scr, self.kind)


# ======================================================================================== services
class Services:
    def __init__(self, app, profile=None, data_dir=None, run=None, flow=None):
        self.app = app
        self.run = run
        self.profile = profile if profile is not None else S.Profile()
        self.tutor = None
        self.data_dir = data_dir
        self.flow = flow
        self._mark = app.time

    # ------------------------------------------------------------------ paths
    @property
    def run_path(self):
        return os.path.join(self.data_dir, "run.json")

    @property
    def profile_path(self):
        return os.path.join(self.data_dir, "profile.json")

    @classmethod
    def dev(cls, app=None, run=None, profile=None, seed=1):
        """Services for a scene harness: real FlowApp, a fresh run, no saves, no Title."""
        app = app if app is not None else FlowApp()
        if run is None:
            run = R.new_run(seed, False)
        return cls(app, profile, None, run)

    # ------------------------------------------------------------------ the contract
    def report(self, key):
        if self.tutor is not None:
            self.tutor.report(key)

    def pick_card(self, purpose, selectable, on_pick, button="Cancel"):
        app = self.app
        picker = scene_class("PickerScene")

        def done(uid):
            app.pop(uid)
            _after(app, lambda: on_pick(uid))

        app.push(picker(self, purpose, selectable, done, button))

    def menu(self):
        if self.tutor is not None:
            self.tutor.menu()
            return
        app = self.app
        app.push(scene_class("MenuScene")(self, self._menu_done))

    def _menu_done(self, choice):
        app = self.app
        if choice == "how_to_play":
            from nla.scenes.draft import HowToPlayScene
            app.push(HowToPlayScene(self, lambda _=None: app.pop()))
        elif choice == "save_quit" and self.flow is not None:
            self.flow.save_quit()
        elif choice == "abandon" and self.flow is not None:
            self.flow.abandon()
        else:
            app.pop()

    def tip(self, key, then=None):
        """Zero's first-time tip (story.TIPS[key]): once per profile, never during the tutorial. then() always runs."""
        run, profile = self.run, self.profile
        lines = story.TIPS.get(key)
        seen = key in profile.tips_seen
        if run is not None:
            armed = key in run.tips
            if armed or not seen:
                R.consume_tip(run, profile, key)
        elif not seen:
            profile.tips_seen.append(key)
        if not lines or seen or (run is not None and run.tutorial):
            if then:
                then()
            return
        self.app.say(lines, then)

    def say(self, lines, then=None):
        self.app.say(lines, then)

    def card_info(self, card):
        self.app.card_info(card)

    def save(self):
        if self.data_dir is None:
            return
        try:
            S.save_profile(self.profile, self.profile_path)
            run = self.run
            if run is not None and not run.tutorial and not run.done:
                self.tick_clock()
                S.save_run(run, self.run_path)
        except OSError:
            pass                                   # a read-only card must never crash the game

    def tick_clock(self):
        """Fold the play time since the last mark into run.stats["secs"]."""
        now = self.app.time
        if self.run is not None:
            self.run.stats["secs"] = self.run.stats.get("secs", 0) + (now - self._mark)
        self._mark = now

    def flush_tips(self, then=None):
        """Play every tip the Rules armed (first Major, first Curse, ...) one after another, then then()."""
        key = R.pending_tip(self.run, self.profile) if self.run is not None else ""
        if not key:
            if then:
                then()
            return
        self.tip(key, lambda: self.flush_tips(then))


def _after(app, fn):
    hook = getattr(app, "after_change", None)
    if hook is None:
        fn()
    else:
        hook(fn)


# ============================================================================================ flow
class Flow:
    def __init__(self, data_dir=None):
        self.data_dir = data_dir
        profile = S.load_profile(os.path.join(data_dir, "profile.json")) if data_dir else S.Profile()
        self.app = FlowApp()
        self.svc = Services(self.app, profile, data_dir, flow=self)
        self.app.flow = self
        self.tutorial = None
        self.quip = 0
        self.title(transition=False)

    # ------------------------------------------------------------------ helpers
    def _show(self, scene, tips=True):
        """Switch to `scene`; the armed first-time tips then play on top of it."""
        self.app.switch(scene)
        if tips:
            _after(self.app, self.svc.flush_tips)

    def _cutscene(self, key, then, **kw):
        from nla.scenes.cutscene import CutsceneScene
        self.app.switch(CutsceneScene(self.svc, key, lambda _=None: then(), **kw))

    def _saved_run(self):
        if not self.data_dir:
            return None
        return S.load_run(self.svc.run_path)

    # ------------------------------------------------------------------ title / new run
    def title(self, transition=True):
        from nla.scenes.title import TitleScene
        self.svc.tutor = None
        self.app.tutor = None
        self.tutorial = None
        self._continue = self._saved_run()
        scene = TitleScene(self.svc, self._title_done, can_continue=self._continue is not None,
                           tutorial_done=bool(self.svc.profile.flags.get("tutorial_done")))
        self.app.reset(scene, transition=transition)

    def _title_done(self, choice):
        if choice == "continue":
            self.svc.run = self._continue
            self.svc.tick_clock()
            self._resume()
        else:
            self._new_run(tutorial=(choice == "learn"), opening=True)

    def _new_run(self, tutorial, opening):
        svc = self.svc
        if self.data_dir:
            S.delete_run(svc.run_path)
        svc.run = R.new_run(random.getrandbits(30), tutorial, bells=svc.profile.bells)
        svc.profile.runs += 1
        svc.tick_clock()
        if self.data_dir:
            S.save_profile(svc.profile, svc.profile_path)       # the run itself is saved from the Night Path on
        start = self._start_tutorial if tutorial else self._start_draft
        if opening:
            self._cutscene("opening", start)
        else:
            start()

    def _start_tutorial(self):
        from nla.scenes.tutorial import Tutorial
        self.tutorial = Tutorial(self.svc, self)
        self.tutorial.start()

    def _start_draft(self, first_pick=0):
        from nla.scenes.draft import Draft
        Draft(self.svc, self._enter_attic, first_pick).start()

    def tutorial_finished(self):
        """All three lessons done: graduate, then the attic."""
        svc = self.svc
        R.finish_tutorial(svc.run)
        svc.profile.flags["tutorial_done"] = True
        svc.tutor = None
        self.app.tutor = None
        svc.save()
        self._cutscene("tutorial_graduate", self._enter_attic, lines=story.TUTORIAL[-1].lines)

    def tutorial_skipped(self, picks):
        """Skip Tutorial from the menu: back to the starting Spread, then the remaining Draft picks."""
        svc = self.svc
        R.finish_tutorial(svc.run)
        svc.tutor = None
        self.app.tutor = None
        self.tutorial = None
        self._start_draft(first_pick=picks)

    # ------------------------------------------------------------------ chapter 1
    def _enter_attic(self):
        self._cutscene("enter_attic", self._path)

    def _resume(self):
        run = self.svc.run
        if run.current is not None:
            self._node_chosen(run.current)
        else:
            self._path()

    def _path(self):
        self.svc.save()
        self._show(scene_class("PathScene")(self.svc, self._node_chosen))

    def _node_chosen(self, node):
        if node.kind in ("fight", "elite", "boss"):
            self._start_fight(node)
        else:
            cls = scene_class(NODE_SCENES[node.kind])
            self._show(cls(self.svc, lambda _=None: self._node_done()))

    def _node_done(self):
        run = self.svc.run
        R.finish_node(run)
        self.svc.save()
        self._path()

    # ------------------------------------------------------------------ fights
    def _start_fight(self, node):
        enemy = ENEMIES[node.key]
        boss = node.kind == "boss"
        won = self._boss_won if boss else self._node_done
        if node.key + "_intro" in story.SCENES:
            self._cutscene(node.key + "_intro", lambda: self.fight(enemy, won))
        else:
            self.fight(enemy, won)

    def fight(self, enemy, on_won, lesson=None):
        """Spread -> simulate -> Battle -> (defeated story) -> Reward -> Level Ups -> on_won()."""
        svc = self.svc
        spread = scene_class("SpreadScene")

        def to_battle(_=None):
            result = simulate(svc.run, enemy, R.battle_seed(svc.run))
            battle = scene_class("BattleScene")
            self.app.switch(battle(svc, enemy, result, lambda r: after_battle(result, r)))

        def after_battle(result, _r):
            if not result.won:
                self._lost(lesson)
                return
            rewards = R.battle_rewards(svc.run, enemy, result)
            story_key = enemy.key + "_defeated"
            if story_key in story.SCENES:
                self._cutscene(story_key, lambda: reward(rewards))
            else:
                reward(rewards)

        def reward(rewards):
            skip = rewards.skip_treats
            if lesson is not None:
                skip = 0 if lesson == 0 else R.SKIP_TREATS
            scene = scene_class("RewardScene")(svc, rewards.options, lambda card: self._levels(on_won),
                                               skip_treats=skip)
            self.app.switch(scene)


        self._show(spread(svc, enemy, to_battle, lesson=lesson), tips=lesson is None)

    def _levels(self, then):
        run = self.svc.run
        if run.tutorial or not run.pending_levels:
            then()
            return
        pending = len(run.pending_levels)

        def done(_=None):
            if len(run.pending_levels) < pending:
                self._levels(then)
            else:
                then()

        self._show(scene_class("LevelUpScene")(self.svc, done), tips=False)

    # ------------------------------------------------------------------ end of the night
    def _boss_won(self):
        svc = self.svc
        run = svc.run
        run.done = True
        svc.tick_clock()
        S.record_win(svc.profile, run, run.stats.get("secs", 0))
        if self.data_dir:
            S.delete_run(svc.run_path)
        svc.save()
        self._cutscene("ending", self._demo_end)

    def _demo_end(self):
        from nla.scenes.ending import EndingScene
        self.app.switch(EndingScene(self.svc, lambda _=None: self._parlor(dying=False, lines=None)))

    def _lost(self, lesson):
        svc = self.svc
        if lesson is not None:                      # tutorial: no bell, just try the lesson again
            self.tutorial.retry()
            return
        n = S.record_death(svc.profile, svc.run)
        if self.data_dir:
            S.delete_run(svc.run_path)
        svc.run.done = True
        svc.save()
        if n == 3:
            self._cutscene("third_death_dream", lambda: self._parlor(dying=True, lines=None))
        elif n == 1:
            self._parlor(dying=True, lines=story.SCENES["first_death"])
        else:
            self._parlor(dying=True, lines=story.SCENES["parlor_return"])

    def _parlor(self, dying, lines):
        from nla.scenes.parlor import ParlorScene
        quip = story.PARLOR_QUIPS[self.quip % len(story.PARLOR_QUIPS)]
        self.quip += 1
        scene = ParlorScene(self.svc, self._parlor_done, dying=dying, lines=lines, quip=quip)
        self.app.switch(scene)

    def _parlor_done(self, choice):
        if choice == "title":
            self.title()
        else:
            self._new_run(tutorial=False, opening=False)

    # ------------------------------------------------------------------ menu actions
    def save_quit(self):
        self.svc.save()
        self.title()

    def abandon(self):
        svc = self.svc
        if self.data_dir:
            S.delete_run(svc.run_path)
        svc.run.done = True
        svc.save()
        self._parlor(dying=False, lines=None)


def make(data_dir=None):
    """The game object for the engine Runner (and `tools/sim.py --game nla.flow:make`)."""
    return Flow(data_dir if data_dir is not None else default_data_dir()).app
