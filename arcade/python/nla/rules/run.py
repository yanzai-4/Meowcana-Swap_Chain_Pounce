"""Run state and progression: Night Path, rewards, Stash/XP/Level Up, Spots' Stall, Cat Bed,
Encounters, Cardboard Box, duplicates, Box handling, tutorial lessons, first-time tips.

Every random draw is keyed by (seed, purpose, step ...), never by a running counter, so a
saved run reproduces exactly and screens can be re-entered safely.
"""
import random
from dataclasses import dataclass, field
from typing import Optional

from .cards import (Card, CARD_DEFS, MAJOR_IDS, CHARMS, DROPPINGS, FIRE, AIR, WATER, EARTH,
                    CATNIP, YARN, MOONLIGHT, RAT_BITE, FOOL, charm_rank, is_curse_charm, is_major)
from .enemies import (ENEMIES, ELITE_KEYS, RAT_KEYS_EARLY, RAT_KEYS_LATE, TUTORIAL_KEYS)

STEPS = 6                       # Night Path steps before the Boss (path[STEPS] is the Boss)
LEVEL_XP = {2: 1, 3: 3, 4: 5, 5: 7}     # cumulative XP per level (retuned for 6 steps)
MAX_LEVEL = 5
START_HP = 36
START_TREATS = 5
MAX_SPREAD = 6
MAX_BOX = 8
SKIP_TREATS = 3
TUNA_PRICE = 5
TUNA_HEAL = 12

STARTER = ((FIRE * 10 + 2, False), (FIRE * 10 + 3, False), (AIR * 10 + 4, True),
           (WATER * 10 + 2, False))     # Fire 3, Fire 4, Air 5 (Reversed), Water 3


@dataclass
class Node:
    kind: str    # "fight" "elite" "stall" "encounter" "bed" "box" "boss"
    key: str     # enemy key / encounter key / ""
    label: str
    desc: str = ""


@dataclass
class Rewards:
    treats: int
    xp: int
    options: list              # Cards to pick from (Elite/Boss: includes the Chewed Major)
    skip_treats: int = SKIP_TREATS   # Treats for skipping (0 = no Skip button)
    levels: int = 0            # Level Ups now pending
    stash: int = 0             # part of `treats` that came from the Stash


@dataclass
class EncounterOption:
    label: str
    text: str
    needs_card: bool = False


@dataclass
class EncounterDef:
    key: str
    title: str
    intro: str
    options: list


@dataclass
class EncounterResult:
    text: str
    card: Optional[Card] = None   # gained card still to be placed (status is take_card's result)
    status: str = ""


@dataclass
class StallItem:
    kind: str                  # "card" | "service" | "tuna"
    price: int
    card: Optional[Card] = None
    service: str = ""          # wider_cloth bigger_box charm_up flea_bath flip
    index: int = 0
    sold: bool = False


@dataclass
class StallStock:
    cards: list
    service: StallItem
    tuna: StallItem
    reroll_cost: int
    rerolls: int = 0


@dataclass
class TutorialLesson:
    lesson: int          # 0..2
    enemy: str
    spread: list
    note: str


@dataclass
class RunState:
    seed: int
    tutorial: bool = False
    hp: int = START_HP
    max_hp: int = START_HP
    treats: int = START_TREATS
    spread: list = field(default_factory=list)
    spread_size: int = 4
    box: list = field(default_factory=list)
    box_size: int = 6
    level: int = 1
    xp: int = 0
    step: int = 0                  # 0..STEPS-1 = path steps, STEPS = Boss
    path: list = field(default_factory=list)   # list[list[Node]] per step (+ Boss)
    flags: dict = field(default_factory=dict)
    bells: int = 9                 # Nine Bells still lit when the run started
    next_uid: int = 1
    pending_levels: list = field(default_factory=list)
    tips: list = field(default_factory=list)   # armed first-time tips
    stall: Optional[StallStock] = None
    current: Optional[Node] = None
    stats: dict = field(default_factory=dict)  # best_hit, battles, ...
    mouse_tokens: int = 0
    done: bool = False


# --- RNG ----------------------------------------------------------------------------------------
def _rng(run, *parts):
    return random.Random(":".join(str(p) for p in (run.seed,) + parts))


