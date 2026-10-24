"""Tutorial driver: Prologue "The Reading Table" (story.TUTORIAL, 3 lessons, 27 steps).

The coach is not a scene. It sits beside the real scenes and does four things:

  * Steps. A step opens (once the right scene is on screen and has settled) with its highlight arrow and Zero's
    dialogue; when the last line closes, `wait_for == "press_a"` steps are done, every other step waits for the
    action key a scene reports through `services.report(key)`.
  * Gating. While a step waits, `gate()` masks the buttons the step does not allow (and the stick when "stick" is not
    allowed) before the scene sees them. A blocked press, or about 8 s without input, shows the step's nudge.
  * Arrow. `draw_over()` paints the pulsing ui_tut_arrow next to `scene.region(step.highlight)` after the scene's
    own drawing and erases it with `scene.restore(scr, rect)` when the step moves on.
  * Lessons. Each lesson is `rules.run.tutorial_setup(run, i)` + a tutorial mouse fought through Flow.fight(); the
    Reward is the same Pick 1 of 3 as Fate's Draft (`draft_options(run, i)`, via battle_rewards).

Skip Tutorial (the menu while the tutorial runs) leaves for the Draft with the picks that remain. A lost lesson
starts that lesson again. B never leaves the tutorial: the menu only offers the Skip confirm (default No).
"""

from nla import story
from nla.rules import run as R
from nla.rules.enemies import ENEMIES
from nla.ui import theme as T

SETTLE = 0.6          # seconds a scene must sit still before the next step opens over it
IDLE_NUDGE = 8.0
NUDGE_GAP = 5.0
DIALOGUE_RECT = (16, 228, 448, 60)
ARROW = 13            # badge: a 9x9 arrow on a dark plate with a rim, readable over any text

_DEFAULT_ALLOW = {
    "press_fight": "a", "pick_reward": "a", "close_info": "c", "pick_up": "a", "hiss_fixed": "a",
    "box_to_spread": "a", "catwalk_made": "a", "battle_speed": "a", "battle_skip": "b", "battle_done": "a,b",
}
_BATTLE_KEYS = ("battle_speed", "battle_skip")


def _need_scene(step):
    wf = step.wait_for
    if wf in ("battle_speed", "battle_skip", "battle_done"):
        return "BattleScene"
    if wf == "pick_reward":
        return "RewardScene"
    return "SpreadScene"


def _allow(step):
    items = {x.strip() for x in step.allow.split(",") if x.strip()}
    if not items:
        items = {"stick"} | {x for x in _DEFAULT_ALLOW.get(step.wait_for.split(":")[0], "").split(",") if x}
    return items


def _hits(a, b):
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


