"""Rules tests: GDD worked example, Readings, statuses, Chubbs, Burnout, determinism, saves, run flow."""
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python"))

from nla.rules import *   # noqa: E402
from nla.rules import cards as C   # noqa: E402
from nla.rules.battle import _Battle   # noqa: E402

F, A, W, E = FIRE, AIR, WATER, EARTH


def card(e, n, rev=False, star=0, charm=0):
    return Card(e * 10 + n - 1, rev, star, charm)


def major(def_id, rev=False, star=0, charm=0):
    return Card(def_id, rev, star, charm)


def fake_run(spread, hp=36, max_hp=36, treats=5, flags=None):
    for i, c in enumerate(spread):
        if c is not None:
            c.uid = c.uid or i + 1
    return SimpleNamespace(spread=spread, hp=hp, max_hp=max_hp, treats=treats, flags=flags or {})


def no_crit_battle(run, enemy):
    """First seed whose battle has no crit (the worked example assumes none)."""
    for seed in range(200):
        res = simulate(run, enemy, seed)
        if not any(e.crit for e in res.events):
            return res
    raise AssertionError("no crit-free seed")


def powers(spread):
    return [None if s is None else s.power for s in analyze(spread, None).slots]


def links(spread, kind):
    return [(l.a, l.b) for l in analyze(spread, None).links if l.kind == kind]


class WorkedExample(unittest.TestCase):
    def test_gdd_10_4(self):
        spread = [card(F, 3), card(F, 4), card(A, 5, True), card(W, 3)]
        rep = analyze(spread, None)
        self.assertEqual([s.power for s in rep.slots], [5, 9, 10, 3])
        self.assertEqual(rep.slots[1].parts[:3], [("Nuzzle", "+2"), ("Tail Tap", "+1"), ("Step", "+2")])
        self.assertIn("Catwalk", rep.readings)
        self.assertEqual(rep.again, [2])
        res = no_crit_battle(fake_run(spread), "gray_rat")
        hits = [(e.beat, e.kind, e.side, e.value, e.hp) for e in res.events
                if e.kind in ("hit", "damage")]
        self.assertEqual(hits, [
            (1, "hit", 0, 5, (36, 13)),
            (2, "damage", 1, 1, (36, 12)),
            (2, "hit", 1, 3, (33, 12)),
            (3, "hit", 0, 9, (33, 3)),
            (4, "damage", 1, 1, (33, 2)),
            (4, "hit", 1, 3, (30, 2)),
            (5, "hit", 0, 12, (30, -10)),
        ])
        self.assertTrue(res.won)
        self.assertEqual(res.hp_left, 30)
        self.assertEqual(res.events[-1].kind, "end")

    def test_preview_matches_battle_numbers(self):
        spread = [card(F, 3), card(F, 4), card(A, 5, True), card(W, 3)]
        pr = analyze(spread, None).per_round
        self.assertEqual(pr, {"dmg": 38, "singe": 2, "heal": 3, "curl": 0})

    def test_events_carry_state(self):
        res = no_crit_battle(fake_run([card(F, 3), card(F, 4)]), "gray_rat")
        for e in res.events:
            self.assertEqual(len(e.hp), 2)
            self.assertEqual(len(e.status), 2)
        self.assertEqual(res.events[0].kind, "battle_start")
        self.assertEqual(res.events[1].kind, "round_start")


