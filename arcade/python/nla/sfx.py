"""Sound hooks. Game code calls `sfx.play("hit")` / `sfx.music("music_boss")`; they do nothing until a backend
installs itself (only the PC runner in arcade/pc/ does, so the board build is silent and pays almost nothing).

    sfx.play(name)           one-shot effect; unknown names are ignored by the backend
    sfx.music(name | None)   start a looping track (None stops music); asking for the playing track is a no-op
    sfx.install(backend)     backend has play(name) and music(name); install(None) removes it
    sfx.count                number of play() calls so far (not counting "type"); the UIKit App compares it around
                             a frame to decide whether a scene already made its own sound before it adds a default
"""

_backend = None
count = 0


def install(backend):
    global _backend
    _backend = backend


def play(name):
    global count
    if name != "type":          # typewriter ticks must not hide the App's default sound for A/B/C
        count += 1
    if _backend is not None:
        _backend.play(name)


def music(name=None):
    if _backend is not None:
        _backend.music(name)
