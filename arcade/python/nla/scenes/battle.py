"""Battle scene: plays back a precomputed `nla.rules.battle.BattleResult` with animation, VFX and a Result panel.

    BattleScene(services, enemy, result, done)       done({"won": bool, "skipped": bool})

Layout (GDD 6.8, design/styles/moonlit-grimoire/battle.png): backdrop `bg_attic`, top plate (enemy name, HP bar with
lag segment, 50% tick for the boss), enemy scrap row, the stage with Domino (left) and the enemy (right) on the floor
line, chain popup, Domino's row with the Paw marker, READING panel, footer (Domino HP + `A 1x/2x/4x  B Skip  C Info`).

Playback is a generator per event (`_on_<kind>`): it yields waits in base seconds, which are scaled by the pace
factor (fights land at 20-40 s at 1x) and by the speed (1x, 2x, 4x); animation clocks and effect frames are driven
by scene ticks. State changes (HP, statuses, eaten / flipped / added cards, the Still Hungry swap) go through
`_apply(event)`, which is idempotent, so B (skip) just applies every remaining event and shows the end state.

    scene.region(key)       tutorial highlight rects: hp_bar enemy_row spread footer reading_bar slot:N
    scene.restore(scr, r)   cheap repaint of a rect (dialogue closed, tutorial arrow erased)
    scene.paused            True while the script must hold (the tutorial may set it)

Reported to services: battle_speed (A), battle_skip (B), battle_done (Result visible). The Result panel needs A or B.
"""

import random

from nla import sfx, story
from nla.rules import cards
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene
from nla.ui.fx import HitStop

import engine

from . import battle_stage as S
from .battle_bounds import CHARS
from .battle_hud import ChainPanel, Hud
from .battle_result import RECT as RESULT_RECT
from .battle_result import ResultPanel

SPEEDS = (1, 2, 4)
TARGET_SECONDS = 34.0
BASE = {"battle_start": 0.7, "round_start": 0.05, "paw": 0.28, "play": 0.35, "reading": 0.55, "crit": 0.35,
        "hit": 0.8, "damage": 0.55, "heal": 0.65, "curl": 0.5, "status": 0.45, "flip": 0.55, "eat": 1.4,
        "leap_block": 0.7, "phase": 1.0, "add_card": 0.5, "charm": 0.5, "steal": 0.5, "burnout": 0.9, "ko": 1.4,
        "end": 0.5, "line": 0.0}
IMMEDIATE = ("round_start", "paw", "play", "reading", "crit", "battle_start")
CONTACT_LEAD = 0.20
FOE_CAST = (("a0", 0, 0.10), ("a1", 0, 0.12), ("a0", 0, 0.10))
VICTORY = (("v0", 0, 0.17), ("v1", 0, 0.17), ("v2", 0, 0.17), ("v3", 0, 0.17))
LINK_FRAME = {"Nuzzle": 0, "Tail Tap": 1, "Hiss": 2, "Step": 3, "Catwalk": 3, "Long Catwalk": 3, "Twins": 5,
              "Triplets": 5, "Full Litter": 5, "Mirror Cat": 4, "Fool's Journey": 6}
STATUS_HELP = {
    "singe": ("Singe", "Each card played burns: lose that much HP, then it fades by 1."),
    "puff": ("Puff", "Every hit gets +1 damage per Puff."),
    "drowsy": ("Drowsy", "Hits deal 25% less. Wears off each Round."),
    "curl": ("Curl", "A shield. Hits chew through Curl before HP."),
    "leap": ("Leap", "The next hit misses completely."),
}
STATUS_ICON = {"singe": 0, "puff": 1, "drowsy": 2, "curl": 3, "leap": 4}
ELEM_SPARKS = {0: (T.FIRE2, T.AMBER3, T.FIRE1), 1: (T.AIR2, T.MOON, T.AIR1), 2: (T.WATER2, T.MOON, T.WATER1),
               3: (T.EARTH2, T.HEAL, T.EARTH1)}
MAJOR_SPARKS = (T.GOLD4, T.GOLD3, T.MOON)


def _signed(v):
    return ("+%d" % v) if v >= 0 else str(v)


