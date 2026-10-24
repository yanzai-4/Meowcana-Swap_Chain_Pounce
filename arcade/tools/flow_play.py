"""State-aware autopilot for whole-game simulator runs (Flow's end-to-end scripts).

A fixed `--keys` string cannot play a game whose frames cost anywhere from 17 ms to 1 s, so these scripts watch the
game state instead of the clock: "tap A until the dialogue is gone", "wait until the Reward scene is up".

    python tools/flow_play.py tutorial --shots build/shots/flow_tutorial/
    python tools/flow_play.py skip     --shots build/shots/flow_skip/
    python tools/flow_play.py boss     --shots build/shots/flow_boss/
    python tools/flow_play.py death    --shots build/shots/flow_death/

Scenarios are generator functions in SCENARIOS: `yield from p.tap("A")`, `p.wait(1.5)`, `p.until(fn, "what")`,
`p.shot("name")`, `p.dialogue()`. Each prints one line per milestone and exits non-zero when a wait times out.
"""

import argparse
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sim  # noqa: E402  (puts python/ on sys.path)
from sim import Clock, Device, FakeBridge, Library, Recorder, engine  # noqa: E402

BUTTONS = {"A": 1, "B": 2, "C": 4}
STICK = {"L": (-127, 0), "R": (127, 0), "U": (0, 127), "D": (0, -127)}


class Pad:
    def __init__(self):
        self.mask = self.x = self.y = 0

    def at(self, now):
        return self.mask, self.x, self.y


class Stuck(Exception):
    pass


class Pilot:
    def __init__(self, factory, out, seed=1, quiet=False):
        self.out = Path(out) if out else None
        if self.out:
            self.out.mkdir(parents=True, exist_ok=True)
        self.lib = Library()
        self.device = Device(self.lib)
        self.clock = Clock()
        engine.time = self.clock
        random.seed(seed)
        self.pad = Pad()
        self.bridge = FakeBridge(self.device, self.clock, self.pad, throttle=False)
        self.app = factory()
        self.runner = engine.Runner(self.app, self.bridge, fps=engine.FPS)
        self.rec = Recorder()
        self.quiet = quiet
        self.last_ms = [0.0, 0.0]
        self.shots = 0

    # ------------------------------------------------------------------ script helpers
    @property
    def now(self):
        return self.bridge.now()

    @property
    def scene(self):
        return type(self.app.scene).__name__ if self.app.scene is not None else ""

    @property
    def tutor(self):
        return self.app.tutor

    def say(self, msg):
        if not self.quiet:
            print("[%7.1fs] %s" % (self.now, msg))

    def wait(self, seconds):
        yield ("wait", seconds)

    def tap(self, key):
        yield ("tap", key)

    def taps(self, *keys):
        for k in keys:
            yield ("tap", k)

    def until(self, fn, what, timeout=60):
        yield ("until", fn, timeout, what)

    def shot(self, name):
        yield ("shot", name)

    def settled(self):
        return not self.app.busy and self.app._trans is None and not self.app._need_full

    def dialogue(self):
        """A through every box of the open dialogue overlay."""
        yield from self.until(lambda: self.app.overlays, "a dialogue", 20)
        guard = 0
        while self.app.overlays and guard < 60:
            guard += 1
            yield from self.wait(1.0)
            if self.app.overlays:
                yield from self.tap("A")

    def scene_is(self, name):
        return lambda: self.scene == name and self.settled()

    # ------------------------------------------------------------------ runner
    def save_shot(self, name):
        if self.out:
            self.device.img.save(self.out / (name + ".png"))
            self.shots += 1

    def frame(self):
        self.runner.step()
        if self.runner.error is not None:
            raise SystemExit("game raised (traceback above)")
        row = self.bridge.take_frame()
        self.rec.add(self.now, row, self.runner.busy)
        self.last_ms = [self.last_ms[1], row[0]]

    def run(self, script, limit=1800.0):
        gen = script(self)
        cmd = None
        state = {}
        try:
            while self.now < limit:
                self.frame()
                while True:
                    if cmd is None:
                        try:
                            cmd = next(gen)
                        except StopIteration:
                            return self.finish(0)
                        state = {"t0": self.now, "n": 0}
                    done = self._exec(cmd, state)
                    if done:
                        cmd = None
                        continue
                    break
            raise Stuck("time limit")
        except Stuck as err:
            self.say("STUCK: %s" % err)
            self.save_shot("stuck")
            return self.finish(1)

    def _exec(self, cmd, st):
        kind = cmd[0]
        if kind == "wait":
            return self.now - st["t0"] >= cmd[1]
        if kind == "shot":
            self.save_shot(cmd[1])
            return True
        if kind == "until":
            _, fn, timeout, what = cmd
            if fn():
                return True
            if self.now - st["t0"] > timeout:
                raise Stuck("timed out waiting for %s (scene %s, phase %s)" % (
                    what, self.scene, getattr(self.tutor, "phase", "-")))
            return False
        if kind == "tap":
            key = cmd[1]
            n = st["n"]
            if n == 0:                                   # press only on quiet frames
                if max(self.last_ms) > 60 or self.app._trans is not None:
                    return False
                mask = BUTTONS.get(key, 0)
                x, y = STICK.get(key, (0, 0))
                self.pad.mask, self.pad.x, self.pad.y = mask, x, y
            elif n == 2:
                self.pad.mask = self.pad.x = self.pad.y = 0
            elif n == 4:
                return True
            st["n"] = n + 1
            return False
        raise ValueError(cmd)

    def finish(self, code):
        if self.out:
            self.save_shot("final")
            self.rec.save(self.out / "cost.csv")
        print(self.rec.summary())
        rows = sorted(self.rec.rows, key=lambda r: -r[1])[:5]
        print("worst frames (t, ms, busy):", [(r[0], r[1], r[7]) for r in rows])
        return code


