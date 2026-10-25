"""Meowcana on PC: the real game (nla.flow.make) in a pygame-ce window with mouse, keyboard and sound.

    python pc/play.py                              # 960x640 window, saves in %APPDATA%/Meowcana
    python pc/play.py --scale 3 --fullscreen --mute
    python pc/play.py --script "wait 1; click 240 160; wait 1; shot tutorial" --shots build/shots/pc/

The game code is untouched: it draws through the engine's op stream, which tools/sim.py decodes into a persistent
480x320 framebuffer (no device cost throttling); once per frame that image is scaled by an integer factor into the
window. Mouse events become `App.pointer(x, y, kind)` calls in game coordinates (docs/pc-version.md); sounds go to
nla.sfx through pc/audio.py.

Keys: arrows / WASD stick; Enter, Space = A (Confirm); Backspace = B (Back); I, Tab = C (Info); Esc or M = pause Menu
(or Back inside an overlay / the Menu); F fast-forward in battle; F11 fullscreen; N mute; - / = volume.
Mouse: move hover, left click = Confirm, right click = Back, middle click = Info, wheel up/down.

--script runs headless (SDL dummy video and audio) on a deterministic virtual clock; commands are separated by ';'
(game coordinates, mouse events are synthesized at the matching window pixels so the real mapping is exercised):

    move X Y | click X Y | right X Y | middle X Y | wheel up|down [X Y] | drag X1 Y1 X2 Y2
    key NAME [secs]   tap or hold a key (enter space backspace i tab esc m f up down left right w a s d f11 n)
    wait SECS         run the game for SECS virtual seconds
    shot NAME         save the window image to <shots>/NAME.png      scene   print the active scene and overlays
    expect SceneName  exit 1 unless that scene is active             sfx     print the sounds the mixer played
    size W H          resize the window (resizing / letterbox checks)
"""

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(HERE))

TITLE = "Meowcana: Swap. Chain. Pounce."
FPS = 30
W, H = 480, 320


def parse():
    ap = argparse.ArgumentParser(description="Play Meowcana on PC")
    ap.add_argument("--scale", type=int, default=2, help="initial window scale (default 2 = 960x640)")
    ap.add_argument("--fullscreen", action="store_true")
    ap.add_argument("--mute", action="store_true", help="start with sound muted")
    ap.add_argument("--data", help="save folder (default %%APPDATA%%/Meowcana, or NLA_DATA_DIR)")
    ap.add_argument("--seed", type=int, help="fixed random seed (default: random each launch)")
    ap.add_argument("--script", help="headless scripted session, see the module doc")
    ap.add_argument("--shots", help="folder for `shot` PNGs in --script mode")
    return ap.parse_args()


def data_dir(args):
    if args.data:
        return args.data
    if os.environ.get("NLA_DATA_DIR"):
        return os.environ["NLA_DATA_DIR"]
    if args.script:
        return tempfile.mkdtemp(prefix="meowcana_script_")        # scripted runs never touch real saves
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "Meowcana")


def ensure_assets():
    if not (ROOT / "build" / "sim_assets.bin").exists():
        subprocess.run([sys.executable, str(ROOT / "tools" / "pack_assets.py")], check=True, cwd=ROOT)


# ======================================================================================= window
class Window:
    """The pygame window: integer-scaled, letterboxed, F11 fullscreen; maps window pixels to game coordinates."""

    def __init__(self, pygame, scale, fullscreen):
        self.pg = pygame
        self.windowed = (W * scale, H * scale)
        self.fullscreen = False
        self.screen = None
        self.surface = None
        self._open(fullscreen)

    def _open(self, fullscreen):
        pg = self.pg
        if fullscreen:
            self.screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
        else:
            self.screen = pg.display.set_mode(self.windowed, pg.RESIZABLE)
        self.fullscreen = fullscreen
        self.screen.fill((0, 0, 0))
        pg.display.flip()

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.windowed = self.screen.get_size()
        self._open(not self.fullscreen)

    def resize(self, w, h):
        self.windowed = (w, h)
        self._open(False)

    def layout(self):
        """(scale, x, y, w, h) of the game image inside the window. Integer scale; fractional below 1x."""
        ww, wh = self.screen.get_size()
        s = min(ww / W, wh / H)
        s = int(s) if s >= 1 else s
        w, h = int(W * s), int(H * s)
        return s, (ww - w) // 2, (wh - h) // 2, w, h

    def to_game(self, px, py, clamp=False):
        """Window pixel -> game (x, y), or None outside the image (clamp=True pulls it to the nearest edge)."""
        s, ox, oy, w, h = self.layout()
        x, y = int((px - ox) / s), int((py - oy) / s)
        if 0 <= x < W and 0 <= y < H:
            return x, y
        return (min(W - 1, max(0, x)), min(H - 1, max(0, y))) if clamp else None

    def to_window(self, x, y):
        s, ox, oy, _, _ = self.layout()
        return int(ox + x * s + s / 2), int(oy + y * s + s / 2)

    def present(self, image):
        pg = self.pg
        s, ox, oy, w, h = self.layout()
        frame = pg.image.frombuffer(image.tobytes(), (W, H), "RGB")
        if (w, h) != (W, H):
            frame = pg.transform.scale(frame, (w, h)) if s >= 1 else pg.transform.smoothscale(frame, (w, h))
        if (w, h) != self.screen.get_size():
            self.screen.fill((0, 0, 0))
        self.screen.blit(frame, (ox, oy))
        pg.display.flip()


