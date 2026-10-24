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
import traceback

from nla import story
from nla.rules import run as R
from nla.rules import save as S
from nla.rules.battle import simulate
from nla.rules.cards import Card
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
HOLD_B = 0.6          # seconds of holding B that open the pause Menu on any screen
PIP_AFTER = 0.25      # the progress pip only shows for holds longer than a tap
PIP = (214, 301, 84, 19)


class GatedInput(Input):
    """Input whose per-frame result can be masked (the tutorial coach blocks buttons that are off-topic).

    B is deferred: its press edge is swallowed and delivered as a tap when B is released early, so a hold of HOLD_B
    seconds can open the Menu on any screen without the screen first reacting to the press."""

    mask = None
    on_hold = None          # callable() -> bool: True when it opened the Menu

    def __init__(self):
        super().__init__()
        self.b_time = 0.0       # seconds B has been held (0 when not held)
        self._b_down = False
        self._b_fired = False

    def update(self, ctl, dt):
        super().update(ctl, dt)
        if self.b:
            self.b = False
            self._b_down, self._b_fired, self.b_time = True, False, 0.0
        if self._b_down:
            if self.held_b:
                self.b_time += dt
                if not self._b_fired and self.b_time >= HOLD_B and self.on_hold is not None and self.on_hold():
                    self._b_fired = True
            else:
                if not self._b_fired:
                    self.b = True
                self._b_down, self._b_fired, self.b_time = False, False, 0.0
        if self.mask is not None:
            self.mask(self)