# =================================================================================================== scenarios
def _flow(tmp=None):
    from nla.flow import Flow
    return Flow(tmp or tempfile.mkdtemp(prefix="nla_play_")).app


def to_lesson_start(p):
    """Title -> Begin -> Learn to Play -> opening (skipped with B) -> lesson 1 on screen."""
    yield from p.until(p.scene_is("TitleScene"), "title")
    yield from p.wait(1.0)
    yield from p.shot("01_title")
    yield from p.tap("A")
    yield from p.until(lambda: p.app.scene.mode == "choice" and p.settled(), "tutorial choice")
    yield from p.shot("02_choice")
    yield from p.tap("A")
    yield from p.until(p.scene_is("CutsceneScene"), "opening cutscene")
    yield from p.until(lambda: p.app.overlays, "opening dialogue")
    yield from p.wait(2.5)
    yield from p.shot("03_opening")
    yield from p.tap("B")                                # B skips the whole scene
    yield from p.until(p.scene_is("SpreadScene"), "lesson 1 Spread")
    p.say("lesson 1 Spread is up")


def play_to(p, step_id, shots=()):
    """Let the coach talk (A through each box) until step `step_id` is waiting for the player (or has passed)."""
    from nla import story
    target = [x.id for x in story.TUTORIAL].index(step_id)
    seen = set()
    for _ in range(600):
        t = p.tutor
        if t is None or t.idx > target or (t.idx == target and t.phase in ("waiting", "hold")):
            break
        if t.phase == "reading" and p.app.overlays:
            if t.idx not in seen:
                seen.add(t.idx)
                yield from p.wait(2.2)
                if t.step.id in shots:
                    yield from p.shot("step_" + t.step.id)
            yield from p.tap("A")
            yield from p.wait(0.6)
        else:
            yield from p.wait(0.3)
    else:
        raise Stuck("coach never reached %s" % step_id)
    yield from p.wait(0.3)


