#!/usr/bin/env python3
"""Monte Carlo balance check: plays whole Chapter 1 runs with a greedy bot and prints a summary.

    python arcade/tools/balance.py --runs 2000
    python arcade/tools/balance.py --runs 500 --skill basic      # weaker bot (analysis only)

Targets (GDD section 14): Rat Fight 1-2 rounds, Elite 2, Chubbs 3-4 rounds, battles <= ~40 beats,
Chubbs win rate for a good bot 60-75%.
"""
import argparse
import os
import sys
from collections import defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python"))

from nla.rules import (analyze, simulate, new_run, enter_node, finish_node, path_options, battle_seed,  # noqa: E402
                       battle_rewards, skip_reward, take_card, merge, keep_both, replace_card,
                       duplicate_targets, level_up_options, apply_level_up, stall_stock, buy,
                       reroll, cat_bed, encounter, resolve_encounter, open_box, card_price,
                       all_cards, ENEMIES, STEPS, find_card, is_major, has_curse)

# --- bot ---------------------------------------------------------------------------------------


def spread_score(spread):
    rep = analyze(spread, None)
    pr = rep.per_round
    return pr["dmg"] + 2.0 * pr["singe"] + 0.7 * pr["heal"] + 0.4 * pr["curl"]


def sim_score(run, spread, enemy, seeds):
    """Mean over seeds: win = 100 + HP left; loss = 50 minus the enemy's remaining HP."""
    saved = run.spread
    run.spread = spread
    try:
        total = 0.0
        for s in seeds:
            res = simulate(run, enemy, s)
            total += (100 + res.hp_left) if res.won else (50 - res.events[-1].hp[1])
        return total / len(seeds)
    finally:
        run.spread = saved


def neighbors(spread, pool):
    """Swaps inside the Spread, and swaps with Box cards."""
    n = len(spread)
    for i in range(n):
        for j in range(i + 1, n):
            if spread[i] is not None or spread[j] is not None:
                s = list(spread)
                s[i], s[j] = s[j], s[i]
                yield s
        for c in pool:
            s = list(spread)
            s[i] = c
            yield s


def arrange(run, enemy_key, skill):
    """Hill-climb the Spread (cards from Spread + Box)."""
    tier = ENEMIES[enemy_key].tier
    use_sim = skill == "good" and tier in ("elite", "boss")
    seeds = (11, 12, 13) if tier == "boss" else (11, 12)
    cards = all_cards(run)
    spread = list(run.spread)
    # fill empty slots greedily first
    for i, c in enumerate(spread):
        if c is None:
            rest = [x for x in cards if x not in spread]
            if rest:
                spread[i] = max(rest, key=lambda x: card_price(x))

    def score(sp):
        return sim_score(run, sp, enemy_key, seeds) if use_sim else spread_score(sp)

    best = score(spread)
    for _ in range(12 if use_sim else 25):
        pool = [c for c in cards if c not in spread]
        improved = False
        for cand in neighbors(spread, pool):
            sc = score(cand)
            if sc > best + 1e-9:
                best, spread, improved = sc, cand, True
        if not improved:
            break
    # apply
    run.spread = spread
    used = {c.uid for c in spread if c is not None}
    box = [c for c in cards if c.uid not in used]
    run.box = box + [None] * (run.box_size - len(box))


def place_new(run, card, skill):
    st = take_card(run, card)
    if st == "duplicate":
        tgt = duplicate_targets(run, card)[0]
        merge(run, card, tgt.uid)
    elif st == "box_full":
        weakest = min(all_cards(run), key=lambda c: (card_price(c) if not is_major(c) else 99))
        if card_price(card) > card_price(weakest) or is_major(card):
            replace_card(run, card, weakest.uid)


