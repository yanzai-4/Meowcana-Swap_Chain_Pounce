# Meowcana on PC — mouse + sound contract

The same game code (`python/nla/`) runs on the UNO Q and on a Windows PC. The PC build adds a window
(pygame-ce), mouse input and sound. On the board nothing changes: pointer code is never called and
`nla.sfx.play()` is a no-op. **Never break the board path** (no pygame import outside `arcade/pc/`).

## Launch

`arcade/pc/play.py` (and `Meowcana.bat` next to it): opens a 960x640 window (2x, integer scaling, F11
fullscreen), runs the real game object from `nla.flow.make()` through the simulator's op decoder in real
time (no device cost-model throttling), 30 fps. Saves go to `%APPDATA%/Meowcana/`.
Keyboard: arrows/WASD = stick, Z/Enter/Space = A, X/Backspace = B, C/Tab = C, Esc = pause Menu.
Mouse: move = hover, left click = select/do, right click = B, middle click = C, wheel = up/down.

## Pointer API (game coordinates 480x320)

`App.pointer(x, y, kind)` — kind is one of `"move"`, `"down"`, `"up"`, `"right"`, `"middle"`,
`"wheel_up"`, `"wheel_down"`. The App routes it to the topmost overlay, else the active scene:

```python
def pointer(self, x, y, kind) -> str | None:
    """Return a synthesized input for this frame or None.
    Allowed returns: "a", "b", "c", "up", "down", "left", "right", "menu".
    Typical: on "move" put the cursor on the item under (x, y) (no input); on "up" (click release)
    put the cursor there and return "a"; on "right" return "b"."""
```

- Synthesized inputs are injected into the next `Input` frame exactly like button presses, so the
  tutorial's input gate and all key semantics still apply. `"menu"` opens the pause Menu (same as hold-B).
- Hover moves the cursor only; the tutorial gate may veto it (`App.pointer_gate`, set by the tutorial
  coach: when the current step doesn't allow the stick, hover does nothing).
- Default when a scene/overlay has no `pointer()`: `"up"` → `"a"`, `"right"` → `"b"`, `"middle"` → `"c"`.
- The footer's button gems (`A Fight  B Menu  C Info`) are clickable everywhere (handled once in UIKit).
- Drag and drop on the Spread: `"down"` on a card picks it up, `"up"` over another slot drops it.
- Hit rectangles must match what is drawn. Keep them in the scene next to the drawing code.

## Sound API

`from nla import sfx` then `sfx.play(name)`; optional `sfx.music(name | None)` for loops. Unknown names
are ignored. The PC backend (`arcade/pc/audio.py`, pygame.mixer, 16 channels) loads
`arcade/pc/sfx/<name>.wav`. All sounds are synthesized by `arcade/pc/sfx/gen_sfx.py` (numpy only,
reproducible, 22050 Hz mono 16-bit, short, soft, cozy chiptune timbre matching the moonlit tarot mood).

Names (fixed list; add new ones only in `gen_sfx.py` and here):

| Group | Names |
| --- | --- |
| UI (played centrally by UIKit App on input edges) | `move`, `confirm`, `back`, `info`, `blocked`, `open`, `close`, `transition`, `type` |
| Cards | `pickup`, `drop`, `swap`, `flip`, `deal`, `merge`, `reward` |
| Run | `hop`, `node`, `coin`, `buy`, `sell`, `heal`, `levelup`, `nap`, `box_open`, `bell` |
| Battle | `play_fire`, `play_air`, `play_water`, `play_earth`, `play_major`, `play_scrap`, `hit`, `hit_big`, `crit`, `meow`, `curl`, `singe`, `hiss`, `chain_1` … `chain_5`, `eat`, `roar`, `bite`, `miss`, `ko`, `victory`, `defeat`, `burnout`, `squeak` |
| Music loops | `music_title`, `music_attic`, `music_boss` |