def tutorial(p):
    from nla import story
    steps = story.TUTORIAL
    ids = {s.id: i for i, s in enumerate(steps)}
    yield from to_lesson_start(p)
    # ---- lesson 1
    yield from play_to(p, "l1_peek", shots=("l1_hello",))
    yield from p.shot("l1_peek_wait")
    yield from p.tap("A")                                 # blocked: not allowed here
    yield from p.until(lambda: p.app.overlays, "nudge after a blocked A", 5)
    yield from p.shot("l1_nudge")
    yield from p.dialogue()
    yield from p.tap("C")
    yield from p.until(lambda: p.app.overlays and p.settled(), "card info", 10)
    yield from p.wait(2.5)
    yield from p.shot("l1_info")
    yield from p.tap("C")
    yield from play_to(p, "l1_fight", shots=("l1_order", "l1_enemy", "l1_hp"))
    yield from p.shot("l1_fight_wait")
    yield from _to_fight(p)
    yield from p.tap("A")
    yield from play_to(p, "l1_speed")
    yield from p.shot("l1_battle")
    if p.tutor.phase == "waiting":
        yield from p.tap("A")
    yield from _finish_battle(p, ids["l1_prize"])
    yield from _pick_reward(p, "l1_prize")
    # ---- lesson 2
    yield from p.until(lambda: p.scene == "SpreadScene" and p.tutor.idx >= ids["l2_intro"], "lesson 2")
    yield from play_to(p, "l2_pickup", shots=("l2_intro", "l2_chart"))
    yield from p.shot("l2_pickup_wait")
    yield from _goto(p, 1, 2)                              # slot 3 is the Water card
    yield from p.tap("A")
    yield from play_to(p, "l2_drop")
    yield from _goto(p, 1, 3)
    yield from p.tap("A")
    yield from play_to(p, "l2_box", shots=("l2_fixed",))
    yield from p.shot("l2_box_wait")
    yield from _goto(p, 2, 0)
    yield from p.tap("A")
    yield from _goto(p, 1, 0)
    yield from p.tap("A")                                 # Box card up into the Spread
    yield from play_to(p, "l2_fight")
    yield from _to_fight(p)
    yield from p.tap("A")
    yield from _finish_battle(p, ids["l2_prize"])
    yield from _pick_reward(p, "l2_prize")
    # ---- lesson 3
    yield from p.until(lambda: p.scene == "SpreadScene" and p.tutor.idx >= ids["l3_intro"], "lesson 3")
    yield from play_to(p, "l3_reversed", shots=("l3_intro", "l3_catwalk"))
    yield from p.shot("l3_reversed_wait")
    p.say("lesson 3 reached the reversed-card step")
    yield from p.tap("C")
    yield from p.until(lambda: p.app.overlays and p.settled(), "reversed card info", 10)
    yield from p.wait(2.0)
    yield from p.tap("C")
    yield from play_to(p, "l3_arrange", shots=())
    yield from p.shot("l3_arrange_wait")
    yield from _goto(p, 1, 2)
    yield from p.tap("A")
    yield from _goto(p, 1, 3)
    yield from p.tap("A")                                  # swap: 2-3-4-5
    yield from play_to(p, "l3_fight", shots=("l3_catwalk_made", "l3_curl"))
    yield from _to_fight(p)
    yield from p.tap("A")
    yield from _finish_battle(p, 0)
    yield from _pick_reward(p, "l3_prize")
    yield from p.until(lambda: p.scene == "CutsceneScene", "graduation cutscene", 60)
    yield from autoplay(p, lambda: p.scene == "PathScene" and p.settled(),
                        shots={"CutsceneScene": "graduate_cutscene"})
    yield from p.wait(1.5)
    yield from p.shot("attic_path")
    run = p.app.flow.svc.run
    p.say("tutorial over: tutorial=%s deck=%d cards, box=%d" % (
        run.tutorial, len([c for c in run.spread if c]), len([c for c in run.box if c])))
    yield from autoplay(p, lambda: p.app.flow.svc.run.step >= 1 and p.scene == "PathScene" and p.settled(),
                        shots={"SpreadScene": "attic_spread", "BattleScene": "attic_battle"})
    yield from p.shot("attic_after_fight")
    p.say("first real node done")


