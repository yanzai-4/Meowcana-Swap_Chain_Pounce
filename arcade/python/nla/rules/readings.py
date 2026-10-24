"""Readings (Elemental Dignity, Number Path, Fool's Journey, Litter, Mirror Cat, Major Readings)
and Power calculation. `compute` is shared by the Spread preview (`analyze`) and the battle
simulator, so previews never lie.

Power = floor((base + flat) * (100 + sum_pct) / 100 * product_mult), minimum 1, with all
multipliers in fixed point. Majors whose effect is a percentage (Fool, Magician, Paw Punch,
Magnifying Glass, ...) carry that percentage as their Power (SlotInfo.pct is True).
"""
from dataclasses import dataclass, field

from .cards import (CARD_DEFS, MAJOR_DATA, FIXED, FIRE, AIR, WATER, EARTH, FOOL, MAGICIAN,
                    EMPRESS, EMPEROR, CHARIOT, STRENGTH, HANGED, SUN, DROPPINGS, CATNIP,
                    MOONLIGHT, RAT_BITE, skill_for)


@dataclass
class SlotInfo:
    power: int
    base: int
    parts: list = field(default_factory=list)   # [("Nuzzle", "+2"), ("Two-Tone", "+25%")]
    pct: bool = False                            # Power is a percent (Fool, Magician, ...)
    skill: str = ""                              # skill name for the current orientation


@dataclass
class Link:
    a: int
    b: int
    kind: str   # nuzzle tail_tap hiss step mirror litter journey catwalk major
    name: str = ""    # display name ("Nuzzle", "Long Catwalk", "Lion Sun", ...)
    value: int = 0    # signed flat bonus for dignity/step/litter links, else 0


@dataclass
class SpreadReport:
    slots: list
    links: list
    readings: list
    per_round: dict
    again: list = field(default_factory=list)       # slots that Activate again (Catwalk / Journey end)
    major_readings: list = field(default_factory=list)   # display names
    ctx: set = field(default_factory=set)           # internal keys: lion_sun, throne, ...
    mirror: dict = field(default_factory=dict)      # slot -> partner slot
    eat_slot: int = -1                               # slot Chubbs would eat (only vs Chubbs)


@dataclass
class Item:
    """One occupied slot as seen by the Power calculator."""
    def_id: int
    reversed: bool
    star: int = 0
    charm: int = 0
    flat: int = 0         # battle-long flat Power (Ace, Zoomies growth, ...)
    next_flat: int = 0    # Yarn
    next_pct: int = 0     # New Angle


MAJOR_READINGS = (
    ("new_journey", "New Journey"), ("throne", "The Throne"), ("willpower", "Willpower"),
    ("lion_sun", "Lion Sun"), ("upside_sun", "Upside Sun"), ("four_seeds", "Four Seeds"),
    ("completion", "Completion"),
)
_ORDER = ("Nuzzle", "Tail Tap", "Hiss", "Step", "Catwalk", "Long Catwalk", "Twins", "Triplets",
          "Full Litter", "Mirror Cat", "Fool's Journey")


def _relation(ea, eb):
    if ea == eb:
        return "Nuzzle", 2, "nuzzle"
    s = {ea, eb}
    if s == {FIRE, AIR} or s == {WATER, EARTH}:
        return "Tail Tap", 1, "tail_tap"
    if s == {FIRE, WATER} or s == {AIR, EARTH}:
        return "Hiss", -1, "hiss"
    return None


def _signed(v):
    return ("+%d" % v) if v >= 0 else str(v)