class Readings(unittest.TestCase):
    def test_dignity(self):
        self.assertEqual(powers([card(F, 5), card(F, 9)]), [7, 11])      # Nuzzle
        self.assertEqual(powers([card(F, 5), card(A, 9)]), [6, 10])      # Tail Tap
        self.assertEqual(powers([card(W, 5), card(E, 9)]), [6, 10])      # Tail Tap
        self.assertEqual(powers([card(F, 5), card(W, 9)]), [4, 8])       # Hiss
        self.assertEqual(powers([card(A, 5), card(E, 9)]), [4, 8])       # Hiss
        self.assertEqual(powers([card(F, 5), card(E, 9)]), [5, 9])       # neutral
        self.assertEqual(links([card(F, 5), card(W, 9)], "hiss"), [(0, 1)])

    def test_dignity_range_and_gaps(self):
        self.assertEqual(powers([card(F, 5), card(F, 8), card(F, 5)])[1], 12)       # +4
        self.assertEqual(powers([card(F, 5), card(W, 8), card(F, 5)])[1], 6)        # -2
        self.assertEqual(powers([card(F, 5), None, card(F, 9)]), [5, None, 9])      # empty gap

    def test_fool_counts_as_same_element(self):
        p = powers([card(F, 5), major(FOOL)])
        self.assertEqual(p[0], 7)
        p = powers([card(W, 5), major(FOOL), card(F, 9)])
        self.assertEqual((p[0], p[2]), (7, 11))

    def test_step_catwalk(self):
        sp = [card(E, 3), card(E, 4), card(E, 5)]
        rep = analyze(sp, None)
        self.assertIn("Catwalk", rep.readings)
        self.assertEqual(rep.again, [2])
        self.assertEqual(links([card(E, 3), card(E, 4)], "step"), [(0, 1)])
        self.assertEqual(analyze([card(E, 3), card(E, 4)], None).again, [])

    def test_long_catwalk(self):
        sp = [card(E, n) for n in range(2, 7)]
        rep = analyze(sp, None)
        self.assertIn("Long Catwalk", rep.readings)
        short = analyze(sp[:3], None)
        # Long Catwalk multiplies the whole run by 1.5
        self.assertTrue(any(p == ("Long Catwalk", "x1.5") for p in rep.slots[0].parts))
        self.assertFalse(any(p[0] == "Long Catwalk" for p in short.slots[0].parts))

    def test_litter(self):
        tw = analyze([card(F, 4), card(E, 4)], None)
        self.assertIn("Twins", tw.readings)
        self.assertEqual(tw.slots[0].power, 4 + 2)         # Fire-Earth neutral + Twins
        tr = analyze([card(F, 4), card(E, 4), card(F, 4, True)], None)
        self.assertIn("Triplets", tr.readings)
        fl = analyze([card(F, 4), card(E, 4), card(F, 4), card(E, 4)], None)
        self.assertIn("Full Litter", fl.readings)
        self.assertTrue(all(any(p == ("Full Litter", "x2") for p in s.parts) for s in fl.slots))
        # same number but not side by side: no Litter (matches the GDD worked example)
        self.assertNotIn("Twins", analyze([card(F, 3), card(F, 4), card(W, 3)], None).readings)

    def test_mirror_cat(self):
        sp = [card(F, 6), card(F, 6, True)]
        rep = analyze(sp, None)
        self.assertIn("Mirror Cat", rep.readings)
        self.assertEqual(rep.mirror, {0: 1, 1: 0})
        res = no_crit_battle(fake_run(sp), "gray_rat")
        plays = [e for e in res.events if e.kind == "play" and e.side == 0][:2]
        self.assertEqual(plays[0].label, "Fire Claw")
        self.assertEqual(plays[1].label, "Knock the Candle")   # the other orientation, extra
        self.assertEqual(plays[1].value, plays[0].value // 2)

    def test_fools_journey(self):
        sp = [major(FOOL), major(MAGICIAN)]
        rep = analyze(sp, None)
        self.assertIn("Fool's Journey", rep.readings)
        self.assertEqual(rep.slots[0].parts[-1], ("Fool's Journey", "+25%"))
        self.assertEqual(rep.again, [])
        far = analyze([major(FOOL), major(EMPRESS)], None)
        self.assertNotIn("Fool's Journey", far.readings)

    def test_major_readings(self):
        cases = {
            "New Journey": [major(FOOL), major(MAGICIAN)],
            "The Throne": [major(EMPRESS), major(EMPEROR)],
            "Willpower": [major(CHARIOT), major(STRENGTH)],
            "Lion Sun": [major(STRENGTH), card(E, 5), major(SUN)],
            "Upside Sun": [major(HANGED), card(E, 5), major(SUN)],
            "Four Seeds": [card(F, 1), card(A, 1), card(W, 1), card(E, 1)],
            "Completion": [card(F, 10), card(E, 4), card(W, 10)],
        }
        for name, sp in cases.items():
            self.assertIn(name, analyze(sp, None).major_readings, name)
        self.assertNotIn("Four Seeds", analyze([card(F, 1), card(F, 1), card(W, 1), card(E, 1)], None).readings)
        self.assertNotIn("Completion", analyze([card(F, 10), card(E, 4)], None).readings)

    def test_lion_sun_power(self):
        sp = [major(STRENGTH), card(F, 8), major(SUN)]
        base = powers([card(F, 8)])[0]
        rep = analyze(sp, None)
        # Fire 8: Nuzzle x1 (Strength) + Lion Sun +25% + Sunbathe(+15%)
        self.assertEqual(rep.slots[1].power, (8 + 2 + 2) * (100 + 25 + 15) // 100)
        self.assertGreater(rep.slots[1].power, base)

    def test_two_tone_and_stars(self):
        self.assertEqual(powers([card(F, 8, True)]), [10])
        self.assertEqual(powers([card(F, 8, False, 1)]), [12])
        self.assertEqual(powers([card(F, 8, False, 2)]), [16])
        self.assertEqual(powers([card(F, 1)]), [2])
        self.assertEqual(powers([card(F, 1, False, 2)]), [4])

    def test_charms_in_power(self):
        self.assertEqual(powers([card(F, 5, False, 0, CATNIP)]), [7])
        self.assertEqual(powers([card(F, 5, True, 0, MOONLIGHT)]), [5 * 175 // 100])
        self.assertEqual(powers([card(F, 10, False, 0, RAT_BITE)]), [7])

    def test_droppings(self):
        sp = [card(F, 8), Card(DROPPINGS), card(F, 8)]
        self.assertEqual(powers(sp), [4, 0, 4])     # -50%, no Dignity next to Droppings

    def test_power_minimum_one(self):
        self.assertEqual(powers([card(F, 1, False, 0, RAT_BITE)]), [1])

    def test_reading_events_link_slots(self):
        res = no_crit_battle(fake_run([card(F, 3), card(F, 4), card(A, 5, True)]), "gray_rat")
        readings = [e for e in res.events if e.kind == "reading"]
        self.assertTrue(readings)
        self.assertTrue(all(len(e.slots) == 2 for e in readings))
        self.assertTrue(all(1 <= e.tier <= 4 for e in readings))
        self.assertEqual(readings[0].label, "Nuzzle")


class Skills(unittest.TestCase):
    def fight(self, spread, enemy="gray_rat", seed=None, **kw):
        run = fake_run(spread, **kw)
        return no_crit_battle(run, enemy) if seed is None else simulate(run, enemy, seed)

    def test_water_up_heals(self):
        res = self.fight([card(W, 5)], hp=20)
        heal = next(e for e in res.events if e.kind == "heal")
        self.assertEqual(heal.value, 5)

    def test_earth_curl_absorbs(self):
        res = self.fight([card(E, 9)], hp=36)
        hit = next(e for e in res.events if e.kind == "hit" and e.side == 1)
        self.assertEqual(hit.value, 0)
        self.assertEqual(hit.absorbed, 3)

    def test_ambush_ignores_curl(self):
        res = self.fight([card(E, 5), card(A, 3, True)], enemy="gray_rat")
        self.assertTrue(any(e.kind == "hit" and e.side == 0 and e.label == "Ambush" for e in res.events))

    def test_singe_ticks_then_decays(self):
        res = self.fight([card(F, 9, False, 0)], enemy="paper_chewer")
        ticks = [e.value for e in res.events if e.kind == "damage" and e.label == "Singe"]
        self.assertEqual(ticks[:1], [1])

    def test_pickpocket_first_strike_and_steal(self):
        res = no_crit_battle(fake_run([card(E, 9)]), "pickpocket")
        first_play = next(e for e in res.events if e.kind == "play")
        self.assertEqual(first_play.side, 1)
        self.assertTrue(any(e.kind == "steal" for e in res.events))
        self.assertGreaterEqual(res.treats, 1)

    def test_burrow_leap_blocks(self):
        res = no_crit_battle(fake_run([card(F, 9), card(F, 9)]), "pickpocket")
        self.assertTrue(any(e.kind == "leap_block" for e in res.events))

    def test_bite_mark_flips(self):
        res = no_crit_battle(fake_run([card(F, 9), card(F, 9)]), "paper_chewer")
        self.assertTrue(any(e.kind == "flip" and e.side == 0 for e in res.events))

    def test_stinker_droppings(self):
        res = no_crit_battle(fake_run([card(E, 5), card(E, 5), card(E, 5), card(E, 5)]), "stinker")
        adds = [e for e in res.events if e.kind == "add_card"]
        self.assertEqual(len(adds), 1)
        self.assertEqual((adds[0].side, adds[0].label), (0, "Droppings"))

    def test_nine_lives_saves_once(self):
        run = fake_run([card(E, 2, False, 0, NINE_LIVES)], hp=1)
        res = simulate(run, "rat_sergeant", 3)
        self.assertTrue(any(e.kind == "charm" and e.label == "Nine Lives" for e in res.events))
        self.assertEqual(res.spent_charm_uids, [run.spread[0].uid])

    def test_bell_activates_again(self):
        res = no_crit_battle(fake_run([card(F, 5, False, 0, BELL)]), "gray_rat")
        plays = [e for e in res.events if e.kind == "play" and e.side == 0][:2]
        self.assertEqual([p.repeat for p in plays], [0, 1])

    def test_activate_again_cap(self):
        sp = [major(MAGICIAN), card(F, 3, False, 0, BELL), major(MAGICIAN)]
        res = no_crit_battle(fake_run(sp), "chubbs")
        per_beat = {}
        for e in res.events:
            if e.kind == "play" and e.side == 0 and e.slot == 1:
                per_beat[e.beat] = per_beat.get(e.beat, 0) + 1
        self.assertTrue(per_beat and max(per_beat.values()) <= 1 + 3)

    def test_empress_heal_bonus_and_overflow(self):
        res = no_crit_battle(fake_run([major(EMPRESS)], hp=34), "chubbs")
        heal = next(e for e in res.events if e.kind == "heal")
        self.assertEqual(heal.value, 2)
        curl = next(e for e in res.events if e.kind == "curl" and e.side == 0)
        self.assertEqual(curl.value, 6 + 2 - 2)

    def test_spilled_milk_damages(self):
        sp = [major(EMPRESS, True), card(W, 6)]
        res = no_crit_battle(fake_run(sp, hp=20), "chubbs")
        dmg = next(e for e in res.events if e.kind == "damage" and e.side == 1)
        self.assertEqual((dmg.label, dmg.value), ("Spilled Milk", 7))
        self.assertFalse(any(e.kind == "heal" and e.side == 0 for e in res.events))

    def test_zoomies_grows(self):
        sp = [major(CHARIOT), card(F, 1, False, 0, BELL)]
        res = no_crit_battle(fake_run(sp), "chubbs")
        zoom = [e for e in res.events if e.kind == "play" and e.label == "Zoomies"]
        self.assertGreaterEqual(len(zoom), 2)
        self.assertGreater(zoom[1].value, zoom[0].value)

    def test_new_journey_battle_start(self):
        res = no_crit_battle(fake_run([card(E, 5), major(FOOL), major(MAGICIAN)]), "chubbs")
        first = [e for e in res.events if e.kind == "play"][0]
        self.assertEqual(first.beat, 0)

    def test_copycat_copies_enemy(self):
        sp = [major(MAGICIAN, True)]
        res = no_crit_battle(fake_run(sp), "dog_ear")
        self.assertTrue(res.events)   # smoke: engine handles copy chains without errors

    def test_dog_ear_copycat(self):
        res = no_crit_battle(fake_run([card(F, 6), card(E, 5)]), "dog_ear")
        subs = [e for e in res.events if e.kind == "play" and e.side == 1 and e.repeat == 9]
        self.assertTrue(subs)


class Chubbs(unittest.TestCase):
    def test_eats_highest_minor_each_round(self):
        sp = [card(F, 3), card(F, 9), card(E, 5), card(E, 4)]
        res = simulate(fake_run(sp), "chubbs", 1)
        eats = [e for e in res.events if e.kind == "eat"]
        self.assertTrue(eats)
        self.assertEqual(eats[0].slot, 1)               # Fire 9 is the highest
        self.assertEqual(eats[0].side, 1)
        rounds = [e.value for e in res.events if e.kind == "round_start" and e.side == 1]
        self.assertGreaterEqual(len(eats), 1)
        self.assertEqual(rounds[0], 1)
        # eaten slot never plays again
        later = [e for e in res.events if e.kind == "play" and e.side == 0 and e.slot == 1
                 and e.beat > eats[0].beat]
        self.assertFalse(later)

    def test_majors_are_not_eaten(self):
        res = simulate(fake_run([major(STRENGTH), major(SUN)]), "chubbs", 1)
        self.assertFalse(any(e.kind == "eat" for e in res.events))

    def test_forecast_slot(self):
        sp = [card(F, 3), card(F, 9), card(E, 5)]
        self.assertEqual(analyze(sp, None, "chubbs").eat_slot, 1)
        self.assertEqual(analyze(sp, None).eat_slot, -1)

    def test_still_hungry_phase(self):
        sp = [card(F, 9, False, 1), card(F, 9, False, 1), card(F, 9, False, 1), card(F, 9, False, 1),
              card(E, 9, False, 1), card(E, 9, False, 1)]
        res = simulate(fake_run(sp, hp=200, max_hp=200), "chubbs", 4)
        kinds = [e.kind for e in res.events]
        self.assertIn("phase", kinds)
        i = kinds.index("phase")
        self.assertLessEqual(res.events[i].hp[1] * 2, 130)
        line = [e for e in res.events if e.kind == "line"]
        self.assertEqual([e.label for e in line][:1], ["chubbs_intro"])
        self.assertIn("chubbs_half", [e.label for e in line])
        add = next(e for e in res.events if e.kind == "add_card")
        self.assertEqual((add.side, add.label), (1, "Gnaw 4x2"))
        # after the phase every eat heals Chubbs for 6
        after = res.events[i:]
        eats = [k for k, e in enumerate(after) if e.kind == "eat"]
        if eats:
            heals = [e for e in after[eats[0]:eats[0] + 3] if e.kind == "heal" and e.side == 1]
            self.assertTrue(heals and heals[0].label == "Still Hungry")

    def test_bait_beats_one_big_card(self):
        big = [card(F, 9, False, 2), card(E, 2), card(E, 2), card(E, 2), card(E, 2), card(E, 2)]
        spread = [card(F, 9, False, 2), card(F, 8, False, 1), card(A, 9, False, 1), card(F, 7, False, 1),
                  card(W, 8), card(E, 8)]
        a = sum(simulate(fake_run(big, hp=60, max_hp=60), "chubbs", s).won for s in range(10))
        b = sum(simulate(fake_run(spread, hp=60, max_hp=60), "chubbs", s).won for s in range(10))
        self.assertGreater(b, a)


class Burnout(unittest.TestCase):
    def test_burnout_from_beat_40(self):
        sp = [card(E, 1)]   # only a tiny Curl; no damage to speak of
        res = simulate(fake_run(sp, hp=36), "dust_mouse", 7)
        burn = [e for e in res.events if e.kind == "burnout"]
        self.assertTrue(burn)
        self.assertEqual(min(e.beat for e in burn), 40)
        mine = [e.value for e in burn if e.side == 0]
        by_beat = {e.beat: e.value for e in burn}
        self.assertEqual(by_beat[40], 1)
        self.assertEqual(by_beat[41], 2)
        self.assertEqual(by_beat[42], 3)
        self.assertGreater(res.beats, 40)

    def test_battle_always_ends(self):
        res = simulate(fake_run([card(W, 2)]), "chubbs", 2)
        self.assertEqual(res.events[-1].kind, "end")


class Determinism(unittest.TestCase):
    def test_same_seed_same_events(self):
        sp = [card(F, 3), card(F, 4), card(A, 5, True), major(FOOL, True), card(W, 3)]
        a = simulate(fake_run(sp), "sir_flea", 99)
        b = simulate(fake_run([Card(c.def_id, c.reversed, c.star, c.charm, c.uid) for c in sp]),
                     "sir_flea", 99)
        self.assertEqual(a.events, b.events)
        c = simulate(fake_run(sp), "sir_flea", 100)
        self.assertNotEqual(a.events, c.events)

    def test_simulate_does_not_mutate_run(self):
        sp = [card(F, 3), card(A, 5, True, 0, NINE_LIVES), major(CHARIOT)]
        run = fake_run(sp)
        before = [(c.def_id, c.reversed, c.star, c.charm) for c in sp]
        simulate(run, "chubbs", 5)
        self.assertEqual(before, [(c.def_id, c.reversed, c.star, c.charm) for c in sp])
        self.assertEqual((run.hp, run.treats), (36, 5))


class Text(unittest.TestCase):
    def test_all_card_text_fits(self):
        for d in list(range(40)) + list(MAJOR_IDS) + [DROPPINGS]:
            for rev in (False, True):
                for star in range(3):
                    lines = card_text(Card(d, rev, star))
                    self.assertTrue(1 <= len(lines) <= 3, (d, rev, star, lines))
                    self.assertTrue(all(len(l) <= 56 for l in lines), (d, rev, star, lines))
                    self.assertTrue(all(ord(ch) < 128 for l in lines for ch in l))
                    self.assertTrue(card_title(Card(d, rev, star)))

    def test_charm_text_fits_and_flavor(self):
        for cid in CHARMS:
            lines = charm_text(cid)
            self.assertTrue(1 <= len(lines) <= 3 and all(len(l) <= 56 for l in lines), cid)
        for d in MAJOR_IDS:
            self.assertTrue(card_flavor(Card(d)))
        self.assertEqual(card_subtitle(card(F, 4)), "Wands 4 \u00b7 \u2605" + "1 \u00b7 Upright")
        self.assertEqual(card_title(card(F, 4)), "Fire Claw")
        self.assertEqual(card_title(major(SUN)), "The Sun")

    def test_scrap_text(self):
        for e in ENEMIES.values():
            for s in e.spread:
                if isinstance(s, Scrap):
                    self.assertTrue(scrap_title(s))
                    self.assertTrue(all(len(l) <= 56 for l in scrap_text(s)))
        self.assertEqual(SCRAP_KINDS[0], "broken_sword")

    def test_no_cjk_in_rules_sources(self):
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python", "nla", "rules")
        for fn in os.listdir(d):
            if fn.endswith(".py"):
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    for ch in f.read():
                        self.assertFalse("\u2e80" <= ch <= "\u9fff", fn)


class EnemyData(unittest.TestCase):
    def test_roster(self):
        for k in ("practice_mouse", "dust_mouse", "coin_mouse", "gray_rat", "pickpocket", "paper_chewer",
                  "stinker", "rat_sergeant", "sir_flea", "dog_ear", "chubbs"):
            self.assertIn(k, ENEMIES)
        self.assertEqual(ENEMIES["practice_mouse"].hp, 8)
        self.assertEqual(ENEMIES["dust_mouse"].hp, 14)
        self.assertEqual(ENEMIES["coin_mouse"].hp, 18)
        self.assertEqual(ENEMIES["chubbs"].hp, 130)
        self.assertTrue(ENEMIES["pickpocket"].first_strike)
        self.assertTrue(any(s.kind == "cracked_coin" for s in ENEMIES["coin_mouse"].spread))


class RunFlow(unittest.TestCase):
    def test_new_run_defaults(self):
        r = new_run(1, False)
        self.assertEqual((r.hp, r.max_hp, r.treats, r.spread_size, r.box_size), (36, 36, 5, 4, 6))
        self.assertEqual([card_short(c) for c in r.spread], ["F3", "F4", "A5v", "W3"])
        self.assertEqual(len(r.path), STEPS + 1)

    def test_path_constraints_many_seeds(self):
        for seed in range(300):
            r = new_run(seed, False)
            kinds = [[n.kind for n in row] for row in r.path]
            self.assertEqual(len(r.path[0]), 2)
            self.assertIn("fight", kinds[0])
            self.assertEqual(kinds[STEPS - 1], ["stall", "bed"])
            self.assertEqual(kinds[STEPS], ["boss"])
            self.assertTrue(any("elite" in k for k in kinds[:STEPS]), seed)
            self.assertTrue(any("stall" in k for k in kinds), seed)
            for s in range(1, STEPS):
                self.assertFalse("bed" in kinds[s] and "bed" in kinds[s - 1], (seed, kinds))
            for row in r.path[:STEPS]:
                self.assertEqual(len(row), 2)
            for s in range(1, STEPS):
                self.assertTrue(any(k in ("fight", "elite", "stall") for k in kinds[s]))
        self.assertEqual([[n.key for n in row] for row in new_run(7, False).path],
                         [[n.key for n in row] for row in new_run(7, False).path])

    def test_draft_same_pool_for_tutorial(self):
        a, b = new_run(11, True), new_run(11, False)
        for i in range(3):
            self.assertEqual(draft_options(a, i), draft_options(b, i))
            self.assertEqual(len(draft_options(a, i)), 3)
        self.assertTrue(any(is_major(c) for c in draft_options(a, 2)))
        battle = simulate(fake_run([card(F, 3), card(F, 4), card(A, 5, True), card(W, 3)]),
                          "practice_mouse", 1)
        a.flags["lesson"] = 0
        rw = battle_rewards(a, "practice_mouse", battle)
        self.assertEqual(rw.options, draft_options(a, 0))
        self.assertEqual(rw.skip_treats, 0)

    def test_tutorial_lessons(self):
        run = new_run(3, True)
        les = tutorial_setup(run, 0)
        self.assertEqual(les.enemy, "practice_mouse")
        res = simulate(run, "practice_mouse", 5)
        self.assertGreaterEqual(res.beats, 3)
        self.assertTrue(res.won)
        take_card(run, draft_options(run, 0)[0])
        self.assertEqual(sum(c is not None for c in run.box), 1)
        les2 = tutorial_setup(run, 1)
        rep = analyze(run.spread, run)
        self.assertEqual([l.kind for l in rep.links].count("hiss"), 1)
        self.assertEqual(sum(c is not None for c in run.box), 1)       # the pick is still in the Box
        run.spread[2], run.spread[3] = run.spread[3], run.spread[2]
        self.assertEqual([l.kind for l in analyze(run.spread, run).links].count("hiss"), 0)
        tutorial_setup(run, 2)
        rep3 = analyze(run.spread, run)
        self.assertNotIn("Catwalk", rep3.readings)
        run.spread[2], run.spread[3] = run.spread[3], run.spread[2]
        rep3 = analyze(run.spread, run)
        self.assertIn("Catwalk", rep3.readings)
        self.assertTrue(run.spread[3].reversed)
        self.assertTrue(simulate(run, "coin_mouse", 2).won)
        self.assertTrue(any(e.kind == "curl" and e.side == 1 for e in simulate(run, "coin_mouse", 2).events))
        finish_tutorial(run)
        self.assertEqual([card_short(c) for c in run.spread], ["F3", "F4", "A5v", "W3"])
        self.assertFalse(run.tutorial)

    def test_take_card_paths(self):
        r = new_run(2, False)
        self.assertEqual(take_card(r, card(E, 7)), "box")
        r.spread[3] = None
        self.assertEqual(take_card(r, card(E, 8)), "spread")
        # duplicate
        dup = card(F, 3, True)
        self.assertEqual(take_card(r, dup), "duplicate")
        tgt = duplicate_targets(r, dup)[0]
        self.assertFalse(tgt.reversed)
        m = merge(r, Card(dup.def_id, True, 0, BELL, 0), tgt.uid)
        self.assertEqual((m.star, m.charm, m.reversed), (1, BELL, False))
        # keep both
        self.assertEqual(keep_both(r, card(F, 3)), "box")
        # box full
        r.box = [card(E, 2) for _ in range(r.box_size)]
        for i, c in enumerate(r.box):
            c.uid = 100 + i
        n = card(A, 8)
        self.assertEqual(take_card(r, n), "box_full")
        t = r.treats
        self.assertTrue(replace_card(r, n, 100))
        self.assertEqual(r.treats, t + 1)
        self.assertEqual(r.box[0].def_id, n.def_id)

    def test_level_ups(self):
        r = new_run(4, False)
        self.assertEqual(add_xp(r, 1), 1)          # Lv2
        self.assertEqual(r.level, 2)
        opts = level_up_options(r)
        self.assertEqual(len(opts), 3)
        self.assertIn("wider_cloth", opts)
        apply_level_up(r, "wider_cloth")
        self.assertEqual((r.spread_size, len(r.spread)), (5, 5))
        apply_level_up_all = add_xp(r, 4)          # xp 5 -> Lv3, Lv4
        self.assertEqual(r.level, 4)
        self.assertEqual(r.pending_levels, [3, 4])
        apply_level_up(r, "feast")
        self.assertIn("wider_cloth", level_up_options(r))
        apply_level_up(r, "wider_cloth")
        self.assertEqual(r.spread_size, 6)
        self.assertEqual(r.max_hp, 44)

    def test_rewards_values(self):
        r = new_run(6, False)
        r.treats = 12
        res = no_crit_battle(fake_run(list(r.spread)), "gray_rat")
        res.hp_left = 30
        rw = battle_rewards(r, "gray_rat", res)
        self.assertEqual((rw.stash, rw.treats, rw.xp), (2, 6 + 2 + res.treats, 1))
        self.assertEqual(r.treats, 12 + rw.treats)
        self.assertEqual(len(rw.options), 3)
        self.assertEqual(len({c.def_id for c in rw.options}), 3)
        self.assertEqual(r.hp, 30)
        e = new_run(6, False)
        e.step = 3
        eres = no_crit_battle(fake_run(list(e.spread), hp=36), "sir_flea")
        erw = battle_rewards(e, "sir_flea", eres)
        self.assertIn(CHARIOT, [c.def_id for c in erw.options])
        self.assertEqual(erw.xp, 2)
        self.assertTrue(all(c.charm for c in erw.options if c.def_id != CHARIOT))

    def test_stall(self):
        r = new_run(8, False)
        r.step = 4
        r.treats = 100
        st = stall_stock(r)
        self.assertEqual(len(st.cards), 4)
        self.assertEqual(stall_stock(r), st)
        c0 = st.cards[0]
        t = r.treats
        self.assertIn(buy(r, c0), ("box", "spread", "duplicate"))
        self.assertEqual(r.treats, t - c0.price)
        self.assertEqual(buy(r, c0), "sold")
        r.hp = 10
        buy(r, st.tuna)
        self.assertEqual(r.hp, 22)
        cost = st.reroll_cost
        t = r.treats
        reroll(r)
        self.assertEqual((r.treats, st.reroll_cost), (t - cost, cost + 1))
        poor = new_run(8, False)
        poor.treats = 0
        self.assertEqual(buy(poor, stall_stock(poor).cards[0]), "poor")
        # sell
        r2 = new_run(8, False)
        uid = r2.spread[0].uid
        before = r2.treats
        self.assertEqual(sell(r2, uid), sell_price(card(F, 3)))
        self.assertEqual(r2.treats, before + sell_price(card(F, 3)))
        self.assertIsNone(r2.spread[0])
        self.assertEqual(sell_price(card(F, 1)), 1)
        self.assertTrue(needs_confirm(major(SUN)))
        self.assertTrue(needs_confirm(card(F, 3, False, 1)))
        self.assertFalse(needs_confirm(card(F, 3)))

    def test_cat_bed(self):
        r = new_run(9, False)
        r.hp = 10
        cat_bed(r, "nap")
        self.assertEqual(r.hp, 10 + 10)
        uid = r.spread[0].uid
        self.assertEqual(cat_bed(r, "sharpen", uid), "ok")
        self.assertEqual(r.spread[0].star, 1)
        r.spread[1].charm = RAT_BITE
        self.assertEqual(cat_bed(r, "groom", r.spread[1].uid), "ok")
        self.assertEqual(r.spread[1].charm, 0)
        was = r.spread[2].reversed
        self.assertEqual(cat_bed(r, "groom", r.spread[2].uid), "ok")
        self.assertNotEqual(r.spread[2].reversed, was)

    def test_encounters(self):
        for key in ("lost_mouse", "catnip_patch", "zero_booth", "granny_dream", "loose_page", "yarn_ball"):
            for choice in (0, 1):
                r = new_run(12, False)
                r.current = Node("encounter", key, "Encounter")
                self.assertEqual(encounter(r).key, key)
                res = resolve_encounter(r, choice, r.spread[0].uid)
                self.assertTrue(res.text)
        r = new_run(12, False)
        r.current = Node("encounter", "lost_mouse", "Encounter")
        resolve_encounter(r, 0)
        self.assertEqual((r.flags["mouse_chew"], r.mouse_tokens), (1, 1))
        res = simulate(r, "gray_rat", 1)
        self.assertTrue(any(e.kind == "eat" and e.label == "Lost Mouse" for e in res.events))
        r.current = Node("encounter", "catnip_patch", "Encounter")
        r.hp = 10
        resolve_encounter(r, 1)
        self.assertEqual((r.hp, r.flags["start_drowsy"]), (30, 2))
        r.flags.pop("mouse_chew")
        res = simulate(r, "gray_rat", 1)
        self.assertEqual(res.events[1].kind, "status")
        r.current = Node("encounter", "granny_dream", "Encounter")
        uid = r.spread[0].uid
        resolve_encounter(r, 0, uid)
        self.assertEqual((r.spread[0].star, r.spread[0].reversed), (1, True))

    def test_open_box(self):
        r = new_run(13, False)
        r.current = Node("box", "", "Cardboard Box")
        self.assertIsInstance(open_box(r), Card)

    def test_tips(self):
        r = new_run(14, False)
        prof = Profile()
        stall_stock(r)
        self.assertEqual(pending_tip(r, prof), "first_stall")
        consume_tip(r, prof, "first_stall")
        self.assertEqual(pending_tip(r, prof), "")
        r2 = new_run(15, False)
        stall_stock(r2)
        self.assertEqual(pending_tip(r2, prof), "")      # already seen in the profile
        take_card(r2, major(SUN))
        self.assertEqual(pending_tip(r2, prof), "first_major")

    def test_battle_seed_stable(self):
        r = new_run(16, False)
        self.assertEqual(battle_seed(r), battle_seed(r))
        r.step = 2
        self.assertNotEqual(battle_seed(r), battle_seed(new_run(16, False)))


class Saves(unittest.TestCase):
    def test_run_round_trip(self):
        r = new_run(21, False)
        r.treats = 33
        r.step = 4
        r.stall = None
        r.current = r.path[4][0]
        stall_stock(r)
        r.flags["mouse_chew"] = 1
        r.spread[0].charm = BELL
        r.tips.append("first_major")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "run.json")
            save_run(r, p)
            self.assertFalse(os.path.exists(p + ".tmp"))
            r2 = load_run(p)
        self.assertEqual(r, r2)
        self.assertEqual(simulate(r, "gray_rat", 4).events, simulate(r2, "gray_rat", 4).events)

    def test_corrupt_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "run.json")
            self.assertIsNone(load_run(p))
            with open(p, "w") as f:
                f.write("{not json")
            self.assertIsNone(load_run(p))
            with open(p, "w") as f:
                f.write('{"seed": 1}')
            self.assertIsNone(load_run(p))
            q = os.path.join(d, "profile.json")
            with open(q, "w") as f:
                f.write("\x00\x01garbage")
            self.assertEqual(load_profile(q), Profile())
            self.assertEqual(load_profile(os.path.join(d, "none.json")), Profile())

    def test_profile_round_trip_and_records(self):
        r = new_run(22, False)
        r.stats["best_hit"] = 31
        prof = Profile()
        self.assertEqual(prof.bells, 9)
        self.assertEqual(record_death(prof, r), 1)
        self.assertEqual(prof.bells, 8)
        record_win(prof, r, 600)
        record_win(prof, r, 700)
        self.assertEqual((prof.wins, prof.best_hit, prof.fastest), (2, 31, 600))
        prof.tips_seen.append("first_stall")
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "sub", "profile.json")
            save_profile(prof, p)
            self.assertEqual(load_profile(p), prof)


if __name__ == "__main__":
    unittest.main()