def battle_seed(run) -> int:
    """Seed for the battle at the current node (stable across save/load)."""
    return _rng(run, "battle", run.step, run.stats.get("battles", 0)).getrandbits(31)


# --- construction -------------------------------------------------------------------------------
def _uid(run) -> int:
    u = run.next_uid
    run.next_uid += 1
    return u


def new_run(seed, tutorial, bells=9) -> RunState:
    run = RunState(seed=seed, tutorial=bool(tutorial), bells=bells)
    run.stats = {"best_hit": 0, "battles": 0, "beats": 0, "elites": 0}
    run.spread = [Card(d, r, 0, 0, _uid(run)) for d, r in STARTER]
    run.box = [None] * run.box_size
    run.path = _build_path(run)
    if tutorial:
        run.flags["lesson"] = -1
        run.flags["tut_uids"] = [c.uid for c in run.spread]
    return run


_NODE_INFO = {
    "fight": ("Rat Fight", "A scrap-card rat blocks the way. Win for Treats, XP and a new card."),
    "elite": ("Elite", "A tough rat guards a stolen Major card. Win to take it back."),
    "stall": ("Spots' Stall", "Spots sells cards, services and Tuna Cans."),
    "encounter": ("Encounter", "Something is going on here."),
    "bed": ("Cat Bed", "Nap, sharpen your claws, or groom."),
    "box": ("Cardboard Box", "A cardboard box. What's inside?"),
    "boss": ("Chubbs", "Chubbs, the Pantry King, guards the stolen Strength."),
}
_ENCOUNTER_KEYS = ("lost_mouse", "catnip_patch", "zero_booth", "granny_dream", "loose_page",
                   "yarn_ball")


def _node(kind, key=""):
    label, desc = _NODE_INFO[kind]
    if kind == "elite":
        label = ENEMIES[key].name
        desc = ENEMIES[key].blurb
    elif kind == "fight":
        desc = ENEMIES[key].blurb or desc
    return Node(kind, key, label, desc)


def _build_path(run):
    rng = _rng(run, "map")
    enc = list(_ENCOUNTER_KEYS)
    rng.shuffle(enc)
    weights = [("fight", 45), ("elite", 10), ("stall", 12), ("encounter", 18), ("bed", 12),
               ("box", 3)]

    def pick_kind(step, avoid=()):
        opts = [(k, w) for k, w in weights if k not in avoid
                and (k != "elite" or 2 <= step <= 4)]
        tot = sum(w for _, w in opts)
        r = rng.uniform(0, tot)
        for k, w in opts:
            r -= w
            if r <= 0:
                return k
        return opts[-1][0]

    kinds = []
    for step in range(STEPS):
        if step == 0:
            kinds.append(["fight", "encounter"])
        elif step == STEPS - 1:
            kinds.append(["stall", "bed"])
        else:
            a = pick_kind(step)
            b = pick_kind(step, avoid=(a,) if a != "fight" else ("fight",))
            if a not in ("fight", "elite") and b not in ("fight", "elite"):
                b = "fight"
            kinds.append([a, b])
    # no Cat Bed in consecutive steps (the last step always offers one)
    for step in range(1, STEPS - 1):
        prev_bed = "bed" in kinds[step - 1]
        next_bed = "bed" in kinds[step + 1]
        if "bed" in kinds[step] and (prev_bed or next_bed):
            kinds[step] = [("fight" if k == "bed" else k) for k in kinds[step]]
            if kinds[step][0] == kinds[step][1]:
                kinds[step][1] = "encounter"
    # at least one Elite option (steps 3-5) and one extra Stall option (steps 2-5)
    if not any("elite" in kinds[s] for s in range(2, 5)):
        s = rng.choice((2, 3, 4))
        kinds[s][1] = "elite"
        if kinds[s][0] == "elite":
            kinds[s][0] = "fight"
    if not any("stall" in kinds[s] for s in range(1, 5)):
        cand = [s for s in range(1, 5) if "elite" not in kinds[s] and "bed" not in kinds[s]]
        s = rng.choice(cand or [1])
        kinds[s][1] = "stall"
        if not any(k in ("fight", "elite") for k in kinds[s]):
            kinds[s][0] = "fight"
    for s in range(1, STEPS - 1):        # re-check Bed adjacency after the fixes
        if "bed" in kinds[s] and ("bed" in kinds[s - 1] or "bed" in kinds[s + 1]):
            kinds[s] = ["fight" if k == "bed" else k for k in kinds[s]]
            if kinds[s][0] == kinds[s][1]:
                kinds[s][1] = "encounter"
    path = []
    for step, ks in enumerate(kinds):
        row, used = [], set()
        for k in ks:
            if k == "fight":
                pool = ("gray_rat",) if step == 0 else (RAT_KEYS_EARLY if step < 3 else RAT_KEYS_LATE)
                pool = [x for x in pool if x not in used] or list(pool)
                key = pool[0] if step == 0 else rng.choice(pool)
                used.add(key)
                row.append(_node("fight", key))
            elif k == "elite":
                row.append(_node("elite", rng.choice(ELITE_KEYS)))
            elif k == "encounter":
                row.append(_node("encounter", enc.pop() if enc else rng.choice(_ENCOUNTER_KEYS)))
            else:
                row.append(_node(k))
        path.append(row)
    path.append([_node("boss", "chubbs")])
    return path


