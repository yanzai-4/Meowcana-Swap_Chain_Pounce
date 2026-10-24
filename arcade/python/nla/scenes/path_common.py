"""Shared building blocks for the Night Path node scenes (path, stall, catbed, encounter, box, levelup, menu).

    wrap(text, chars)                 word-wrap a string that may hold "\\n" into a list of lines
    inside(a, b)                      True when two (x, y, w, h) rects overlap
    Tile(x, y, w, h, fill, bg)        selectable plate: body is painted once, focus only repaints a 2 px rim
    NodeScene                         base Scene: ground fill, retained statics and widgets, tip scheduling,
                                      toast strip, footer with HP / Treats / Level, cheap restore() after overlays
    node_text(node)                   (title, tag, description lines) for a Night Path node
    enc_story(key)                    story.EncounterText for a Rules encounter key (aliases the two renamed keys)
    place_card(services, card, status, done)   the Reward flow for a gained card (duplicate / box full)
    status_items(run)                 footer left items: name, HP, Treats, level

Scenes keep every static element as a (rect, paint function) pair and every dirty-tracked widget with its rect.
A full redraw paints everything; restore(rect) after an overlay closes repaints only what intersects the rect, so
closing a Dialogue does not cost a whole-screen repaint.
"""

import textwrap

from nla import story
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.app import Scene

CENTER_X, CENTER_W = 70, 340      # centered one-line labels: 340 px holds 56 characters of BODY, fewer fast pixels to clear
FRAME = (2, 2, T.SCREEN_W - 4, T.FOOTER_DIV_Y - 2)      # ends above the footer rule (the footer clears its own band)


# --------------------------------------------------------------------------- small helpers
def wrap(text, chars):
    """Word-wrap `text` (explicit newlines kept) to lines of at most `chars` characters."""
    out = []
    for part in text.split("\n"):
        out.extend(textwrap.wrap(part, chars) or [""])
    return out


def detail_lines(lines, rows=3, width=50):
    """Re-wrap rules text to `width` characters (a 56-character BODY line is a 47 ms repaint, 50 is 43 ms). When the
    narrower wrap would need more than `rows` lines the original lines are kept."""
    narrow = wrap(" ".join(lines), width)
    return narrow if len(narrow) <= rows else list(lines)