class Tutorial:
    def __init__(self, services, flow):
        self.svc = services
        self.flow = flow
        self.app = services.app
        self.steps = story.TUTORIAL
        self.firsts = [next(i for i, s in enumerate(self.steps) if s.id.startswith("l%d_" % n)) for n in (1, 2, 3)]
        self.idx = 0
        self.lesson = 0
        self.picks = 0
        self.phase = "off"       # off | pending | reading | waiting | hold
        self.allow = set()
        self.settle = 0.0
        self.idle = 0.0
        self.last_nudge = -99.0
        self._arrow = None       # (rect, frame, pulse, scene) as painted
        self._rect = None        # cached (key, rect, frame)
        self._erase = None       # badge to wipe after a step change

    # ------------------------------------------------------------------ public (Services / Flow)
    @property
    def step(self):
        return self.steps[self.idx]

    @property
    def active(self):
        return self.phase != "off"

    @property
    def waiting(self):
        return self.phase == "waiting"

    def start(self):
        self.svc.tutor = self
        self.app.tutor = self
        self.picks = 0
        self._begin_lesson(0)

    def retry(self):
        self._begin_lesson(self.lesson)

    def menu(self):
        self.app.confirm("Skip the lessons?\nYou still pick your cards.", self._skip, yes="Skip",
                         no="Keep going")

    def report(self, key):
        if self.phase in ("off", "hold", "reading"):
            return
        step = self.step
        if key == "battle_done" and step.wait_for in _BATTLE_KEYS:
            i = self.idx
            while i < len(self.steps) and self.steps[i].wait_for in _BATTLE_KEYS:
                i += 1
            self._go(i)
        elif key == step.wait_for:
            self._go(self.idx + 1)

    # ------------------------------------------------------------------ lessons
    def _begin_lesson(self, i):
        self.lesson = i
        lesson = R.tutorial_setup(self.svc.run, i)
        self._go(self.firsts[i])
        self.flow.fight(ENEMIES[lesson.enemy], self._lesson_done, lesson=i)

    def _lesson_done(self):
        self.picks += 1
        if self.lesson < 2:
            self._begin_lesson(self.lesson + 1)
        else:
            self.phase = "off"
            self.flow.tutorial_finished()

    def _skip(self):
        self.phase = "off"
        self.flow.tutorial_skipped(self.picks)

    # ------------------------------------------------------------------ steps
    def _go(self, i):
        self._erase = self._arrow
        self.idx = min(i, len(self.steps) - 1)
        self.settle = 0.0
        self.idle = 0.0
        self._rect = None
        self.phase = "hold" if self.idx == len(self.steps) - 1 else "pending"
        if self.phase == "pending":
            self.allow = _allow(self.step)

    def tick(self, dt):
        app = self.app
        if self.phase == "pending":
            scene = app.scene
            if (app._trans is None and not app._need_full and not app.overlays and scene is not None
                    and type(scene).__name__ == _need_scene(self.step)):
                self.settle += dt
                if self.settle >= SETTLE:
                    self._open()
            else:
                self.settle = 0.0
        elif self.phase == "waiting" and not app.overlays and app._trans is None:
            self.idle += dt
            if self.idle >= IDLE_NUDGE:
                self._nudge()

    def _open(self):
        self.phase = "reading"
        self.app.say(self.step.lines, self._lines_done)

    def _lines_done(self):
        if self.phase != "reading":
            return
        if self.step.wait_for == "press_a":
            self._go(self.idx + 1)
        else:
            self.phase = "waiting"
            self.idle = 0.0

    def _nudge(self):
        self.idle = 0.0
        line = self.step.nudge
        if line is not None and self.app.time - self.last_nudge >= NUDGE_GAP:
            self.last_nudge = self.app.time
            self.app.say([line], None)

    # ------------------------------------------------------------------ input gate
    def gate(self, inp):
        app = self.app
        if inp.any:
            self.idle = 0.0
        if self.phase != "waiting" or app.overlays or app._trans is not None:
            return
        allow = self.allow
        blocked = False
        if inp.a and "a" not in allow:
            inp.a = False
            blocked = True
        if inp.b and "b" not in allow:
            inp.b = False                            # B is the scene's Menu button: here it offers the Skip confirm
            self.menu()
            return
        if inp.c and "c" not in allow:
            inp.c = False
            blocked = True
        if (inp.dx or inp.dy) and "stick" not in allow:
            inp.dx = inp.dy = 0
        if blocked:
            self._nudge()

    # ------------------------------------------------------------------ arrow
    def _place(self, region, below_first=False):
        """Arrow rect + frame near `region` (x, y, w, h): above, below, left, right, never under the dialogue."""
        x, y, w, h = region
        cx, cy = x + w // 2 - ARROW // 2, y + h // 2 - ARROW // 2
        above, below = (cx, y - ARROW - 3, 1), (cx, y + h + 3, 0)
        options = (below, above) if below_first else (above, below)
        options += ((x - ARROW - 3, cy, 3), (x + w + 3, cy, 2))
        first = None
        for ax, ay, frame in options:
            rect = (ax, ay, ARROW, ARROW)
            if ax < 0 or ay < 0 or ax + ARROW > T.SCREEN_W or ay + ARROW > T.SCREEN_H:
                continue
            if first is None:
                first = (rect, frame)
            if not _hits(rect, DIALOGUE_RECT):
                return rect, frame
        return first if first else (None, 0)

    def _target(self, scene):
        key = (id(scene), self.idx)
        if self._rect is None or self._rect[0] != key:
            region = None
            fn = getattr(scene, "region", None)
            if fn is not None and self.step.highlight:
                region = fn(self.step.highlight)
            rect, frame = self._place(region, self.step.highlight == "fight") if region else (None, 0)
            self._rect = (key, rect, frame)
        return self._rect[1], self._rect[2]

    def draw_over(self, scr, kind):
        app = self.app
        scene = app.scene
        if scene is None:
            return
        if kind == "transition":
            return
        erase = self._erase
        if erase is not None:
            self._erase = None
            if erase[3] is scene and not app.overlays:
                scene.restore(scr, erase[0])         # the scene repaints just the badge's rect
                self._arrow = None
        if kind == "full":
            self._arrow = None                       # a restore may have painted over the badge: draw it again
        if self.phase not in ("reading", "waiting"):
            return
        rect, frame = self._target(scene)
        if rect is None:
            return
        if app.overlays:
            top = app.overlays[-1][0]
            if top.full_screen or _hits(rect, top.rect):
                self._arrow = None
                return
        if type(scene).__name__ != _need_scene(self.step):
            return
        pulse = int(app.time * 2.5) % 2
        look = (rect, frame, pulse, scene)
        if self._arrow == look:
            return
        x, y = rect[0], rect[1]
        scr.fill_rect(x, y, ARROW, ARROW, T.PANEL)
        scr.rect(x, y, ARROW, ARROW, T.AMBER3 if pulse else T.AMBER1)
        scr.blit(T.asset("ui_tut_arrow"), frame, x + 2, y + 2, tint=T.AMBER3 if pulse else T.AMBER1, bg=T.PANEL)
        self._arrow = look
