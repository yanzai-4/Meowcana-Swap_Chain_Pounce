"""The Spread screen (GDD 6.5): Enemy row, Reading bar, Spread row + FIGHT, Box row, detail panel, footer.

    SpreadScene(services, enemy, done, lesson=None)      done("fight")

Cursor rows (up/down, wrapping): Enemy row (portrait + scrap cards), Spread row (slots + FIGHT), Box row. The cursor
opens on FIGHT. A picks a card up / puts it down (swap, or move into an empty slot, also across into the Box); B
puts a held card back, otherwise opens the Menu; C explains whatever is under the cursor. While a card is in the hand
the rows show where it would land (live preview): Power numbers count up/down, link glyphs appear between cards,
the Reading bar and the per-Round chips follow. Dropping a card on a copy of itself asks to Merge.

Tutorial: reports `pick_up:slotN drop:slotN hiss_fixed box_to_spread catwalk_made press_fight open_info close_info`
through services.report and answers region() for `spread slot:N fight box enemy_row reading_bar footer hp_bar
reversed_card`. Dev harnesses: `dev_spread()` and `dev_spread_boss()` (python tools/sim.py --game
nla.scenes.spread:dev_spread).
"""

from nla import story
from nla.rules import cards, enemies as E, readings, run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene

from .spread_board import Board, DetailPanel, PANEL_RECT, box_x, hit, slot_x, text_rows, SLOT_Y

ROW_ENEMY, ROW_SPREAD, ROW_BOX = 0, 1, 2
ENEMY_Y = T.ENEMY_SCRAP_Y
SHAKE_S = 0.25
HOT_S = 1.6
NOTE_S = 2.2
READING_X = 16 + 7 * 6 + 12
READING_CHARS = (T.INNER_R + 1 - READING_X) // 6

# Chubbs' rules for the C page on his portrait (no story.py entry exists for them).
BOSS_RULES = (
    (None, "Bottomless Belly", "Every Round Chubbs eats your strongest Minor card. It is gone for the rest of the "
                               "fight. The bite mark on your Spread shows who is next."),
    (None, "Still Hungry", "Below half HP he heals 6 each time he eats, and a Gnaw 4x2 joins his cards."),
)


def _unwrap(enemy):
    return E.ENEMIES[enemy] if isinstance(enemy, str) else enemy