def path_options(run) -> list:
    """The choices for the current step (the Boss step has one)."""
    return run.path[min(run.step, STEPS)]


def enter_node(run, index) -> Node:
    node = path_options(run)[index]
    run.current = node
    if node.kind == "elite":
        arm_tip(run, "first_elite")
    if node.kind in ("fight", "elite", "boss"):
        e = ENEMIES[node.key]
        if any(getattr(c, "kind", "") in ("droppings", "fleas") for c in e.spread):
            arm_tip(run, "first_curse")
    return node


def finish_node(run):
    run.current = None
    run.stall = None
    run.step = min(run.step + 1, STEPS)
    if run.step == STEPS:
        arm_tip(run, "boss_warning")


# --- tips ---------------------------------------------------------------------------------------
TIP_KEYS = ("first_stall", "first_major", "first_elite", "first_curse", "first_hiss",
            "first_levelup", "boss_warning")


def arm_tip(run, key):
    if key not in run.tips and key not in run.flags.get("tips_done", ()):
        run.tips.append(key)


def pending_tip(run, profile=None) -> str:
    """First armed tip the player has never seen (profile.tips_seen), or ''."""
    seen = profile.tips_seen if profile is not None else ()
    for k in run.tips:
        if k not in seen:
            return k
    return ""


def consume_tip(run, profile, key):
    if key in run.tips:
        run.tips.remove(key)
    if profile is not None and key not in profile.tips_seen:
        profile.tips_seen.append(key)
    run.flags.setdefault("tips_done", []).append(key)


# --- card helpers -------------------------------------------------------------------------------
def find_card(run, uid):
    """-> (zone, index, card) with zone "spread" or "box", or (None, -1, None)."""
    for zone, row in (("spread", run.spread), ("box", run.box)):
        for i, c in enumerate(row):
            if c is not None and c.uid == uid:
                return zone, i, c
    return None, -1, None


def all_cards(run) -> list:
    return [c for c in run.spread + run.box if c is not None]


def has_curse(run) -> bool:
    return any(is_curse_charm(c.charm) for c in all_cards(run))


def duplicate_targets(run, card) -> list:
    """Owned cards with the same face that can still gain a Star (Spread first)."""
    return [c for c in run.spread + run.box if c is not None and c.def_id == card.def_id
            and c.star < 2]


def _place(run, card, zones):
    for zone in zones:
        row = run.spread if zone == "spread" else run.box
        for i, c in enumerate(row):
            if c is None:
                row[i] = card
                return zone
    return ""


def take_card(run, card) -> str:
    """Add a card. -> "spread" | "box" | "duplicate" | "box_full".
    "duplicate": nothing placed yet; call merge() or keep_both(). "box_full": call
    replace_card() or skip the card."""
    if not card.uid:
        card.uid = _uid(run)
    if is_major(card):
        arm_tip(run, "first_major")
    if is_curse_charm(card.charm):
        arm_tip(run, "first_curse")
    if duplicate_targets(run, card):
        return "duplicate"
    return keep_both(run, card)


