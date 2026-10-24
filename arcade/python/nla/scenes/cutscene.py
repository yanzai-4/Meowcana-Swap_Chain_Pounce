"""Cutscene: a background, the speakers standing in it, and a story.SCENES script played through the Dialogue box.

    CutsceneScene(services, key, done, lines=None, bg=None, cast=None, dim=False)

`key` names the script in story.SCENES (or pass `lines` directly). Backdrop and cast default to the table below, so
Flow only passes the key. `cast` entries are (character asset, x, feet_y[, flip[, frame]]); flip mirrors the
sprite so a character can face left (Domino is baked facing right, rats facing left), frame picks a pose
(`domino_story`: 0 worried, 1 pointing forward, 2 holding a card high). The scene paints once, then the
Dialogue overlay (A next, B skips the whole scene) does the talking; the scene finishes when it closes.
"""

from nla import story
from nla.ui import theme as T
from nla.ui.app import Scene

# Backdrops
_ATTIC = "bg_attic"
_PARLOR = "bg_parlor"
_END = "bg_end"

_STORY = "domino_story"
_WORRIED, _POINT, _PROUD = 0, 1, 2


def _hero(pose):
    return [(_STORY, 40, 222, False, pose), ("zero", 110, 222)]


def _table(pose):
    """Parlor: Zero left of the reading table, Domino on the floor right of it facing back toward Granny and Zero."""
    return [(_STORY, 372, 222, True, pose), ("zero", 44, 222)]


SETS = {
    "opening": (_PARLOR, False, _table(_WORRIED)),
    "tutorial_graduate": (_PARLOR, False, _table(_POINT)),
    "enter_attic": (_ATTIC, False, _hero(_POINT)),
    "sir_flea_intro": (_ATTIC, False, _hero(_POINT) + [("sir_flea", 340, 222)]),
    "sir_flea_defeated": (_ATTIC, False, _hero(_PROUD) + [("sir_flea", 340, 222)]),
    "dog_ear_intro": (_ATTIC, False, _hero(_POINT) + [("dog_ear", 350, 222)]),
    "dog_ear_defeated": (_ATTIC, False, _hero(_PROUD) + [("dog_ear", 350, 222)]),
    "chubbs_intro": (_ATTIC, False, _hero(_POINT) + [("chubbs", 340, 222)]),
    "chubbs_defeated": (_ATTIC, False, _hero(_PROUD) + [("chubbs", 340, 222)]),
    "ending": (_ATTIC, False, _hero(_PROUD)),
    "third_death_dream": (_PARLOR, True, []),
    "demo_end": (_END, False, []),
}


class CutsceneScene(Scene):
    def __init__(self, services, key, done=None, lines=None, bg=None, cast=None, dim=None):
        super().__init__(done)
        self.svc = services
        self.lines = lines if lines is not None else story.SCENES[key]
        d_bg, d_dim, d_cast = SETS.get(key, (_ATTIC, False, _hero(_POINT)))
        self.bg = bg or d_bg
        self.dim = d_dim if dim is None else dim
        self.cast = d_cast if cast is None else cast
        self._painted = False
        self._opened = False

    def region(self, key):
        return None

    def update(self, ctl, dt):
        if self._painted and not self._opened:
            self._opened = True
            self.app.say(self.lines, self._over)

    def _over(self):
        self.finish()

    def draw(self, scr, full):
        if not full:
            return
        art = T.asset(self.bg)
        scr.blit(art, 0, 0, 0, dim=self.dim)
        if art.h < T.SCREEN_H:
            scr.fill_rect(0, art.h, T.SCREEN_W, T.SCREEN_H - art.h, T.GROUND)
        for name, x, feet, *extra in self.cast:
            sprite = T.asset(name)
            flip = bool(extra and extra[0])
            frame = extra[1] if len(extra) > 1 else 0
            scr.blit(sprite, frame, x, feet - sprite.h, flip=flip, bg=None)
        self._painted = True
