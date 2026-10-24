"""Whole-battle simulation. The full event list is computed at once; the UI only plays it back.

Event conventions (every Event carries both sides' HP and statuses *after* it):
  battle_start  label = enemy name
  line          label = story key ("chubbs_intro", "chubbs_half", ...), side 1
  round_start   side = fighter, value = round number
  paw           side/slot = card about to act
  play          side/slot, value = Power, label = skill name, tier 0..4 (reading chain length),
                repeat > 0 for Activate-again / copied / mirrored effects
  reading       side 0, slot = acting slot, slots = (a, b) linked slots, label = reading name,
                value = signed bonus (0 for non-numeric), tier = running chain position 1..4
  crit          side/slot = attacker
  hit           side/slot = ATTACKER, value = HP the target lost, absorbed = Curl that soaked,
                crit flag, label = skill name
  damage        side = VICTIM, non-attack damage (Singe, self damage, Spilled Milk ...), label = source
  burnout       side = victim, value = damage
  heal          side = healer, value = HP actually restored
  curl          side = owner, value = +gained / -lost
  status        side = owner, label = "singe|puff|drowsy|leap|fleas", value = change
  flip          side = owner of the card, slot, value = 1 if now Reversed
  eat           side = eater, slot = target slot on the other side, value = Power, label = card
  leap_block    side = fighter whose Leap absorbed a hit
  phase         side 1, label = "Still Hungry"
  add_card      side = owner of the Spread, slot = new/changed slot, label = card
  charm         side 0, slot, label = charm name (Bell, Nine Lives, Fish Bone, Paw Pad, Yarn)
  steal         side 1 (thief), value = Treats stolen
  ko            side = fighter at 0 HP
  end           side 0, value = 1 when Domino won
"""
import random
from dataclasses import dataclass, field

from .cards import (Card, Scrap, FIXED, DROPPINGS, FOOL, MAGICIAN, EMPRESS, EMPEROR, CHARIOT,
                    STRENGTH, NINE_LIVES, BELL, FISH_BONE, PAW_PAD, YARN, FLEAS, RAT_BITE,
                    CARD_DEFS, MAJOR_DATA, _MINOR_SKILLS, skill_for, has_activate, card_title, scrap_title)
from .readings import Item, compute
from .enemies import ENEMIES, EnemyDef, HALF_LINE_KEY

BURNOUT_BEAT = 40
AGAIN_CAP = 3
CRIT_PCT = 5
STATUSES = ("singe", "puff", "drowsy", "curl", "leap")
_NO_COPY = ("fool_up", "magician_up", "magician_rev", "none")
_TIER_XP = {"rat": 1, "elite": 2}
_MINOR_NAME = {k: n for k, n in _MINOR_SKILLS.values()}
_ELEM = ("fire", "air", "water", "earth")


@dataclass
class Event:
    kind: str        # see module docstring
    side: int        # actor (or affected fighter, see docstring)
    slot: int = -1
    value: int = 0
    label: str = ""
    tier: int = 0
    crit: bool = False
    hp: tuple = (0, 0)
    status: tuple = ({}, {})
    absorbed: int = 0
    slots: tuple = ()
    repeat: int = 0
    beat: int = 0


@dataclass
class BattleResult:
    events: list
    won: bool
    hp_left: int
    treats: int
    xp: int
    best_hit: int
    beats: int = 0
    rounds: int = 0
    spent_charm_uids: list = field(default_factory=list)
    steals: int = 0


class _Done(Exception):
    def __init__(self, won):
        self.won = won


class _Slot:
    __slots__ = ("card", "scrap", "def_id", "reversed", "star", "charm", "uid", "flat",
                 "next_flat", "next_pct", "gone", "used", "fleas", "bell_used")

    def __init__(self, card=None, scrap=None):
        self.card = card
        self.scrap = scrap
        if card is not None:
            self.def_id, self.reversed, self.star = card.def_id, card.reversed, card.star
            self.charm, self.uid = card.charm, card.uid
        else:
            self.def_id, self.reversed, self.star, self.charm, self.uid = -1, False, 0, 0, 0
        self.flat = self.next_flat = self.next_pct = 0
        self.gone = self.used = self.fleas = self.bell_used = False

    def item(self):
        return Item(self.def_id, self.reversed, self.star, self.charm, self.flat,
                    self.next_flat, self.next_pct)