def _goto(p, row, col, limit=24):
    """Move the Spread cursor to (row, col): rows ENEMY 0 / SPREAD 1 / BOX 2; the Spread row ends in FIGHT."""
    for _ in range(limit):
        sc = p.app.scene
        if sc.row == row and sc.col == col:
            return
        if sc.row != row:
            yield from p.tap("U" if sc.row > row else "D")
        else:
            yield from p.tap("R" if col > sc.col else "L")
    raise Stuck("cursor never reached row %d col %d" % (row, col))


def _to_fight(p):
    """Move the Spread cursor onto FIGHT (the row ends in the Fight plaque)."""
    yield from _goto(p, 1, p.app.scene.ns)


def _finish_battle(p, next_idx):
    yield from p.until(lambda: p.scene == "BattleScene", "battle", 30)
    yield from p.wait(2.0)
    guard = 0
    while p.scene == "BattleScene" and guard < 120:
        guard += 1
        t = p.tutor
        key = "A"
        if t is not None and t.phase == "waiting" and t.step.wait_for == "battle_skip":
            key = "B"
        yield from p.tap(key)
        yield from p.wait(1.0)
    yield from p.until(lambda: p.scene == "RewardScene" and p.settled(), "reward", 30)


def _pick_reward(p, step_id):
    yield from play_to(p, step_id)
    yield from p.shot(step_id)
    yield from p.tap("A")
    yield from p.wait(2.0)
    for _ in range(4):                                    # a Duplicate prompt (Merge / Keep Both) may follow
        if p.app.overlays or p.scene == "RewardScene":
            if p.app.overlays and p.settled():
                yield from p.shot(step_id + "_merge")
            yield from p.tap("A")
            yield from p.wait(2.0)


# ---------------------------------------------------------------------------------------------- autoplay
def autoplay(p, stop, limit=900.0, shots=None):
    """Play any scene with a plain policy until stop() is true: A through dialogue, skip cutscenes, walk the Path,
    FIGHT, A through battle and rewards, leave shops. `shots` maps scene name -> shot name (taken once)."""
    taken = set()
    t_scene, last = p.now, None
    while not stop():
        sc = p.scene
        if (sc, p.app.overlays and True) != last:
            last, t_scene = (sc, p.app.overlays and True), p.now
        if p.now - t_scene > 90:
            raise Stuck("no progress in %s for 90 s" % sc)
        if p.now > limit:
            raise Stuck("autoplay time limit")
        if shots and sc in shots and sc not in taken and p.settled():
            taken.add(sc)
            yield from p.wait(1.5)
            yield from p.shot(shots[sc])
        if p.app._trans is not None or (p.app.busy and sc != "BattleScene"):
            yield from p.wait(0.4)
        elif p.app.overlays:
            yield from p.wait(1.2)
            if p.app.overlays:
                yield from p.tap("A")
        elif sc == "CutsceneScene":
            yield from p.wait(1.0)
            yield from p.tap("B")
        elif sc == "SpreadScene":
            yield from p.wait(0.8)
            yield from _to_fight(p)
            yield from p.tap("A")
        elif sc in ("StallScene", "CatBedScene", "EncounterScene", "BoxScene"):
            yield from p.wait(1.0)
            yield from p.tap("A" if sc != "StallScene" else "B")
            yield from p.wait(0.8)
            yield from p.tap("A")
        else:
            yield from p.wait(0.8)
            yield from p.tap("A")


def new_run_via_title(p, learn):
    yield from p.until(p.scene_is("TitleScene"), "title")
    yield from p.wait(1.0)
    yield from p.tap("A")
    yield from p.until(lambda: p.app.scene.mode == "choice" and p.settled(), "tutorial choice")
    if not learn:
        yield from p.tap("D")
        yield from p.wait(0.5)
    yield from p.shot("choice_learn" if learn else "choice_skip")
    yield from p.tap("A")


