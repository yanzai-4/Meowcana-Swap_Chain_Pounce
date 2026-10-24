"""Cutscene: a background, the speakers standing in it, and a story.SCENES script played through the Dialogue box.

    CutsceneScene(services, key, done, lines=None, bg=None, cast=None, dim=False)

`key` names the script in story.SCENES (or pass `lines` directly). Backdrop and cast default to the table below, so
Flow only passes the key. `cast` entries are (character asset, x, feet_y). The scene paints once, then the
Dialogue overlay (A next, B skips the whole scene) does the talking; the scene finishes when it closes.
"""

from nla import story
from nla.ui import theme as T
from nla.ui.app import Scene

# character -> (asset name, faces right?)
_ATTIC = "bg_attic"
_PARLOR = "bg_parlor"
_END = "bg_end"

_HERO = [("domino", 40, 222), ("zero", 110, 222)]
_TABLE = [("domino", 292, 196), ("zero", 44, 222)]

SETS = {
    "opening": (_PARLOR, False, _TABLE),
    "tutorial_graduate": (_PARLOR, False, _TABLE),
    "enter_attic": (_ATTIC, False, _HERO),
    "sir_flea_intro": (_ATTIC, False, _HERO + [("sir_flea", 340, 222)]),
    "sir_flea_defeated": (_ATTIC, False, _HERO + [("sir_flea", 340, 222)]),
    "dog_ear_intro": (_ATTIC, False, _HERO + [("dog_ear", 350, 222)]),
    "dog_ear_defeated": (_ATTIC, False, _HERO + [("dog_ear", 350, 222)]),
    "chubbs_intro": (_ATTIC, False, _HERO + [("chubbs", 340, 222)]),
    "chubbs_defeated": (_ATTIC, False, _HERO + [("chubbs", 340, 222)]),
    "ending": (_ATTIC, False, _HERO),
    "third_death_dream": (_PARLOR, True, []),
    "demo_end": (_END, False, []),
}


class CutsceneScene(Scene):
    def __init__(self, services, key, done=None, lines=None, bg=None, cast=None, dim=None):
        super().__init__(done)
        self.svc = services
        self.lines = lines if lines is not None else story.SCENES[key]
        d_bg, d_dim, d_cast = SETS.get(key, (_ATTIC, False, _HERO))
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
        for name, x, feet in self.cast:
            sprite = T.asset(name)
            scr.blit(sprite, 0, x, feet - sprite.h, bg=None)
        self._painted = True
