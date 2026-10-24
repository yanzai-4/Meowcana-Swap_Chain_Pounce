"""The game object the engine Runner drives: scene stack, transitions, modal overlays, the `busy` flag.

API:

    app = App(first_scene)                 Runner(app, bridge): needs .required, .update(controls, dt), .draw(screen, full)
    app.push(scene)   app.pop(result=None)   app.switch(scene)   app.reset(scene)
                                           change the scene with the card-flip wipe (pass transition=False for a cut).
                                           push keeps the scene below alive (it is redrawn in full when you pop),
                                           switch replaces the top, reset drops the whole stack (e.g. back to Title).
    app.open(overlay, on_close=None)       modal layer drawn above the scene, input goes to it
    app.say(lines, on_done=None)           Dialogue overlay (typewriter, portrait, A next / B skip)
    app.confirm(question, on_yes, on_no=None, yes="Yes", no="No")   default No
    app.card_info(card)                    full-screen Card Info for a rules Card (B or C closes)
    app.busy                               True during transitions, full redraws and while the scene says busy
    app.time                               seconds since start (idle twinkles etc.)

Scene interface (subclass `Scene`; scenes never import each other, flow.py wires them with `done` callbacks):

    class MyScene(Scene):
        def __init__(self, ..., done=None)   # call self.finish(result) when the scene is over
        def enter(self, app)                 # called once when it becomes active (self.app is set)
        def resume(self, result)             # a scene pushed above this one was popped
        def update(self, ctl, dt)            # ctl is nla.ui.input.Input (dx/dy steps, a/b/c edges)
        def draw(self, scr, full)            # full=True: repaint EVERY pixel (start with a ground fill or backdrop);
                                             # otherwise draw only what changed
        def restore(self, scr, rect)         # an overlay covering `rect` closed; default = draw(scr, True)
        busy = False                         # set True while animating heavy stuff (battle playback, shake)

Frame rules: a scene change runs behind the wipe (8 columns of 60 px fast-filled with night1, center out,
then one blink of the cat-eye moon), then the new scene draws once with full=True. Idle frames should send
<= 45 ms of drawing, animation frames <= 70 ms (see demo-plan.md section 2); the simulator logs both.
"""

import engine

from . import theme as T
from .input import Input
from .widgets import Confirm, Dialogue, card_info

COLUMN_W = 60
COLUMN_ORDER = ((3, 4), (2, 5), (1, 6), (0, 7))     # center out, a pair per frame


class Scene:
    """Base class for every screen. Override what you need."""

    busy = False

    def __init__(self, done=None):
        self.done = done
        self.app = None

    def finish(self, result=None):
        if self.done:
            self.done(result)

    def enter(self, app):
        self.app = app

    def exit(self):
        pass

    def resume(self, result):
        pass

    def update(self, ctl, dt):
        pass

    def draw(self, scr, full):
        pass

    def restore(self, scr, rect):
        self.draw(scr, True)