# ======================================================================================= input
class Keys:
    """Keyboard -> the raw button/stick values the engine reads. A tap shorter than a frame is latched."""

    def __init__(self, pg):
        k = pg
        self.buttons = {}
        for keys, bit in (((k.K_RETURN, k.K_KP_ENTER, k.K_SPACE), 1), ((k.K_i, k.K_TAB), 4)):
            for key in keys:
                self.buttons[key] = bit
        self.stick = {k.K_LEFT: (-1, 0), k.K_a: (-1, 0), k.K_RIGHT: (1, 0), k.K_d: (1, 0),
                      k.K_UP: (0, 1), k.K_w: (0, 1), k.K_DOWN: (0, -1), k.K_s: (0, -1)}   # raw y is up-positive
        self.down = set()
        self.latch = 0

    def press(self, key):
        self.down.add(key)
        self.latch |= self.buttons.get(key, 0)

    def release(self, key):
        self.down.discard(key)

    def clear(self):
        self.down.clear()
        self.latch = 0

    def read(self):
        mask = self.latch
        x = y = 0
        for key in self.down:
            mask |= self.buttons.get(key, 0)
            dx, dy = self.stick.get(key, (0, 0))
            x, y = x + dx, y + dy
        self.latch = 0
        return mask, max(-1, min(1, x)) * 127, max(-1, min(1, y)) * 127


class Bridge:
    """The two Bridge methods the engine calls: inputs come from Keys, op bytes go to the simulator's Device."""

    def __init__(self, device, keys, engine, clock):
        self.device, self.keys, self.engine, self.clock = device, keys, engine, clock
        self.dirty = True
        self.t0 = clock.monotonic()

    def now(self):
        return self.clock.monotonic() - self.t0

    def raw(self):
        mask, x, y = self.keys.read()
        zero = self.engine.MOVEMENT_ZERO_MG
        return json.dumps({"video": 0, "epoch": 0, "connected": 7, "buttons": mask, "x": x, "y": y,
                           "ax": zero[0], "ay": zero[1], "az": zero[2]})

    def call(self, name, payload=None):
        if name == "arcade_read_inputs":
            return self.raw()
        if name != "arcade_draw_ops":
            raise ValueError(f"unknown bridge method {name}")
        self.device.apply(bytes(payload))
        self.dirty = True
        return self.raw()