def keep_both(run, card) -> str:
    if not card.uid:
        card.uid = _uid(run)
    zones = ("box",) if run.flags.get("to_box") else ("spread", "box")
    z = _place(run, card, zones)
    return z or "box_full"


def merge(run, card, target_uid):
    """Merge a new card into an owned one: Star +1, keeps the target's orientation and the
    better Charm."""
    _, _, t = find_card(run, target_uid)
    if t is None or t.star >= 2:
        return None
    t.star += 1
    if charm_rank(card.charm) > charm_rank(t.charm):
        t.charm = card.charm
    return t


def replace_card(run, card, uid) -> bool:
    """Box full: throw out the owned card `uid` (+1 Treat) and put the new card in its place."""
    zone, i, old = find_card(run, uid)
    if old is None:
        return False
    if not card.uid:
        card.uid = _uid(run)
    (run.spread if zone == "spread" else run.box)[i] = card
    run.treats += 1
    return True


def remove_card(run, uid):
    zone, i, c = find_card(run, uid)
    if c is not None:
        (run.spread if zone == "spread" else run.box)[i] = None
    return c


def card_price(card) -> int:
    base = 15 if is_major(card) else 2 + (CARD_DEFS[card.def_id].number + 2) // 3
    if card.charm and not is_curse_charm(card.charm):
        base += {"common": 4, "rare": 8, "legendary": 14}[CHARMS[card.charm].rarity]
    return base * (card.star + 1)


