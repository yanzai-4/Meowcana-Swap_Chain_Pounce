"""Pause menu. MenuScene(services, done) -> done("resume" | "save_quit" | "abandon").

Resume / How to Play / Save & Quit / Abandon Run. Up/Down move (wrapping), A picks, B is Resume (it never commits
anything), C explains the highlighted entry. How to Play opens the `story.HOW_TO_PLAY` page here and returns to the
menu when closed, so this scene never reports "how_to_play" to Flow. Abandon Run asks first (Confirm, default No).
Save & Quit saves through `services.save()` and then reports "save_quit".
"""

from nla import story
from nla.rules import run as R
from nla.ui import theme as T
from nla.ui import widgets as W
from nla.ui.input import step

from .path_common import NodeScene, Tile, hit, wrap

_RESUME = ("resume", "Back to the game.", "Resume", "Close the menu and keep playing.")
_HOW = ("how", "Read the rules again.", "How to Play",
        "The one-page recap: buttons, readings and how a night is won.")
RUN_ENTRIES = (
    _RESUME, _HOW,
    ("save_quit", "Save here and go to the title.", "Save & Quit",
     "Your run is saved at this step. Pick Continue on the title screen to come back."),
    ("abandon", "Give up this night.", "Abandon Run",
     "Ends this run for good and returns you to the Parlor. This cannot be undone."),
)
TUTORIAL_ENTRIES = (
    _RESUME, _HOW,
    ("skip_tutorial", "Skip the lessons, pick your cards.", "Skip Tutorial",
     "Jump to Fate's Draft for the cards you have not picked yet."),
    ("quit_tutorial", "Leave the lessons.", "Quit Tutorial",
     "Go back to the title screen. You can start the lessons again any time."),
)
NAMES = {e[0]: e[2] for e in RUN_ENTRIES + TUTORIAL_ENTRIES}
ROW_X, ROW_W, ROW_H, ROW_GAP, ROW_Y = 120, 240, 34, 6, 76
HELP_Y = 250


class HowToPlay(W.Overlay):
    """Full-screen How to Play page (B or A closes). Painted in bands, one frame budget at a time."""

    BAND = 24000

    def __init__(self, page):
        super().__init__()
        self.page = page
        self.full_screen = True
        self.rect = (0, 0, T.SCREEN_W, T.SCREEN_H)
        self._stage = 0
        self._y = 0

    def update(self, ctl, dt):
        if ctl.b or ctl.a or ctl.c:
            self.close()

    def draw(self, scr, full=False):
        if full:
            self._stage, self._y = 0, 0
        if self._stage == 0:
            self.busy = True
            n = max(1, min(T.SCREEN_H - self._y, self.BAND // T.SCREEN_W))
            scr.fill_rect(0, self._y, T.SCREEN_W, n, T.GROUND)
            self._y += n
            if self._y >= T.SCREEN_H:
                self._stage = 1
            return
        if self._stage == 1:
            self.busy = True
            scr.rect(2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4, T.RULE_DIM)
            W.corners(scr, 2, 2, T.SCREEN_W - 4, T.SCREEN_H - 4)
            scr.text_center(10, self.page.title, T.LABEL, T.GROUND, T.TITLE)
            W.divider(scr, T.INNER_L, T.INNER_R, 42)
            self._stage, self._y = 2, 0
            return
        if self._stage == 2:
            self.busy = True
            y = 52 + 17 * self._y
            row = self.page.rows[self._y]
            if row:
                W.rich(scr, T.INNER_L + 8, y, row, T.TEXT if row[:2] not in ("A ", "B ", "C ") else T.ACCENT, T.GROUND)
            self._y += 1
            if self._y >= len(self.page.rows):
                self._stage = 3
            return
        if self._stage == 3:
            self.busy = False
            W.Footer(hints=[("B", "Close")]).draw(scr, True)
            self._stage = 4


class MenuScene(NodeScene):
    TOAST = (T.INNER_L, 272, T.INNER_W, 20)

    def __init__(self, services, done=None):
        super().__init__(services, done)
        self.sel = 0
        run = self.run
        self.entries = TUTORIAL_ENTRIES if run.tutorial else RUN_ENTRIES
        self.add_frame()
        self.add_title("Paused", y=6)
        if run.tutorial:
            where = "Prologue {.} The Reading Table"
        elif run.flags.get("draft_pick") is not None:
            where = "Fate's Draft"
        else:
            where = "Chapter 1: The Dusty Attic {.} " + ("Boss: Chubbs" if run.step >= R.STEPS else "Step %d of %d" % (run.step + 1, R.STEPS))
        self.add_text(T.INNER_L, 38, W.glyphs(where), T.MUTED, w=T.INNER_W, align="c")
        self.add_divider(60)
        self.rows = []
        for i, (key, _, _, _) in enumerate(self.entries):
            t = Tile(ROW_X, ROW_Y + i * (ROW_H + ROW_GAP), ROW_W, ROW_H, fill=T.GROUND)
            t.set(rows=[(NAMES[key], T.CURSE if key == "abandon" else T.TEXT, T.BODY, 9, "c")])
            self.rows.append(t)
            self.add_widget(t, t.rect)
        self.add_divider(HELP_Y - 8)
        self.help = W.Label(T.INNER_L, HELP_Y, T.INNER_W, T.BODY, T.TEXT, T.GROUND, "c")
        self.add_widget(self.help, (T.INNER_L, HELP_Y, T.INNER_W, 15))
        self._focus()

    def _focus(self):
        for i, t in enumerate(self.rows):
            t.set(focused=(i == self.sel))
        self.help.set(self.entries[self.sel][1])
        self.set_hints([("A", "Select"), ("B", "Resume"), ("C", "Info")])

    def target_at(self, x, y):
        for i, t in enumerate(self.rows):
            if hit(t.rect, x, y):
                return i
        return None

    def current_target(self):
        return self.sel

    def hover(self, target):
        self.sel = target
        self._focus()

    def update(self, ctl, dt):
        self.toast.update(dt)
        if ctl.dy or ctl.dx:
            self.sel = step(self.sel, ctl.dy or ctl.dx, len(self.entries))
            self._focus()
        elif ctl.b:
            self.finish("resume")
        elif ctl.a:
            self._pick(self.sel)
        elif ctl.c:
            _, _, name, long = self.entries[self.sel]
            self.sv.app.open(W.InfoOverlay(name, "Menu", wrap(long, 56)))

    def _pick(self, i):
        key = self.entries[i][0]
        if key == "resume":
            self.finish("resume")
        elif key == "how":
            self.sv.app.open(HowToPlay(story.HOW_TO_PLAY))
        elif key == "save_quit":
            self.sv.save()
            self.finish("save_quit")
        elif key == "skip_tutorial":
            self.sv.app.confirm("Skip the lessons?\nYou still pick your cards.", lambda: self.finish("skip_tutorial"),
                                yes="Skip", no="Keep going")
        elif key == "quit_tutorial":
            self.sv.app.confirm("Quit the lessons?\nYou can learn again from the title.",
                                lambda: self.finish("quit_tutorial"), yes="Quit", no="Keep going")
        else:
            self.sv.app.confirm("Abandon this run?\nYou lose this night's progress.", lambda: self.finish("abandon"),
                                yes="Abandon", no="Keep playing")


def dev_menu():
    from . import path_dev
    return path_dev.dev_menu()