class App:
    required = engine.BUTTONS | engine.JOYSTICK

    def __init__(self, scene=None):
        self.stack = []
        self.overlays = []          # (overlay, on_close)
        self.input = Input()
        self.busy = False
        self.kind = "idle"          # idle | anim | full | transition (what the last draw() was)
        self.time = 0.0
        self._trans = None          # {"step": int, "apply": callable}
        self._need_full = True
        self._restore = []          # rects of overlays that closed this frame
        if scene is not None:
            self._apply(lambda: self._do_push(scene))

    # ------------------------------------------------------------------ scene changes
    @property
    def scene(self):
        return self.stack[-1] if self.stack else None

    def push(self, scene, transition=True):
        self._change(lambda: self._do_push(scene), transition)

    def pop(self, result=None, transition=True):
        self._change(lambda: self._do_pop(result), transition)

    def switch(self, scene, transition=True):
        self._change(lambda: self._do_switch(scene), transition)

    def reset(self, scene, transition=True):
        self._change(lambda: self._do_reset(scene), transition)

    def _change(self, fn, transition):
        if self._trans is not None:          # a wipe is already running: chain, newest wins
            old = self._trans["apply"]
            self._trans["apply"] = lambda: (old(), fn())
            return
        if transition and self.stack:
            self._trans = {"step": 0, "apply": fn}
        else:
            self._apply(fn)

    def _apply(self, fn):
        fn()
        self.overlays.clear()
        self.input.clear()
        self._need_full = True

    def _do_push(self, scene):
        self.stack.append(scene)
        scene.enter(self)

    def _do_pop(self, result):
        old = self.stack.pop()
        old.exit()
        if self.stack:
            self.stack[-1].resume(result)

    def _do_switch(self, scene):
        if self.stack:
            self.stack.pop().exit()
        self._do_push(scene)

    def _do_reset(self, scene):
        while self.stack:
            self.stack.pop().exit()
        self._do_push(scene)

    # ------------------------------------------------------------------ overlays
    def open(self, overlay, on_close=None):
        overlay.attach(self)
        self.overlays.append((overlay, on_close))
        self.input.clear()

    def say(self, lines, on_done=None):
        self.open(Dialogue(lines, on_done))

    def confirm(self, question, on_yes, on_no=None, yes="Yes", no="No"):
        self.open(Confirm(question, on_yes, on_no, yes, no))

    def card_info(self, card):
        self.open(card_info(card))

    # ------------------------------------------------------------------ Runner interface
    def update(self, controls, dt):
        self.time += dt
        self.input.update(controls, dt)
        if self._trans is not None:
            return                       # input is ignored while the wipe runs
        if self.overlays:
            entry = self.overlays[-1]
            overlay, on_close = entry
            overlay.update(self.input, dt)
            if overlay.closed:
                self.overlays.remove(entry)      # a close callback may already have opened another overlay
                self._restore.append(overlay)
                self.input.clear()
                if on_close:
                    on_close(overlay.result)
            return
        if self.stack:
            self.stack[-1].update(self.input, dt)

    def draw(self, scr, full):
        self.busy = False
        self.kind = "idle"
        if full and self._trans is not None:
            self._apply(self._trans["apply"])
            self._trans = None
        if self._trans is not None:
            self._draw_transition(scr)
            return
        scene = self.scene
        if scene is None:
            return
        if full or self._need_full:
            self._need_full = False
            self.busy = True
            self.kind = "full"
            scene.draw(scr, True)
            for overlay, _ in self.overlays:
                overlay.draw(scr, True)
            self._restore.clear()
            return
        if self._restore:
            closed, self._restore = self._restore, []
            self.busy = True
            self.kind = "full"
            if any(o.full_screen for o in closed):
                scene.draw(scr, True)
            else:
                for o in closed:
                    scene.restore(scr, o.rect)
            for overlay, _ in self.overlays:
                overlay.draw(scr, True)
            return
        if self.overlays:
            overlay = self.overlays[-1][0]
            overlay.draw(scr, False)
            if overlay.busy:
                self.busy = True
                self.kind = "overlay"
            return
        scene.draw(scr, False)
        if scene.busy:
            self.busy = True
            self.kind = "anim"

    def _draw_transition(self, scr):
        t = self._trans
        step = t["step"]
        self.busy = True
        self.kind = "transition"
        if step < len(COLUMN_ORDER):
            for col in COLUMN_ORDER[step]:
                scr.fill_rect(col * COLUMN_W, 0, COLUMN_W, T.SCREEN_H, T.GROUND)
        elif step == len(COLUMN_ORDER):
            eye = T.asset("ui_moon_eye")
            scr.blit(eye, 0, (T.SCREEN_W - eye.w) // 2, (T.SCREEN_H - eye.h) // 2, bg=T.GROUND)
        elif step == len(COLUMN_ORDER) + 1:
            eye = T.asset("ui_moon_eye")
            scr.blit(eye, 2, (T.SCREEN_W - eye.w) // 2, (T.SCREEN_H - eye.h) // 2, bg=T.GROUND)
        else:
            fn = t["apply"]
            self._trans = None
            self._apply(fn)
            self.draw(scr, False)
            return
        t["step"] += 1
