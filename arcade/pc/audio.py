"""pygame.mixer backend for `nla.sfx` (PC only; the board never imports this).

    audio = Audio(sfx_dir, settings_path)   # opens the mixer (22050 Hz mono, 16 channels); .ok is False without a device
    nla.sfx.install(audio)                  # nla.sfx.play(name) / .music(name) now reach it

WAVs are `pc/sfx/<name>.wav`, loaded on first use (unknown or missing names are ignored once, then remembered).
Volumes live in `settings.json` next to the saves: {"sfx": 0.8, "music": 0.5, "muted": false}.
`log` collects (name) of every sound that was actually handed to the mixer (used by the scripted checks).
"""

import json
import time
from pathlib import Path

import pygame

CHANNELS = 16
MIN_GAP = {"type": 0.045, "move": 0.03, "hit": 0.03}      # seconds between two plays of the same name
DEFAULT_GAP = 0.02
DEFAULTS = {"sfx": 0.8, "music": 0.45, "muted": False}
STEP = 0.1


class Audio:
    def __init__(self, sfx_dir, settings_path=None, clock=time.monotonic):
        self.dir = Path(sfx_dir)
        self.path = Path(settings_path) if settings_path else None
        self.clock = clock
        self.cache = {}                  # name -> pygame Sound or None (missing)
        self.last = {}                   # name -> time of the last play
        self.log = []
        self.missing = set()
        self.settings = dict(DEFAULTS)
        self.track = None                # name of the music loop that should be playing
        self.music_channel = None
        self.ok = False
        self._load_settings()
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            pygame.mixer.set_num_channels(CHANNELS)
            pygame.mixer.set_reserved(1)                 # channel 0 is the music loop's
            self.music_channel = pygame.mixer.Channel(0)
            self.ok = True
        except pygame.error as error:
            print(f"audio: no sound device ({error}); running silent", flush=True)

    # ------------------------------------------------------------------ settings
    def _load_settings(self):
        try:
            data = json.loads(self.path.read_text())
            for key, default in DEFAULTS.items():
                if isinstance(data.get(key), type(default)):
                    self.settings[key] = data[key]
        except (OSError, ValueError, AttributeError):
            pass

    def _save_settings(self):
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.settings))
            except OSError:
                pass

    def _music_volume(self):
        return 0.0 if self.settings["muted"] else self.settings["music"]

    def toggle_mute(self):
        self.settings["muted"] = not self.settings["muted"]
        self._apply_music_volume()
        self._save_settings()
        return self.settings["muted"]

    def change_volume(self, delta):
        """Master change for effects and music together, clamped to 0..1; unmutes. Returns the new effect volume."""
        for key in ("sfx", "music"):
            self.settings[key] = round(min(1.0, max(0.0, self.settings[key] + delta)), 2)
        self.settings["muted"] = False
        self._apply_music_volume()
        self._save_settings()
        return self.settings["sfx"]

    def _apply_music_volume(self):
        if self.music_channel is not None:
            self.music_channel.set_volume(self._music_volume())

    # ------------------------------------------------------------------ backend interface
    def _sound(self, name):
        if name in self.cache:
            return self.cache[name]
        sound = None
        path = self.dir / (name + ".wav")
        if path.is_file():
            try:
                sound = pygame.mixer.Sound(str(path))
            except pygame.error as error:
                print(f"audio: cannot load {path.name}: {error}", flush=True)
        else:
            self.missing.add(name)
        self.cache[name] = sound
        return sound

    def play(self, name):
        if not self.ok or self.settings["muted"]:
            return
        now = self.clock()
        if now - self.last.get(name, -1.0) < MIN_GAP.get(name, DEFAULT_GAP):
            return
        sound = self._sound(name)
        if sound is None:
            return
        self.last[name] = now
        sound.set_volume(self.settings["sfx"])
        if sound.play() is not None:
            self.log.append(name)

    def music(self, name=None):
        if name == self.track:
            return
        self.track = name
        if not self.ok:
            return
        if name is None:
            self.music_channel.fadeout(400)
            return
        sound = self._sound(name)
        if sound is None:
            self.music_channel.fadeout(400)
            return
        self._apply_music_volume()
        self.music_channel.play(sound, loops=-1, fade_ms=600)

    def close(self):
        if self.ok:
            pygame.mixer.stop()
