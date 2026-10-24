"""Run/profile persistence: JSON, atomic write (temp file + rename), robust load."""
import json
import os
from dataclasses import dataclass, field

from .cards import Card
from .run import RunState, Node, StallStock, StallItem

NINE_BELLS = 9
VERSION = 1


@dataclass
class Profile:
    deaths: int = 0              # Nine Bells: bells lit = 9 - deaths
    wins: int = 0
    runs: int = 0
    best_hit: int = 0
    fastest: int = 0             # seconds of the fastest win (0 = none yet)
    tips_seen: list = field(default_factory=list)
    settings: dict = field(default_factory=lambda: {"speed": 1})
    flags: dict = field(default_factory=dict)   # story beats already shown, etc.

    @property
    def bells(self) -> int:
        return max(0, NINE_BELLS - self.deaths)


def record_death(profile, run=None) -> int:
    """Nine Bells -1. Returns the new death count (1st and 3rd trigger story)."""
    profile.deaths += 1
    if run is not None:
        profile.best_hit = max(profile.best_hit, run.stats.get("best_hit", 0))
    return profile.deaths


def record_win(profile, run, seconds=0):
    profile.wins += 1
    profile.best_hit = max(profile.best_hit, run.stats.get("best_hit", 0))
    if seconds > 0 and (profile.fastest == 0 or seconds < profile.fastest):
        profile.fastest = int(seconds)


# --- (de)serialization ------------------------------------------------------------------------
def _card_d(c):
    return None if c is None else [c.def_id, int(c.reversed), c.star, c.charm, c.uid]


def _card_l(d):
    return None if d is None else Card(d[0], bool(d[1]), d[2], d[3], d[4])


def _item_d(i):
    return {"kind": i.kind, "price": i.price, "card": _card_d(i.card), "service": i.service,
            "index": i.index, "sold": i.sold}


def _item_l(d):
    return StallItem(d["kind"], d["price"], _card_l(d["card"]), d["service"], d["index"], d["sold"])


def run_to_dict(run) -> dict:
    st = run.stall
    return {
        "v": VERSION, "seed": run.seed, "tutorial": run.tutorial, "hp": run.hp,
        "max_hp": run.max_hp, "treats": run.treats, "spread": [_card_d(c) for c in run.spread],
        "spread_size": run.spread_size, "box": [_card_d(c) for c in run.box],
        "box_size": run.box_size, "level": run.level, "xp": run.xp, "step": run.step,
        "path": [[[n.kind, n.key, n.label, n.desc] for n in row] for row in run.path],
        "flags": run.flags, "bells": run.bells, "next_uid": run.next_uid,
        "pending_levels": run.pending_levels, "tips": run.tips,
        "stall": None if st is None else {
            "cards": [_item_d(i) for i in st.cards], "service": _item_d(st.service),
            "tuna": _item_d(st.tuna), "reroll_cost": st.reroll_cost, "rerolls": st.rerolls},
        "current": None if run.current is None else [run.current.kind, run.current.key,
                                                      run.current.label, run.current.desc],
        "stats": run.stats, "mouse_tokens": run.mouse_tokens, "done": run.done,
    }


def run_from_dict(d) -> RunState:
    st = d["stall"]
    run = RunState(seed=d["seed"], tutorial=d["tutorial"], hp=d["hp"], max_hp=d["max_hp"],
                   treats=d["treats"], spread=[_card_l(c) for c in d["spread"]],
                   spread_size=d["spread_size"], box=[_card_l(c) for c in d["box"]],
                   box_size=d["box_size"], level=d["level"], xp=d["xp"], step=d["step"],
                   path=[[Node(*n) for n in row] for row in d["path"]], flags=dict(d["flags"]),
                   bells=d["bells"], next_uid=d["next_uid"], pending_levels=list(d["pending_levels"]),
                   tips=list(d["tips"]),
                   stall=None if st is None else StallStock(
                       [_item_l(i) for i in st["cards"]], _item_l(st["service"]),
                       _item_l(st["tuna"]), st["reroll_cost"], st["rerolls"]),
                   current=None if d["current"] is None else Node(*d["current"]),
                   stats=dict(d["stats"]), mouse_tokens=d["mouse_tokens"], done=d["done"])
    if len(run.spread) != run.spread_size or len(run.box) != run.box_size:
        raise ValueError("inconsistent run")
    return run


def _atomic_write(path, text):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    os.replace(tmp, path)


def save_run(run, path):
    _atomic_write(path, json.dumps(run_to_dict(run), separators=(",", ":")))


def load_run(path):
    """-> RunState, or None when there is no (valid) saved run."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return run_from_dict(json.load(f))
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return None


def delete_run(path):
    try:
        os.remove(path)
    except OSError:
        pass


def save_profile(profile, path):
    d = {"v": VERSION, "deaths": profile.deaths, "wins": profile.wins, "runs": profile.runs,
         "best_hit": profile.best_hit, "fastest": profile.fastest,
         "tips_seen": profile.tips_seen, "settings": profile.settings, "flags": profile.flags}
    _atomic_write(path, json.dumps(d, separators=(",", ":")))


def load_profile(path) -> Profile:
    """Fresh Profile when the file is missing or corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        p = Profile()
        for k in ("deaths", "wins", "runs", "best_hit", "fastest"):
            setattr(p, k, int(d.get(k, 0)))
        p.tips_seen = [str(x) for x in d.get("tips_seen", [])]
        p.settings = dict(d.get("settings", {"speed": 1}))
        p.flags = dict(d.get("flags", {}))
        return p
    except (OSError, ValueError, TypeError, AttributeError):
        return Profile()