def gain_value(run, card):
    """How much the best Spread improves if `card` joins the pool (cheap proxy)."""
    pool = all_cards(run) + [card]
    spread = [c for c in run.spread]
    best = spread_score(spread)
    if None in spread:
        i = spread.index(None)
        s = list(spread)
        s[i] = card
        best = max(best, spread_score(s))
    for i, c in enumerate(spread):
        s = list(spread)
        s[i] = card
        best = max(best, spread_score(s))
    return best


def choose_reward(run, options):
    return max(options, key=lambda c: gain_value(run, c) + (3 if is_major(c) else 0) + (2 if c.charm else 0))


def sharpen_target(run):
    cards = [c for c in all_cards(run) if c.star < 2]
    spread = [c for c in run.spread if c is not None and c.star < 2]
    pool = spread or cards
    if not pool:
        return None
    rep = analyze(run.spread, None)
    best, tgt = -1, pool[0]
    for i, c in enumerate(run.spread):
        if c is not None and c.star < 2 and rep.slots[i].power > best:
            best, tgt = rep.slots[i].power, c
    return tgt


def do_level_ups(run):
    while run.pending_levels:
        opts = level_up_options(run)
        for k in ("wider_cloth", "sharpen", "feast", "lucky_cat", "bigger_box"):
            if k in opts:
                key = k
                break
        uid = None
        if key == "sharpen":
            t = sharpen_target(run)
            if t is None:
                key = "feast"
            else:
                uid = t.uid
        apply_level_up(run, key, uid)


def choose_path(run):
    opts = path_options(run)
    kinds = [n.kind for n in opts]
    hp = run.hp / run.max_hp

    def prio(n):
        k = n.kind
        if k == "boss":
            return 100
        if k == "bed":
            return 90 if hp < 0.6 else 10
        if k == "elite":
            return 80 if hp > 0.75 and run.level >= 2 else 20
        if k == "fight":
            return 60
        if k == "stall":
            return 70 if run.treats >= 12 else 25
        if k == "encounter":
            return 40 if hp > 0.3 else 15
        return 50
    return max(range(len(opts)), key=lambda i: prio(opts[i]))


def visit_stall(run, skill):
    st = stall_stock(run)
    for _ in range(3):
        bought = False
        if st.service.service == "wider_cloth" and not st.service.sold and run.treats >= st.service.price:
            buy(run, st.service)
            bought = True
        if run.hp < run.max_hp * 0.6 and run.treats >= st.tuna.price + 0:
            buy(run, st.tuna)
            bought = True
        best, bi = -1e9, None
        for it in st.cards:
            if it.sold or run.treats < it.price:
                continue
            g = gain_value(run, it.card) - spread_score(run.spread)
            if g > best - 1:
                best, bi = g, it
        if bi is not None:
            res = buy(run, bi)
            if res == "duplicate":
                tgt = duplicate_targets(run, bi.card)[0]
                merge(run, bi.card, tgt.uid)
            elif res == "box_full":
                place_new(run, bi.card, skill)
            bought = True
        if not bought:
            break


def do_encounter(run):
    enc = encounter(run)
    choice, uid = 0, None
    if enc.key == "granny_dream":
        t = sharpen_target(run)
        if t is None:
            choice = 1
        else:
            uid = t.uid
    if enc.key == "yarn_ball" and run.hp < 15:
        choice = 1
    if enc.key == "lost_mouse" and run.hp < run.max_hp * 0.4:
        choice = 1
    res = resolve_encounter(run, choice, uid)
    if res.card is not None:
        if res.status == "duplicate":
            tgt = duplicate_targets(run, res.card)[0]
            merge(run, res.card, tgt.uid)
        elif res.status == "box_full":
            place_new(run, res.card, "basic")


