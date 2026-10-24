"""Card, charm and scrap definitions plus all rules text (pure Python, stdlib only).

Id contract (shared with the art pipeline):
  Minor = element * 10 + (number - 1)   -> 0..39   (Ace = number 1)
  Majors 40..47: Fool, Magician, Empress, Emperor, Chariot, Strength, Hanged Man, Sun
  48 = Droppings (curse card, battle-only)
Charm ids 1..9 follow the GDD order. Scrap kinds are the art keys in SCRAP_KINDS order.
"""
from dataclasses import dataclass
from typing import Optional

FIRE, AIR, WATER, EARTH = 0, 1, 2, 3
ELEMENT_NAMES = ("Fire", "Air", "Water", "Earth")
SUIT_NAMES = ("Wands", "Swords", "Cups", "Pentacles")

FOOL, MAGICIAN, EMPRESS, EMPEROR, CHARIOT, STRENGTH, HANGED, SUN = range(40, 48)
DROPPINGS = 48
MAJOR_IDS = tuple(range(40, 48))

CATNIP, FISH_BONE, PAW_PAD, YARN, BELL, MOONLIGHT, NINE_LIVES, RAT_BITE, FLEAS = range(1, 10)

STAR_PCT = (100, 150, 200)


@dataclass(frozen=True)
class CardDef:
    id: int
    name: str
    element: int
    number: int
    is_major: bool


@dataclass
class Card:
    def_id: int
    reversed: bool = False
    star: int = 0      # 0..2 = ★1..★3
    charm: int = 0     # 0 = none, 1..9 see CHARMS
    uid: int = 0       # stable identity for UI


@dataclass(frozen=True)
class CharmDef:
    id: int
    name: str
    rarity: str   # "common" | "rare" | "legendary" | "curse"
    text: str


@dataclass(frozen=True)
class Scrap:
    kind: str       # one of SCRAP_KINDS
    value: int = 0  # X
    hits: int = 1   # 2 for Gnaw X x2


SCRAP_KINDS = ["broken_sword", "gnaw", "burnt_wand", "cracked_coin", "leaky_cup", "bite_mark",
               "snatch", "burrow", "droppings", "fleas", "sleep_dust"]


@dataclass(frozen=True)
class Skill:
    key: str            # engine dispatch key
    name: str           # player-visible skill name
    powers: tuple       # base Power per star (0 = no Power)
    unit: str           # "pow" (plain number), "pct" (Power is a percent) or "none"


ROMAN = {40: "0", 41: "I", 42: "III", 43: "IV", 44: "VII", 45: "VIII", 46: "XII", 47: "XIX"}

# --- Major table -----------------------------------------------------------------------------
_NONE = Skill("none", "", (0, 0, 0), "none")


def _sk(key, name, powers, unit="pow"):
    return Skill(key, name, powers, unit)