# ======================================================================================= player
class Player:
    """Owns game, runner, window, audio and keys; `handle()` turns pygame events into pointer / key input."""

    def __init__(self, args, headless):
        import pygame
        self.pg = pygame
        import engine
        import sim
        from nla import flow, sfx
        self.engine, self.sfx = engine, sfx
        ensure_assets()
        pygame.init()
        pygame.display.set_caption(TITLE)
        self._icon()
        if headless:
            self.clock = sim.Clock()
        else:
            import time
            self.clock = time
        engine.time = self.clock
        random.seed(args.seed if args.seed is not None else (1 if headless else None))
        self.data = data_dir(args)
        os.makedirs(self.data, exist_ok=True)
        if sys.stdout is None:                     # pythonw: keep prints and tracebacks in a log
            sys.stdout = sys.stderr = open(Path(self.data) / "game.log", "w", buffering=1)
        os.environ["NLA_DATA_DIR"] = self.data
        self.window = Window(pygame, max(1, args.scale), args.fullscreen)
        from audio import Audio
        self.audio = Audio(HERE / "sfx", Path(self.data) / "settings.json", clock=self.clock.monotonic)
        if args.mute:
            self.audio.settings["muted"] = True
        sfx.install(self.audio)
        self.library = sim.Library()
        self.device = sim.Device(self.library)
        self.keys = Keys(pygame)
        self.bridge = Bridge(self.device, self.keys, engine, self.clock)
        self.game = flow.make(self.data, pc=True)
        self.runner = engine.Runner(self.game, self.bridge, fps=FPS + 3)
        self.quit = False
        self.hover = None
        self.mouse_log = 0
        self.expose = True

    def _icon(self):
        try:
            icon = self.pg.image.load(str(ROOT / "assets" / "raw" / "characters" / "domino" / "portrait.png"))
            self.pg.display.set_icon(self.pg.transform.scale(icon.convert_alpha(), (64, 64)))
        except (self.pg.error, FileNotFoundError):
            pass

    # -- one game frame
    def frame(self):
        self.runner.step()
        if self.runner.error is not None:
            raise RuntimeError(f"game raised {self.runner.error!r} (traceback in game.log / above)")
        if self.bridge.dirty or self.expose:
            self.window.present(self.device.img)
            self.bridge.dirty = self.expose = False

    # -- events
    def pointer(self, px, py, kind, clamp=False):
        pos = self.window.to_game(px, py, clamp)
        if pos is None:
            return
        if kind == "move":
            if pos == self.hover:
                return
            self.hover = pos
        self.game.pointer(pos[0], pos[1], kind)

    def key(self, key, down):
        pg = self.pg
        if down:
            if key == pg.K_F11:
                self.window.toggle_fullscreen()
                self.expose = True
            elif key in (pg.K_ESCAPE, pg.K_m):
                self.game.pc_key("esc")
            elif key == pg.K_BACKSPACE:
                self.game.pc_key("back")
            elif key == pg.K_f:
                scene = self.game.scene
                if type(scene).__name__ == "BattleScene" and scene.phase != "result":     # fast-forward = speed
                    self.game.input.inject("a")
            elif key == pg.K_n:
                self.audio.toggle_mute()
            elif key in (pg.K_MINUS, pg.K_KP_MINUS):
                self.audio.change_volume(-0.1)
            elif key in (pg.K_EQUALS, pg.K_PLUS, pg.K_KP_PLUS):
                self.audio.change_volume(0.1)
            else:
                self.keys.press(key)
        else:
            self.keys.release(key)

    def handle(self, e):
        pg = self.pg
        if e.type == pg.QUIT:
            self.quit = True
        elif e.type == pg.KEYDOWN:
            self.key(e.key, True)
        elif e.type == pg.KEYUP:
            self.key(e.key, False)
        elif e.type == pg.MOUSEMOTION:
            self.pointer(*e.pos, "move")
        elif e.type == pg.MOUSEBUTTONDOWN:
            if self.mouse_log < 16:                # confirm the real button numbering in game.log
                self.mouse_log += 1
                print(f"mouse: button {e.button} down at {tuple(e.pos)} touch={getattr(e, 'touch', None)}", flush=True)
            kind = {1: "down", 2: "middle", 3: "right"}.get(e.button)     # 4/5 are the wheel (MOUSEWHEEL below)
            if kind:
                self.pointer(*e.pos, kind, clamp=kind != "down")      # Back / Info also work on the letterbox bars
        elif e.type == pg.MOUSEBUTTONUP:
            if self.mouse_log < 16:
                self.mouse_log += 1
                print(f"mouse: button {e.button} up at {tuple(e.pos)}", flush=True)
            if e.button == 1:
                self.pointer(*e.pos, "up", clamp=True)
        elif e.type == pg.MOUSEWHEEL and e.y:
            x, y = pg.mouse.get_pos() if self.hover is None else self.window.to_window(*self.hover)
            self.pointer(x, y, "wheel_up" if e.y > 0 else "wheel_down")
        elif e.type in (pg.VIDEOEXPOSE, pg.WINDOWRESTORED, pg.WINDOWSIZECHANGED, pg.WINDOWSHOWN):
            self.expose = True
        elif e.type == pg.WINDOWFOCUSLOST:
            self.keys.clear()

    def run(self):
        pg = self.pg
        while not self.quit:
            for e in pg.event.get():
                self.handle(e)
            self.frame()
        self.audio.close()
        pg.quit()