class SpreadScene(Scene):
    def __init__(self, services, enemy, done, lesson=None):
        super().__init__(done)
        self.sv = services
        self.enemy = _unwrap(enemy)
        self.lesson = lesson
        run = services.run
        self.ns, self.nb = len(run.spread), len(run.box)
        self.board = Board(self.ns, self.nb)
        # enemy row
        self.scraps = list(self.enemy.spread)
        n = len(self.scraps)
        pitch = 48 if n <= 4 else (46 if n == 5 else 44)
        x0 = T.INNER_R + 1 - (n * pitch - (pitch - T.CARD_SW))
        self.scrap_views = []
        for i, c in enumerate(self.scraps):
            v = W.CardView(x0 + i * pitch, ENEMY_Y, small=True)
            v.set_enemy_card(c)
            self.scrap_views.append(v)
        self.scrap_x0 = x0
        hp_text = "HP %d" % self.enemy.hp
        self.hp_text = hp_text
        self.hp_w = max(48, min(101, x0 - 88 - 6 * len(hp_text) - 14))
        self.enemy_hp = W.HpBar(88, 48, self.hp_w, 9, tick=0.5 if "still_hungry" in self.enemy.passives else None)
        self.enemy_hp.set(self.enemy.hp, self.enemy.hp)
        # widgets
        self.fight = W.FightPlaque()
        self.chips = W.ChipRow(160, 89, T.INNER_R - 160 + 1, align="r", gap=14)
        self.reading = W.TextRun(READING_X, 70)
        self.detail = DetailPanel()
        self.footer = W.Footer()
        self._candle = None
        # state
        self.row, self.col = ROW_SPREAD, self.ns
        self.held = None
        self.origin = None
        self.report = None
        self._arr_key = None
        self._prev_readings = None
        self._hot = set()
        self._hot_t = 0.0
        self._reading_key = None
        self._detail_key = None
        self._note = None
        self._note_t = 0.0
        self._shake_t = 0.0
        self._info_open = False
        self._booted = False
        self._later = None
        self._step_id = None
        self._merge_view = None
        self._merge_t = 0.0
        self._footer_key = None
        self._animating = False
        self._static = self._build_static()
        self._widgets = self._build_widgets()
        self._recompute()

    # ------------------------------------------------------------------ helpers
    @property
    def run(self):
        return self.sv.run

    def _row_len(self, row):
        return (1 + len(self.scraps), self.ns + 1, self.nb)[row]

    def _center_x(self, row, col):
        if row == ROW_ENEMY:
            return 45 if col == 0 else self.scrap_views[col - 1].x + 20
        if row == ROW_SPREAD:
            return slot_x(col) + 24 if col < self.ns else T.SPREAD_FIGHT[0] + 46
        return box_x(col) + 20

    def _zone_index(self):
        """(zone, index) of the cursor when it is on a card slot, else None."""
        if self.row == ROW_SPREAD and self.col < self.ns:
            return ("s", self.col)
        if self.row == ROW_BOX:
            return ("b", self.col)
        return None

    def _cards(self, zone):
        return self.run.spread if zone == "s" else self.run.box

    def _arrange(self):
        """(spread, box, hover) as they would be if the held card were dropped at the cursor."""
        run = self.run
        sp, bx = list(run.spread), list(run.box)
        hover = self._zone_index()
        if self.held is None:
            return sp, bx, hover
        lists = {"s": sp, "b": bx}
        oz, oi = self.origin
        lists[oz][oi] = None
        if hover is None:
            hover = self.origin
        hz, hi = hover
        displaced = lists[hz][hi]
        lists[hz][hi] = self.held
        if displaced is not None and hover != self.origin:
            lists[oz][oi] = displaced
        return sp, bx, hover

    def _note_text(self, text):
        self._note, self._note_t = text, NOTE_S

    def _shake(self, text=None):
        self._shake_t = SHAKE_S
        if text:
            self._note_text(text)

    # ------------------------------------------------------------------ preview
    def _recompute(self):
        sp, bx, hover = self._arrange()
        held = self.held is not None
        self.board.show(sp, bx, origin=self.origin if held else None, hover=hover if held else None)
        key = tuple(None if c is None else (c.uid, c.def_id, c.reversed, c.star, c.charm) for c in sp)
        if key != self._arr_key:
            self._arr_key = key
            rep = readings.analyze(sp, self.run, self.enemy)
            self.report = rep
            self._spread_now = sp
            self.board.set_report(rep, sp)
            self.board.set_bite(rep.eat_slot)
            self._apply_report(rep)
        self._detail_key = None

    def _apply_report(self, rep):
        names = list(rep.readings)
        if self._prev_readings is not None:
            new = set(names) - set(self._prev_readings)
            if new:
                self._hot, self._hot_t = new, HOT_S
        self._prev_readings = names
        self._reading_key = None
        pr = rep.per_round
        items = [W.chip("PER ROUND", T.CAPTION), W.chip("DMG %d" % pr.get("dmg", 0), T.ACCENT)]
        if pr.get("singe"):
            items.append(W.status_chip("singe", pr["singe"]))
        if pr.get("heal"):
            items.append(W.chip("HEAL %d" % pr["heal"], T.HEAL, ("ui_heart", 0)))
        if pr.get("curl"):
            items.append(W.status_chip("curl", pr["curl"]))
        self.chips.set(items)

    def _reading_segments(self):
        names = list(self.report.readings)
        if not names:
            return [("none yet", T.CAPTION)]
        segs, used = [], 0
        for k, name in enumerate(names):
            need = len(name) + (3 if k else 0)
            if used + need > READING_CHARS - (3 if k < len(names) - 1 else 0):
                segs += [6, ("...", T.CAPTION)]
                break
            if k:
                segs += [6, ("{.}", T.RULE), 6]
            segs.append((name, T.FOCUS if name in self._hot else T.TEXT))
            used += need
        return segs

    def _check_events(self):
        """After the arrangement really changed (or on entry): tips and tutorial progress."""
        rep = self.report
        if any(lk.kind == "hiss" for lk in rep.links):
            R.arm_tip(self.run, "first_hiss")
            if "first_hiss" in self.run.tips:
                self.sv.tip("first_hiss")
        else:
            self.sv.report("hiss_fixed")
        if any("Catwalk" in r for r in rep.readings):
            self.sv.report("catwalk_made")

    # ------------------------------------------------------------------ update
    def update(self, ctl, dt):
        if not self._booted:
            self._booted = True
            self._check_events()
        if self._info_open and not self.app.overlays:
            self._info_open = False
            self.sv.report("close_info")
        if self._later is not None and not self.app.overlays:     # work a closing dialogue asked for
            fn, self._later = self._later, None
            fn()
            return
        self._tut_sync()
        if self._hot_t > 0:
            self._hot_t -= dt
            if self._hot_t <= 0:
                self._hot = set()
                self._reading_key = None
        if self._note_t > 0:
            self._note_t -= dt
            if self._note_t <= 0:
                self._note = None
                self._detail_key = None
        if self._merge_t > 0:
            self._merge_t -= dt
            if self._merge_t <= 0 and self._merge_view is not None:
                self._merge_view.flash = False
                self._merge_view = None
        if self._shake_t > 0:
            self._shake_t = max(0.0, self._shake_t - dt)
        self._animating = self.board.tick(dt) or self._shake_t > 0
        self.busy = self._animating
        if ctl.dx or ctl.dy:
            self._move(ctl.dx, ctl.dy)
        if ctl.a:
            self._press_a()
        elif ctl.b:
            self._press_b()
        elif ctl.c:
            self._press_c()

    def _tut_sync(self):
        tutor = self.sv.tutor
        step = getattr(tutor, "step", None) if tutor is not None else None
        sid = getattr(step, "id", None)
        if sid == self._step_id:
            return
        self._step_id = sid
        if step is None or self.held is not None:
            return
        hl = step.highlight or ""
        if hl.startswith("slot:"):
            n = int(hl[5:]) - 1
            if 0 <= n < self.ns:
                self.row, self.col = ROW_SPREAD, n
        elif hl == "fight":
            self.row, self.col = ROW_SPREAD, self.ns
        elif hl == "reversed_card":
            for i, c in enumerate(self.run.spread):
                if c is not None and c.reversed:
                    self.row, self.col = ROW_SPREAD, i
                    break
        self._detail_key = None

    def _move(self, dx, dy):
        row, col = self.row, self.col
        holding = self.held is not None
        if dx:
            n = self._row_len(row)
            col = (col + dx) % n
            if holding and row == ROW_SPREAD and col == self.ns:
                col = (col + dx) % n
        if dy:
            rows = [r for r in (ROW_ENEMY, ROW_SPREAD, ROW_BOX) if self._row_len(r) and not (holding and r == ROW_ENEMY)]
            if len(rows) > 1:
                cx = self._center_x(row, col)
                row = rows[(rows.index(row) + dy) % len(rows)]
                n = self._row_len(row)
                cand = [c for c in range(n) if not (holding and row == ROW_SPREAD and c == self.ns)]
                col = min(cand, key=lambda c: abs(self._center_x(row, c) - cx))
        if (row, col) != (self.row, self.col):
            self.row, self.col = row, col
            if holding:
                self._recompute()
            self._detail_key = None

    # ------------------------------------------------------------------ buttons
    def _press_a(self):
        run = self.run
        if self.held is not None:
            self._drop()
            return
        if self.row == ROW_SPREAD and self.col == self.ns:
            if not any(c is not None for c in run.spread):
                self._shake("Put a card in your Spread first.")
                return
            self.sv.report("press_fight")
            self.finish("fight")
            return
        zi = self._zone_index()
        card = None if zi is None else self._cards(zi[0])[zi[1]]
        if card is None:
            self._shake()
            return
        self.held, self.origin = card, zi
        if zi[0] == "s":
            self.sv.report("pick_up:slot%d" % (zi[1] + 1))
        self._recompute()

    def _press_b(self):
        if self.held is None:
            self.sv.menu()
            return
        self.row, self.col = (ROW_SPREAD if self.origin[0] == "s" else ROW_BOX), self.origin[1]
        self.held = self.origin = None
        self._recompute()

    def _press_c(self):
        if self.held is not None:
            self._open_card_info(self.held)
            return
        if self.row == ROW_ENEMY:
            if self.col == 0:
                self._open(self._enemy_overlay())
            else:
                c = self.scraps[self.col - 1]
                if isinstance(c, cards.Card):
                    self._open_card_info(c)
                else:
                    self._open(self._scrap_overlay(c))
            return
        zi = self._zone_index()
        if zi is None:
            self._open(self._fight_overlay())
            return
        card = self._cards(zi[0])[zi[1]]
        if card is None:
            self._note_text("An empty slot. Pick up a card, then press A here.")
            self._detail_key = None
        else:
            self._open_card_info(card)

    def _open(self, overlay):
        self._info_open = True
        self.sv.report("open_info")
        self.app.open(overlay)

    def _open_card_info(self, card):
        self._info_open = True
        self.sv.report("open_info")
        self.sv.card_info(card)

    # ------------------------------------------------------------------ drop / merge
    def _drop(self):
        zi = self._zone_index()
        if zi is None or zi == self.origin:
            self._press_b()
            return
        target = self._cards(zi[0])[zi[1]]
        if target is not None and target.def_id == self.held.def_id and target.star < 2:
            R.arm_tip(self.run, "first_merge")
            self.sv.tip("first_merge", lambda: setattr(self, "_later", lambda: self._ask_merge(target, zi)))
            return
        self._commit(zi)

    def _commit(self, zi):
        run = self.run
        sp, bx, _ = self._arrange()
        run.spread[:] = sp
        run.box[:] = bx
        origin_zone = self.origin[0]
        self.held = self.origin = None
        if zi[0] == "s":
            self.sv.report("drop:slot%d" % (zi[1] + 1))
            if origin_zone == "b":
                self.sv.report("box_to_spread")
        self._recompute()
        self._check_events()

    def _ask_merge(self, target, zi):
        def yes():
            held = self.held
            if held is None:
                return
            R.remove_card(self.run, held.uid)
            if R.merge(self.run, held, target.uid) is None:
                return
            self.held = self.origin = None
            view = (self.board.slots if zi[0] == "s" else self.board.box)[zi[1]]
            view.flash, self._merge_view, self._merge_t = True, view, 0.25
            self._recompute()
            self._check_events()

        self.app.confirm("Merge these cards?\nThe result gets +1 Star.", yes, None, yes="Merge", no="Not Now")

    # ------------------------------------------------------------------ overlays (C)
    def _enemy_overlay(self):
        e = self.enemy
        text = story.ENEMY_TEXT.get(e.key)
        body = text.desc.split("\n") if text else []
        if e.blurb:
            body += cards.wrap_lines(e.blurb, 54)
        notes = list(BOSS_RULES) if "bottomless_belly" in e.passives else []
        name = e.name.split(",")[0]
        sub = e.name.split(", ", 1)[1].capitalize() if ", " in e.name else {"tutorial": "Practice rat", "rat": "Rat",
                                                                           "elite": "Elite", "boss": "Boss"}.get(e.tier, "")
        return W.InfoOverlay(name, "%s {.} HP %d" % (sub, e.hp) if sub else "HP %d" % e.hp, body, notes=notes)

    def _scrap_overlay(self, c):
        cv = W.CardView(0, 0, small=True)
        cv.set_enemy_card(c)
        return W.InfoOverlay(cards.enemy_card_title(c), "%s {.} Scrap" % self.enemy.name.split(",")[0],
                             cards.enemy_card_text(c), cv)

    def _fight_overlay(self):
        rep, sp = self.report, self._spread_now
        body = ["Your cards play left to right, then the rat plays one.", ""]
        for i, c in enumerate(sp):
            if c is not None:
                body.append("%d. %s {.} Power %d" % (i + 1, cards.card_title(c), rep.slots[i].power))
        body.append("")
        body.append("Readings: " + (", ".join(rep.readings) if rep.readings else "none yet"))
        pr = rep.per_round
        body.append("Per Round: DMG %d, Singe %d, Heal %d, Curl %d" % (
            pr.get("dmg", 0), pr.get("singe", 0), pr.get("heal", 0), pr.get("curl", 0)))
        return W.InfoOverlay("Fight", "vs %s" % self.enemy.name.split(",")[0], body)

    # ------------------------------------------------------------------ tutorial regions
    def region(self, key):
        ns, nb = self.ns, self.nb
        if key == "spread":
            return (slot_x(0) - 6, SLOT_Y - 6, slot_x(ns - 1) + T.CARD_W + 6 - (slot_x(0) - 6), 76)
        if key.startswith("slot:"):
            n = int(key[5:]) - 1
            return (slot_x(n) - 4, SLOT_Y - 4, T.CARD_W + 8, 72) if 0 <= n < ns else None
        if key == "fight":
            x, y, w, h = T.SPREAD_FIGHT
            return (x - 4, y - 4, w + 8, h + 8)
        if key == "box":
            return (box_x(0) - 6, T.SPREAD_BOX_Y - 6, nb * T.SPREAD_BOX_PITCH + 6, T.CARD_SH + 12)
        if key == "enemy_row":
            return (12, 4, T.INNER_R + 6 - 12, 60)
        if key == "reading_bar":
            return (T.INNER_L - 2, T.SPREAD_READING_Y0 - 2, T.INNER_W + 4, 20)
        if key == "footer":
            return (T.INNER_L, T.FOOTER_Y - 1, T.INNER_W, T.FOOTER_H)
        if key == "hp_bar":
            return (16 + 6 * 6 + 8, T.FOOTER_Y - 1, 12 + 6 * len("HP %d/%d" % (self.run.hp, self.run.max_hp)) + 12,
                    T.FOOTER_H)
        if key == "reversed_card":
            for i, c in enumerate(self.run.spread):
                if c is not None and c.reversed:
                    return (slot_x(i) - 4, SLOT_Y - 4, T.CARD_W + 8, 72)
        return None

    # ------------------------------------------------------------------ drawing
    def _build_static(self):
        """(test(rect) -> painted rect or None, paint(scr)) pairs; test(None) means a full repaint."""
        items = []
        e = self.enemy

        def box(rect):
            return lambda r: rect if (r is None or hit(r, rect)) else None

        def frame(scr):
            scr.rect(2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4, T.RULE_DIM)
            W.corners(scr, 2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4)

        full = (0, 0, T.SCREEN_W, T.SCREEN_H)
        items.append((lambda r: None if (r is not None and 8 <= r[0] and 8 <= r[1] and r[0] + r[2] <= 472
                                         and r[1] + r[3] <= 312) else full, frame))

        def portrait(scr):
            W.panel(scr, 16, 9, 59, 53, orn=False)
            p = W.portrait(e.key)
            if p is not None:
                scr.blit(p, 0, 22, 13, bg=T.PANEL)
        items.append((box((15, 8, 61, 55)), portrait))

        text = story.ENEMY_TEXT.get(e.key)
        name = (text.name if text else e.name).split(",")[0]
        sub = e.name.split(", ", 1)[1] if ", " in e.name else ""
        sub = sub[:1].upper() + sub[1:]

        def names(scr):
            scr.text(88, 9, name, T.LABEL, T.GROUND, T.TITLE)
            if sub:
                scr.text(88, 29, sub, T.MUTED, T.GROUND)
            scr.text(88 + self.hp_w + 6, 45, self.hp_text, T.TEXT, T.GROUND)
        items.append((box((88, 9, self.scrap_x0 - 92, 52)), names))

        for y in (T.SPREAD_DIV1_Y, T.SPREAD_DIV2_Y, T.SPREAD_DIV3_Y, T.FOOTER_DIV_Y):
            items.append((box((T.INNER_L, y - 2, T.INNER_W, 5)),
                          lambda scr, y=y: W.divider(scr, T.INNER_L, T.INNER_R, y, mid=y != T.FOOTER_DIV_Y)))

        items.append((box((16, 70, 42, 15)), lambda scr: scr.text(16, 70, "READING", T.LABEL, T.GROUND)))

        def decor(scr):
            for sx, sy in ((396, 190), (440, 192), (407, 232), (428, 230)):
                scr.blit(T.asset("ui_sparkle"), 1, sx - 2, sy - 2, bg=T.GROUND)
            scr.blit(T.asset("ui_moon_eye_s"), 0, 410, 204, bg=T.GROUND)
        items.append((box((390, 186, 74, 56)), decor))
        d = PANEL_RECT
        items.append((box((d[0] - 1, d[1] - 1, d[2] + 2, d[3] + 2)), lambda scr: W.panel(scr, *d)))
        return items

    def _build_widgets(self):
        """(invalidate(), rect) for everything that is not part of the Board."""
        w = []
        for v in self.scrap_views:
            w.append((v.invalidate, (v.x - 4, v.y - 4, v.w + 8, v.h + 8)))
        w.append((self.enemy_hp.invalidate, (88, 48, self.hp_w, 9)))
        w.append((self.fight.invalidate, T.SPREAD_FIGHT))
        w.append((self.chips.invalidate, (160, 89, 304, 15)))
        w.append((self.reading.invalidate, (READING_X, 70, T.INNER_R + 1 - READING_X, 15)))
        w.append((self.detail.invalidate, PANEL_RECT))
        w.append((self.footer.invalidate, (0, T.FOOTER_DIV_Y, T.SCREEN_W, T.SCREEN_H - T.FOOTER_DIV_Y)))
        w.append((self._forget_candles, (384, 219, 71, 22)))
        return w

    def _forget_candles(self):
        self._candle = None

    def _paint_static(self, scr, clip=None):
        painted = []
        for test, paint in self._static:
            r = test(clip)
            if r is not None:
                paint(scr)
                painted.append(r)
        return painted

    def restore(self, scr, rect):
        x, y, w, h = rect
        x, y = max(0, x - 2), max(0, y - 2)
        w, h = min(T.SCREEN_W - x, w + 4), min(T.SCREEN_H - y, h + 4)
        rect = (x, y, w, h)
        if w * h > T.SCREEN_W * T.SCREEN_H // 2:
            self.draw(scr, True)
            return
        scr.fill_rect(x, y, w, h, T.GROUND)
        painted = [rect] + self._paint_static(scr, rect)
        for r in painted:
            self.board.invalidate(r)
            for invalidate, wr in self._widgets:
                if hit(r, wr):
                    invalidate()
        self._paint(scr, False)

    def draw(self, scr, full):
        if full:
            scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, T.GROUND)
            self._paint_static(scr)
            self._detail_key = None
        self._paint(scr, full)

    def _paint(self, scr, full):
        self._point_cursor()
        self.board.draw(scr, full)           # the cursor goes first: it is the immediate feedback
        for v in self.scrap_views:
            v.draw(scr, full)
        self.enemy_hp.draw(scr, full)
        self.fight.set(focused=self.row == ROW_SPREAD and self.col == self.ns and self.held is None,
                       disabled=self.held is not None)
        self.fight.draw(scr, full)
        self.chips.draw(scr, full)
        key = (tuple(self.report.readings), tuple(sorted(self._hot)))
        if key != self._reading_key:
            self._reading_key = key
            self.reading.set(self._reading_segments())
        self.reading.draw(scr, full)
        self._draw_candles(scr, full)
        self._refresh_detail()
        self.detail.draw(scr, full)
        self._refresh_footer()
        self.footer.draw(scr, full)
        if scr.stats()["ms"] > 45.0:      # a card repaint alone costs ~55 ms: count it as an animation frame
            self.busy = True

    def _point_cursor(self):
        lifted = self.held is not None
        dx = 0
        if self._shake_t > 0:
            dx = (-2, 2, -1, 1)[int(self._shake_t * 40) % 4]
        row, col = self.row, self.col
        if row == ROW_ENEMY:
            if col == 0:
                px, py, pw, ph = T.ENEMY_PORTRAIT
                self.board.cursor_rect(px + dx, py, pw, ph)
            else:
                v = self.scrap_views[col - 1]
                self.board.cursor_rect(v.x + dx, v.y, v.w, v.h)
        elif row == ROW_SPREAD and col == self.ns:
            fx, fy, fw, fh = T.SPREAD_FIGHT
            self.board.cursor_rect(fx + dx, fy, fw, fh)
        else:
            zone = "s" if row == ROW_SPREAD else "b"
            self.board.cursor_to(zone, col, lifted, dx)

    def _draw_candles(self, scr, full):
        frame = int(self.app.time * 3) % 2
        if full or (frame != self._candle and not W.over_budget(scr, 200, 2)):
            c = T.asset("ui_candle")
            scr.blit(c, frame, 384, 219, bg=T.GROUND)
            scr.blit(c, (frame + 1) % 2, 450, 221, bg=T.GROUND)
            self._candle = frame

    # ------------------------------------------------------------------ detail panel and footer
    def _refresh_detail(self):
        if self._detail_key == (self.row, self.col, self.held is not None):
            return
        self._detail_key = (self.row, self.col, self.held is not None)
        self.detail.set(*self._detail_lines())

    def _detail_lines(self):
        """(title | None, subtitle, rows) for the detail panel."""
        if self._note is not None:
            return None, "", [[(self._note, T.ACCENT)]]
        row, col = self.row, self.col
        e = self.enemy
        if row == ROW_ENEMY:
            if col == 0:
                return (e.name.split(",")[0], "HP %d" % e.hp,
                        text_rows([e.blurb]) if e.blurb else [])
            c = self.scraps[col - 1]
            tag = "Chewed Major" if isinstance(c, cards.Card) else "Scrap"
            return cards.enemy_card_title(c), tag, text_rows(cards.enemy_card_text(c))
        if row == ROW_SPREAD and col == self.ns:
            if any(c is not None for c in self.run.spread):
                return None, "", [[("Press A to fight", T.TEXT)]]
            return None, "", [[("Put a card in your Spread first.", T.TEXT)]]
        sp, bx, _ = self._arrange()
        zone = "s" if row == ROW_SPREAD else "b"
        card = (sp if zone == "s" else bx)[col]
        if card is None:
            return None, "", [[("Empty slot", T.CAPTION)]]
        title, sub = cards.card_title(card), cards.card_subtitle(card)
        if zone == "s":
            info = self.report.slots[col]
            if info is not None and info.parts:
                return title, sub, [self._power_segments(info)]
        return title, sub, text_rows(cards.card_text(card))

    def _power_segments(self, info):
        parts = [("%s %s" % (name, val), T.HEAL if val.startswith("+") else T.CURSE) for name, val in info.parts]
        width = sum(len(p[0]) for p in parts) + 3 * (len(parts) - 1) + len(" > Power %d" % info.power) + 3
        segs = []
        if width + len("Base %d" % info.base) + 3 <= 68:
            segs += [("Base %d" % info.base, T.MUTED), 6, ("{.}", T.RULE), 6]
        for k, p in enumerate(parts):
            if k:
                segs += [6, ("{.}", T.RULE), 6]
            segs.append(p)
        segs += [8, ("{>}", T.RULE), 8, ("Power %d" % info.power, T.ACCENT)]
        return segs

    def _refresh_footer(self):
        run = self.run
        zi = self._zone_index()
        if self.held is not None:
            hints = [("A", "Drop"), ("B", "Put back"), ("C", "Info")]
        elif self.row == ROW_ENEMY:
            hints = [("B", "Menu"), ("C", "Info")]
        elif self.row == ROW_SPREAD and self.col == self.ns:
            hints = [("A", "Fight"), ("B", "Menu"), ("C", "Info")]
        elif zi is not None and self._cards(zi[0])[zi[1]] is not None:
            hints = [("A", "Pick up"), ("B", "Menu"), ("C", "Info")]
        else:
            hints = [("B", "Menu"), ("C", "Info")]
        left = [("name", "Domino"), ("hp", "HP %d/%d" % (run.hp, run.max_hp)), ("treat", "Treats %d" % run.treats)]
        key = (tuple(hints), tuple(left))
        if key != self._footer_key:
            self._footer_key = key
            self.footer.set_hints(hints)
            self.footer.set_left(left)


# =========================================================================== dev harnesses
def dev_spread():
    from .dev_spread import StubServices, dev_run, make_app
    sv = StubServices(dev_run())
    return make_app(sv, lambda: SpreadScene(sv, "dust_mouse", lambda r: print("done", r)))


def dev_spread_boss():
    from .dev_spread import StubServices, dev_run, make_app
    sv = StubServices(dev_run(boss=True))
    return make_app(sv, lambda: SpreadScene(sv, "chubbs", lambda r: print("done", r)))