MAJOR_DATA = {
    FOOL: dict(name="The Fool", cat="Zero the Stray", element=AIR, number=0,
               up=_sk("fool_up", "Follow Along", (50, 75, 100), "pct"),
               rev=_sk("fool_rev", "Wander", (7, 10, 13)),
               flavor="Every journey starts with one silly step."),
    MAGICIAN: dict(name="The Magician", cat="Trick Cat", element=AIR, number=1,
                   up=_sk("magician_up", "Sleight of Paw", (50, 75, 100), "pct"),
                   rev=_sk("magician_rev", "Copycat", (80, 100, 130), "pct"),
                   flavor="Now you see the treat. Now you don't."),
    EMPRESS: dict(name="The Empress", cat="Mama Cat", element=EARTH, number=3,
                  up=_sk("empress_up", "Nurture", (6, 9, 12)),
                  rev=_sk("empress_rev", "Spilled Milk", (0, 0, 0), "none"),
                  flavor="Mama's lap is always warm."),
    EMPEROR: dict(name="The Emperor", cat="Box King", element=FIRE, number=4,
                  up=_sk("emperor_up", "My Box", (6, 9, 12)),
                  rev=_sk("emperor_rev", "Paw Punch", (60, 80, 100), "pct"),
                  flavor="If it fits, I sit. If I sit, it's mine."),
    CHARIOT: dict(name="The Chariot", cat="Zoomies Cat", element=WATER, number=7,
                  up=_sk("chariot_up", "Zoomies", (4, 6, 8)),
                  rev=_sk("chariot_rev", "Crash", (0, 0, 0), "none"),
                  flavor="3 a.m. Hallway. Nobody can stop me."),
    STRENGTH: dict(name="Strength", cat="Lionheart", element=FIRE, number=8,
                   up=_sk("strength_up", "Puff Up", (2, 3, 4)),
                   rev=_sk("strength_rev", "Feral", (4, 6, 8)),
                   flavor="A lion is just a big cat."),
    HANGED: dict(name="The Hanged Man", cat="Upside-Down Cat", element=WATER, number=12,
                 up=_sk("hanged_up", "New Angle", (30, 50, 70), "pct"),
                 rev=_sk("hanged_rev", "Hang Loose", (0, 0, 0), "none"),
                 flavor="Hang upside down long enough and the rats are on the ceiling."),
    SUN: dict(name="The Sun", cat="Sunbeam Cat", element=FIRE, number=19,
              up=_sk("sun_up", "Sunbathe", (2, 3, 4)),
              rev=_sk("sun_rev", "Magnifying Glass", (200, 300, 400), "pct"),
              flavor="3 p.m. Windowsill. Best spot in the universe."),
}

# Fixed per-star numbers that are not "Power" (auras, side effects).
FIXED = {
    "nurture_bonus": (2, 3, 4),
    "spilled_pct": (100, 125, 150),
    "mybox_keep": (50, 75, 100),
    "zoomies_growth": (2, 3, 4),
    "crash_dmg": (3, 2, 1),
    "hangloose_pct": (20, 30, 40),
    "sunbathe_pct": (15, 20, 30),
    "wander_range": ((2, 12), (4, 16), (6, 20)),
    "ace_up_bonus": (1, 2, 3),
    "ace_rev_bonus": (2, 3, 4),
}

_MINOR_SKILLS = {
    (FIRE, False): ("fire_up", "Fire Claw"),
    (FIRE, True): ("fire_rev", "Knock the Candle"),
    (AIR, False): ("air_up", "Double Swipe"),
    (AIR, True): ("air_rev", "Ambush"),
    (WATER, False): ("water_up", "Lick Wounds"),
    (WATER, True): ("water_rev", "Push the Cup"),
    (EARTH, False): ("earth_up", "Coin Nap"),
    (EARTH, True): ("earth_rev", "Bat the Coins"),
}


def _make_defs():
    defs = {}
    for e in range(4):
        for n in range(1, 11):
            i = e * 10 + n - 1
            name = ("Ace of " if n == 1 else "%d of " % n) + SUIT_NAMES[e]
            defs[i] = CardDef(i, name, e, n, False)
    for i, d in MAJOR_DATA.items():
        defs[i] = CardDef(i, d["name"], d["element"], d["number"], True)
    defs[DROPPINGS] = CardDef(DROPPINGS, "Droppings", FIRE, 0, False)
    return defs


CARD_DEFS = _make_defs()


def card_def(card_or_id) -> CardDef:
    return CARD_DEFS[card_or_id if isinstance(card_or_id, int) else card_or_id.def_id]


def is_major(card) -> bool:
    return card.def_id in MAJOR_DATA


def is_minor(card) -> bool:
    return card.def_id < 40


def is_ace(card) -> bool:
    return card.def_id < 40 and card.def_id % 10 == 0


def element_of(card) -> int:
    return CARD_DEFS[card.def_id].element


def number_of(card) -> int:
    return CARD_DEFS[card.def_id].number