def skip(p):
    yield from new_run_via_title(p, learn=False)
    yield from p.until(p.scene_is("CutsceneScene"), "opening cutscene")
    yield from p.tap("B")
    yield from p.until(p.scene_is("RewardScene"), "draft pick 1")
    yield from p.wait(2.5)
    yield from p.shot("draft_1")
    yield from autoplay(p, lambda: p.scene == "PathScene" and p.settled(), shots={"HowToPlayScene": "howto"})
    yield from p.wait(1.5)
    yield from p.shot("path_first")
    p.say("first Night Path reached")
    yield from autoplay(p, lambda: p.app.flow.svc.run.step >= 2 and p.scene == "PathScene" and p.settled(),
                        shots={"SpreadScene": "node_spread", "BattleScene": "node_battle",
                               "RewardScene": "node_reward"})
    yield from p.shot("path_after_two")
    p.say("two nodes done; run step %d" % p.app.flow.svc.run.step)


def boss(p):
    yield from p.until(lambda: p.scene == "CutsceneScene", "boss intro")
    yield from autoplay(p, lambda: p.scene == "EndingScene" and p.app.flow.svc.run.done and p.settled(),
                        shots={"SpreadScene": "boss_spread", "BattleScene": "boss_battle",
                               "RewardScene": "boss_reward"})
    yield from p.wait(3.0)
    yield from autoplay(p, lambda: p.scene == "EndingScene" and p.app.scene.phase == "screen" and p.settled())
    yield from p.wait(1.0)
    yield from p.shot("demo_end")
    prof = p.app.flow.svc.profile
    p.say("Demo End reached; wins=%d best_hit=%d fastest=%d" % (prof.wins, prof.best_hit, prof.fastest))
    yield from p.tap("A")
    yield from p.until(p.scene_is("ParlorScene"), "parlor after the demo end")
    yield from p.wait(1.5)
    yield from p.shot("parlor_after_win")


def death(p):
    yield from p.until(lambda: p.scene == "SpreadScene", "doomed fight")
    yield from autoplay(p, lambda: p.scene == "ParlorScene" and p.settled(),
                        shots={"BattleScene": "death_battle"})
    yield from p.wait(5.0)
    yield from p.shot("parlor_dead")
    prof = p.app.flow.svc.profile
    p.say("Parlor reached; deaths=%d bells lit=%d" % (prof.deaths, prof.bells))
    yield from autoplay(p, lambda: p.app.overlays and False or p.scene == "ParlorScene" and not p.app.overlays
                        and p.app.scene.ready and p.settled())
    yield from p.tap("A")                                   # Start Night
    yield from autoplay(p, lambda: p.scene == "RewardScene" and p.settled())
    yield from p.wait(2.0)
    yield from p.shot("new_run_draft")
    p.say("new run began in the draft (tutorial %s)" % p.app.flow.svc.run.tutorial)


SCENARIOS = {"tutorial": tutorial, "skip": skip, "boss": boss, "death": death}
DEFAULT_GAME = {"boss": "nla.scenes.dev_flow:dev_boss_run", "death": "nla.scenes.dev_flow:dev_defeat_run"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", choices=sorted(SCENARIOS))
    ap.add_argument("--shots")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--game", default=None, help="module:callable overriding the scenario's game")
    args = ap.parse_args()
    factory = _flow
    args.game = args.game or DEFAULT_GAME.get(args.scenario)
    if args.game:
        import importlib
        mod, _, attr = args.game.partition(":")
        factory = getattr(importlib.import_module(mod), attr)
    pilot = Pilot(factory, args.shots, args.seed)
    sys.exit(pilot.run(SCENARIOS[args.scenario]))


if __name__ == "__main__":
    main()