def sell_price(card) -> int:
    return max(1, card_price(card) // 2)


def needs_confirm(card) -> bool:
    """Selling / discarding a Major or a ★2+ card asks for confirmation."""
    return is_major(card) or card.star >= 1


# --- card generation ----------------------------------------------------------------------------
def _roll_charm(rng):
    r = rng.random()
    if r < 0.75:
        pool = [c for c in CHARMS.values() if c.rarity == "common"]
    elif r < 0.97:
        pool = [c for c in CHARMS.values() if c.rarity == "rare"]
    else:
        pool = [c for c in CHARMS.values() if c.rarity == "legendary"]
    return rng.choice(pool).id


def _gen_card(rng, step, major_chance, charm=None) -> Card:
    if rng.random() < major_chance:
        return Card(rng.choice(MAJOR_IDS), rng.random() < 0.5, 0,
                    _roll_charm(rng) if charm else 0)
    e = rng.randrange(4)
    r = rng.random()
    if r < 0.06:
        n = 1
    elif r < 0.10:
        n = 10
    else:
        n = rng.randint(2, 6) if step < 2 else rng.randint(3, 9)
    star = 1 if step >= 3 and rng.random() < 0.10 else 0
    has_charm = charm if charm is not None else rng.random() < 0.15
    return Card(e * 10 + n - 1, rng.random() < 0.5, star, _roll_charm(rng) if has_charm else 0)


def _distinct(rng, count, make):
    out, seen = [], set()
    for _ in range(60):
        c = make()
        if c.def_id not in seen:
            seen.add(c.def_id)
            out.append(c)
            if len(out) == count:
                break
    return out


_STARTER_IDS = {d for d, _ in STARTER}


def draft_options(run, pick: int) -> list:
    """Pick 1 of 3, identical for tutorial rewards and Fate's Draft (depends only on seed + pick)."""
    rng = random.Random("%s:draft:%d" % (run.seed, pick))
    elems = list(range(4))
    rng.shuffle(elems)
    cards = []
    count = 2 if pick == 2 else 3
    for k in range(count):
        e = elems[k]
        for _ in range(40):
            n = rng.randint(2, 6)
            d = e * 10 + n - 1
            if d not in _STARTER_IDS:
                break
        cards.append(Card(d, rng.random() < 0.5))
    if pick == 2:
        cards.append(Card(rng.choice(MAJOR_IDS), rng.random() < 0.5))
    for i, c in enumerate(cards):
        c.uid = 0
    return cards


# --- XP / levels --------------------------------------------------------------------------------
def add_xp(run, n) -> int:
    gained = 0
    run.xp += n
    while run.level < MAX_LEVEL and run.xp >= LEVEL_XP[run.level + 1]:
        run.level += 1
        run.pending_levels.append(run.level)
        gained += 1
    if gained:
        arm_tip(run, "first_levelup")
    return gained


LEVEL_UP_INFO = {
    "feast": ("Feast", "+8 max HP and restore 8 HP."),
    "wider_cloth": ("Wider Cloth", "+1 Spread Slot."),
    "bigger_box": ("Bigger Box", "+2 Box slots."),
    "sharpen": ("Sharpen Claws", "Pick a card: it gets +1 Star."),
    "lucky_cat": ("Lucky Cat", "+15 Treats."),
}


def level_up_options(run) -> list:
    """Three option keys for the first pending Level Up."""
    if not run.pending_levels:
        return []
    lvl = run.pending_levels[0]
    rng = _rng(run, "level", lvl)
    pool = ["feast", "lucky_cat"]
    if run.spread_size < MAX_SPREAD:
        pool.append("wider_cloth")
    if run.box_size < MAX_BOX:
        pool.append("bigger_box")
    if any(c.star < 2 for c in all_cards(run)):
        pool.append("sharpen")
    rng.shuffle(pool)
    out = pool[:3]
    if lvl in (2, 4) and "wider_cloth" in pool and "wider_cloth" not in out:
        out[-1] = "wider_cloth"
    return out


def apply_level_up(run, key, uid=None) -> str:
    if key == "sharpen":
        _, _, c = find_card(run, uid)
        if c is None or c.star >= 2:
            return "need_card"
        c.star += 1
    elif key == "feast":
        run.max_hp += 8
        run.hp = min(run.max_hp, run.hp + 8)
    elif key == "wider_cloth":
        if run.spread_size >= MAX_SPREAD:
            return "full"
        run.spread_size += 1
        run.spread.append(None)
    elif key == "bigger_box":
        run.box_size += 2
        run.box.extend([None, None])
    elif key == "lucky_cat":
        run.treats += 15
    else:
        raise ValueError(key)
    if run.pending_levels:
        run.pending_levels.pop(0)
    return "ok"


# --- battle rewards -----------------------------------------------------------------------------
def tutorial_lesson_of(enemy_key):
    return TUTORIAL_KEYS.index(enemy_key) if enemy_key in TUTORIAL_KEYS else -1


def battle_rewards(run, enemy, result) -> Rewards:
    """Apply a won battle to the run (HP, Treats, XP, spent Charms, records) and roll the reward."""
    if isinstance(enemy, str):
        enemy = ENEMIES[enemy]
    if not result.won:
        raise ValueError("battle_rewards needs a won battle")
    run.hp = max(1, result.hp_left)
    for uid in result.spent_charm_uids:
        _, _, c = find_card(run, uid)
        if c is not None:
            c.charm = 0
    run.flags.pop("start_drowsy", None)
    run.flags.pop("mouse_chew", None)
    if enemy.tier == "tutorial":
        run.hp = run.max_hp
        return Rewards(0, 0, draft_options(run, tutorial_lesson_of(enemy.key)), 0)
    run.stats["battles"] = run.stats.get("battles", 0) + 1
    run.stats["beats"] = run.stats.get("beats", 0) + result.beats
    run.stats["best_hit"] = max(run.stats.get("best_hit", 0), result.best_hit)
    if enemy.tier == "elite":
        run.stats["elites"] = run.stats.get("elites", 0) + 1
    rng = _rng(run, "reward", run.step)
    if enemy.tier == "boss":
        run.treats += result.treats
        return Rewards(0, 0, [Card(enemy.chewed, rng.random() < 0.5, 0, 0, 0)], 0)
    base = 12 if enemy.tier == "elite" else 6
    stash = min(5, run.treats // 5)
    run.treats += base + stash + result.treats
    levels = add_xp(run, result.xp)
    if enemy.tier == "elite":
        cards = [Card(enemy.chewed, rng.random() < 0.5)]
        cards += _distinct(rng, 2, lambda: _gen_card(rng, run.step, 0.0, charm=True))
    else:
        cards = _distinct(rng, 3, lambda: _gen_card(rng, run.step, 0.05))
    if any(is_major(c) for c in cards):
        arm_tip(run, "first_major")
    return Rewards(base + stash + result.treats, result.xp, cards, SKIP_TREATS, levels, stash)


def skip_reward(run, rewards=None):
    run.treats += SKIP_TREATS


# --- Spots' Stall -------------------------------------------------------------------------------
_SERVICE_NAMES = {
    "wider_cloth": ("Wider Cloth", "+1 Spread Slot."),
    "bigger_box": ("Bigger Box", "+2 Box slots."),
    "charm_up": ("Charm Up", "A random Charm for a card you pick."),
    "flea_bath": ("Flea Bath", "Remove a Curse from a card you pick."),
    "flip": ("Flip", "Permanently flip a card you pick."),
}
SERVICE_INFO = _SERVICE_NAMES


def _stall_cards(run, rng):
    return [StallItem("card", card_price(c), card=c, index=i)
            for i, c in enumerate(_distinct(rng, 4, lambda: _gen_card(rng, run.step, 0.25)))]


def stall_stock(run) -> StallStock:
    arm_tip(run, "first_stall")
    if run.stall is not None:
        return run.stall
    rng = _rng(run, "stall", run.step, 0)
    opts = ["charm_up", "flip"]
    if run.spread_size < MAX_SPREAD:
        opts.append("wider_cloth")
    if run.box_size < MAX_BOX:
        opts.append("bigger_box")
    if has_curse(run):
        opts.append("flea_bath")
    svc = rng.choice(opts)
    price = {"wider_cloth": 15 if run.spread_size == 4 else 25, "bigger_box": 8,
             "charm_up": 10, "flea_bath": 6, "flip": 3}[svc]
    run.stall = StallStock(_stall_cards(run, rng), StallItem("service", price, service=svc),
                           StallItem("tuna", TUNA_PRICE), 2)
    return run.stall


def buy(run, item, uid=None) -> str:
    """Buy a StallItem. Cards: take_card's status ("spread"/"box"/"duplicate"/"box_full").
    Services needing a card without `uid` return "need_card". Else "ok", "poor" or "sold"."""
    if item.sold:
        return "sold"
    if run.treats < item.price:
        return "poor"
    if item.kind == "tuna":
        run.treats -= item.price
        run.hp = min(run.max_hp, run.hp + TUNA_HEAL)
        return "ok"
    if item.kind == "card":
        run.treats -= item.price
        item.sold = True
        return take_card(run, item.card)
    svc = item.service
    if svc in ("charm_up", "flea_bath", "flip"):
        _, _, c = find_card(run, uid)
        if c is None:
            return "need_card"
        if svc == "flea_bath" and not is_curse_charm(c.charm):
            return "need_card"
        if svc == "flip":
            c.reversed = not c.reversed
        elif svc == "flea_bath":
            c.charm = 0
        else:
            c.charm = _stall_charm(run, c)
    elif svc == "wider_cloth":
        if run.spread_size >= MAX_SPREAD:
            return "sold"
        run.spread_size += 1
        run.spread.append(None)
    elif svc == "bigger_box":
        run.box_size += 2
        run.box.extend([None, None])
    run.treats -= item.price
    item.sold = True
    return "ok"


def _stall_charm(run, card):
    rng = _rng(run, "charmup", run.step, card.uid)
    for _ in range(20):
        c = _roll_charm(rng)
        if c != card.charm:
            return c
    return CATNIP


def sell(run, uid) -> int:
    """Sell a card for half price (min 1). Returns Treats gained (0 if not found)."""
    c = remove_card(run, uid)
    if c is None:
        return 0
    n = sell_price(c)
    run.treats += n
    return n


def reroll(run) -> StallStock:
    st = stall_stock(run)
    if run.treats < st.reroll_cost:
        return st
    run.treats -= st.reroll_cost
    st.rerolls += 1
    st.reroll_cost = 2 + st.rerolls
    st.cards = _stall_cards(run, _rng(run, "stall", run.step, st.rerolls))
    return st


# --- Cat Bed ------------------------------------------------------------------------------------
def groom_targets(run) -> list:
    """Cards Groom can act on: Cursed cards first (remove Curse), else any card (Flip)."""
    cursed = [c for c in all_cards(run) if is_curse_charm(c.charm)]
    return cursed or all_cards(run)


def cat_bed(run, choice, uid=None) -> str:
    """choice: "nap" | "sharpen" | "groom". Returns "ok" or "need_card"."""
    if choice == "nap":
        run.hp = min(run.max_hp, run.hp + run.max_hp * 30 // 100)
        return "ok"
    _, _, c = find_card(run, uid)
    if c is None:
        return "need_card"
    if choice == "sharpen":
        if c.star >= 2:
            return "need_card"
        c.star += 1
        return "ok"
    if choice == "groom":
        if is_curse_charm(c.charm):
            c.charm = 0
        elif has_curse(run):
            return "need_card"
        else:
            c.reversed = not c.reversed
        return "ok"
    raise ValueError(choice)


# --- Encounters ---------------------------------------------------------------------------------
ENCOUNTERS = {
    "lost_mouse": EncounterDef(
        "lost_mouse", "Lost Mouse", "A tiny mouse is stuck behind a sock. It looks scared.",
        [EncounterOption("Let it go", "Next battle, it chews up the enemy's first card. +1 Mouse Token."),
         EncounterOption("Eat it", "Restore 12 HP. +2 max HP.")]),
    "catnip_patch": EncounterDef(
        "catnip_patch", "Catnip Patch", "A patch of catnip grows in a crack in the floor.",
        [EncounterOption("Sniff", "A random card gets Catnip."),
         EncounterOption("Roll around", "Restore 20 HP. Start next battle with 2 Drowsy.")]),
    "zero_booth": EncounterDef(
        "zero_booth", "Zero's Reading Booth", "Zero sits in a tiny booth made of boxes. \"Want a reading?\"",
        [EncounterOption("Draw a card", "Gain a random Major. If it is Reversed, another card gets Rat Bite."),
         EncounterOption("Walk away", "Nothing happens.")]),
    "granny_dream": EncounterDef(
        "granny_dream", "Granny's Dream", "You curl up and dream of Granny's warm lap.",
        [EncounterOption("Choose a card", "Permanently Flip it and +1 Star.", True),
         EncounterOption("Rest", "Restore 30% max HP.")]),
    "loose_page": EncounterDef(
        "loose_page", "Loose Page", "A torn page flutters by, covered in strange cards.",
        [EncounterOption("Pick it up", "Gain a random 2-Star Minor (always Reversed)."),
         EncounterOption("Burn it", "A random card gets Moonlight.")]),
    "yarn_ball": EncounterDef(
        "yarn_ball", "Ball of Yarn", "A ball of yarn rolls past. So tempting.",
        [EncounterOption("Chase it!", "50%: a card gets Yarn. 50%: lose 5 HP."),
         EncounterOption("Ignore it", "Nothing happens.")]),
}


def encounter(run) -> EncounterDef:
    return ENCOUNTERS[run.current.key]


def _random_card(run, rng, no_charm=False, exclude_uid=0):
    cards = [c for c in all_cards(run) if c.uid != exclude_uid and not (no_charm and c.charm)]
    if not cards and no_charm:
        cards = [c for c in all_cards(run) if c.uid != exclude_uid]
    return rng.choice(cards) if cards else None


def resolve_encounter(run, choice, uid=None) -> EncounterResult:
    key = run.current.key
    rng = _rng(run, "enc", run.step)
    if key == "lost_mouse":
        if choice == 0:
            run.flags["mouse_chew"] = 1
            run.mouse_tokens += 1
            return EncounterResult("The mouse scampers off. It will help you in the next battle.")
        run.max_hp += 2
        run.hp = min(run.max_hp, run.hp + 12)
        return EncounterResult("Yum! +2 max HP.")
    if key == "catnip_patch":
        if choice == 0:
            c = _random_card(run, rng, no_charm=True)
            if c is None:
                return EncounterResult("Sniff sniff. Nothing happens.")
            c.charm = CATNIP
            return EncounterResult("%s gets Catnip!" % CARD_DEFS[c.def_id].name)
        run.hp = min(run.max_hp, run.hp + 20)
        run.flags["start_drowsy"] = 2
        return EncounterResult("So relaxing. A little too relaxing...")
    if key == "zero_booth":
        if choice == 1:
            return EncounterResult("You walk away.")
        card = Card(rng.choice(MAJOR_IDS), rng.random() < 0.5)
        status = take_card(run, card)
        text = "Zero flips a card: %s." % CARD_DEFS[card.def_id].name
        if card.reversed:
            c = _random_card(run, rng, exclude_uid=card.uid)
            if c is not None:
                c.charm = RAT_BITE
                arm_tip(run, "first_curse")
                text += " A rat gnaws one of your cards."
        return EncounterResult(text, card, status)
    if key == "granny_dream":
        if choice == 1:
            run.hp = min(run.max_hp, run.hp + run.max_hp * 30 // 100)
            return EncounterResult("You wake up feeling rested.")
        _, _, c = find_card(run, uid)
        if c is None:
            return EncounterResult("Pick a card.", None, "need_card")
        c.reversed = not c.reversed
        c.star = min(2, c.star + 1)
        return EncounterResult("Granny's dream changes the card.")
    if key == "loose_page":
        if choice == 0:
            card = _gen_card(rng, 0, 0.0, charm=False)
            card.star = 1
            card.reversed = True
            status = take_card(run, card)
            return EncounterResult("A new card!", card, status)
        c = _random_card(run, rng, no_charm=True)
        if c is None:
            return EncounterResult("The page burns away.")
        c.charm = MOONLIGHT
        return EncounterResult("%s gets Moonlight!" % CARD_DEFS[c.def_id].name)
    if key == "yarn_ball":
        if choice == 1:
            return EncounterResult("You ignore it.")
        if rng.random() < 0.5:
            c = _random_card(run, rng, no_charm=True)
            if c is not None:
                c.charm = YARN
                return EncounterResult("Got it! %s gets Yarn." % CARD_DEFS[c.def_id].name)
            return EncounterResult("Got it! Nothing to tie it to.")
        run.hp = max(1, run.hp - 5)
        return EncounterResult("It bites back! -5 HP.")
    raise ValueError(key)


def open_box(run) -> Card:
    """Cardboard Box: one card (40% Major), 50% with a Charm. Pass the card to take_card()."""
    rng = _rng(run, "box", run.step)
    return _gen_card(rng, run.step, 0.40, charm=rng.random() < 0.5)


# --- tutorial -----------------------------------------------------------------------------------
_LESSONS = (
    ("practice_mouse", [(FIRE * 10 + 2, False), (FIRE * 10 + 3, False), (AIR * 10 + 4, True),
                        (WATER * 10 + 2, False)], "Cards play left to right."),
    ("dust_mouse", [(FIRE * 10 + 2, False), (FIRE * 10 + 3, False), (WATER * 10 + 2, False),
                    (AIR * 10 + 4, True)], "Fire next to Water hisses. Move the Water card."),
    ("coin_mouse", [(EARTH * 10 + 1, False), (FIRE * 10 + 2, False), (AIR * 10 + 4, True),
                    (FIRE * 10 + 3, False)], "Put the numbers in order: 2-3-4-5 is a Catwalk."),
)


def tutorial_setup(run, lesson) -> TutorialLesson:
    """Rebuild the Spread for tutorial lesson 0..2 (keeps cards the player picked, in the Box)."""
    enemy, cards, note = _LESSONS[lesson]
    old = set(run.flags.get("tut_uids", ()))
    keep = [c for c in all_cards(run) if c.uid not in old]
    run.spread = [None] * run.spread_size
    run.box = [None] * run.box_size
    for c in keep:
        _place(run, c, ("box",))
    mine = []
    for k, (d, r) in enumerate(cards):
        c = Card(d, r, 0, 0, _uid(run))
        run.spread[k] = c
        mine.append(c.uid)
    run.flags["tut_uids"] = mine
    run.flags["lesson"] = lesson
    run.flags["to_box"] = True
    run.hp = run.max_hp
    return TutorialLesson(lesson, enemy, list(run.spread), note)


def finish_tutorial(run):
    """End the prologue: restore the starting Spread, keep picked cards in the Box."""
    old = set(run.flags.get("tut_uids", ()))
    keep = [c for c in all_cards(run) if c.uid not in old]
    run.spread = [Card(d, r, 0, 0, _uid(run)) for d, r in STARTER] + [None] * (run.spread_size - 4)
    run.box = [None] * run.box_size
    for c in keep:
        _place(run, c, ("box", "spread"))
    for k in ("tut_uids", "lesson", "to_box"):
        run.flags.pop(k, None)
    run.tutorial = False
    run.hp = run.max_hp
    run.step = 0