class FlowApp(App):
    def __init__(self):
        self._after = []
        self.crashed = False
        self._crash_drawn = False
        self.tutor = None
        super().__init__(None)
        self.input = GatedInput()
        self.input.mask = self._mask
        self.input.on_hold = self._hold
        self._pip = None        # (scene, filled px) while the hold pip is on screen
        self._held, self._armed, self._calm = None, False, 0

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

    def _hold(self):
        flow = getattr(self, "flow", None)
        if self.crashed or flow is None or not flow.menu_allowed():
            return False
        flow.svc.menu()
        return True

    def _draw_pip(self, scr, kind):
        """Progress pip near the footer's B gem while B is held: 'Hold B: Menu' + a fill bar. Only for holds longer
        than a tap; erased through the scene's own restore()."""
        inp = self.input
        flow = getattr(self, "flow", None)
        t = inp.b_time if inp._b_down and not inp._b_fired and inp.held_b else 0.0
        show = t >= PIP_AFTER and flow is not None and self._trans is None and flow.menu_allowed()
        x, y, w, h = PIP
        if show:
            fill = int((w - 2) * min(1.0, t / HOLD_B))
            if self._pip is None or kind == "full" or self._pip[0] is not self.scene:
                scr.fill_rect(x, y, w, h, T.PANEL)
                scr.rect(x, y, w, h, T.RULE)
                scr.text(x + 6, y + 1, "Hold B: Menu", T.ACCENT, T.PANEL)
                self._pip = (self.scene, -1)
            if self._pip[1] != fill:
                scr.fill_rect(x + 1, y + h - 3, fill, 2, T.AMBER2)
                scr.fill_rect(x + 1 + fill, y + h - 3, w - 2 - fill, 2, T.PANEL)
                self._pip = (self.scene, fill)
        elif self._pip is not None:
            scene, self._pip = self._pip[0], None
            if (scene is self.scene and kind != "full" and self._trans is None
                    and not any(o.full_screen for o, _ in self.overlays)):
                scene.restore(scr, PIP)

    def hold_overlays(self, overlays):
        """Overlays set aside by the Menu: put back once the scene below has finished repainting (an overlay on top
        stops the scene's own progressive repaint, so they wait until a few frames in a row are cheap)."""
        self._held, self._armed, self._calm = list(overlays), False, 0
        if overlays:
            _after(self, self._arm)

    def _arm(self):
        self._armed = True

    def _release_overlays(self, scr):
        if self._held is None or not self._armed:
            return
        ms = scr.stats()["ms"]
        self._calm = self._calm + 1 if (self.kind != "full" and self.kind != "transition" and ms < 30) else 0
        if self._calm >= 3:
            held, self._held = self._held, None
            self.overlays.extend(held)
            for overlay, _ in held:
                overlay.draw(scr, True)

    def update(self, controls, dt):
        if self.crashed:
            self.input.update(controls, dt)
            if self.input.a:
                self._recover()
            return
        try:
            if self._held is not None and self._armed:
                self.time += dt                      # frozen: the scene repaints itself (dt 0), overlays come back after
                self.input.update(controls, dt)
                if self._trans is None and self.scene is not None:
                    self.scene.update(Input(), 0.0)
                return
            super().update(controls, dt)
            if self.tutor is not None:
                self.tutor.tick(dt)
        except Exception:
            self._crash()

    def draw(self, scr, full):
        if not self.crashed:
            try:
                super().draw(scr, full)
                if self.tutor is not None and self._trans is None:
                    self.tutor.draw_over(scr, self.kind)
                self._draw_pip(scr, self.kind)
                self._release_overlays(scr)
                return
            except Exception:
                self._crash()
        self.busy = full or not self._crash_drawn
        if self.busy:
            self._crash_drawn = True
            scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
            scr.text_center(110, "Something went wrong", T.FOCUS, T.GROUND, font=T.TITLE, scale=2)
            scr.text_center(180, "Your night is safe.", T.TEXT, T.GROUND)
            scr.text_center(210, "Press A to go on", T.LABEL, T.GROUND)

    # ------------------------------------------------------------------ last-resort guard
    def _crash(self):
        """A scene raised: log it once, drop every layer and wait for A (never retry the frame)."""
        traceback.print_exc()
        self.crashed = True
        self._crash_drawn = False
        self.tutor = None
        self._trans = None
        self._after = []
        self.overlays.clear()
        self._restore.clear()
        self.input.clear()

    def _recover(self):
        self.crashed = False
        self._need_full = True
        try:
            self.flow.recover()
        except Exception:
            traceback.print_exc()
            self.flow.title_cold()


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
        """Push the pause Menu over whatever is on screen. Open overlays (dialogue, confirm, info) are set aside and
        put back when the Menu resumes, so nothing underneath moves or loses its place."""
        app = self.app
        if any(type(s).__name__ == "MenuScene" for s in app.stack):
            return
        self._overlays = list(app.overlays)
        app.push(scene_class("MenuScene")(self, self._menu_done))

    def _menu_done(self, choice):
        app, flow = self.app, self.flow
        if choice == "save_quit" and flow is not None:
            flow.save_quit()
        elif choice == "abandon" and flow is not None:
            flow.abandon()
        elif choice == "quit_tutorial" and flow is not None:
            flow.quit_tutorial()
        elif choice == "skip_tutorial" and self.tutor is not None:
            self.tutor.skip()
        else:
            saved, self._overlays = getattr(self, "_overlays", []), []
            app.pop()
            app.hold_overlays(saved)

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
        if self.data_dir and not tutorial:                      # practising the lessons never touches a saved night
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
        """All three lessons done: graduate, then the attic. A replay with a saved night on disk goes back to the
        Title instead (the lessons are practice and must not replace that night)."""
        svc = self.svc
        keep = self._saved_run() is not None
        R.finish_tutorial(svc.run)
        svc.profile.flags["tutorial_done"] = True
        svc.tutor = None
        self.app.tutor = None
        if self.data_dir:
            S.save_profile(svc.profile, svc.profile_path)
        if keep:
            self._cutscene("tutorial_graduate", self.title, lines=story.TUTORIAL[-1].lines)
            return
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
        flags = run.flags
        if flags.get("draft_pick") is not None:
            self._start_draft(first_pick=flags["draft_pick"])
        elif run.current is not None and flags.get("won_node"):
            on_won = self._boss_won if run.current.kind == "boss" else self._node_done
            pending = flags.get("pending_reward")
            if pending:
                options = [Card(*c) for c in pending["cards"]]
                self._reward(options, pending["skip"], on_won)
            else:
                self._levels(on_won)
        elif run.current is not None:
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
        run.flags.pop("won_node", None)
        run.flags.pop("pending_reward", None)
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
            else:                                   # a saved night re-offers exactly these cards on Continue
                svc.run.flags["won_node"] = True
                svc.run.flags["pending_reward"] = {
                    "skip": skip, "cards": [[c.def_id, int(c.reversed), c.star, c.charm] for c in rewards.options]}
                svc.save()
            self._reward(rewards.options, skip, on_won)


        self._show(spread(svc, enemy, to_battle, lesson=lesson), tips=lesson is None)

    def _reward(self, options, skip, on_won):
        svc = self.svc

        def picked(card):
            svc.run.flags.pop("pending_reward", None)
            self._levels(on_won)

        self.app.switch(scene_class("RewardScene")(svc, options, picked, skip_treats=skip))

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
            self._new_run(tutorial=(choice == "learn"), opening=False)

    # ------------------------------------------------------------------ menu actions
    def menu_allowed(self):
        """The pause Menu can open on every screen of a run (tutorial and draft included), not on Title, Parlor,
        the Demo End or a recovery screen."""
        run = self.svc.run
        app = self.app
        scene = app.scene
        if run is None or run.done or scene is None or app._trans is not None or app.crashed:
            return False
        if type(scene).__name__ in ("TitleScene", "ParlorScene", "EndingScene", "MenuScene"):
            return False
        return not any(type(s).__name__ == "MenuScene" for s in app.stack)

    def save_quit(self):
        self.svc.save()
        self.title()

    def quit_tutorial(self):
        """Leave the lessons for the Title (a saved night, if any, is untouched; nothing of the tutorial is saved)."""
        self.title()

    def abandon(self):
        svc = self.svc
        if self.data_dir:
            S.delete_run(svc.run_path)
        svc.run.done = True
        svc.save()
        self._parlor(dying=False, lines=None)

    # ------------------------------------------------------------------ crash recovery
    def title_cold(self):
        self.title(transition=False)

    def recover(self):
        """After a scene raised: back to the Night Path with the saved run (the step's choices again), else Title."""
        svc = self.svc
        run = None
        try:
            run = self._saved_run()
        except Exception:
            run = None
        if run is None:
            self.title_cold()
            return
        run.current = None
        svc.run = run
        svc.tick_clock()
        self.tutorial = None
        self.app.stack.clear()
        self._path_cold()

    def _path_cold(self):
        self.svc.save()
        self.app.reset(scene_class("PathScene")(self.svc, self._node_chosen), transition=False)


def make(data_dir=None):
    """The game object for the engine Runner (and `tools/sim.py --game nla.flow:make`)."""
    return Flow(data_dir if data_dir is not None else default_data_dir()).app
