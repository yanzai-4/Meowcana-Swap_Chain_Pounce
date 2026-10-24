"""Frame-based effects for scenes: floating text, particles, slashes, sprite bursts, shake, hit-stop, tint flashes.

All timing counts DRAWN frames (one `update()` call = one frame), so on a slow device the effects slow down
with the frame rate instead of skipping. Everything is budgeted: at most `Effects.MAX_ITEMS` live items, and an
item whose look did not change since last frame sends nothing.

API:

    fx = Effects(restore)           restore(scr, rect) repaints whatever is behind rect = (x, y, w, h)
                                    (flat fill: lambda scr, r: scr.fill_rect(*r, T.NIGHT1); attic backdrop:
                                    scr.region(...)). Call fx.update() once per frame, fx.draw(scr) after the scene
                                    drew. `restore` is called BEFORE any effect is painted in that frame.
    fx.busy                         True while anything is alive (use it for App.busy / cost accounting)

    fx.float_text(x, y, text, color, font=T.BODY, scale=1, rise=14, frames=14, shadow=T.NIGHT0)
                                    text centered on x rising `rise` px over `frames`
    fx.damage(x, y, value, big=False, heal=False, crit=False)
                                    NUM-font number; big (>= 30) = scale 2 with three gold/moon flashes
    fx.chain_text(x, y, text, tier) tier 0..4: color ramp white-yellow-orange-red-gold, 1x until tier 1, then 2x
    fx.sparks(x, y, colors, n=5, up=(12, 24), life=6)    2x2 sparks rising and dying
    fx.element_burst(x, y, element, n=4)                 baked element particles (fx_part)
    fx.slash(x, y)                  baked 40x40 claw slash centered on (x, y)
    fx.sprite(name, x, y, frames=None, hold=1, center=True)   play a baked asset once (fx_spark, fx_heal, fx_curl, fx_bite)
    fx.clear(scr=None)              drop everything (restores the rects if scr is given)

    Shake(amp=2, frames=4)          .start()  .step() once per frame  .offset -> (dx, dy)  .active
    HitStop(frames=3)               .start(frames)  .frozen() -> True (and consumes one frame) while the scene must pause
    TintFlash()                     .white(frames=2) .red(frames=2) .triple(frames=1)  .step()  .tint -> color or None
                                    pass `tint=flash.tint` to scr.blit / scr.asset for the flashing sprite
"""

import random

from . import theme as T



class _Item:
    last_key = None
    last_rect = None
    dead = False

    def step(self):
        raise NotImplementedError

    def key(self):
        raise NotImplementedError

    def rect(self, scr):
        raise NotImplementedError

    def paint(self, scr):
        raise NotImplementedError