def skill_for(def_id: int, reversed_: bool) -> Skill:
    """Skill of a face in a given orientation."""
    if def_id == DROPPINGS:
        return _NONE
    if def_id in MAJOR_DATA:
        return MAJOR_DATA[def_id]["rev" if reversed_ else "up"]
    e, n = divmod(def_id, 10)
    if n == 0:
        return Skill("ace_rev" if reversed_ else "ace_up",
                     "Dig" if reversed_ else "Plant the Seed", (2, 3, 4), "pow")
    key, name = _MINOR_SKILLS[(e, reversed_)]
    return Skill(key, name, tuple((((n + 1) * p) // 100) for p in STAR_PCT), "pow")


def base_power(def_id: int, star: int, reversed_: bool) -> int:
    """Power before bonuses: number x Stars (Minor) or the table value (Major)."""
    return skill_for(def_id, reversed_).powers[star]


def has_activate(def_id: int, reversed_: bool) -> bool:
    """False for aura-only faces (Spilled Milk, Hang Loose) and Droppings."""
    if def_id == DROPPINGS:
        return False
    if def_id in (EMPRESS, HANGED) and reversed_:
        return False
    return True


def card_title(card) -> str:
    """"Fire Claw" for Minors (the skill), "The Sun" for Majors."""
    if card.def_id in MAJOR_DATA or card.def_id == DROPPINGS:
        return CARD_DEFS[card.def_id].name
    return skill_for(card.def_id, card.reversed).name


def card_skill_name(card) -> str:
    return skill_for(card.def_id, card.reversed).name


def card_number_text(card) -> str:
    if card.def_id in MAJOR_DATA:
        return ROMAN[card.def_id]
    if card.def_id == DROPPINGS:
        return ""
    n = number_of(card)
    return "A" if n == 1 else str(n)


def card_subtitle(card) -> str:
    """"Wands 4 · ★1 · Upright"."""
    ori = "Reversed" if card.reversed else "Upright"
    if card.def_id == DROPPINGS:
        return "Curse"
    stars = "\u2605%d" % (card.star + 1)
    if card.def_id in MAJOR_DATA:
        return "Major %s \u00b7 %s \u00b7 %s" % (ROMAN[card.def_id], stars, ori)
    n = number_of(card)
    return "%s %s \u00b7 %s \u00b7 %s" % (SUIT_NAMES[element_of(card)], "Ace" if n == 1 else n, stars, ori)


def card_short(card) -> str:
    """Compact label for tight places: "F4", "A5v", "XIX"."""
    if card.def_id in MAJOR_DATA:
        return ROMAN[card.def_id] + ("v" if card.reversed else "")
    if card.def_id == DROPPINGS:
        return "Drop"
    return "FAWE"[element_of(card)] + card_number_text(card) + ("v" if card.reversed else "")


def card_flavor(card) -> str:
    if card.def_id in MAJOR_DATA:
        return MAJOR_DATA[card.def_id]["flavor"]
    if card.def_id == DROPPINGS:
        return "One bad apple spoils the bunch."
    return ("Grumpy hearth cat.", "Rooftop flying cat.", "Windowsill grooming cat.",
            "Cardboard coin-keeper cat.")[element_of(card)]


# --- Charms ------------------------------------------------------------------------------------
CHARMS = {
    CATNIP: CharmDef(CATNIP, "Catnip", "common", "Aura: This card gains +2 Power."),
    FISH_BONE: CharmDef(FISH_BONE, "Fish Bone", "common",
                        "Activate: Gain 1 Treat after this battle. (Max 3 per battle.)"),
    PAW_PAD: CharmDef(PAW_PAD, "Paw Pad", "common", "Activate: Gain 2 Curl."),
    YARN: CharmDef(YARN, "Yarn", "common",
                   "Activate: The Right card gains +2 Power on its next activation."),
    BELL: CharmDef(BELL, "Bell", "rare",
                   "Once per battle: The first time this card activates, activate it again."),
    MOONLIGHT: CharmDef(MOONLIGHT, "Moonlight", "rare",
                        "Aura: While this card is Reversed, it gains +50% Power."),
    NINE_LIVES: CharmDef(NINE_LIVES, "Nine Lives", "legendary",
                         "Once per battle: When you would drop to 0 HP, your HP becomes 1 "
                         "instead. Then destroy this Charm."),
    RAT_BITE: CharmDef(RAT_BITE, "Rat Bite", "curse", "Aura: This card loses 30% Power."),
    FLEAS: CharmDef(FLEAS, "Fleas", "curse", "Activate: Take 1 non-attack damage."),
}
CHARM_RANK = {"curse": -1, "common": 1, "rare": 2, "legendary": 3}


def charm_rank(charm_id: int) -> int:
    return CHARM_RANK[CHARMS[charm_id].rarity] if charm_id else 0


def is_curse_charm(charm_id: int) -> bool:
    return bool(charm_id) and CHARMS[charm_id].rarity == "curse"


def charm_text(charm_id: int) -> list:
    return wrap_lines(CHARMS[charm_id].text)


# --- Rules text --------------------------------------------------------------------------------
LINE_W = 56


def wrap_lines(text: str, width: int = LINE_W) -> list:
    out, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        out.append(cur)
    return out


_MINOR_TEXT = {
    "fire_up": "Activate: Deal P damage. Then inflict 1 Singe.",
    "fire_rev": "Activate: Inflict Singe equal to half P (round up) + 1.",
    "air_up": "Activate: Deal 2 hits. Each hit = half P (round up). "
              "These hits get +10% Crit chance.",
    "air_rev": "Activate: Deal 1 hit equal to P + 2. This hit ignores Curl.",
    "water_up": "Activate: Restore P HP. Then remove 1 stack of a random negative "
                "status from yourself.",
    "water_rev": "Activate: Deal half P (round up) damage. Then restore that much HP.",
    "earth_up": "Activate: Gain P Curl.",
    "earth_rev": "Activate: Lose all your Curl. Then deal damage equal to the Curl lost + P.",
}
_SUIT_UP = ("Fire Claw", "Double Swipe", "Lick Wounds", "Coin Nap")
_SUIT_REV = ("Knock the Candle", "Ambush", "Push the Cup", "Bat the Coins")


def _major_text(def_id: int, rev: bool, s: int) -> str:
    n = lambda k: FIXED[k][s]
    p = MAJOR_DATA[def_id]["rev" if rev else "up"].powers[s]
    if def_id == FOOL and not rev:
        return ("Aura: For Elemental Dignity, this card counts as the same element as each "
                "Adjacent card. Activate: Copy the Right card's Activate effect at %d%% Power." % p)
    if def_id == FOOL:
        lo, hi = n("wander_range")
        return "Activate: Perform a random element's Upright skill with a random Power of %d-%d." % (lo, hi)
    if def_id == MAGICIAN and not rev:
        return ("Activate: Activate the Left card again, then the Right card again. "
                "Each at %d%% Power." % p)
    if def_id == MAGICIAN:
        return ("Activate: Copy the last card the opponent activated, at %d%% Power. "
                "Swap \"you\" and \"the opponent\" in its effect." % p)
    if def_id == EMPRESS and not rev:
        return ("Aura: Whenever you restore HP, restore %d more. Healing above your max HP "
                "becomes Curl. Activate: Restore %d HP." % (n("nurture_bonus"), p))
    if def_id == EMPRESS:
        return ("Aura: Whenever you would restore HP, you restore none. Instead, deal "
                "non-attack damage equal to %d%% of that amount." % n("spilled_pct"))
    if def_id == EMPEROR and not rev:
        return ("Aura: At your Round Start, keep %d%% of your Curl. Activate: Gain %d Curl."
                % (n("mybox_keep"), p))
    if def_id == EMPEROR:
        return "Activate: Deal damage equal to %d%% of your Curl. You keep your Curl." % p
    if def_id == CHARIOT and not rev:
        return ("Activate: Deal %d damage. Then this effect's damage increases by %d "
                "this battle." % (p, n("zoomies_growth")))
    if def_id == CHARIOT:
        return ("Activate: Take %d non-attack damage. Then your Paw moves to your next card "
                "and activates it now. (No Beat used.)" % n("crash_dmg"))
    if def_id == STRENGTH and not rev:
        return "Activate: Gain %d Puff." % p
    if def_id == STRENGTH:
        return "Activate: Gain %d Puff. Then, if your HP is 50%% or more, lose 4 HP." % p
    if def_id == HANGED and not rev:
        return ("Activate: Flip the Adjacent cards. Each flipped card gains +%d%% Power "
                "on its next activation." % p)
    if def_id == HANGED:
        return "Aura: Your Reversed cards gain +%d%% Power." % n("hangloose_pct")
    if def_id == SUN and not rev:
        return ("Aura: Your Upright cards gain +%d%% Power. Activate: Inflict %d Singe."
                % (n("sunbathe_pct"), p))
    return ("Activate: Remove all Singe from the opponent. Then deal non-attack damage "
            "equal to the Singe removed x%d." % (p // 100))


def card_text(card) -> list:
    """Rules text for the card's current face, <= 3 lines x 56 chars."""
    d = card.def_id
    if d == DROPPINGS:
        return wrap_lines("Aura: Adjacent cards lose 50% Power. It takes the last empty Slot.")
    if d in MAJOR_DATA:
        lines = wrap_lines(_major_text(d, card.reversed, card.star))
    elif d % 10 == 0:
        e = d // 10
        sk = _SUIT_REV[e] if card.reversed else _SUIT_UP[e]
        if card.reversed:
            x = FIXED["ace_rev_bonus"][card.star]
            t = ("Activate: Perform %s. Then your other Reversed %s cards gain +%d Power "
                 "this battle, and your other Upright ones lose 1." % (sk, ELEMENT_NAMES[e], x))
        else:
            x = FIXED["ace_up_bonus"][card.star]
            t = ("Activate: Perform %s. Then your other %s cards gain +%d Power this battle. "
                 "(Stacks.)" % (sk, ELEMENT_NAMES[e], x))
        lines = wrap_lines(t)
    else:
        lines = wrap_lines(_MINOR_TEXT[skill_for(d, card.reversed).key])
    return lines


def card_text_full(card) -> list:
    """card_text plus the Charm lines (for the Info overlay)."""
    lines = card_text(card)
    if card.charm:
        lines = lines + [CHARMS[card.charm].name + ":"] + charm_text(card.charm)
    return lines


# --- Scrap text --------------------------------------------------------------------------------
_SCRAP_NAME = {
    "broken_sword": "Broken Sword", "gnaw": "Gnaw", "burnt_wand": "Burnt Wand",
    "cracked_coin": "Cracked Coin", "leaky_cup": "Leaky Cup", "bite_mark": "Bite Mark",
    "snatch": "Snatch", "burrow": "Burrow", "droppings": "Droppings", "fleas": "Fleas",
    "sleep_dust": "Sleep Dust",
}
_SCRAP_TEXT = {
    "broken_sword": "Activate: Deal {x} damage.",
    "gnaw": "Activate: Deal 2 hits of {x}.",
    "burnt_wand": "Activate: Deal {x} damage. Then inflict 1 Singe.",
    "cracked_coin": "Activate: Gain {x} Curl.",
    "leaky_cup": "Activate: Restore {x} HP.",
    "bite_mark": "Activate: Flip the card your opponent's Paw points to.",
    "snatch": "Activate: Deal {x} damage. Steal 1 Treat. (If you win, get it back +1.)",
    "burrow": "Activate: Gain 1 Leap.",
    "droppings": "Activate: Add 1 Droppings to your opponent's Spread. (Once per battle.)",
    "fleas": "Activate: A random card in your opponent's Spread gets the Fleas Curse "
             "this battle.",
    "sleep_dust": "Activate: Inflict {x} Drowsy.",
}


def scrap_title(scrap: Scrap) -> str:
    n = _SCRAP_NAME[scrap.kind]
    if scrap.kind == "gnaw":
        return "%s %dx%d" % (n, scrap.value, scrap.hits)
    if scrap.value:
        return "%s %d" % (n, scrap.value)
    return n


def scrap_text(scrap: Scrap) -> list:
    return wrap_lines(_SCRAP_TEXT[scrap.kind].format(x=scrap.value))


def enemy_card_title(c) -> str:
    return scrap_title(c) if isinstance(c, Scrap) else card_title(c)


def enemy_card_text(c) -> list:
    return scrap_text(c) if isinstance(c, Scrap) else card_text(c)
