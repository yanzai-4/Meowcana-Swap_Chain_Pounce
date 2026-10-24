"""The Result panel of the Battle scene: Victory/Defeat title, Treats / XP / best hit, a quip, A or B continues.

Built in row slices over several frames (a 240x140 panel is far too many slow pixels for one frame); `ready` turns
True when the last slice is on screen.
"""

from nla.ui import theme as T
from nla.ui import widgets as W

from .battle_hud import run_jobs

RECT = (104, 46, 240, 140)


class ResultPanel:
    def __init__(self, won, boss, treats, xp, best_hit, rounds, quip):
        self.won, self.boss = won, boss
        self.treats, self.xp, self.best_hit, self.rounds, self.quip = treats, xp, best_hit, rounds, quip
        self.rect = RECT
        self.jobs = None
        self.ready = False

    def _rows(self):
        rows = []
        if self.won:
            rows.append((("ui_treat", 0), "Treats", "+%d" % self.treats))
            if self.xp:
                rows.append((("ui_star", 0), "XP", "+%d" % self.xp))
        else:
            rows.append((("ui_heart", 0), "Rounds", str(self.rounds)))
        rows.append((("ui_sparkle", 0), "Best hit", str(self.best_hit)))
        return rows

    def _build(self):
        x, y, w, h = self.rect
        jobs = []
        step = max(1, 6000 // w)
        for r0 in range(0, h, step):
            rows = min(step, h - r0)
            jobs.append((w * rows, lambda scr, r0=r0, rows=rows: scr.fill_rect(x, y + r0, w, rows, T.PANEL)))

        def chrome(scr):
            scr.rect(x, y, w, h, T.RULE_BRIGHT)
            scr.rect(x + 2, y + 2, w - 4, h - 4, T.RULE_DIM)
            W.corners(scr, x - 1, y - 1, w + 2, h + 2)

        def title(scr):
            text = "Victory!" if self.won else "Defeat"
            color = T.GOLD4 if self.won else T.CURSE
            scr.text_center(y + 8, text, color, T.PANEL, T.TITLE, cx=x + w // 2)
            W.divider(scr, x + 14, x + w - 15, y + 36, bg=T.PANEL)

        def stats(scr):
            ty = y + 46
            for icon, label, value in self._rows():
                a = T.asset(icon[0])
                scr.blit(a, icon[1], x + 44, ty + (15 - a.h) // 2, bg=T.PANEL)
                scr.text(x + 60, ty, label, T.MUTED, T.PANEL)
                scr.text_right(x + w - 44, ty, value, T.ACCENT, T.PANEL)
                ty += 20

        def quip(scr):
            scr.text_center(y + h - 28, self.quip, T.TEXT, T.PANEL, cx=x + w // 2)

        jobs += [(900, chrome), (500, title), (900, stats), (400, quip)]
        return jobs

    def draw(self, scr):
        if self.ready:
            return
        if self.jobs is None:
            self.jobs = self._build()
        if run_jobs(scr, self.jobs):
            self.ready = True