class _FloatText(_Item):
    def __init__(self, x, y, text, color, font, scale, rise, frames, shadow, flash=None):
        self.x, self.y, self.text, self.color, self.font, self.scale = x, y, text, color, font, scale
        self.rise, self.frames, self.shadow, self.flash = rise, frames, shadow, flash
        self.age = 0

    def step(self):
        self.age += 1
        self.dead = self.age > self.frames

    def _dy(self):
        return -(self.rise * min(self.age, self.frames)) // self.frames

    def _color(self):
        if self.flash:
            return self.flash[(self.age // 2) % len(self.flash)] if self.age < 6 else self.color
        return self.color

    def key(self):
        return (self._dy(), self._color())

    def rect(self, scr):
        w, h = scr.measure(self.text, self.font, self.scale)
        return (self.x - w // 2 - 1, self.y + self._dy() - 1, w + 2, h + (3 if self.shadow is not None else 2))

    def paint(self, scr):
        w, h = scr.measure(self.text, self.font, self.scale)
        x, y = self.x - w // 2, self.y + self._dy()
        if self.shadow is not None:
            scr.text(x, y + 2, self.text, self.shadow, None, self.font, self.scale)
        scr.text(x, y, self.text, self._color(), None, self.font, self.scale)


class _Spark(_Item):
    def __init__(self, x, y, vx, vy, color, life):
        self.x, self.y, self.vx, self.vy, self.color, self.life = x, y, vx, vy, color, life
        self.age = 0

    def step(self):
        self.age += 1
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.5 if self.age > self.life // 2 else 0
        self.dead = self.age >= self.life

    def key(self):
        return (int(self.x), int(self.y))

    def rect(self, scr):
        return (int(self.x), int(self.y), 2, 2)

    def paint(self, scr):
        scr.fill_rect(int(self.x), int(self.y), 2, 2, self.color)


class _Anim(_Item):
    """A baked asset played once, hold frames per image."""

    def __init__(self, asset, frames, x, y, hold, element=None):
        self.asset, self.frames, self.x, self.y, self.hold = asset, frames, x, y, hold
        self.age = 0

    def step(self):
        self.age += 1
        self.dead = self.age >= len(self.frames) * self.hold

    def _frame(self):
        return self.frames[min(len(self.frames) - 1, self.age // self.hold)]

    def key(self):
        return self._frame()

    def rect(self, scr):
        return (self.x, self.y, self.asset.w, self.asset.h)

    def paint(self, scr):
        scr.blit(self.asset, self._frame(), self.x, self.y)


class Effects:
    MAX_ITEMS = 16

    def __init__(self, restore=None):
        self.restore = restore or (lambda scr, r: scr.fill_rect(r[0], r[1], r[2], r[3], T.GROUND))
        self.items = []
        self.rng = random.Random(7)

    @property
    def busy(self):
        return bool(self.items)

    # -- spawners
    def _add(self, item):
        if len(self.items) >= self.MAX_ITEMS:
            # drop the oldest sparks first, they are the cheapest to lose
            for i, it in enumerate(self.items):
                if isinstance(it, _Spark):
                    it.dead = True
                    break
            else:
                self.items[0].dead = True
        self.items.append(item)

    def float_text(self, x, y, text, color, font=T.BODY, scale=1, rise=14, frames=14, shadow=T.NIGHT0):
        self._add(_FloatText(x, y, text, color, font, scale, rise, frames, shadow))

    def damage(self, x, y, value, big=False, heal=False, crit=False):
        if heal:
            self._add(_FloatText(x, y, "+%d" % value, T.HEAL, T.NUM, 1, 14, 16, T.NIGHT0))
            return
        text = str(value)
        if big or crit:
            self._add(_FloatText(x, y, text, T.DAMAGE, T.NUM, 2, 10, 20, T.AMBER1, flash=(T.GOLD4, T.MOON, T.GOLD4)))
        else:
            self._add(_FloatText(x, y, text, T.DAMAGE, T.NUM, 1, 14, 14, T.AMBER1))

    def chain_text(self, x, y, text, tier):
        scale = 1 if tier <= 1 else 2
        self._add(_FloatText(x, y, text, T.tier_color(tier), T.BODY, scale, 10, 16, T.NIGHT0))

    def sparks(self, x, y, colors, n=5, up=(12, 24), life=6):
        for _ in range(n):
            rise = self.rng.randint(*up)
            vy = -rise / life
            vx = self.rng.uniform(-1.6, 1.6)
            self._add(_Spark(x + self.rng.randint(-6, 6), y, vx, vy, self.rng.choice(colors), life))

    def element_burst(self, x, y, element, n=4):
        a = T.asset("fx_part")
        for i in range(n):
            ox = x + self.rng.randint(-14, 10)
            oy = y + self.rng.randint(-10, 6)
            self._add(_Anim(a, [element * 3, element * 3 + 1, element * 3 + 2], ox, oy, 1 + i % 2))

    def slash(self, x, y):
        a = T.asset("fx_slash")
        self._add(_Anim(a, [0, 1, 2, 3], x - a.w // 2, y - a.h // 2, 1))

    def sprite(self, name, x, y, frames=None, hold=1, center=True):
        a = T.asset(name)
        frames = list(frames if frames is not None else range(a.frames))
        self._add(_Anim(a, frames, x - a.w // 2 if center else x, y - a.h // 2 if center else y, hold))

    # -- frame loop
    def update(self):
        for it in self.items:
            it.step()

    def draw(self, scr):
        if not self.items:
            return
        restores = []
        paints = []
        for it in self.items:
            if it.dead:
                if it.last_rect is not None:
                    restores.append(it.last_rect)
                continue
            key = it.key()
            if key == it.last_key:
                continue
            if it.last_rect is not None:
                restores.append(it.last_rect)
            paints.append(it)
        for r in restores:
            self.restore(scr, r)
        for it in paints:
            it.last_key = it.key()
            it.last_rect = it.rect(scr)
            it.paint(scr)
        # an item that did not repaint but overlaps a restored rect must repaint too
        if restores:
            for it in self.items:
                if it.dead or it in paints or it.last_rect is None:
                    continue
                if any(_overlap(it.last_rect, r) for r in restores):
                    it.paint(scr)
        self.items = [it for it in self.items if not it.dead]

    def clear(self, scr=None):
        if scr is not None:
            for it in self.items:
                if it.last_rect is not None:
                    self.restore(scr, it.last_rect)
        self.items = []


def _overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


# --------------------------------------------------------------------------- controllers (no drawing)
class Shake:
    """Screen shake: .offset is the (dx, dy) to add to everything inside the shaken rect this frame."""

    _PATTERN = ((1, 0), (-1, 1), (1, -1), (-1, 0))

    def __init__(self, amp=2, frames=4):
        self.amp, self.frames = amp, frames
        self._left = 0
        self._i = 0

    def start(self, amp=None, frames=None):
        if amp is not None:
            self.amp = amp
        if frames is not None:
            self.frames = frames
        self._left = self.frames
        self._i = 0

    @property
    def active(self):
        return self._left > 0

    @property
    def offset(self):
        if self._left <= 0:
            return (0, 0)
        dx, dy = self._PATTERN[self._i % 4]
        return (dx * self.amp, dy * self.amp)

    def step(self):
        if self._left > 0:
            self._left -= 1
            self._i += 1


class HitStop:
    """Freeze the animation for a few frames on a big hit: `if hitstop.frozen(): return` at the top of update."""

    def __init__(self, frames=3):
        self.frames = frames
        self._left = 0

    def start(self, frames=None):
        self._left = frames if frames is not None else self.frames

    def frozen(self):
        if self._left > 0:
            self._left -= 1
            return True
        return False


class TintFlash:
    """Sequence of flat tint colors for a sprite: pass `tint=flash.tint` (None = normal). Call step() per frame."""

    def __init__(self):
        self._seq = []

    def _start(self, colors, hold):
        self._seq = [c for c in colors for _ in range(hold)]

    def white(self, frames=2):
        self._start([T.MOON], frames)

    def red(self, frames=2):
        self._start([T.RED], frames)

    def triple(self, frames=1):
        """Gold, moon, gold, moon, gold, moon: the 3 flashes of a big hit."""
        self._start([T.GOLD4, T.MOON] * 3, frames)

    @property
    def tint(self):
        return self._seq[0] if self._seq else None

    @property
    def active(self):
        return bool(self._seq)

    def step(self):
        if self._seq:
            self._seq.pop(0)
