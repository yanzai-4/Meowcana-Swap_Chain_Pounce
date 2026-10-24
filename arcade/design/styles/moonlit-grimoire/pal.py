"""Moonlit Grimoire palette (RGB565-exact) and shared pixel helpers."""
from PIL import Image


def snap(rgb):
    """Snap an 8-bit RGB triple to the exact 8-bit value of its RGB565 code (bit-replication expansion)."""
    r, g, b = rgb
    r5, g6, b5 = round(r * 31 / 255), round(g * 63 / 255), round(b * 31 / 255)
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))


def to565(rgb):
    r, g, b = rgb
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def is565(rgb):
    return snap(rgb) == tuple(rgb)


RAW = {
    # midnight indigo ramp (night1 = 0x2929, a "fast fill" colour: high byte == low byte)
    "night0": (14, 10, 34), "night1": (41, 36, 74), "night2": (58, 52, 102), "night3": (84, 78, 134), "night4": (122, 116, 168),
    # moonlight silver
    "silver1": (160, 164, 194), "silver2": (202, 208, 230), "moon": (240, 242, 252),
    # antique gold
    "gold0": (88, 62, 32), "gold1": (140, 100, 44), "gold2": (196, 150, 60), "gold3": (234, 194, 98), "gold4": (252, 228, 152),
    # candle amber (the single warm accent)
    "amber0": (130, 56, 36), "amber1": (206, 98, 40), "amber2": (246, 152, 52), "amber3": (255, 206, 114),
    # elements (dark / mid / light)
    "fire0": (110, 34, 40), "fire1": (196, 64, 48), "fire2": (240, 122, 72),
    "air0": (130, 116, 64), "air1": (222, 206, 130), "air2": (250, 240, 186),
    "water0": (30, 54, 122), "water1": (60, 110, 196), "water2": (132, 178, 236),
    "earth0": (30, 74, 58), "earth1": (70, 136, 84), "earth2": (140, 196, 120),
    # reversed (cool) variants, dark / mid per element
    "rfire0": (62, 40, 96), "rfire1": (112, 80, 150),
    "rair0": (72, 84, 110), "rair1": (150, 166, 196),
    "rwater0": (24, 38, 88), "rwater1": (66, 92, 156),
    "rearth0": (28, 62, 70), "rearth1": (64, 118, 116),
    # rat scrap gray-green
    "rat0": (44, 56, 52), "rat1": (86, 104, 90), "rat2": (136, 156, 126), "rat3": (180, 196, 160),
    "pink": (206, 124, 132),
    # rarity / feedback
    "blue": (84, 120, 226), "purple": (160, 98, 214), "red": (226, 58, 74), "heal": (112, 216, 134),
}
P = {k: snap(v) for k, v in RAW.items()}
FAST_BG = P["night1"]

ELEM = ["fire", "air", "water", "earth"]


def elem_cols(e, reversed_=False):
    """(dark, mid, light) for an element; reversed uses the cool set (light = silver-ish)."""
    if reversed_:
        return P["r" + e + "0"], P["r" + e + "1"], P["silver2"]
    return P[e + "0"], P[e + "1"], P[e + "2"]


def palette_image(colors):
    pal = Image.new("P", (1, 1))
    flat = []
    for c in colors:
        flat += list(c)
    flat += [0] * (768 - len(flat))
    pal.putpalette(flat)
    return pal


def quantize_to(img_rgb, colors):
    """Nearest-colour mapping (no dithering) of an RGB image to the given colour list."""
    q = img_rgb.quantize(palette=palette_image(colors), dither=Image.Dither.NONE)
    return q.convert("RGB")
