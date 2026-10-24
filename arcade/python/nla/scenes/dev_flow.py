"""Dev entry points for the simulator (Flow's scenes and whole-game scripts). Every factory uses a throwaway data dir,
so runs never touch the real saves.

    python tools/sim.py --game nla.scenes.dev_flow:fresh      the real game from the Title
    python tools/sim.py --game nla.scenes.dev_flow:parlor     Parlor after a defeat (first_death lines)
    python tools/sim.py --game nla.scenes.dev_flow:ending     the Demo End screen
    python tools/sim.py --game nla.scenes.dev_flow:howto      the How to Play recap
    python tools/sim.py --game nla.scenes.dev_flow:cutscene   the opening cutscene
    python tools/sim.py --game nla.scenes.dev_flow:dev_boss_run   straight to the Chubbs fight with a strong deck
    python tools/sim.py --game nla.scenes.dev_flow:dev_defeat_run  a doomed fight at the first node
"""

import tempfile

from nla import story
from nla.flow import Flow
from nla.rules import run as R
from nla.rules.cards import Card


def _flow():
    return Flow(tempfile.mkdtemp(prefix="nla_"))


def fresh():
    return _flow().app


def parlor():
    f = _flow()
    f.svc.run = R.new_run(1, False)
    f.svc.profile.deaths = 1
    f._parlor(dying=True, lines=story.SCENES["first_death"])
    return f.app


def ending():
    f = _flow()
    f.svc.run = R.new_run(1, False)
    f._demo_end()
    return f.app


def howto():
    from nla.scenes.draft import HowToPlayScene
    f = _flow()
    f.app.reset(HowToPlayScene(f.svc, lambda _=None: None), transition=False)
    return f.app


def cutscene():
    f = _flow()
    f.svc.run = R.new_run(1, False)
    f._cutscene("opening", lambda: None)
    return f.app


def _strong(run):
    """Deck that wins: a Strength-free Catwalk of high stars with spare HP."""
    run.max_hp = run.hp = 80
    run.spread_size = 6
    run.spread = [Card(d, False, 2, 0, i + 1) for i, d in enumerate((2, 3, 4, 5, 6, 7))]
    run.next_uid = 100
    run.treats = 20


def _jump(f, run):
    f.svc.run = run
    f._node_chosen(R.enter_node(run, 0))
    return f.app


def dev_boss_run():
    f = _flow()
    run = R.new_run(7, False)
    _strong(run)
    run.step = R.STEPS
    return _jump(f, run)


def dev_defeat_run():
    f = _flow()
    run = R.new_run(7, False)
    run.hp = 1
    return _jump(f, run)