class _Fighter:
    def __init__(self, side, name, hp, max_hp, slots):
        self.side, self.name, self.hp, self.max_hp = side, name, hp, max_hp
        self.slots = slots
        self.st = dict.fromkeys(STATUSES, 0)
        self.paw = 0
        self.round = 0
        self.last = None   # (skill_key, power) of the last activation


def _snap(f):
    return {k: v for k, v in f.st.items() if v}


class _Battle:
    def __init__(self, spread, hp, max_hp, enemy, seed, treats=0, start_drowsy=0, mouse_chew=False,
                 preview=False):
        self.preview = preview
        self.rng = random.Random(seed)
        self.enemy = enemy
        dom = [None if c is None else _Slot(card=Card(c.def_id, c.reversed, c.star, c.charm, c.uid))
               for c in spread]
        if enemy is None:
            es = []
            ehp = 10 ** 6
            name = "Dummy"
        else:
            es = []
            for c in enemy.spread:
                if isinstance(c, Scrap):
                    es.append(_Slot(scrap=c))
                else:
                    es.append(_Slot(card=Card(c.def_id, c.reversed, c.star, c.charm, c.uid)))
            ehp, name = enemy.hp, enemy.name
        self.F = [_Fighter(0, "Domino", hp, max_hp, dom), _Fighter(1, name, ehp, ehp, es)]
        self.F[0].st["drowsy"] = start_drowsy
        self.mouse_chew = mouse_chew
        self.events = []
        self.beat = 0
        self.again_cnt = {}
        self.fish = 0
        self.treats_have = treats
        self.steals = 0
        self.best_hit = 0
        self.nine_used = False
        self.spent = []
        self.hungry = False
        self.crash = False
        self.stat = {"dmg": 0, "singe": 0, "heal": 0, "curl": 0}
        self.passives = enemy.passives if enemy else ()

    # --- events -----------------------------------------------------------------------------
    def ev(self, kind, side, slot=-1, value=0, label="", tier=0, crit=False, absorbed=0,
           slots=(), repeat=0):
        F0, F1 = self.F
        self.events.append(Event(kind, side, slot, value, label, tier, crit, (F0.hp, F1.hp),
                                 (_snap(F0), _snap(F1)), absorbed, tuple(slots), repeat, self.beat))

    # --- analysis -----------------------------------------------------------------------------
    def report(self, side):
        items = [None if (s is None or s.gone or s.scrap is not None) else s.item()
                 for s in self.F[side].slots]
        return compute(items, side == 0)

    def cardlike(self, side, i):
        sl = self.F[side].slots
        if i < 0 or i >= len(sl):
            return None
        s = sl[i]
        if s is None or s.gone or s.scrap is not None or s.def_id == DROPPINGS:
            return None
        return s

    def activatable(self, side, i):
        s = self.F[side].slots[i]
        if s is None or s.gone:
            return False
        if s.scrap is not None:
            return not (s.scrap.kind == "droppings" and s.used)
        return has_activate(s.def_id, s.reversed)

    # --- state changes ------------------------------------------------------------------------
    def check(self):
        F0, F1 = self.F
        if F1.hp <= 0:
            raise _Done(True)
        if F0.hp <= 0:
            if not self.nine_used:
                for i, s in enumerate(F0.slots):
                    if s is not None and not s.gone and s.charm == NINE_LIVES and s.scrap is None:
                        self.nine_used = True
                        s.charm = 0
                        self.spent.append(s.uid)
                        F0.hp = 1
                        self.ev("charm", 0, i, 1, "Nine Lives")
                        return
            if F1.hp <= 0:
                raise _Done(True)
            raise _Done(False)
        if "still_hungry" in self.passives and not self.hungry and F1.hp * 2 <= F1.max_hp:
            self.hungry = True
            self.ev("phase", 1, -1, 0, "Still Hungry")
            key = HALF_LINE_KEY.get(self.enemy.key)
            if key:
                self.ev("line", 1, -1, 0, key)
            F1.slots.append(_Slot(scrap=Scrap("gnaw", 4, 2)))
            self.ev("add_card", 1, len(F1.slots) - 1, 0, "Gnaw 4x2")

    def add_status(self, side, name, n, from_side=None):
        f = self.F[side]
        f.st[name] += n
        if from_side == 0 and side == 1 and name == "singe":
            self.stat["singe"] += n
        self.ev("status", side, -1, n, name)

    def gain_curl(self, side, n):
        if n <= 0:
            return
        self.F[side].st["curl"] += n
        if side == 0:
            self.stat["curl"] += n
        self.ev("curl", side, -1, n)

    def gain_puff(self, side, n):
        if "willpower" in self.report(side).ctx:
            n += 1
        self.add_status(side, "puff", n)

    def non_attack(self, side, amt, label, slot=-1):
        if amt <= 0:
            return
        self.F[side].hp -= amt
        if side == 1 and label not in ("Singe", "Burnout"):
            self.stat["dmg"] += amt
        self.ev("damage", side, slot, amt, label)
        self.check()

    def heal(self, side, amt, label, slot=-1):
        if amt <= 0:
            return
        f = self.F[side]
        rep = self.report(side)
        bonus = 0
        spilled = 0
        for s in f.slots:
            if s is None or s.gone or s.scrap is not None:
                continue
            if s.def_id == EMPRESS:
                if s.reversed:
                    spilled += FIXED["spilled_pct"][s.star]
                else:
                    bonus += FIXED["nurture_bonus"][s.star]
        amt += bonus
        if spilled:
            self.non_attack(1 - side, amt * spilled // 100, "Spilled Milk", slot)
            return
        actual = min(amt, f.max_hp - f.hp)
        over = amt - actual
        f.hp += actual
        if side == 0:
            self.stat["heal"] += amt
        self.ev("heal", side, slot, actual, label)
        if over > 0 and bonus:
            self.gain_curl(side, over)
        if "throne" in rep.ctx:
            self.gain_curl(side, amt * 50 // 100)

    def flip(self, side, i):
        s = self.F[side].slots[i]
        s.reversed = not s.reversed
        self.ev("flip", side, i, int(s.reversed), card_title(Card(s.def_id, s.reversed)))

    def hit(self, side, base, slot, label, ignore_curl=False, crit_bonus=0):
        if base <= 0:
            return 0
        me, op = self.F[side], self.F[1 - side]
        crit = False if self.preview else self.rng.randrange(100) < CRIT_PCT + crit_bonus
        b = base * 2 if crit else base
        d = b + me.st["puff"]
        if me.st["drowsy"] > 0:
            d = max(1, d * 75 // 100)
        if op.st["leap"] > 0:
            op.st["leap"] -= 1
            self.ev("leap_block", 1 - side, -1, 0, label)
            return 0
        if crit:
            self.ev("crit", side, slot)
        absorbed = 0
        if not ignore_curl and op.st["curl"] > 0:
            absorbed = min(op.st["curl"], d)
            op.st["curl"] -= absorbed
        dealt = d - absorbed
        op.hp -= dealt
        if side == 0:
            self.best_hit = max(self.best_hit, d)
            self.stat["dmg"] += d
        self.ev("hit", side, slot, dealt, label, crit=crit, absorbed=absorbed)
        self.check()
        return d

    # --- turn structure -----------------------------------------------------------------------
    def new_round(self, f):
        f.round += 1
        f.paw = 0
        self.ev("round_start", f.side, -1, f.round)
        keep = 0
        if f.side == 0:
            rep = self.report(0)
            for s in f.slots:
                if s is not None and not s.gone and s.scrap is None and s.def_id == EMPEROR \
                        and not s.reversed:
                    k = FIXED["mybox_keep"][s.star] + (25 if "throne" in rep.ctx else 0)
                    keep = max(keep, min(100, k))
        cur = f.st["curl"]
        kept = cur * keep // 100
        if cur != kept:
            f.st["curl"] = kept
            self.ev("curl", f.side, -1, kept - cur)
        if f.st["drowsy"] > 0:
            f.st["drowsy"] -= 1
            self.ev("status", f.side, -1, -1, "drowsy")
        if f.side == 1 and "bottomless_belly" in self.passives:
            self.belly()

    def belly(self):
        rep = self.report(0)
        best, idx = -1, -1
        for j, info in enumerate(rep.slots):
            s = self.cardlike(0, j)
            if s is not None and s.def_id < 40 and info.power > best:
                best, idx = info.power, j
        if idx < 0:
            return
        s = self.F[0].slots[idx]
        s.gone = True
        self.ev("eat", 1, idx, best, card_title(Card(s.def_id, s.reversed)))
        if self.hungry:
            self.heal(1, 6, "Still Hungry")

    def next_slot(self, f):
        for _ in range(2):
            if f.round == 0 or f.paw >= len(f.slots):
                self.new_round(f)
            while f.paw < len(f.slots):
                i = f.paw
                f.paw += 1
                if self.activatable(f.side, i):
                    return i
        return None

    def turn(self, side):
        f = self.F[side]
        self.again_cnt = {}
        i = self.next_slot(f)
        self.take_turn(side, i, True)

    def take_turn(self, side, i, pre=True):
        f = self.F[side]
        if i is not None:
            self.ev("paw", side, i)
        if pre:
            if i is not None and f.st["singe"] > 0:
                dmg = f.st["singe"]
                f.st["singe"] -= 1
                f.hp -= dmg
                self.ev("damage", side, i, dmg, "Singe")
                self.check()
            if self.beat >= BURNOUT_BEAT:
                n = self.beat - BURNOUT_BEAT + 1
                f.hp -= n
                self.ev("burnout", side, -1, n, "Burnout")
                self.check()
        if i is None:
            return
        self.exec(side, i, 100, 0, True)
        while self.crash:
            self.crash = False
            j = None
            while f.paw < len(f.slots):
                k = f.paw
                f.paw += 1
                if self.activatable(side, k):
                    j = k
                    break
            if j is None:
                break
            self.ev("paw", side, j)
            self.exec(side, j, 100, 0, True)

    def reexec(self, side, i, factor):
        if not self.activatable(side, i):
            return
        key = (side, i)
        c = self.again_cnt.get(key, 0)
        if c >= AGAIN_CAP:
            return
        self.again_cnt[key] = c + 1
        self.exec(side, i, factor, c + 1, False)

    def exec(self, side, i, factor, repeat, primary):
        f = self.F[side]
        s = f.slots[i]
        if s.scrap is not None:
            sc = s.scrap
            power = sc.value * factor // 100 if sc.value else 0
            if sc.value and power < 1:
                power = 1
            self.ev("play", side, i, power, scrap_title(sc), 0, repeat=repeat)
            self.perform(side, i, sc.kind, power, sc, False)
            f.last = (sc.kind, power, scrap_title(sc))
            return
        rep = self.report(side)
        info = rep.slots[i]
        power = info.power
        if factor != 100 and power:
            power = max(1, power * factor // 100)
        if side == 1 and self.enemy is not None and self.enemy.chewed_pct != 100 and power:
            power = max(1, power * self.enemy.chewed_pct // 100)
        s.next_flat = 0
        s.next_pct = 0
        sk = skill_for(s.def_id, s.reversed)
        mine = [l for l in rep.links if (l.a == i or l.b == i) and
                (l.kind != "catwalk" or l.b == i)] if side == 0 else []
        tier = min(4, len(mine))
        self.ev("play", side, i, power, sk.name, tier, repeat=repeat)
        if repeat == 0:
            for k, l in enumerate(mine):
                self.ev("reading", side, i, l.value, l.name, min(4, k + 1), slots=(l.a, l.b))
        self.perform(side, i, sk.key, power, s, False)
        f.last = (sk.key, power, sk.name)
        if side == 0:
            self.charm_effects(i, s)
        if i in rep.mirror and has_activate(s.def_id, not s.reversed):
            sk2 = skill_for(s.def_id, not s.reversed)
            p2 = max(1, power // 2) if power else 0
            self.ev("play", side, i, p2, sk2.name, tier, repeat=8)
            self.perform(side, i, sk2.key, p2, s, False)
        extra = 0
        if primary and i in rep.again:
            extra += 1
        if side == 0 and s.charm == BELL and not s.bell_used:
            s.bell_used = True
            self.ev("charm", 0, i, 0, "Bell")
            extra += 1
        for _ in range(extra):
            self.reexec(side, i, 100)

    def charm_effects(self, i, s):
        c = s.charm
        if c == FISH_BONE and self.fish < 3:
            self.fish += 1
            self.ev("charm", 0, i, 1, "Fish Bone")
        elif c == PAW_PAD:
            self.ev("charm", 0, i, 2, "Paw Pad")
            self.gain_curl(0, 2)
        elif c == YARN:
            t = self.cardlike(0, i + 1)
            if t is not None:
                t.next_flat += 2
                self.ev("charm", 0, i, 2, "Yarn", slots=(i, i + 1))
        if c == FLEAS or s.fleas:
            self.non_attack(0, 1, "Fleas", i)

    # --- skills ---------------------------------------------------------------------------------
    def perform(self, side, i, key, p, src, copied):
        me, op = self.F[side], self.F[1 - side]
        if key == "none":
            return
        if key.startswith(("fire", "air", "water", "earth")):
            e, ori = key.split("_")
            return self.minor(side, i, e, ori == "rev", p, _MINOR_NAME[key])
        if key in ("ace_up", "ace_rev"):
            rev = key == "ace_rev"
            e = src.def_id // 10
            self.minor(side, i, _ELEM[e], rev, p, skill_for(src.def_id, rev).name)
            if copied:
                return
            rep = self.report(side)
            dbl = 2 if "four_seeds" in rep.ctx else 1
            x = FIXED["ace_rev_bonus" if rev else "ace_up_bonus"][src.star] * dbl
            for j, t in enumerate(me.slots):
                if j == i or self.cardlike(side, j) is None or t.def_id >= 40 or t.def_id // 10 != e:
                    continue
                if not rev:
                    t.flat += x
                elif t.reversed:
                    t.flat += x
                else:
                    t.flat -= 1
            return
        if key in _MAJOR_SKILLS:
            return _MAJOR_SKILLS[key](self, side, i, p, src, copied)
        # scraps
        if key == "broken_sword":
            self.hit(side, p, i, "Broken Sword")
        elif key == "gnaw":
            for _ in range(src.hits):
                self.hit(side, p, i, "Gnaw")
        elif key == "burnt_wand":
            self.hit(side, p, i, "Burnt Wand")
            self.add_status(1 - side, "singe", 1, side)
        elif key == "cracked_coin":
            self.gain_curl(side, p)
        elif key == "leaky_cup":
            self.heal(side, p, "Leaky Cup", i)
        elif key == "bite_mark":
            tgt = None
            for j in list(range(op.paw, len(op.slots))) + list(range(0, op.paw)):
                if self.cardlike(1 - side, j) is not None:
                    tgt = j
                    break
            if tgt is not None:
                self.flip(1 - side, tgt)
        elif key == "snatch":
            self.hit(side, p, i, "Snatch")
            if side == 1 and self.treats_have > 0:
                self.treats_have -= 1
                self.steals += 1
                self.ev("steal", 1, i, 1, "Snatch")
        elif key == "burrow":
            self.add_status(side, "leap", 1)
        elif key == "droppings":
            if isinstance(src, Scrap) and not me.slots[i].used:
                me.slots[i].used = True
                self.add_droppings(1 - side)
        elif key == "fleas":
            cands = [j for j in range(len(op.slots)) if self.cardlike(1 - side, j) is not None]
            if cands:
                j = self.rng.choice(cands)
                op.slots[j].fleas = True
                self.ev("status", 1 - side, j, 1, "fleas")
        elif key == "sleep_dust":
            self.add_status(1 - side, "drowsy", p)

    def add_droppings(self, side):
        f = self.F[side]
        idx = -1
        for j in range(len(f.slots) - 1, -1, -1):
            t = f.slots[j]
            if t is None or t.gone:
                idx = j
                break
        if idx < 0:
            for j in range(len(f.slots) - 1, -1, -1):
                if f.slots[j].def_id != DROPPINGS:
                    idx = j
                    break
        if idx < 0:
            return
        f.slots[idx] = _Slot(card=Card(DROPPINGS))
        self.ev("add_card", side, idx, 0, "Droppings")

    def minor(self, side, i, e, rev, p, label):
        me, op = self.F[side], self.F[1 - side]
        if e == "fire":
            if not rev:
                self.hit(side, p, i, label)
                self.add_status(1 - side, "singe", 1, side)
            else:
                self.add_status(1 - side, "singe", (p + 1) // 2 + 1, side)
        elif e == "air":
            if not rev:
                for _ in range(2):
                    self.hit(side, (p + 1) // 2, i, label, crit_bonus=10)
            else:
                self.hit(side, p + 2, i, label, ignore_curl=True)
        elif e == "water":
            if not rev:
                self.heal(side, p, label, i)
                neg = [k for k in ("singe", "drowsy") if me.st[k] > 0]
                if neg:
                    k = self.rng.choice(neg)
                    me.st[k] -= 1
                    self.ev("status", side, -1, -1, k)
            else:
                h = (p + 1) // 2
                self.hit(side, h, i, label)
                self.heal(side, h, label, i)
        else:
            if not rev:
                self.gain_curl(side, p)
            else:
                lost = me.st["curl"]
                if lost:
                    me.st["curl"] = 0
                    self.ev("curl", side, -1, -lost)
                self.hit(side, lost + p, i, label)

    def sub_play(self, side, slot, power, name):
        self.ev("play", side, slot, power, name, 0, repeat=9)


# --- Major skills -------------------------------------------------------------------------------
def _fool_up(b, side, i, p, src, copied):
    t = b.cardlike(side, i + 1)
    if t is None or not has_activate(t.def_id, t.reversed):
        return
    rep = b.report(side)
    sk = skill_for(t.def_id, t.reversed)
    if sk.key in _NO_COPY:
        return
    pw = max(1, rep.slots[i + 1].power * p // 100)
    b.sub_play(side, i + 1, pw, sk.name)
    b.perform(side, i + 1, sk.key, pw, t, True)


def _fool_rev(b, side, i, p, src, copied):
    e = b.rng.randrange(4)
    lo, hi = FIXED["wander_range"][src.star]
    pw = b.rng.randint(lo, hi)
    nm = skill_for(e * 10 + 5, False).name
    b.sub_play(side, i, pw, nm)
    b.minor(side, i, _ELEM[e], False, pw, nm)


def _magician_up(b, side, i, p, src, copied):
    for j in (i - 1, i + 1):
        if b.cardlike(side, j) is not None:
            b.reexec(side, j, p)


def _magician_rev(b, side, i, p, src, copied):
    last = b.F[1 - side].last
    if last is None or last[0] in _NO_COPY:
        return
    pw = max(1, last[1] * p // 100)
    b.sub_play(side, i, pw, last[2])
    key = last[0]
    if key in ("ace_up", "ace_rev", "droppings"):
        return
    b.perform(side, i, key, pw, _FakeScrap(key, pw), True)


class _FakeScrap:
    """Stand-in source when a copied effect has no card (scrap effects copied by Copycat)."""
    def __init__(self, key, pw):
        self.kind, self.value, self.hits = key, pw, 2 if key == "gnaw" else 1
        self.def_id, self.star, self.reversed = -1, 0, False


def _empress_up(b, side, i, p, src, copied):
    b.heal(side, p, "Nurture", i)


def _emperor_up(b, side, i, p, src, copied):
    b.gain_curl(side, p)


def _emperor_rev(b, side, i, p, src, copied):
    d = b.F[side].st["curl"] * p // 100
    if d > 0:
        b.hit(side, d, i, "Paw Punch")


def _chariot_up(b, side, i, p, src, copied):
    b.hit(side, p, i, "Zoomies")
    if not copied and hasattr(src, "flat"):
        g = FIXED["zoomies_growth"][src.star]
        if "willpower" in b.report(side).ctx:
            g *= 2
        src.flat += g


def _chariot_rev(b, side, i, p, src, copied):
    b.non_attack(side, FIXED["crash_dmg"][src.star], "Crash", i)
    b.crash = True


def _strength_up(b, side, i, p, src, copied):
    b.gain_puff(side, p)


def _strength_rev(b, side, i, p, src, copied):
    b.gain_puff(side, p)
    f = b.F[side]
    if f.hp * 2 >= f.max_hp:
        b.non_attack(side, 4, "Feral", i)


def _hanged_up(b, side, i, p, src, copied):
    for j in (i - 1, i + 1):
        t = b.cardlike(side, j)
        if t is not None:
            b.flip(side, j)
            t.next_pct += p


def _sun_up(b, side, i, p, src, copied):
    b.add_status(1 - side, "singe", p, side)


def _sun_rev(b, side, i, p, src, copied):
    op = b.F[1 - side]
    removed = op.st["singe"]
    if removed:
        op.st["singe"] = 0
        b.ev("status", 1 - side, -1, -removed, "singe")
    b.non_attack(1 - side, removed * p // 100, "Magnifying Glass", i)


_MAJOR_SKILLS = {
    "fool_up": _fool_up, "fool_rev": _fool_rev, "magician_up": _magician_up,
    "magician_rev": _magician_rev, "empress_up": _empress_up, "emperor_up": _emperor_up,
    "emperor_rev": _emperor_rev, "chariot_up": _chariot_up, "chariot_rev": _chariot_rev,
    "strength_up": _strength_up, "strength_rev": _strength_rev, "hanged_up": _hanged_up,
    "sun_up": _sun_up, "sun_rev": _sun_rev,
}


def _start_effects(b):
    rep = b.report(0)
    if "new_journey" in rep.ctx:
        fi = next(j for j, s in enumerate(b.F[0].slots) if b.cardlike(0, j) and s.def_id == FOOL)
        mi = next(j for j, s in enumerate(b.F[0].slots) if b.cardlike(0, j) and s.def_id == MAGICIAN)
        b.ev("reading", 0, fi, 0, "New Journey", 2, slots=(fi, mi))
        for j in (fi, mi):
            if b.activatable(0, j):
                b.again_cnt = {}
                b.exec(0, j, 100, 0, False)


def simulate(run, enemy, seed: int) -> BattleResult:
    if isinstance(enemy, str):
        enemy = ENEMIES[enemy]
    flags = run.flags
    b = _Battle(run.spread, run.hp, run.max_hp, enemy, seed, run.treats,
                flags.get("start_drowsy", 0), bool(flags.get("mouse_chew", 0)))
    won = False
    b.ev("battle_start", 0, -1, 0, enemy.name)
    try:
        if enemy.intro:
            b.ev("line", 1, -1, 0, enemy.intro)
        if b.mouse_chew and b.F[1].slots:
            b.F[1].slots[0].gone = True
            b.ev("eat", 0, 0, 0, "Lost Mouse")
        if b.F[0].st["drowsy"]:
            b.ev("status", 0, -1, b.F[0].st["drowsy"], "drowsy")
        _start_effects(b)
        side = 1 if enemy.first_strike else 0
        while True:
            b.beat += 1
            if b.beat > 600:
                raise _Done(b.F[0].hp >= b.F[1].hp)
            b.turn(side)
            side ^= 1
    except _Done as d:
        won = d.won
    b.ev("ko", 1 if won else 0)
    b.ev("end", 0, -1, 1 if won else 0)
    F0 = b.F[0]
    return BattleResult(b.events, won, max(0, F0.hp), b.fish + b.steals, _TIER_XP.get(enemy.tier, 0),
                        b.best_hit, b.beat, F0.round, b.spent, b.steals)


def preview_round(items) -> dict:
    """Per-Round output of Domino's Spread: {"dmg", "singe", "heal", "curl"} (no Crit, no Crit RNG)."""
    cards = [None if it is None else Card(it.def_id, it.reversed, it.star, it.charm) for it in items]
    b = _Battle(cards, 10 ** 5, 10 ** 6, None, 0, preview=True)
    for s, it in zip(b.F[0].slots, items):
        if s is not None:
            s.flat, s.next_flat, s.next_pct = it.flat, it.next_flat, it.next_pct
    try:
        _start_effects(b)
        f = b.F[0]
        b.new_round(f)
        b.again_cnt = {}
        for i in range(len(f.slots)):
            if b.activatable(0, i):
                f.paw = i + 1
                b.again_cnt = {}
                b.take_turn(0, i, False)
    except _Done:
        pass
    return dict(b.stat)