def inside(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def status_items(run):
    return [("name", "Domino"), ("hp", W.fmt_hp(run.hp, run.max_hp)), ("treat", str(run.treats)),
            ("txt", "Lv %d" % run.level)]


_ENC_ALIAS = {"granny_dream": "grannys_dream", "yarn_ball": "ball_of_yarn"}


def enc_story(key):
    return story.ENCOUNTERS[_ENC_ALIAS.get(key, key)]


_KIND_TEXT = {"fight": "rat_fight", "bed": "cat_bed"}


def node_text(node):
    """(title, tag, description lines) for a Night Path node. Rat Fight and Elite show the rat's own name."""
    kind = _KIND_TEXT.get(node.kind, node.kind)
    base = story.NODE_TEXT[kind]
    if node.kind in ("fight", "elite") and node.key in story.ENEMY_TEXT:
        et = story.ENEMY_TEXT[node.key]
        return et.name, base.name, et.desc.split("\n")
    return base.name, "", base.desc.split("\n")


def place_card(services, card, status, done):
    """A card was gained (take_card already ran). Hand "duplicate" and "box_full" to the Reward flow; others finish
    at once. done(final_status) with "spread" | "box" | "merged" | "replaced" | "discarded"."""
    if status in ("duplicate", "box_full"):
        from nla.scenes import reward
        reward.place_card(services, card, status, done)
    else:
        done(status)


# --------------------------------------------------------------------------- Tile
class Tile:
    """A plate with rows of text and an optional icon. The body is painted when its content changes, in stages (erase,
    icon, one text row per stage) that are spread over frames when they do not fit one; moving the focus repaints only a
    two-pixel rim (a few hundred pixels), so the cursor answers at once. `pending` is True while stages remain."""

    LIMIT_MS = 45.0

    def __init__(self, x, y, w, h, fill=T.PANEL, bg=T.GROUND):
        self.x, self.y, self.w, self.h, self.fill, self.bg = x, y, w, h, fill, bg
        self.rows = []              # (text, color, font, dy, align)
        self.icon = None            # fn(scr, x, y, w, h, fill, dim)
        self.icon_key = None
        self.focused = False
        self.dim = False
        self._body = None           # look of the body that is on screen
        self._rim = None
        self._job = None            # [(est_ms, fn)] of the body being painted
        self._job_look = None

    @property
    def rect(self):
        return (self.x, self.y, self.w, self.h)

    @property
    def pending(self):
        return bool(self._job)

    def set(self, rows=None, icon=None, icon_key=None, dim=None, focused=None):
        if rows is not None:
            self.rows = [tuple(r) for r in rows]
        if icon is not None:
            self.icon, self.icon_key = icon, icon_key
        if dim is not None:
            self.dim = dim
        if focused is not None:
            self.focused = focused

    def invalidate(self):
        self._body = self._rim = None
        self._job = None

    def draw(self, scr, full=False):
        look = (tuple(self.rows), self.dim, self.icon_key)
        if full and not self._job:
            self._body = None
        if self._body != look and (self._job is None or self._job_look != look):
            self._job = self._plan(scr, skip_fill=full and self.fill == self.bg)
            self._job_look = look
            self._rim = None
        if self._job:
            while self._job:
                est, fn = self._job[0]
                st = scr.stats()
                if st["ops"] > 0 and (not full and st["ms"] + est > self.LIMIT_MS or full and st["ms"] + est > 52):
                    return
                fn(scr)
                self._job.pop(0)
            self._body = self._job_look
            self._job = None
        if self._rim != self.focused:
            if not full and self._rim is not None and W.over_budget(scr, 400, 4):
                return                      # one frame later; a rim is cheap but a body just used the budget
            self._paint_rim(scr)
            self._rim = self.focused

    def _plan(self, scr, skip_fill):
        """Paint stages for the body: erase, icon, then one per text row. skip_fill: ground already laid there."""
        x, y, w, h = self.rect
        job = []
        if not skip_fill:
            rate = 770.0 if T.is_fast(self.fill) else 180.0
            if w * h > 9000:                # a big plate erases in two halves
                h1 = h // 2
                job.append((4 + w * h1 / rate, lambda s: s.fill_rect(x, y, w, h1, self.fill)))
                job.append((4 + w * (h - h1) / rate, lambda s: s.fill_rect(x, y + h1, w, h - h1, self.fill)))
            else:
                job.append((4 + w * h / rate, lambda s: s.fill_rect(x, y, w, h, self.fill)))
        if self.icon is not None:
            job.append((getattr(self.icon, "est", 22), lambda s: self.icon(s, x, y, w, h, self.fill, self.dim)))
        for text, color, font, dy, align in self.rows:
            if self.dim and color != T.CURSE:       # a red row is a price flash: keep it readable on a dim plate
                color = T.NIGHT4
            text = W.glyphs(text)
            tw, th = scr.measure(text, font)
            tx = x + (w - tw) // 2 if align == "c" else x + 10
            job.append((4 + tw * th / 180.0, lambda s, tx=tx, dy=dy, text=text, color=color, font=font:
                        s.text(tx, y + dy, text, color, self.fill, font)))
        return job

    def _paint_rim(self, scr):
        x, y, w, h = self.rect
        if self.focused:
            scr.rect(x, y, w, h, T.AMBER3)
            scr.rect(x + 1, y + 1, w - 2, h - 2, T.AMBER1)
        else:
            scr.rect(x, y, w, h, T.NIGHT3 if self.dim else T.RULE)
            scr.rect(x + 1, y + 1, w - 2, h - 2, self.fill)


# --------------------------------------------------------------------------- Sprite
class Sprite:
    """A baked character animation standing on a flat ground color. A new frame is one opaque window (transparent
    pixels painted with `bg`, about 4096 px = 23 ms for a 64 px sprite). `clock()` returns seconds (App.time); anim=False holds frame 0."""

    def __init__(self, name, x, y, bg, clock, flip=False, anim=True):
        self.asset = T.asset(name)
        self.x, self.y, self.bg, self.clock, self.flip, self.anim = x, y, bg, clock, flip, anim
        self._frame = None

    @property
    def rect(self):
        return (self.x, self.y, self.asset.w, self.asset.h)

    def invalidate(self):
        self._frame = None

    def draw(self, scr, full=False):
        f = self.asset.frame_at(self.clock()) if self.anim else 0
        if not full and (f == self._frame or W.over_budget(scr, self.asset.w * self.asset.h, 3)):
            return
        scr.blit(self.asset, f, self.x, self.y, flip=self.flip, bg=self.bg)     # one window, transparent = bg
        self._frame = f


# --------------------------------------------------------------------------- footer
class _SplitFooter:
    """The UIKit Footer as two widgets (status on the left, button hints on the right). A whole Footer costs about
    70 ms to paint at once; the halves cost about 35 ms each and are painted on separate frames."""

    def __init__(self, bg):
        self.left = W.Footer(bg=bg)
        self.right = W.Footer(bg=bg, divider_line=False)

    def set_left(self, items):
        self.left.set_left(items)

    def set_hints(self, hints):
        self.right.set_hints(hints)


# --------------------------------------------------------------------------- NodeScene
class NodeScene(Scene):
    """Base class: retained statics + widgets, first-time tip scheduling, a toast strip and the standard footer."""

    ground = T.GROUND
    TOAST = (T.INNER_L, 274, T.INNER_W, 20)

    def __init__(self, services, done=None):
        super().__init__(done)
        self.sv = services
        self.statics = []           # (rect, fn(scr), group, est_ms)
        self.widgets = []           # (rect or None, widget, group)
        self.mode = None            # which tagged group is shown (None-tagged items always show)
        self.footer = _SplitFooter(self.footer_bg())
        self.toast = W.Toast(*self.TOAST, bg=self.ground)
        self._tip_key = None
        self._tip_wait = 0
        self._locked = False        # a scripted beat or a tip is running: ignore input
        self._first = True          # no full draw yet
        self._pending = []          # progressive repaint jobs
        self.footer.set_left(status_items(self.run))

    @property
    def run(self):
        return self.sv.run

    def footer_bg(self):
        return self.ground

    # -- registration
    def add_static(self, rect, fn, group=None, est=None):
        """est: paint cost in ms for the frame budget (default: 4 ms plus one ms per 500 px of the rect)."""
        self.statics.append((rect, fn, group, est if est is not None else 4 + rect[2] * rect[3] / 500.0))

    def add_widget(self, widget, rect=None, group=None):
        self.widgets.append((rect, widget, group))
        return widget

    def add_frame(self):
        """Outer 1 px rule with flourish corners, as separate pieces so a restore repaints only what it touches."""
        x, y, w, h = FRAME
        for rect in ((x, y, w, 1), (x, y + h - 1, w, 1), (x, y, 1, h), (x + w - 1, y, 1, h)):
            self.add_static(rect, lambda scr, r=rect: scr.fill_rect(*r, T.RULE_DIM))
        c = T.asset("ui_corner")
        spots = ((x, y, False, False), (x + w - c.w, y, True, False),
                 (x, y + h - c.h, False, True), (x + w - c.w, y + h - c.h, True, True))
        for cx, cy, fx, fy in spots:
            self.add_static((cx, cy, c.w, c.h),
                            lambda scr, cx=cx, cy=cy, fx=fx, fy=fy: scr.blit(c, 0, cx, cy, flip=fx, flip_y=fy))

    def add_title(self, text, y=8, color=T.LABEL, cx=T.SCREEN_W // 2):
        th = T.text_h(T.TITLE)

        def paint(scr):
            scr.text_center(y, text, color, self.ground, T.TITLE, cx=cx)
        self.add_static((cx - 170, y, 340, th), paint)

    def add_text(self, x, y, text, color=T.TEXT, font=T.BODY, w=None, align="l", group=None):
        """Static opaque text. `w` is the width of the rect it may touch (default: 6 px per character)."""
        th = T.text_h(font)
        width = w if w is not None else 6 * len(text) + 4

        def paint(scr):
            if align == "c":
                scr.text_center(y, W.glyphs(text), color, self.ground, font, cx=x + width // 2)
            else:
                scr.text(x, y, W.glyphs(text), color, self.ground, font)
        self.add_static((x, y, width, th), paint, group)

    def add_divider(self, y, x0=T.INNER_L, x1=T.INNER_R, group=None):
        self.add_static((x0, y - 2, x1 - x0 + 1, 5), lambda scr: W.divider(scr, x0, x1, y, bg=self.ground), group)

    # -- painting
    def paint_ground(self, scr, rect):
        if rect is None:
            scr.fill_rect(0, 0, T.SCREEN_W, T.SCREEN_H, self.ground)
        else:
            x, y, w, h = rect
            x0, y0 = max(0, x), max(0, y)
            x1, y1 = min(T.SCREEN_W, x + w), min(T.SCREEN_H, y + h)
            if x1 > x0 and y1 > y0:
                scr.fill_rect(x0, y0, x1 - x0, y1 - y0, self.ground)

    def paint(self, scr, rect=None):
        self.paint_ground(scr, rect)
        for r, fn, group, _est in self.statics:
            if (group is None or group == self.mode) and (rect is None or inside(r, rect)):
                fn(scr)

    def set_mode(self, mode, rect):
        """Switch the screen state: statics and widgets tagged with `mode` appear, others vanish; `rect` repaints."""
        self.mode = mode
        self._queue(rect)

    def all_widgets(self):
        foot = (0, T.FOOTER_DIV_Y, T.SCREEN_W, T.SCREEN_H - T.FOOTER_DIV_Y)
        live = [(r, wd) for r, wd, group in self.widgets if group is None or group == self.mode]
        return live + [(foot, self.footer.left), (foot, self.footer.right), (self.TOAST, self.toast)]

    def draw_widgets(self, scr, full):
        for _rect, wd in self.all_widgets():
            wd.draw(scr, full)

    # A full redraw and every restore after an overlay are painted progressively, a frame budget at a time:
    # stage 0 the ground in row bands of at most REPAINT_PX pixels, stage 1 every static that touches the rect (each
    # exactly once, so nothing is painted twice), stage 2 the widgets that touch the rect.
    REPAINT_PX = 24000
    FRAME_MS = 52              # busy-frame budget (limit 70); an item joins a frame only if its estimate fits
    EST_MS = {"Footer": 38, "Tile": 22, "CardView": 22, "TextRun": 20, "Label": 8, "_Stage": 40, "Sprite": 18}

    def ground_px(self, y):
        """Pixels of ground the repaint may lay down in one frame at row y (a bitmap ground needs far fewer)."""
        return self.REPAINT_PX

    def _queue(self, rect):
        self._pending.append({"rect": rect, "y": rect[1], "stage": 0, "items": None, "i": 0})

    def _over(self, scr, est=6):
        st = scr.stats()
        return st["ops"] > 0 and st["ms"] + est > self.FRAME_MS

    def _est(self, widget):
        return self.EST_MS.get(type(widget).__name__, 14)

    def _repaint_step(self, scr):
        job = self._pending[0]
        x, y, w, h = job["rect"]
        if job["stage"] == 0:
            rows = max(1, self.ground_px(job["y"]) // max(1, w))
            n = max(1, min(rows, y + h - job["y"]))
            self.paint_ground(scr, (x, job["y"], w, n))
            job["y"] += n
            if job["y"] >= y + h:
                job["stage"] = 1
                job["items"] = [(est, fn) for r, fn, g, est in self.statics
                                if (g is None or g == self.mode) and inside(r, job["rect"])]
            return
        if job["stage"] == 1:
            items = job["items"]
            while job["i"] < len(items) and not self._over(scr, items[job["i"]][0]):
                items[job["i"]][1](scr)
                job["i"] += 1
            if job["i"] >= len(items):
                job["stage"], job["i"] = 2, 0
                job["items"] = [wd for r, wd in self.all_widgets() if r is None or inside(r, job["rect"])]
            return
        items = job["items"]
        while job["i"] < len(items) and not self._over(scr, self._est(items[job["i"]])):
            items[job["i"]].draw(scr, True)
            if getattr(items[job["i"]], "pending", False):
                return                      # a staged widget (Tile) continues next frame
            job["i"] += 1
        if job["i"] >= len(items):
            self._pending.pop(0)
            if not self._pending:
                self._first = False
                self.on_full(scr)

    def draw(self, scr, full):
        if full:
            self._pending = []
            self._queue((0, 0, T.SCREEN_W, T.SCREEN_H))
        if self._pending:
            self.busy = True
            self._repaint_step(scr)
            return
        self.busy = self.animating()
        self.draw_widgets(scr, False)
        self.draw_extra(scr)

    def restore(self, scr, rect):
        x, y, w, h = rect          # overlays such as Dialogue draw flourish corners 1 px outside their rect
        x0, y0 = max(0, x - 2), max(0, y - 2)
        self._queue((x0, y0, min(T.SCREEN_W, x + w + 2) - x0, min(T.SCREEN_H, y + h + 2) - y0))

    # hooks
    def on_full(self, scr):
        """Everything queued has been painted (the first full draw or a restore)."""

    def animating(self):
        return False

    def draw_extra(self, scr):
        """Per-frame drawing that is not a retained widget (animations)."""

    # -- tips
    def tip(self, key):
        """Show a first-time tip once the scene is on screen (a few frames after the first full draw)."""
        self._tip_key = key
        self._tip_wait = 3

    def pump_tip(self):
        """Call from update(): True while a tip is waiting for the first frames or is showing."""
        if self._tip_key is None:
            return self._locked
        if self._first:
            return True
        if self._tip_wait > 0:
            self._tip_wait -= 1
            return True
        key, self._tip_key = self._tip_key, None
        self._locked = True
        self.sv.tip(key, self._tip_done)
        return True

    def _tip_done(self):
        self._locked = False

    def set_hints(self, hints):
        self.footer.set_hints(hints)

    def refresh_status(self):
        self.footer.set_left(status_items(self.run))

    def region(self, key):
        """Tutorial highlight rects for the keys these scenes show."""
        if key == "footer":
            return (0, T.FOOTER_DIV_Y, T.SCREEN_W, T.SCREEN_H - T.FOOTER_DIV_Y)
        return None
