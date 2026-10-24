"""Dev harness for the Battle scene (stub Services, real App). Not used by the game.

    python tools/sim.py --game nla.scenes.dev_battle:dev_battle --keys "..." --shots build/shots/battle/
    python tools/sim.py --game nla.scenes.dev_battle:dev_boss   --keys "..." --shots build/shots/battle/

Variants: dev_battle(enemy_key, seed), dev_boss(seed), dev_loss(seed) (a Defeat), dev_tutorial() (restricted input).
"""

import os

from nla.rules import cards
from nla.rules.battle import simulate
from nla.rules.run import new_run
from nla.ui.app import App

from .battle import BattleScene


class _Profile:
    def __init__(self):
        self.settings = {"speed": 1}


class _Tutor:
    class step:
        highlight = "hp_bar"
        allow = "a"
        wait_for = "battle_speed"

    active = True


class StubServices:
    def __init__(self, run, tutor=None):
        self.run = run
        self.profile = _Profile()
        self.tutor = tutor
        self.app = None
        self.reported = []
        self.result = None

    def report(self, key):
        self.reported.append(key)
        print("report:", key)

    def say(self, lines, then=None):
        self.app.say(lines, then)

    def card_info(self, card):
        self.app.card_info(card)


def _trace(scene):
    """Print `time event` for every event the script starts (screenshot planning)."""
    inner = scene.gen

    def traced():
        for w in inner:
            e = scene.events[scene.idx]
            print("trace t=%.2f #%d %s side=%d slot=%d value=%d label=%r tier=%d crit=%s" % (
                scene.app.time, scene.idx, e.kind, e.side, e.slot, e.value, e.label, e.tier, e.crit))
            yield w

    scene.gen = traced()


def _make(run, enemy_key, seed, tutor=None):
    result = simulate(run, enemy_key, seed)
    sv = StubServices(run, tutor)

    def done(r):
        sv.result = r
        print("done:", r)

    scene = BattleScene(sv, enemy_key, result, done)
    if os.environ.get("NLA_BATTLE_TRACE"):
        _trace(scene)
    app = App(scene)
    sv.app = app
    return app


def dev_battle(enemy_key="gray_rat", seed=1):
    return _make(new_run(seed, False), enemy_key, seed)


def _strong(run, star=1):
    c = cards.Card
    run.spread = [c(1, False, star, 0, 901), c(2, False, star, 0, 902), c(3, False, star, 0, 903),
                  c(4, False, star, 0, 904), c(41, False, star, 0, 905), c(45, False, star, 0, 906)]
    run.spread_size = 6
    run.max_hp = run.hp = 60
    return run


def dev_boss(seed=1, star=1):
    return _make(_strong(new_run(seed, False), star), "chubbs", seed)


def dev_loss(seed=3):
    run = new_run(seed, False)
    run.hp = 8
    return _make(run, "rat_sergeant", seed)


def dev_tutorial(seed=1):
    return _make(new_run(seed, True), "practice_mouse", seed, _Tutor())
