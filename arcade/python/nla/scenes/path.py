"""Night Path: the map between fights. PathScene(services, done) -> done(node).

Over `bg_path` the six step sockets (x = 44 + 62 * step, road y 168) and the Boss socket (x 428) are the progress
track. Visited steps show a dimmed icon of the node you took, future steps show dimmed previews, and the current
step offers two lit node icons on its fork rings (y 128 and y 208). A portrait token of Domino stands on the road
socket of the current step. Left/Right (or Up/Down) choose, A enters (the token hops onto the chosen ring), B opens
the Menu, C explains the highlighted node. The first time the Boss is next, Zero warns about it.

Rules touched: `enter_node(run, index)` on A, and `run.flags["trail"]` (index taken at each step) so the map can show
where you have been. `rules.run.finish_node` and the save are Flow's job after the node scene ends.
"""

import math

from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W

from .path_common import NodeScene, inside, node_text
from .path_info import NodeInfo

SOCKET_X = [44 + 62 * i for i in range(6)]
BOSS_X = 428
ROAD_Y = 168
FORK_Y = (128, 208)
NODE_FRAME = {"fight": 0, "elite": 1, "stall": 2, "encounter": 3, "bed": 4, "box": 5, "boss": 6}
PANEL = (16, 228, 448, 64)
HOP_SECONDS = 0.42


def node_pos(step, index, count):
    """Center of a node icon on the map."""
    if step >= R.STEPS:
        return (BOSS_X, ROAD_Y)
    if count == 1:
        return (SOCKET_X[step], FORK_Y[0])
    return (SOCKET_X[step], FORK_Y[index])


