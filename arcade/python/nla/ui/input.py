"""Game input (GDD 6.1): the joystick as a 4-way d-pad with key repeat, A/B/C press edges, cursor helpers.

API:

    inp = Input()                    # owned by the App; scenes receive it as `ctl` in update(ctl, dt)
    ctl.dx, ctl.dy                   # -1 / 0 / +1: a d-pad STEP that fires this frame (press, then repeats)
    ctl.a, ctl.b, ctl.c              # True only on the frame the button went down
    ctl.held_a / held_b / held_c     # level state
    ctl.moved                        # True when dx or dy is non-zero this frame
    ctl.any                          # any step or button edge this frame
    ctl.clear()                      # swallow input (the App does this on every scene change)

Stick rules: the larger axis is the d-pad direction when its deflection is above 50 %; the other axis is
ignored (diagonals never fire); once a direction is held it stays held until the axis drops below 30 %.
A held direction fires once at the start, again after 300 ms, then every 120 ms. Direction changes fire
immediately. B never commits anything and C never changes state (GDD 6.2): scenes decide, this just reports.

Cursor helpers (all wrap by default; GDD: "every cursor row wraps"):

    wrap(i, d, n)                         -> (i + d) % n
    step(i, d, n, wrap=True)              -> new index in a row of n items (clamped if wrap=False)
    grid_step(i, dx, dy, cols, n)         -> new index in a row-major grid of n items (last row may be short)
    Nav(sizes, xs=None)                   multi-row cursor: Nav([6 + 1, 6]) is the Spread screen (6 slots + Fight, Box)
        nav.row, nav.col                  current position
        nav.move(dx, dy) -> bool          True when the cursor moved
        nav.jump(row, col)                set position, clamped
        nav.set_size(row, n)              resize a row (the cursor is clamped)
        xs: optional list (per row) of center x; vertical moves then land on the nearest x in the new row
"""

import engine

DIR_ON = 0.5          # deflection that starts a direction
DIR_OFF = 0.3         # deflection below which a held direction is released
REPEAT_DELAY = 0.300  # seconds until the first repeat
REPEAT_EVERY = 0.120  # seconds between repeats