def compute(items, domino=True) -> SpreadReport:
    n = len(items)
    live = [it is not None for it in items]
    drop = [live[i] and items[i].def_id == DROPPINGS for i in range(n)]
    cl = [live[i] and not drop[i] for i in range(n)]
    minor = [cl[i] and items[i].def_id < 40 for i in range(n)]
    major = [cl[i] and items[i].def_id in MAJOR_DATA for i in range(n)]
    num = [CARD_DEFS[items[i].def_id].number if cl[i] else -99 for i in range(n)]
    flat = [0] * n
    pct = [0] * n
    mult = [[] for _ in range(n)]
    parts = [[] for _ in range(n)]
    links = []
    counts = {}
    again = []
    mirror = {}
    ctx = set()
    major_names = []

    def count(name):
        counts[name] = counts.get(name, 0) + 1

    def add_flat(i, v, name):
        flat[i] += v
        parts[i].append((name, _signed(v)))

    def add_pct(i, v, name):
        pct[i] += v
        parts[i].append((name, _signed(v) + "%"))

    # Elemental Dignity (the upright Fool counts as the same element as each neighbor)
    for i in range(n - 1):
        j = i + 1
        if not (cl[i] and cl[j]):
            continue
        a, b = items[i], items[j]
        ea, eb = CARD_DEFS[a.def_id].element, CARD_DEFS[b.def_id].element
        if (a.def_id == FOOL and not a.reversed) or (b.def_id == FOOL and not b.reversed):
            eb = ea
        rel = _relation(ea, eb)
        if rel:
            name, v, kind = rel
            add_flat(i, v, name)
            add_flat(j, v, name)
            links.append(Link(i, j, kind, name, v))
            count(name)

    # Number Path: Step and Catwalk (Minor numbers only)
    for i in range(1, n):
        if minor[i] and minor[i - 1] and num[i - 1] == num[i] - 1:
            add_flat(i, 2, "Step")
            links.append(Link(i - 1, i, "step", "Step", 2))
            count("Step")
    i = 0
    while i < n:
        if not minor[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and minor[j + 1] and num[j + 1] == num[j] + 1:
            j += 1
        length = j - i + 1
        if length >= 3:
            again.append(j)
            links.append(Link(i, j, "catwalk", "Long Catwalk" if length >= 5 else "Catwalk"))
            if length >= 5:
                count("Long Catwalk")
                for k in range(i, j + 1):
                    mult[k].append(150)
                    parts[k].append(("Long Catwalk", "x1.5"))
            else:
                count("Catwalk")
        i = j + 1

    # Litter: same-number Minors side by side
    i = 0
    while i < n:
        if not minor[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and minor[j + 1] and num[j + 1] == num[i]:
            j += 1
        length = j - i + 1
        if length >= 2:
            name = ("Twins", "Triplets", "Full Litter")[min(length, 4) - 2]
            count(name)
            for k in range(i, j):
                links.append(Link(k, k + 1, "litter", name, 2 if length == 2 else 4 if length == 3 else 0))
            for k in range(i, j + 1):
                if length == 2:
                    add_flat(k, 2, name)
                elif length == 3:
                    add_flat(k, 4, name)
                else:
                    mult[k].append(200)
                    parts[k].append((name, "x2"))
        i = j + 1

    # Mirror Cat
    for i in range(n - 1):
        j = i + 1
        if cl[i] and cl[j] and items[i].def_id == items[j].def_id \
                and items[i].reversed != items[j].reversed:
            mirror[i] = j
            mirror[j] = i
            links.append(Link(i, j, "mirror", "Mirror Cat"))
            count("Mirror Cat")

    # Fool's Journey (Majors with consecutive numbers, left to right)
    i = 0
    while i < n:
        if not major[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and major[j + 1] and num[j + 1] == num[j] + 1:
            j += 1
        length = j - i + 1
        if length >= 2:
            count("Fool's Journey")
            for k in range(i, j):
                links.append(Link(k, k + 1, "journey", "Fool's Journey"))
            for k in range(i, j + 1):
                add_pct(k, 25, "Fool's Journey")
            if length >= 3:
                again.append(j)
        i = j + 1

    # Major Readings (same Spread, any orientation)
    first = {}
    for i in range(n):
        if cl[i]:
            first.setdefault(items[i].def_id, i)

    mname = dict(MAJOR_READINGS)

    def major_pair(key, a, b):
        if a in first and b in first:
            ctx.add(key)
            links.append(Link(min(first[a], first[b]), max(first[a], first[b]), "major", mname[key]))

    major_pair("new_journey", FOOL, MAGICIAN)
    major_pair("throne", EMPRESS, EMPEROR)
    major_pair("willpower", CHARIOT, STRENGTH)
    major_pair("lion_sun", STRENGTH, SUN)
    major_pair("upside_sun", HANGED, SUN)
    ace_slots = [i for i in range(n) if minor[i] and num[i] == 1]
    if len({CARD_DEFS[items[i].def_id].element for i in ace_slots}) == 4:
        ctx.add("four_seeds")
        links.append(Link(min(ace_slots), max(ace_slots), "major", "Four Seeds"))
    tens = [i for i in range(n) if minor[i] and num[i] == 10]
    if len(tens) >= 2:
        ctx.add("completion")
        links.append(Link(tens[0], tens[1], "major", "Completion"))
    for key, name in MAJOR_READINGS:
        if key in ctx:
            major_names.append(name)

    # Percent auras
    sun_pct = sum(FIXED["sunbathe_pct"][items[k].star] for k in range(n)
                  if cl[k] and items[k].def_id == SUN and not items[k].reversed)
    loose_pct = sum(FIXED["hangloose_pct"][items[k].star] for k in range(n)
                    if cl[k] and items[k].def_id == HANGED and items[k].reversed)
    for i in range(n):
        if not cl[i]:
            continue
        it = items[i]
        el = CARD_DEFS[it.def_id].element
        if it.reversed and domino:
            add_pct(i, 25, "Two-Tone")
        if it.reversed and it.charm == MOONLIGHT:
            add_pct(i, 50, "Moonlight")
        if sun_pct and (not it.reversed or "upside_sun" in ctx):
            add_pct(i, sun_pct, "Sunbathe")
        if loose_pct and it.reversed:
            add_pct(i, loose_pct, "Hang Loose")
        if "lion_sun" in ctx and el == FIRE:
            add_pct(i, 25, "Lion Sun")
        if "completion" in ctx and minor[i] and num[i] == 10:
            add_pct(i, 50, "Completion")
        if it.charm == RAT_BITE:
            add_pct(i, -30, "Rat Bite")
        for k in (i - 1, i + 1):
            if 0 <= k < n and drop[k]:
                add_pct(i, -50, "Droppings")
        if it.next_pct:
            add_pct(i, it.next_pct, "New Angle")
        if it.charm == CATNIP:
            add_flat(i, 2, "Catnip")
        if it.flat:
            add_flat(i, it.flat, "Battle")
        if it.next_flat:
            add_flat(i, it.next_flat, "Yarn")

    slots = []
    for i in range(n):
        if not live[i]:
            slots.append(None)
            continue
        it = items[i]
        if drop[i]:
            slots.append(SlotInfo(0, 0, [], False, "Droppings"))
            continue
        sk = skill_for(it.def_id, it.reversed)
        base = sk.powers[it.star]
        if sk.unit == "none":
            slots.append(SlotInfo(0, 0, [], False, sk.name))
            continue
        p = (base + flat[i]) * (100 + pct[i])
        for m in mult[i]:
            p = p * m // 100
        slots.append(SlotInfo(max(1, p // 100), base, parts[i], sk.unit == "pct", sk.name))

    readings = []
    for name in _ORDER:
        c = counts.get(name, 0)
        if c:
            readings.append(name if c == 1 else "%s x%d" % (name, c))
    readings.extend(major_names)
    return SpreadReport(slots, links, readings, {}, sorted(set(again)), major_names, ctx, mirror)


def items_from_cards(spread):
    return [None if c is None else Item(c.def_id, c.reversed, c.star, c.charm) for c in spread]


def analyze(spread, run=None, enemy=None) -> SpreadReport:
    """Full preview of a Spread of Card|None: Power per slot, Readings, links, per-Round output."""
    from .battle import preview_round
    items = items_from_cards(spread)
    rep = compute(items, True)
    rep.per_round = preview_round(items)
    key = getattr(enemy, "key", enemy)
    if key == "chubbs":
        best, idx = -1, -1
        for i, c in enumerate(spread):
            if c is not None and c.def_id < 40 and rep.slots[i] and rep.slots[i].power > best:
                best, idx = rep.slots[i].power, i
        rep.eat_slot = idx
    return rep
