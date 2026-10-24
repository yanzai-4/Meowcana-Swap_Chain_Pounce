"""Checks for the platform layer, runnable without hardware (from arcade/):

  python tools/sim_selftest.py                 # baked fonts == Pillow mockup rendering, op round trips
  python tools/sim.py --game sim_selftest:Game --keys "0.5s" --shots build/shots/   # visual gallery

`Game` is a one-screen gallery of every op: fonts, flipped / tinted / dimmed assets, asset_region.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
sys.path.insert(0, str(ROOT / "tools"))

import engine  # noqa: E402
from engine import BODY, NUM, TINY, TITLE  # noqa: E402

SAMPLES = {BODY: "Round 1: Nuzzle +2, Step +2 (50%)? Catwalk!",
           TITLE: "Fire Claw, Chubbs, Fight Zq",
           NUM: "0123456789 +-x%!/",
           TINY: "ABC 123 Hit!"}
NAMES = {BODY: ("VT323-Regular", 16), TITLE: ("Jacquard24-Regular", 24),
         NUM: ("Jersey10-Regular", 20), TINY: ("Silkscreen-Regular", 8)}


class Game:
    required = 0

    def __init__(self):
        import assets
        self.assets = assets

    def update(self, controls, dt):
        pass

    def draw(self, scr, full):
        if not full:
            return
        a = self.assets
        navy = engine.rgb(41, 36, 74)
        scr.clear(navy)
        y = 4
        for font, text in SAMPLES.items():
            scr.text(8, y, text, engine.WHITE, navy, font)
            y += scr.measure(text, font)[1] + 2
        scr.text(300, y + 40, "A \u00b7 B \u2192 C \u2605 D \u25bc", engine.WHITE, navy, BODY, 2)
        scr.text(8, y, "Scale 2 opaque", engine.YELLOW, engine.BLACK, BODY, 2)
        scr.text(300, y + 4, "transparent", engine.CYAN, None, BODY)
        scr.text(300, y + 20, "Mixed Case", engine.CYAN, None, TITLE)
        w = scr.text_right(472, y + 50, "text_right", engine.GREEN, navy)
        scr.text_center(y + 52, "centered", engine.GREEN, navy, cx=150)
        sprite = a.DOMINO_IDLE
        base = 150
        x = 8
        for kw in ({}, {"flip": True}, {"flip_y": True}, {"tint": engine.WHITE}, {"dim": True}):
            scr.blit(sprite, 0, x, base, bg=navy, **kw)
            x += 70
        scr.blit(sprite, 0, x, base, bg=None)               # transparent over the navy field
        scr.blit(sprite, 0, x + 70, base, scale=2, bg=navy)
        scr.dotted_rect(8, 230, 60, 72, engine.rgb(123, 116, 164))
        scr.fill_rect(80, 230, 140, 72, engine.RED)
        scr.asset_region(sprite, 0, 90, 236, 16, 8, 32, 40, bg=navy)  # a sub-rect restored over red
        stats = scr.stats()
        scr.text(240, 238, f"ops {stats['ops']} bytes {stats['bytes']} ~{stats['ms']:.0f} ms", engine.WHITE, navy)


def check_fonts():
    from PIL import Image, ImageChops, ImageDraw, ImageFont
    import sim

    lib = sim.Library()
    device = sim.Device(lib)
    font_dir = ROOT / "design" / "styles" / "moonlit-grimoire" / "fonts"
    bad = 0
    for font, text in SAMPLES.items():
        ttf, size = NAMES[font]
        pil = ImageFont.truetype(str(font_dir / (ttf + ".ttf")), size)
        height, ascent = engine.font_metrics(font)
        ref = Image.new("1", (400, 60), 0)
        d = ImageDraw.Draw(ref)
        d.fontmode = "1"
        d.text((4, 4 + ascent), text, font=pil, fill=1, anchor="ls")
        device.img.paste((0, 0, 0), (0, 0, 480, 320))
        device.text(4, 4, font, 1, engine.WHITE, None, text.encode())
        got = Image.new("1", (400, 60), 0)
        got.paste(device.img.crop((0, 0, 400, 60)).convert("L").point(lambda v: 255 if v else 0).convert("1"))
        # Pillow shifts a whole string vertically by 1 px when it holds a glyph taller than the rest
        # (e.g. "("); the baked per-glyph cell is consistent, so accept a 1 px shift of the reference.
        shift = next((dy for dy in (0, -1, 1) if ImageChops.offset(ref, 0, dy).tobytes() == got.tobytes()), None)
        same = shift is not None
        w, _ = engine.measure(text, font)
        print(f"font {font}: {'matches Pillow' if same else 'DIFFERS'}"
              f"{' (reference shifted %d px by Pillow)' % shift if shift else ''}; "
              f"measure={w}x{height} ascent={ascent}")
        bad += not same
    return bad


if __name__ == "__main__":
    sys.exit(1 if check_fonts() else 0)