_INJECT = {"a": None, "b": None, "c": None, "menu": None,
           "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class Input:
    def __init__(self):
        self.dx = self.dy = 0
        self.a = self.b = self.c = False
        self.held_a = self.held_b = self.held_c = False
        self.raw = None
        self._dir = (0, 0)
        self._timer = 0.0
        self._mute = False
        self._pending = []      # synthesized inputs waiting for the next update()
        self.menu = False       # True for a frame when a "menu" input was injected (long-B equivalent)

    @property
    def moved(self):
        return bool(self.dx or self.dy)

    @property
    def any(self):
        return bool(self.dx or self.dy or self.a or self.b or self.c)

    def clear(self):
        """Swallow the current frame's input and require the stick to return to center (or buttons to release)."""
        self.dx = self.dy = 0
        self.a = self.b = self.c = False
        self._mute = True

    def inject(self, name):
        """Queue a synthesized input (pointer clicks on the PC) for the next update(): "a", "b", "c", "up", "down",
        "left", "right" or "menu". It lands like a fresh button press / d-pad step (the tutorial gate still applies);
        "menu" sets `self.menu` for that frame, the same request a long B hold makes."""
        if name in _INJECT:
            self._pending.append(name)

    def update(self, ctl, dt):
        """Feed one frame of engine.Controls (plus anything inject()ed since the last frame)."""
        self._poll(ctl, dt)
        self.menu = False
        pending, self._pending = self._pending, []
        for name in pending:
            if name == "menu":
                self.menu = True
            elif name in "abc":
                setattr(self, name, True)
            else:
                self.dx, self.dy = _INJECT[name]

    def _poll(self, ctl, dt):
        self.raw = ctl
        held = ctl.held
        pressed = ctl.pressed
        self.held_a, self.held_b, self.held_c = bool(held & engine.A), bool(held & engine.B), bool(held & engine.C)
        self.a, self.b, self.c = bool(pressed & engine.A), bool(pressed & engine.B), bool(pressed & engine.C)
        self.dx = self.dy = 0
        want = self._direction(ctl.x, ctl.y)
        if self._mute:
            # after clear(): ignore the stick until it is neutral, buttons only count as fresh presses
            if want == (0, 0):
                self._mute = False
            self._dir = want if want != (0, 0) else (0, 0)
            self._timer = REPEAT_DELAY
            return
        if want == (0, 0):
            self._dir = want
            return
        if want != self._dir:
            self._dir = want
            self._timer = REPEAT_DELAY
            self.dx, self.dy = want
            return
        self._timer -= dt
        if self._timer <= 0:
            self._timer += REPEAT_EVERY
            if self._timer <= 0:
                self._timer = REPEAT_EVERY
            self.dx, self.dy = want

    def _direction(self, x, y):
        ax, ay = abs(x), abs(y)
        held = self._dir
        if held != (0, 0):
            # keep a held direction while its axis stays the main one and above the release threshold
            if held[0] and ax >= DIR_OFF and ax >= ay and (x > 0) == (held[0] > 0):
                return held
            if held[1] and ay >= DIR_OFF and ay >= ax and (y > 0) == (held[1] > 0):
                return held
        if ax > ay and ax > DIR_ON:
            return (1 if x > 0 else -1, 0)
        if ay > ax and ay > DIR_ON:
            return (0, 1 if y > 0 else -1)
        return (0, 0)


# --------------------------------------------------------------------------- cursor helpers
def wrap(i, d, n):
    return (i + d) % n if n else 0


def step(i, d, n, wrap=True):
    if n <= 0:
        return 0
    if wrap:
        return (i + d) % n
    return max(0, min(n - 1, i + d))


def grid_step(i, dx, dy, cols, n, wrap=True):
    """Move inside a row-major grid of n items with `cols` columns. Rows and columns wrap; a short last row
    wraps within its own length horizontally and vertical moves skip to the nearest existing item."""
    if n <= 0:
        return 0
    rows = (n + cols - 1) // cols
    r, c = divmod(i, cols)
    if dx:
        width = min(cols, n - r * cols)
        c = step(c, dx, width, wrap)
    if dy:
        r = step(r, dy, rows, wrap)
        c = min(c, n - r * cols - 1)
    return r * cols + c


class Nav:
    """Cursor over rows of different lengths (Spread: row 0 = slots + Fight, row 1 = Box)."""

    def __init__(self, sizes, xs=None, row=0, col=0):
        self.sizes = list(sizes)
        self.xs = xs
        self.row = row
        self.col = col
        self._clamp()

    def _clamp(self):
        self.row = max(0, min(len(self.sizes) - 1, self.row))
        self.col = max(0, min(max(0, self.sizes[self.row] - 1), self.col))

    def set_size(self, row, n):
        self.sizes[row] = n
        self._clamp()

    def jump(self, row, col):
        self.row, self.col = row, col
        self._clamp()

    def move(self, dx, dy):
        before = (self.row, self.col)
        if dx:
            self.col = wrap(self.col, dx, self.sizes[self.row])
        if dy:
            old_row = self.row
            for _ in range(len(self.sizes)):       # skip empty rows
                self.row = wrap(self.row, dy, len(self.sizes))
                if self.sizes[self.row]:
                    break
            if self.row != old_row:
                self.col = self._nearest(old_row, self.col, self.row)
        self._clamp()
        return (self.row, self.col) != before

    def _nearest(self, old_row, col, new_row):
        if self.xs is None:
            return min(col, max(0, self.sizes[new_row] - 1))
        x = self.xs[old_row][col]
        candidates = self.xs[new_row][:self.sizes[new_row]]
        return min(range(len(candidates)), key=lambda k: abs(candidates[k] - x))