def play_run(args):
    seed, skill = args
    run = new_run(seed, False)
    log = []
    while True:
        idx = choose_path(run)
        node = enter_node(run, idx)
        if node.kind in ("fight", "elite", "boss"):
            arrange(run, node.key, skill)
            hp0 = run.hp
            res = simulate(run, node.key, battle_seed(run))
            log.append((node.kind, node.key, res.won, res.rounds, res.beats, hp0 - res.hp_left,
                        res.best_hit, run.level, run.spread_size, sum(1 for c in run.spread if c)))
            if not res.won:
                return {"won": False, "log": log, "step": run.step}
            rw = battle_rewards(run, node.key, res)
            if node.kind == "boss":
                return {"won": True, "log": log, "step": run.step}
            do_level_ups(run)
            pick = choose_reward(run, rw.options)
            place_new(run, pick, skill)
        elif node.kind == "stall":
            visit_stall(run, skill)
        elif node.kind == "bed":
            if run.hp < run.max_hp * 0.65:
                cat_bed(run, "nap")
            else:
                t = sharpen_target(run)
                if t is not None:
                    cat_bed(run, "sharpen", t.uid)
                else:
                    cat_bed(run, "nap")
        elif node.kind == "encounter":
            do_encounter(run)
        elif node.kind == "box":
            place_new(run, open_box(run), skill)
        do_level_ups(run)
        finish_node(run)


def summarize(results):
    n = len(results)
    wins = sum(r["won"] for r in results)
    by = defaultdict(list)
    for r in results:
        for e in r["log"]:
            by[e[0]].append(e)
    print("runs: %d   win rate: %.1f%%" % (n, 100.0 * wins / n))
    print()
    print("%-8s %6s %7s %8s %8s %8s %9s %8s %8s" % ("battle", "count", "win%", "rounds", "beats", "max beats",
                                                    "hp lost", "slots", "level"))
    for kind in ("fight", "elite", "boss"):
        es = by.get(kind, [])
        if not es:
            continue
        w = [e for e in es if e[2]]
        k = len(es)
        print("%-8s %6d %6.1f%% %8.2f %8.1f %8d %9.1f %8.2f %8.2f" % (
            kind, k, 100.0 * len(w) / k, sum(e[3] for e in es) / k, sum(e[4] for e in es) / k,
            max(e[4] for e in es), sum(e[5] for e in w) / max(1, len(w)),
            sum(e[9] for e in es) / k, sum(e[7] for e in es) / k))
    boss = by.get("boss", [])
    if boss:
        print()
        print("reached Chubbs: %.1f%% of runs; won %.1f%% of those" % (
            100.0 * len(boss) / n, 100.0 * sum(e[2] for e in boss) / len(boss)))
        wb = [e for e in boss if e[2]]
        if wb:
            print("Chubbs (wins): rounds avg %.2f, min %d max %d; hp lost avg %.1f" % (
                sum(e[3] for e in wb) / len(wb), min(e[3] for e in wb), max(e[3] for e in wb),
                sum(e[5] for e in wb) / len(wb)))
    deaths = defaultdict(int)
    for r in results:
        if not r["won"] and r["log"]:
            deaths[r["log"][-1][1]] += 1
    if deaths:
        print()
        print("deaths by enemy:", ", ".join("%s %d" % kv for kv in sorted(deaths.items(), key=lambda kv: -kv[1])))
    big = sum(1 for r in results if any(e[6] >= 25 for e in r["log"]))
    print("runs with a >= 25 hit: %.1f%%" % (100.0 * big / n))
    longest = max((e[4] for r in results for e in r["log"]), default=0)
    print("longest battle: %d beats" % longest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1000)
    ap.add_argument("--skill", choices=("good", "basic"), default="good")
    ap.add_argument("--jobs", type=int, default=0)
    a = ap.parse_args()
    jobs = a.jobs or max(1, (os.cpu_count() or 2) - 1)
    work = [(a.seed + i, a.skill) for i in range(a.runs)]
    if jobs == 1:
        results = [play_run(w) for w in work]
    else:
        with Pool(jobs) as p:
            results = p.map(play_run, work, chunksize=max(1, a.runs // (jobs * 8)))
    summarize(results)


if __name__ == "__main__":
    main()