def token_home(step):
    return (SOCKET_X[step], ROAD_Y) if step < R.STEPS else ((SOCKET_X[5] + BOSS_X) // 2, ROAD_Y)


class _RingCursor:
    """Amber brackets around the highlighted node icon; erases itself by repainting the map under it."""

    def __init__(self, scene):
        self.scene = scene
        self.want = None
        self._drawn = None

    def to(self, pos):
        self.want = pos

    def hide(self):
        self.want = None

    def invalidate(self):
        self._drawn = None

    @staticmethod
    def region(pos):
        return (pos[0] - 15, pos[1] - 15, 30, 30)

    def draw(self, scr, full=False):
        if full:
            self._drawn = None
            old = None
        else:
            old = self._drawn
            if old == self.want or W.over_budget(scr, 1800, 8):
                return
        if old is not None:
            self.scene.paint(scr, self.region(old))
        if self.want is not None:
            x, y = self.want
            b = T.asset("ui_bracket")
            scr.blit(b, 0, x - 14, y - 14)
            scr.blit(b, 0, x + 8, y - 14, flip=True)
            scr.blit(b, 0, x - 14, y + 8, flip_y=True)
            scr.blit(b, 0, x + 8, y + 8, flip=True, flip_y=True)
        self._drawn = self.want


class _Token:
    """Domino's portrait token (34x34, gold frame). Moving it repaints the map under its old spot."""

    def __init__(self, scene, pos):
        self.scene = scene
        self.pos = pos
        self._drawn = None
        self.cursor = None

    def invalidate(self):
        self._drawn = None

    @staticmethod
    def region(pos):
        return (pos[0] - 18, pos[1] - 18, 36, 36)

    def draw(self, scr, full=False):
        want = (int(self.pos[0]), int(self.pos[1]))
        if full:
            self._drawn = None
        elif self._drawn == want or W.over_budget(scr, 1500, 6):
            return
        if self._drawn is not None:
            self.scene.paint(scr, self.region(self._drawn))
            if self.cursor is not None and inside(self.region(self._drawn), _RingCursor.region(self.cursor.want or (-99, -99))):
                self.cursor.invalidate()
        x, y = want
        scr.rect(x - 17, y - 17, 34, 34, T.GOLD3)
        scr.rect(x - 16, y - 16, 32, 32, T.NIGHT0)
        scr.asset_region(T.asset("domino_portrait"), 0, x - 15, y - 15, 9, 6, 30, 30)
        self._drawn = want


class PathScene(NodeScene):
    REPAINT_PX = 14000

    def __init__(self, services, done=None):
        super().__init__(services, done)
        run = self.run
        self.step = min(run.step, R.STEPS)
        self.options = R.path_options(run)
        self.sel = 0
        self._hop = None
        self.pos = [node_pos(self.step, i, len(self.options)) for i in range(len(self.options))]

        self.bg = T.asset("bg_path")
        self._trail = list(run.flags.get("trail", []))
        self._build_header()
        self._build_icons()

        self.token = _Token(self, token_home(self.step))
        self.cursor = _RingCursor(self)
        self.token.cursor = self.cursor
        self.add_widget(self.token, (token_home(self.step)[0] - 40, ROAD_Y - 80, 300, 160))
        self.add_widget(self.cursor, (0, 100, T.SCREEN_W, 140))
        self.title = W.Label(30, PANEL[1] + 4, 300, T.TITLE, T.LABEL, T.GROUND)
        self.tag = W.Label(PANEL[0] + PANEL[2] - 190, PANEL[1] + 12, 180, T.BODY, T.MUTED, T.GROUND, "r")
        self.desc = [W.Label(30, PANEL[1] + 31 + 15 * i, 420, T.BODY, T.TEXT, T.GROUND) for i in range(2)]
        for wd in [self.title, self.tag] + self.desc:
            self.add_widget(wd, PANEL)
        px, py, pw, ph = PANEL                      # the panel is a fast fill; paint it as two halves (frame budget)
        for y0, y1 in ((py, py + ph // 2), (py + ph // 2, py + ph)):
            self.add_static((px, y0, pw, y1 - y0), lambda scr, y0=y0, y1=y1: scr.fill_rect(px, y0, pw, y1 - y0, T.GROUND))
        self.add_static((px - 1, py - 1, pw + 2, ph + 2), lambda scr: W.panel(scr, *PANEL, fill=None))
        self._select(0)
        self.set_hints([("A", "Enter"), ("B", "Menu"), ("C", "Info")])
        if self.step >= R.STEPS:
            self.tip("boss_warning")

    # ------------------------------------------------------------------ static art
    FLAT_TOP, FLAT_BOTTOM = 48, 228     # bg_path: flat night1 band above the title line; the info panel and footer
    #                                     cover everything below FLAT_BOTTOM, so those rows are fast fills, not bitmap

    def ground_px(self, y):
        return 24000 if (y < self.FLAT_TOP or y >= self.FLAT_BOTTOM) else 6500

    def paint_ground(self, scr, rect):
        if rect is None:
            rect = (0, 0, T.SCREEN_W, T.SCREEN_H)
        x, y, w, h = rect
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(T.SCREEN_W, x + w), min(T.SCREEN_H, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        for ya, yb, flat in ((y0, min(y1, self.FLAT_TOP), True), (max(y0, self.FLAT_TOP), min(y1, self.FLAT_BOTTOM), False),
                             (max(y0, self.FLAT_BOTTOM), y1, True)):
            if yb <= ya:
                continue
            if flat:
                scr.fill_rect(x0, ya, x1 - x0, yb - ya, T.GROUND)
            else:
                scr.asset_region(self.bg, 0, x0, ya, x0, ya, x1 - x0, yb - ya)

    def _build_header(self):
        run = self.run
        boss = self.step >= R.STEPS
        self.add_static((T.INNER_L, 6, 200, 26),
                        lambda scr: scr.text(T.INNER_L, 6, "Night Path", T.LABEL, T.GROUND, T.TITLE))
        self.add_static((T.INNER_L, 30, 200, 15),
                        lambda scr: scr.text(T.INNER_L, 30, "Chapter 1: The Dusty Attic", T.MUTED, T.GROUND))
        label = "Boss: Chubbs" if boss else "Step %d of %d" % (self.step + 1, R.STEPS)

        def head(scr):
            scr.text_right(T.INNER_R + 1, 8, label, T.TEXT, T.GROUND)
            star = T.asset("ui_star")
            for i in range(R.STEPS):
                scr.blit(star, 0 if i < self.step else 1, T.INNER_R - 8 - 12 * (R.STEPS - 1 - i) - 14, 34, bg=T.GROUND)
        self.add_static((300, 6, 164, 40), head)

    def _icon(self, frame, x, y, dim):
        asset = T.asset("ui_node_dim" if dim else "ui_node")
        self.add_static((x - 10, y - 10, 20, 20), lambda scr: scr.blit(asset, frame, x - 10, y - 10))

    def _build_icons(self):
        path = self.run.path
        for s in range(R.STEPS + 1):
            row = path[s]
            for i, node in enumerate(row):
                x, y = node_pos(s, i, len(row))
                frame = NODE_FRAME[node.kind]
                if s < self.step:
                    continue            # visited steps show only the node that was taken (below)
                self._icon(frame, x, y, dim=(s != self.step))
        for s in range(min(self.step, R.STEPS)):
            idx = self._trail[s] if s < len(self._trail) else None
            if idx is not None and 0 <= idx < len(path[s]):
                self._icon(NODE_FRAME[path[s][idx].kind], SOCKET_X[s], ROAD_Y, dim=True)

    # ------------------------------------------------------------------ selection
    def _select(self, i):
        self.sel = i
        node = self.options[i]
        title, tag, desc = node_text(node)
        self.title.set(title)
        self.tag.set(tag)
        for k, lab in enumerate(self.desc):
            lab.set(desc[k] if k < len(desc) else "")
        self.cursor.to(self.pos[i])

    def _info(self):
        self.sv.app.open(NodeInfo(self.options[self.sel]))

    # ------------------------------------------------------------------ input
    def update(self, ctl, dt):
        self.toast.update(dt)
        if self.pump_tip():
            return
        if self._hop is not None:
            self._advance_hop(dt)
            return
        if (ctl.dx or ctl.dy) and len(self.options) > 1:
            self._select((self.sel + (ctl.dx or ctl.dy)) % len(self.options))
        elif ctl.a:
            self._start_hop()
        elif ctl.b:
            self.sv.menu()
        elif ctl.c:
            self._info()

    def _start_hop(self):
        self.cursor.hide()
        self._hop = {"t": 0.0, "from": token_home(self.step), "to": self.pos[self.sel], "hold": 0.0}

    def _advance_hop(self, dt):
        h = self._hop
        if h["t"] < HOP_SECONDS:
            h["t"] = min(HOP_SECONDS, h["t"] + dt)
            k = h["t"] / HOP_SECONDS
            (x0, y0), (x1, y1) = h["from"], h["to"]
            self.token.pos = (x0 + (x1 - x0) * k, y0 + (y1 - y0) * k - 14 * math.sin(math.pi * k))
            return
        h["hold"] += dt
        if h["hold"] >= 0.12:
            self._hop = None
            self._commit()

    def _commit(self):
        run = self.run
        idx = self.sel
        node = R.enter_node(run, idx)
        trail = run.flags.setdefault("trail", [])
        del trail[run.step:]
        trail.append(idx)
        self.finish(node)

    def animating(self):
        return self._hop is not None


def dev_path():
    from . import path_dev
    return path_dev.dev_path()
