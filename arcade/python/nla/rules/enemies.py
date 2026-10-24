"""Enemy roster: Chapter 1 rats, elites, Chubbs and the three tutorial mice."""
from dataclasses import dataclass, field

from .cards import Card, Scrap, CHARIOT, MAGICIAN, STRENGTH


@dataclass
class EnemyDef:
    key: str
    name: str
    hp: int
    spread: list            # list[Scrap | Card]; Cards are Chewed Majors (always Reversed)
    tier: str               # "tutorial" | "rat" | "elite" | "boss"
    intro: str = ""         # story key for the intro line ("" = none); played as a "line" event
    first_strike: bool = False
    chewed: int = 0         # def_id of the stolen Major (0 = none) returned as a reward
    passives: tuple = ()    # ("bottomless_belly", "still_hungry")
    blurb: str = ""         # one-line description for the Spread screen / Info
    chewed_pct: int = 100   # Power of the Chewed Major in percent (gnawed cards hit softer)


def _s(kind, x=0, hits=1):
    return Scrap(kind, x, hits)


def _chewed(def_id, star=0):
    return Card(def_id, reversed=True, star=star)


ENEMIES = {}


def _add(e):
    ENEMIES[e.key] = e


_add(EnemyDef("practice_mouse", "Practice Mouse", 8,
              [_s("broken_sword", 1), _s("broken_sword", 1)], "tutorial",
              blurb="A tiny apprentice rat in cardboard armor."))
_add(EnemyDef("dust_mouse", "Dust Mouse", 14,
              [_s("broken_sword", 2), _s("gnaw", 1, 2)], "tutorial",
              blurb="A dusty little rat. Not very scary."))
_add(EnemyDef("coin_mouse", "Coin Mouse", 18,
              [_s("cracked_coin", 3), _s("broken_sword", 2), _s("broken_sword", 2)], "tutorial",
              blurb="Hides behind a Cracked Coin. Curl blocks damage."))

_add(EnemyDef("gray_rat", "Gray Rat", 18,
              [_s("broken_sword", 3), _s("broken_sword", 3), _s("cracked_coin", 4)], "rat",
              blurb="A plain rat. Good for learning."))
_add(EnemyDef("pickpocket", "Pickpocket", 16,
              [_s("snatch", 3), _s("burrow"), _s("broken_sword", 4)], "rat",
              first_strike=True,
              blurb="First Strike. Steals Treats. Leaps away from your first hit."))
_add(EnemyDef("paper_chewer", "Paper Chewer", 22,
              [_s("bite_mark"), _s("broken_sword", 4), _s("broken_sword", 4)], "rat",
              blurb="Bite Mark flips one of your cards."))
_add(EnemyDef("stinker", "Stinker", 20,
              [_s("droppings"), _s("broken_sword", 3), _s("cracked_coin", 3)], "rat",
              blurb="Leaves Droppings in your Spread."))
_add(EnemyDef("rat_sergeant", "Rat Sergeant", 30,
              [_s("broken_sword", 4), _s("gnaw", 2, 2), _s("cracked_coin", 6),
               _s("burnt_wand", 4)], "rat",
              blurb="Tough and well armed."))

_add(EnemyDef("sir_flea", "Sir Flea", 75,
              [_s("broken_sword", 9), _s("fleas"), _chewed(CHARIOT), _s("cracked_coin", 6),
               _s("gnaw", 4, 2)], "elite", intro="sir_flea_intro", chewed=CHARIOT,
              blurb="Rat knight on a cockroach. Rides a Chewed Chariot."))
_add(EnemyDef("dog_ear", "Dog-Ear", 76,
              [_s("bite_mark"), _s("broken_sword", 12), _chewed(MAGICIAN), _s("leaky_cup", 6),
               _s("bite_mark")], "elite", intro="dog_ear_intro", chewed=MAGICIAN,
              blurb="Bookworm rat. Its Chewed Magician copies your last card."))

_add(EnemyDef("chubbs", "Chubbs, the Pantry King", 130,
              [_s("broken_sword", 3), _s("leaky_cup", 8), _chewed(STRENGTH), _s("gnaw", 2, 2),
               _s("cracked_coin", 8), _s("broken_sword", 3)], "boss", intro="chubbs_intro",
              chewed=STRENGTH, passives=("bottomless_belly", "still_hungry"), chewed_pct=25,
              blurb="Eats your strongest Minor card every Round."))

ELITE_KEYS = ("sir_flea", "dog_ear")
RAT_KEYS_EARLY = ("gray_rat", "pickpocket", "paper_chewer", "stinker")
RAT_KEYS_LATE = ("pickpocket", "paper_chewer", "stinker", "rat_sergeant")
TUTORIAL_KEYS = ("practice_mouse", "dust_mouse", "coin_mouse")

# Story keys used by "line" events (text lives in nla/story.py):
#   chubbs_intro, chubbs_half, sir_flea_intro, dog_ear_intro
HALF_LINE_KEY = {"chubbs": "chubbs_half"}


def enemy_spread_copy(e: EnemyDef) -> list:
    return [Card(c.def_id, c.reversed, c.star, c.charm, c.uid) if isinstance(c, Card) else c
            for c in e.spread]