# ======================================================================================= script
class Script:
    """Replays a command string against a Player on the virtual clock (see the module doc)."""

    def __init__(self, player, shots):
        self.p = player
        self.pg = player.pg
        self.shots = Path(shots) if shots else None
        if self.shots:
            self.shots.mkdir(parents=True, exist_ok=True)

    def event(self, kind, **kw):
        self.p.handle(self.pg.event.Event(kind, **kw))

    def mouse(self, kind, x, y, button=1):
        px, py = self.p.window.to_window(int(x), int(y))
        if kind == "move":
            self.event(self.pg.MOUSEMOTION, pos=(px, py), rel=(0, 0), buttons=(0, 0, 0))
        elif kind == "down":
            self.event(self.pg.MOUSEBUTTONDOWN, pos=(px, py), button=button)
        else:
            self.event(self.pg.MOUSEBUTTONUP, pos=(px, py), button=button)

    def frames(self, n):
        for _ in range(n):
            self.p.frame()

    def wait(self, seconds):
        end = self.p.clock.monotonic() + seconds
        while self.p.clock.monotonic() < end:
            self.p.frame()

    KEY_ALIASES = {"enter": "RETURN", "esc": "ESCAPE", "space": "SPACE", "tab": "TAB", "backspace": "BACKSPACE"}

    def key(self, name, secs=0.1):
        alias = self.KEY_ALIASES.get(name.lower())
        code = getattr(self.pg, "K_" + (alias or (name.upper() if len(name) > 1 else name.lower())))
        self.event(self.pg.KEYDOWN, key=code)
        self.wait(secs)
        self.event(self.pg.KEYUP, key=code)
        self.frames(1)

    def scene_name(self):
        g = self.p.game
        over = ",".join(type(o).__name__ for o, _ in g.overlays)
        return type(g.scene).__name__ + (f" +[{over}]" if over else "")

    def run(self, text):
        p, pg = self.p, self.pg
        self.frames(2)
        for raw in [c.strip() for c in text.split(";") if c.strip()]:
            cmd, *a = raw.split()
            print(f"[{p.bridge.now():6.2f}s] {raw}", flush=True)
            if cmd == "move":
                self.mouse("move", *a)
                self.frames(1)
            elif cmd in ("click", "right", "middle"):
                x, y = a[:2]
                self.mouse("move", x, y)
                self.frames(1)
                if cmd == "click":
                    self.mouse("down", x, y)
                    self.frames(1)
                    self.mouse("up", x, y)
                else:
                    self.mouse("down", x, y, 3 if cmd == "right" else 2)
                self.frames(2)
            elif cmd == "wheel":
                x, y = (a[1], a[2]) if len(a) >= 3 else (240, 160)
                self.mouse("move", x, y)
                px, py = p.window.to_window(int(x), int(y))
                p.pointer(px, py, "wheel_up" if a[0] == "up" else "wheel_down")
                self.frames(2)
            elif cmd == "drag":
                x1, y1, x2, y2 = (int(v) for v in a[:4])
                self.mouse("move", x1, y1)
                self.frames(1)
                self.mouse("down", x1, y1)
                self.frames(2)
                for i in range(1, 6):
                    self.mouse("move", x1 + (x2 - x1) * i // 5, y1 + (y2 - y1) * i // 5)
                    self.frames(1)
                self.mouse("up", x2, y2)
                self.frames(2)
            elif cmd == "key":
                self.key(a[0], float(a[1]) if len(a) > 1 else 0.1)
            elif cmd == "wait":
                self.wait(float(a[0]))
            elif cmd == "shot":
                self.frames(1)
                if self.shots:
                    pg.image.save(p.window.screen, str(self.shots / (a[0] + ".png")))
                print(f"          shot {a[0]}  size={p.window.screen.get_size()}", flush=True)
            elif cmd == "scene":
                print("          scene:", self.scene_name(), flush=True)
            elif cmd == "expect":
                if type(p.game.scene).__name__ != a[0]:
                    print(f"          FAIL: expected {a[0]}, got {self.scene_name()}", flush=True)
                    raise SystemExit(1)
                print("          ok:", a[0], flush=True)
            elif cmd == "sfx":
                print("          sounds played:", " ".join(p.audio.log) or "(none)", flush=True)
                print("          loaded:", sorted(n for n, s in p.audio.cache.items() if s),
                      "missing:", sorted(p.audio.missing), flush=True)
            elif cmd == "size":
                p.window.resize(int(a[0]), int(a[1]))
                p.expose = True
                self.frames(2)
            else:
                raise SystemExit(f"script: unknown command {raw!r}")
        self.frames(1)


def main():
    args = parse()
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()       # window pixels == real pixels (mouse mapping)
        except (AttributeError, OSError):
            pass
    if args.script is not None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    player = Player(args, headless=args.script is not None)
    if args.script is not None:
        Script(player, args.shots).run(args.script)
        player.audio.close()
        return
    try:
        player.run()
    except Exception:
        # pythonw has no console: keep the traceback next to the saves and tell the player
        import traceback
        text = traceback.format_exc()
        try:
            Path(player.data, "crash.log").write_text(text)
        except OSError:
            pass
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Meowcana crashed. Details: " + str(Path(player.data, "crash.log"))
                                             + "\n\n" + text[-600:], TITLE, 0x10)
        raise


if __name__ == "__main__":
    main()