class BattleScene(Scene):
    def __init__(self, services, enemy, result, done):
        super().__init__(done)
        from nla.rules.enemies import ENEMIES
        self.sv = services
        self.enemy = ENEMIES[enemy] if isinstance(enemy, str) else enemy
        self.res = result
        self.events = result.events
        run = services.run
        self.hand_cards = [None if c is None else cards.Card(c.def_id, c.reversed, c.star, c.charm, c.uid)
                           for c in run.spread]
        self.foe_cards = list(self.enemy.spread)
        foe_n = len(self.foe_cards)
        for e in self.events:
            if e.kind == "add_card" and e.side == 1:
                foe_n = max(foe_n, e.slot + 1)
        self.boss = self.enemy.tier == "boss" or self.enemy.key == "chubbs"
        self.hero_max = run.max_hp
        first = self.events[0]
        self.hud = Hud(self.enemy, self.hand_cards, self.foe_cards, foe_n, run.max_hp, self.boss)
        self.hud.set_hp(0, first.hp[0], run.max_hp, snap=True)
        self.hud.set_hp(1, first.hp[1], self.enemy.hp, snap=True)

        self.stage = S.Stage()
        self.hero = S.Actor("domino", T.BATTLE_HERO_X, +1, self.stage)
        char = self.enemy.key if self.enemy.key in CHARS else "gray_rat"
        self.foe = S.Actor(char, T.BATTLE_ENEMY_X, -1, self.stage)
        self.foe.t = 0.125
        self.paw = self.stage.add(S.PawObj(0, 220))
        self.popup = ChainPanel(self._popup_restore, (134, 84, 187, 45))
        self.popup_shown = False
        self.play_label = ""

        prof = getattr(services, "profile", None)
        speed = 1
        if prof is not None:
            speed = getattr(prof, "settings", {}).get("speed", 1)
        self.speed = speed if speed in SPEEDS else 1
        self.hud.set_hints(self._next_speed_label())
        self.pace = self._pace()
        self.hitstop = HitStop(3)
        self.clock = 0.0
        self.idx = -1
        self.gen = self._script()
        self.wait = 0.0
        self.blocked = False
        self.paused = False
        self.ready = False            # first paint finished, playback may start
        self.settle = 0
        self.phase = "play"           # play | result
        self.skipped = False
        self.panel = None
        self.result_ready_at = None
        self.done_sent = False
        self.crit_pending = False
        self.shake_left = 0
        self.chain = []               # reading texts of the current play
        self.chain_pairs = []
        self.fast = self.speed >= 4
        self._st = [{}, {}]
        self._hit_n = 0
        self._active_slot = [None, None]
        self.panel_wait = 0
        self._sfx_n = 0               # sounds started this frame (battle never stacks more than 3)

    # ------------------------------------------------------------------ plumbing
    def enter(self, app):
        super().enter(app)
        sfx.music("music_boss" if self.boss else "music_attic")

    @property
    def busy(self):
        if self.phase == "result" and self.panel is not None and self.panel.ready and self.result_ready_at is not None:
            return bool(self.stage.pending) or not self.stage.built or self.clock - self.result_ready_at < 0.3
        return True

    def _report(self, key):
        rep = getattr(self.sv, "report", None)
        if rep:
            rep(key)

    def _next_speed_label(self):
        return "%dx" % SPEEDS[(SPEEDS.index(self.speed) + 1) % len(SPEEDS)]

    def _pace(self):
        est = sum(BASE.get(e.kind, 0.3) for e in self.events)
        est += 0.25 * sum(1 for e in self.events if e.kind == "reading")
        return max(0.4, min(1.6, TARGET_SECONDS / max(est, 1.0)))

    def region(self, key):
        return self.hud.region(key, engine.measure)

    # ------------------------------------------------------------------ sound
    def _snd(self, name, minor=False):
        """Battle sound: minor ones are dropped at 4x, nothing plays after B (skip), at most 3 start per frame."""
        if self.skipped or (minor and self.fast) or self._sfx_n >= 3:
            return
        self._sfx_n += 1
        sfx.play(name)

    def _play_sound(self, side, slot):
        card = self.hand_cards[slot] if side == 0 and 0 <= slot < len(self.hand_cards) else None
        if card is None or card.def_id == cards.DROPPINGS:
            return "play_scrap"
        if card.def_id >= 40:
            return "play_major"
        return ("play_fire", "play_air", "play_water", "play_earth")[card.def_id // 10]

    # ------------------------------------------------------------------ pointer
    def pointer(self, x, y, kind):
        """Footer gems (A speed, B skip, C info) are handled by the footer. Right click = B while the battle can be
        skipped (or to leave the Result), middle = C, a left click elsewhere does nothing (the Result takes A)."""
        if kind == "right":
            return "b" if self.phase == "result" or not (self.paused or self.blocked) else None
        if kind == "middle":
            return "c"
        if kind == "up" and self.phase == "result":
            return "a"
        return None

    # ------------------------------------------------------------------ input
    def update(self, ctl, dt):
        self.clock += dt
        self._sfx_n = 0
        if self.phase == "result":
            self._update_result(ctl, dt)
            return
        if ctl.a:
            self._cycle_speed()
        elif ctl.b:
            self._skip()
        elif ctl.c:
            self._info()
        if self.phase == "result":
            return
        if self.hitstop.frozen():
            return
        self._frame(dt)
        if not self.ready:
            self._check_ready()
            return
        if self.paused or self.blocked:
            return
        self._drive(dt)

    def _cycle_speed(self):
        self.speed = SPEEDS[(SPEEDS.index(self.speed) + 1) % len(SPEEDS)]
        self.fast = self.speed >= 4
        self.hud.set_hints(self._next_speed_label())
        prof = getattr(self.sv, "profile", None)
        if prof is not None and self.speed in (1, 2) and hasattr(prof, "settings"):
            prof.settings["speed"] = self.speed
        self._report("battle_speed")

    def _info(self):
        notes = []
        shown = set()
        for side in (0, 1):
            for k, n in self._st[side].items():
                if n and k not in shown and k in STATUS_HELP:
                    shown.add(k)
                    notes.append((("ui_status", STATUS_ICON[k]), STATUS_HELP[k][0], STATUS_HELP[k][1]))
        if not notes:
            notes.append((None, "No statuses right now", "Singe, Puff, Drowsy, Curl and Leap show up here."))
        body = ["You play a card, then the rat plays one. Cards go left to right.",
                "Click the speed hint (or F) for 1x, 2x, 4x. Right-click skips." if getattr(self.app, "pc", False)
                else "A changes the speed (1x, 2x, 4x). B skips to the result."]
        self.app.open(W.InfoOverlay("The Battle", "Round %s {.} Domino %d/%d HP" % (
            self.hud.round_label.msg[6:], self.hud.hero_bar.cur, self.hud.hero_bar.mx), body, notes=notes))

    def _update_result(self, ctl, dt):
        self._frame(dt)
        if self.panel is not None and self.panel.ready:
            if self.result_ready_at is None:
                self.result_ready_at = self.clock
                self._report("battle_done")
                self.done_sent = True
            elif self.clock - self.result_ready_at > 0.7 and (ctl.a or ctl.b):
                self.finish({"won": bool(self.res.won), "skipped": self.skipped})

    # ------------------------------------------------------------------ frame tick
    def _frame(self, dt):
        rate = min(self.speed, 2) if self.phase == "play" else 1
        self.hud.update()
        self.stage.update()
        if self.shake_left > 0:
            amp = 3
            pat = ((1, 0), (-1, 1), (1, -1), (-1, 0))[self.shake_left % 4]
            self.hero.shake = self.foe.shake = (pat[0] * amp, pat[1] * amp)
            self.shake_left -= 1
            if self.shake_left == 0:
                self.hero.shake = self.foe.shake = (0, 0)
        for a in (self.hero, self.foe):
            a.update(dt * rate)
            a.tick()
        self._chips_pop()

    def _check_ready(self):
        if self.stage.built and self.hud.settled():
            self.settle += 1
            if self.settle > 3:
                self.ready = True

    def _drive(self, dt):
        if self.gen is None:
            return
        self.wait -= dt * self.speed
        guard = 0
        while self.wait <= 0 and not self.blocked and not self.paused and guard < 12:
            guard += 1
            try:
                w = next(self.gen)
            except StopIteration:
                self.gen = None
                self._enter_result()
                return
            self.wait += w * self.pace

    # ------------------------------------------------------------------ painting
    def draw(self, scr, full):
        if full:
            self.stage.invalidate()
            self.hud.invalidate()
            self.popup.invalidate()
            self.ready = False
            self.settle = 0
            if self.panel is not None:
                self.panel.jobs = None
                self.panel.ready = False
            scr.fill_rect(0, 0, T.SCREEN_W, S.PLATE_H, T.GROUND)
            scr.fill_rect(0, 232, T.SCREEN_W, T.SCREEN_H - 232, T.GROUND)
            return
        if not self.stage.built:
            self.stage.build_step(scr, 6000)
            if scr.stats()["ms"] < 42.0:
                self.hud.draw(scr)
            return
        self.hud.draw(scr)            # HUD first: its dirty widgets always make progress, effects get what is left
        self.popup.draw(scr)
        self.stage.draw(scr, 52.0)
        if self.panel is not None:
            if self.panel_wait > 0:                       # let the stage erase what the fight left behind first
                if not self.stage.pending and not self.stage.later:
                    self.panel_wait -= 1
            else:
                self.panel.draw(scr)

    def _popup_restore(self, rect):
        self.stage.queue_restore(rect)

    def restore(self, scr, rect):
        if rect[2] >= 400:                      # a wide box (dialogue): repaint whole rows, its text may overhang
            rect = (0, rect[1], T.SCREEN_W, rect[3])
        x, y, w, h = rect
        S_ = S.inter(rect, S.STAGE)
        if S_:
            if S_[2] * S_[3] <= 400:
                self.stage.restore_rect(scr, S_)       # tutorial arrow (13x13): exact and immediate
            else:
                self.stage.queue_restore(S_)           # a dialogue box: strip by strip over the next frames
        if y + h > 232:
            top = max(y, 232)
            scr.fill_rect(x, top, w, y + h - top, T.GROUND)
        if y < S.PLATE_H:
            scr.fill_rect(x, y, w, min(S.PLATE_H, y + h) - y, T.GROUND)
        if y <= T.FOOTER_DIV_Y < y + h:
            x0, x1 = max(x, T.INNER_L), min(x + w, T.INNER_R + 1)
            if x1 > x0:
                scr.fill_rect(x0, T.FOOTER_DIV_Y, x1 - x0, 1, T.RULE_DIM)
        self.hud.invalidate_rect(rect)
        if (self.popup.up or self.popup.want is not None) and S.inter(rect, self.popup.rect):
            self.popup.invalidate()
        if self.panel is not None and S.inter(rect, RESULT_RECT):
            self.panel.jobs = None
            self.panel.ready = False

    # ------------------------------------------------------------------ geometry helpers
    def _actor(self, side):
        return self.hero if side == 0 else self.foe

    def _num_xy(self, side):
        x, top = self._actor(side).top_center
        return x, max(top - 34, 96)

    def _spawn(self, obj, delay=0):
        if isinstance(obj, S.TextObj):
            old = [o for o in self.stage.objs if isinstance(o, S.TextObj) and not o.dead]
            while len(old) >= 3:
                old.pop(0).dead = True
        self.stage.add(obj, delay)
        return obj

    def _number(self, side, value, color, shadow=T.NIGHT0, big=False, flash=None, prefix="", dxo=0):
        x, y = self._num_xy(side)
        scale = 2 if (big or value >= 4) else 1
        self._spawn(S.TextObj(x + dxo, y, prefix + str(value), color, T.NUM, scale, 8, 18, shadow, flash), 1)

    def _label(self, side, text, color, dy=0, dxo=0, delay=2):
        if self.fast:
            return
        a = self._actor(side)
        x, top = a.top_center
        self._spawn(S.TextObj(x + dxo, max(top - 32 + dy, 96), text, color, T.BODY, 1, 8, 20, None), delay)

    # ------------------------------------------------------------------ state
    def _apply(self, ev):
        """Idempotent: HP, statuses and card state after `ev`."""
        h = self.hud
        h.set_hp(0, ev.hp[0])
        h.set_hp(1, ev.hp[1])
        for side in (0, 1):
            if ev.status[side] != self._st[side]:
                grew = [k for k, n in ev.status[side].items() if n > self._st[side].get(k, 0)]
                self._st[side] = dict(ev.status[side])
                h.set_status(side, ev.status[side])
                if grew:
                    h.pop_status(side, grew[0])
        k = ev.kind
        if k == "eat":
            if 0 <= ev.slot < len(h.hand):
                h.hand[ev.slot].set_gone()
                if h.active[0] == ev.slot:
                    h.active[0] = None
        elif k == "flip":
            row = self.hand_cards if ev.side == 0 else None
            if row is not None and 0 <= ev.slot < len(row) and row[ev.slot] is not None:
                row[ev.slot].reversed = bool(ev.value)
                h.hand[ev.slot].set_card(row[ev.slot])
        elif k == "add_card":
            self._add_card(ev)
        elif k == "phase":
            if self.foe.sprite.char == "chubbs" and "chubbs_hungry" in CHARS:
                self.foe.swap("chubbs_hungry")

    def _add_card(self, ev):
        if ev.side == 0 and 0 <= ev.slot < len(self.hud.hand):
            card = cards.Card(cards.DROPPINGS)
            self.hand_cards[ev.slot] = card
            self.hud.hand[ev.slot].set_card(card)
        elif ev.side == 1:
            parts = ev.label.split()
            kind = parts[0].lower() if parts else "gnaw"
            val, hits = 4, 2
            if len(parts) > 1 and "x" in parts[1]:
                try:
                    val, hits = (int(n) for n in parts[1].split("x"))
                except ValueError:
                    pass
            self.hud.add_foe_card(ev.slot, cards.Scrap(kind, val, hits))

    # ------------------------------------------------------------------ chain / chips
    def _chips_pop(self):
        self.hud.tick_pops()

    def _clear_chain(self):
        if self.popup_shown:
            self.popup.hide()
            self.popup_shown = False
        if self.chain_pairs:
            self.hud.clear_links()
            self.chain_pairs = []
        self.hud.unlean()
        self.chain = []

    # ------------------------------------------------------------------ script
    def _script(self):
        i = 0
        n = len(self.events)
        while i < n:
            ev = self.events[i]
            self.idx = i
            if ev.kind in IMMEDIATE:
                self._apply(ev)
            handler = getattr(self, "_on_" + ev.kind, None)
            if handler is None:
                self._apply(ev)
                yield 0.0
            else:
                yield from handler(i, ev)
            i += 1

    def _look_ahead(self, i, side):
        """What the play at event i does: 'attack' (a hit by `side` follows) or 'cast'."""
        for j in range(i + 1, len(self.events)):
            e = self.events[j]
            if e.kind in ("paw", "play", "round_start", "ko", "end"):
                break
            if e.kind == "hit" and e.side == side:
                return "attack"
            if e.kind == "leap_block" and e.side != side:
                return "attack"
        return "cast"

    def _on_battle_start(self, i, ev):
        intro = story.ENEMY_TEXT.get(self.enemy.key)
        if intro is not None and getattr(intro, "intro", ""):
            self.hud.set_line(intro.intro, T.MUTED)
        yield BASE["battle_start"]

    def _on_line(self, i, ev):
        lines = story.SCENES.get(ev.label)
        if lines and not self.skipped:
            self.blocked = True
            self.sv.say(lines, self._unblock)
        yield 0.0

    def _unblock(self, *_):
        self.blocked = False
        self.wait = 0.0

    def _on_round_start(self, i, ev):
        if ev.side == 0:
            self.hud.set_round(ev.value)
        yield 0.0

    def _on_paw(self, i, ev):
        self._clear_chain()
        self.hud.activate(ev.side, ev.slot)
        if ev.side == 0 and 0 <= ev.slot < len(self.hud.hand):
            self.paw.tx = self.hud.slot_center_x(0, ev.slot) - 7
            if not self.paw.visible:
                self.paw.x = self.paw.tx
            self.paw.visible = True
        else:
            self.paw.visible = False
        yield BASE["paw"]

    def _on_play(self, i, ev):
        side, slot = ev.side, ev.slot
        row = self.hud.row(side)
        if ev.repeat in (0, 1, 2, 3, 8) and 0 <= slot < len(row):
            row[slot].flash(2)
        kind = self._look_ahead(i, side)
        a = self._actor(side)
        if kind == "cast":
            a.play(S.SEQ_CAST_DOMINO if side == 0 else FOE_CAST)
        text = ev.label
        if ev.repeat == 8:
            text = "Mirror: " + ev.label
        elif 0 < ev.repeat < 8:
            text = "Again: " + ev.label
        self.play_label = ev.label
        self._snd(self._play_sound(side, slot), minor=True)
        self.hud.set_line("%s %s" % (text, ev.value) if ev.value else text, T.TEXT)
        if not self.fast:
            self._label(side, ev.label if ev.repeat in (0, 9) else text, T.MUTED)
            if side == 0 and 0 <= slot < len(row) and ev.repeat in (0, 1, 2, 3, 8):
                self._card_sparks(slot)
        yield BASE["play"] if ev.repeat == 0 else BASE["play"] * 0.7

    def _card_sparks(self, slot):
        card = self.hand_cards[slot] if slot < len(self.hand_cards) else None
        if card is None:
            return
        cx = self.hud.slot_center_x(0, slot)
        if card.def_id < 40:
            e = card.def_id // 10
            colors = ELEM_SPARKS[e]
            for k in range(3):
                self._spawn(S.AnimObj("fx_part", (e * 3, e * 3 + 1, e * 3 + 2), cx - 12 + k * 9, 218 - 2 * (k % 2),
                                      hold=2, dy=-2.0), delay=k)
        else:
            colors = MAJOR_SPARKS
        n = 3 if self.speed < 2 else 2
        for k in range(n):
            self._spawn(S.SparkObj(cx - 8 + k * 8, 222, (k - 1) * 0.7, -2.2, colors[k % len(colors)], 8), delay=k + 1)

    @staticmethod
    def _fit(texts, width, trail):
        """'A +2 > B +2 >' style join of the last entries that fit `width` px (6 px per glyph)."""
        keep = list(texts)
        tail = " {>}" if trail else ""
        while keep and len(" - ".join(keep) + (" -" if trail else "")) * 6 > width:
            keep.pop(0)
        if not keep:
            return ""
        return W.glyphs(" {>} ".join(keep) + tail)

    def _on_reading(self, i, ev):
        frame = LINK_FRAME.get(ev.label, 6)
        a, b = (ev.slots + (ev.slot, ev.slot))[:2] if ev.slots else (ev.slot, ev.slot)
        self.chain_pairs.append((a, b, frame))
        self.hud.set_links([(p, q, f) for p, q, f in self.chain_pairs if p != q and p < len(self.hud.hand)
                            and q < len(self.hud.hand)])
        text = ev.label if not ev.value else "%s %s" % (ev.label, _signed(ev.value))
        self.chain.append(text)
        tier = max(0, min(4, ev.tier))
        self._snd("chain_%d" % (tier + 1), minor=tier < 3)
        if ev.label == "Hiss":
            self._snd("hiss", minor=True)
        if self.speed == 1:                  # the popup takes a few frames to build: only worth it at 1x
            prior = self._fit(self.chain[:-1], self.popup.rect[2] - 24, True)
            self.popup.show(tier, prior if prior else self.play_label, ev.label + "!", ev.tier)
            self.popup_shown = True
        elif self.popup_shown:
            self.popup.hide()
            self.popup_shown = False
        self.hud.set_line(self._fit(self.chain, self.hud.rw - 20, False), T.tier_color(tier))
        mid = self.hud.slot_center_x(0, a) // 1 if a == b else (self.hud.slot_center_x(0, a) + self.hud.slot_center_x(0, b)) // 2
        if not self.fast:
            col = (T.tier_color(tier), T.MOON, T.GOLD4)
            for k in range(2 + tier):
                self._spawn(S.SparkObj(mid - 6 + 3 * k, 222, (k - 1.5) * 0.6, -2.0, col[k % 3], 8), delay=k)
            if ev.label == "Hiss" and a != b:
                self.hud.lean(a, b)
                self._spawn(S.AnimObj("fx_hiss", (0, 1), mid - 12, 196, hold=3, loops=4))
        yield BASE["reading"] + 0.1 * tier

    def _on_crit(self, i, ev):
        a = self._actor(ev.side)
        x, top = a.top_center
        meow = T.asset("fx_meow")
        mx = min(max(2, x - meow.w // 2), T.SCREEN_W - meow.w - 2)
        self._spawn(S.StillObj("fx_meow", mx, max(top - 36, 96), 16, ((0, 0), (2, 1))))
        self._snd("meow" if ev.side == 0 else "squeak")
        self.crit_pending = True
        yield BASE["crit"]

    def _slash(self, side):
        x, y = self._actor(side).center()
        if not self.fast:
            self.stage.add(S.AnimObj("fx_slash", (0, 1, 2, 3), x - 20, y - 20, hold=2))
        else:
            self.stage.add(S.AnimObj("fx_spark", (0, 1, 2, 3), x - 6, y - 6, hold=1))

    def _on_hit(self, i, ev):
        atk, tgt = ev.side, 1 - ev.side
        a, t = self._actor(atk), self._actor(tgt)
        lead = CONTACT_LEAD if self._hit_n == 0 or not a.seq_busy() else 0.1
        self._hit_n += 1
        a.play(S.SEQ_ATTACK_DOMINO if atk == 0 else S.SEQ_ATTACK_FOE)
        yield lead
        big = ev.value >= 30 or ev.crit
        if ev.value > 0:
            self._snd("crit" if ev.crit else "hit_big" if big else "hit")
        elif ev.absorbed > 0:
            self._snd("curl", minor=True)
        if ev.value > 0:
            self._slash(tgt)
            t.start_hurt(self.fast)
            self.hud.hurt_bar(tgt)
            color = T.GOLD4 if tgt == 1 else T.RED
            shadow = T.AMBER1 if tgt == 1 else T.NIGHT0
            flash = (T.GOLD4, T.MOON, T.GOLD4) if big else None
            self._number(tgt, ev.value, color, shadow, big=big, flash=flash)
        if ev.absorbed > 0:
            x, y = t.center()
            self._spawn(S.AnimObj("fx_curl", (0, 1, 2, 1, 2), x - 8 + (8 if tgt == 1 else -8), y - 8, hold=2))
            self._number(tgt, ev.absorbed, T.SILVER1, T.NIGHT0, prefix="-", dxo=22 if ev.value > 0 else 0)
        self._apply(ev)
        if ev.value > 0 and ev.crit:
            self.shake_left = 5
        if big and ev.value > 0:
            self.hitstop.start(3)
        self.crit_pending = False
        yield BASE["hit"] - lead + (0.1 if big else 0.0)

    def _on_damage(self, i, ev):
        side = ev.side
        a = self._actor(side)
        self._apply(ev)
        self.hud.hurt_bar(side)
        a.start_hurt(True)
        x, top = a.top_center
        if ev.label == "Singe":
            self._snd("singe")
            if not self.fast:
                for k in range(3):
                    self._spawn(S.AnimObj("fx_part", (0, 1, 2), x - 14 + k * 10, top + 28 - (k % 2) * 6, hold=2,
                                          dy=-1.5), delay=k)
            self._number(side, ev.value, T.SINGE, T.AMBER0, prefix="-")
        else:
            self._snd("hit", minor=True)
            self._label(side, ev.label, T.MUTED, dy=-6)
            self._number(side, ev.value, T.RED, T.NIGHT0, prefix="-")
        yield BASE["damage"]

    def _on_burnout(self, i, ev):
        self._apply(ev)
        self._snd("burnout")
        side = ev.side
        self.hud.hurt_bar(side)
        self._actor(side).start_hurt(True)
        self._spawn(S.AnimObj("ui_candle", (0, 1), 214, 76, hold=3, loops=9))
        self._spawn(S.TextObj(T.SCREEN_W // 2 + 10, 74, "Burnout!", T.AMBER2, T.TITLE, 1, 4, 24, T.NIGHT0, hold=6))
        self._number(side, ev.value, T.RED, T.NIGHT0, prefix="-")
        yield BASE["burnout"]

    def _on_heal(self, i, ev):
        side = ev.side
        a = self._actor(side)
        self._apply(ev)
        self._snd("heal")
        x, top = a.top_center
        if not self.fast:
            for k in range(3):
                self._spawn(S.AnimObj("fx_heal", (0, 1, 2), x - 16 + k * 12, top + 12 + (k % 2) * 10, hold=2, dy=-1.0), delay=k)
        self._number(side, ev.value, T.HEAL, T.NIGHT0, prefix="+")
        yield BASE["heal"]

    def _on_curl(self, i, ev):
        side = ev.side
        a = self._actor(side)
        self._apply(ev)
        if ev.value > 0:
            self._snd("curl", minor=True)
        x, y = a.center()
        if ev.value > 0:
            self._spawn(S.AnimObj("fx_curl", (0, 1, 2, 1, 2), x - 8, y - 8, hold=2))
            self._number(side, ev.value, T.SILVER2, T.NIGHT0, prefix="+")
        else:
            self._number(side, -ev.value, T.SILVER1, T.NIGHT0, prefix="-")
        yield BASE["curl"]

    def _on_status(self, i, ev):
        side = ev.side
        self._apply(ev)
        if ev.label == "fleas":
            self.hud.row(side)[ev.slot].flash(3) if 0 <= ev.slot < len(self.hud.row(side)) else None
            self._label(side, "Fleas!", T.HEAL)
            self._snd("squeak", minor=True)
            yield BASE["status"]
            return
        names = {"singe": "Singe", "puff": "Puff", "drowsy": "Drowsy", "leap": "Leap"}
        color = {"singe": T.SINGE, "puff": T.ACCENT, "drowsy": T.WATER2, "leap": T.HEAL}.get(ev.label, T.TEXT)
        self._label(side, "%s %s" % (names.get(ev.label, ev.label), _signed(ev.value)), color)
        if ev.label == "singe" and ev.value > 0 and not self.fast:
            x, top = self._actor(side).top_center
            self._spawn(S.AnimObj("fx_part", (0, 1, 2), x - 4, top + 30, hold=2, dy=-1.5))
        yield BASE["status"]

    def _on_flip(self, i, ev):
        row = self.hud.row(ev.side)
        if ev.side == 0:
            self._snd("bite", minor=True)
        self._snd("flip", minor=True)
        if 0 <= ev.slot < len(row):
            if ev.side == 0 and ev.slot < len(self.hand_cards) and self.hand_cards[ev.slot] is not None:
                self.hand_cards[ev.slot].reversed = bool(ev.value)
                row[ev.slot].flip_to(self.hand_cards[ev.slot])
        self._apply(ev)
        yield BASE["flip"]

    def _on_eat(self, i, ev):
        slot = ev.slot
        sv = self.hud.hand[slot] if 0 <= slot < len(self.hud.hand) else None
        card = self.hand_cards[slot] if sv is not None and slot < len(self.hand_cards) else None
        if sv is not None:
            sv.flash(2)
            self.hud.activate(0, slot)
        yield 0.25
        if sv is None or card is None:
            self._apply(ev)
            yield 0.2
            return
        field = T.elem_body(card.def_id // 10 if card.def_id < 40 else 0, bool(card.reversed))
        mx, my = self.foe.mouth()
        x0 = sv.x0 + 12
        self._apply(ev)
        self.hud.deactivate(0)
        self._label(0, ev.label, T.MUTED, dy=40, dxo=x0 + 8 - T.BATTLE_HERO_X)
        self._spawn(S.FlyCard(field, x0, 200, mx - 6, my - 8, 10))
        yield 0.28
        self._snd("bite")
        self.foe.play(S.SEQ_ATTACK_FOE)
        yield 0.2
        if not self.fast:
            for k in range(3):
                self._spawn(S.SparkObj(mx - 6 + 4 * k, my, (k - 1) * 0.8, -1.5, MAJOR_SPARKS[k], 6), delay=k)
        self._snd("eat")
        self.foe.play(S.SEQ_ATTACK_FOE)
        yield 0.45

    def _on_leap_block(self, i, ev):
        defender = ev.side
        attacker = 1 - defender
        a = self._actor(attacker)
        a.play(S.SEQ_ATTACK_DOMINO if attacker == 0 else S.SEQ_ATTACK_FOE)
        yield CONTACT_LEAD
        self._actor(defender).hop()
        self._snd("miss")
        self._label(defender, "Miss", T.SILVER2)
        self._apply(ev)
        yield BASE["leap_block"] - CONTACT_LEAD

    def _on_phase(self, i, ev):
        self._clear_chain()
        self._apply(ev)
        self._snd("roar")
        self.shake_left = 8
        self.foe.start_hurt(False)
        x, top = self.foe.top_center
        self._spawn(S.TextObj(x - 10, max(top - 30, 96), ev.label + "!", T.GOLD4, T.TITLE, 1, 6, 26, T.NIGHT0, hold=10))
        yield BASE["phase"]

    def _on_add_card(self, i, ev):
        self._apply(ev)
        if ev.side == 0:
            self._snd("deal", minor=True)
            self.hud.hand[ev.slot].flash(3)
            self._label(0, ev.label, T.CURSE, dy=-4)
        yield BASE["add_card"]

    def _on_charm(self, i, ev):
        self._apply(ev)
        self._snd("heal" if ev.label == "Nine Lives" else "bell", minor=True)
        sv_row = self.hud.hand
        if 0 <= ev.slot < len(sv_row):
            sv_row[ev.slot].flash(2)
        self._label(0, ev.label + "!", T.GOLD4)
        if ev.label == "Nine Lives" and not self.fast:
            x, top = self.hero.top_center
            for k in range(3):
                self._spawn(S.AnimObj("fx_heal", (0, 1, 2), x - 16 + k * 12, top + 20, hold=2, dy=-1.0), delay=k)
        yield BASE["charm"]

    def _on_steal(self, i, ev):
        self._apply(ev)
        self._snd("sell", minor=True)
        x, top = self.hero.top_center
        self._spawn(S.AnimObj("ui_treat", (0,), x + 10, max(top - 26, 96), hold=16, dy=-0.5))
        self._label(0, "-%d" % ev.value, T.ACCENT, dy=-6, dxo=-6)
        yield BASE["steal"]

    def _on_ko(self, i, ev):
        self._clear_chain()
        self.paw.visible = False
        self.hud.deactivate(0)
        self.hud.deactivate(1)
        loser = self._actor(ev.side)
        winner = self._actor(1 - ev.side)
        loser.start_ko()
        self._snd("ko")
        yield 0.3
        if ev.side == 1:
            self.hero.play(VICTORY, then_hold="v3")
        yield BASE["ko"] - 0.3

    def _on_end(self, i, ev):
        yield BASE["end"]

    # ------------------------------------------------------------------ skip and result
    def _skip(self):
        if self.skipped:
            return
        self.skipped = True
        self._report("battle_skip")
        start = max(self.idx, 0)
        for ev in self.events[start:]:
            self._apply(ev)
        last = self.events[-1]
        self.gen = None
        self.blocked = False
        for o in self.stage.objs:
            if not isinstance(o, (S.SpriteObj, S.PawObj)):
                o.dead = True
        self.paw.visible = False
        self._clear_chain()
        self.hud.deactivate(0)
        self.hud.deactivate(1)
        self.hud.unlean()
        self.hud.settle_slots()
        won = bool(self.res.won)
        loser = self.foe if won else self.hero
        loser.hurt = []
        loser.seq = None
        loser.ko_step = 99
        loser.hops = []
        self.hero.shake = self.foe.shake = (0, 0)
        self.shake_left = 0
        if won:
            self.hero.seq = None
            self.hero.hold("v3")
        else:
            self.foe.seq = None
            self.foe.hurt = []
        self.hud.set_hp(0, last.hp[0])
        self.hud.set_hp(1, last.hp[1])
        self.hud.foe_bar.snap(last.hp[1])
        self.hud.hero_bar.snap(last.hp[0])
        self._enter_result()

    def _enter_result(self):
        if self.phase == "result":
            return
        self.phase = "result"
        self._clear_chain()
        self.paw.visible = False
        for o in self.stage.objs:
            if not isinstance(o, (S.SpriteObj, S.PawObj)):
                o.dead = True
        self.stage.later = []
        self.panel_wait = 3
        res = self.res
        won = bool(res.won)
        sfx.music(None)
        sfx.play("victory" if won else "defeat")
        rng = random.Random(len(self.events) * 31 + res.hp_left)
        if won:
            if self.boss:
                pool = story.RESULT_LINES["boss_victory"]
            elif res.hp_left * 4 < self.hero_max:
                pool = story.RESULT_LINES["victory_close"]
            else:
                pool = story.RESULT_LINES["victory"]
        else:
            pool = story.RESULT_LINES["defeat"]
        self.panel = ResultPanel(won, self.boss, res.treats, res.xp, res.best_hit, res.rounds,
                                 rng.choice(pool))
        self.hud.set_result_hints()
        self.hud.set_line("", T.TEXT)
        self.hud.activate(0, None)
        if self.hero.sprite.has("v3") and won:
            self.hero.hold("v3")
