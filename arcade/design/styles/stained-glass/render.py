#!/usr/bin/env python3
"""Bell Tower Stained Glass -- reproduces every PNG in this folder.

Inputs : raw/*.png (PixelLab sprites) and fonts/*.ttf (OFL).
Outputs: spread.png battle.png spread@2x.png battle@2x.png sheet.png
Everything except the four character sprites is drawn in code at native resolution.
Run:  python render.py
"""
import math
import os
import random
import sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 480, 320


# --------------------------------------------------------------------------- colour
def snap(c):
    """Snap an RGB888 colour to the nearest exact RGB565 value (bit-replicated back to 888)."""
    r5 = round(c[0] * 31 / 255)
    g6 = round(c[1] * 63 / 255)
    b5 = round(c[2] * 31 / 255)
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))


def rgb565(c):
    return ((c[0] >> 3) << 11) | ((c[1] >> 2) << 5) | (c[2] >> 3)


_RAW = {
    # fast-fill colours (RGB565 high byte == low byte) are marked [fast]
    "lead": (0, 0, 0),            # [fast 0x0000] lead came
    "night": (8, 0, 66),          # [fast 0x0808] text plates
    "stone": (41, 36, 74),        # [fast 0x2929] dominant background
    "stone2": (82, 73, 148),      # [fast 0x5252] mullion highlight
    "ink": (24, 16, 48),
    "cream": (240, 230, 196),
    "white": (240, 242, 255),
    "silver": (180, 188, 226),
    "slate": (108, 110, 154),
    "moon": (206, 220, 255),
    # ruby / fire
    "ruby_d": (99, 12, 40), "ruby": (200, 28, 60), "ruby_l": (255, 112, 120),
    "fire_d": (112, 20, 22), "fire": (232, 76, 28), "fire_l": (255, 160, 70),
    # topaz (gold) / air
    "gold_d": (140, 92, 12), "gold": (232, 170, 36), "gold_l": (255, 232, 130),
    "air_d": (112, 90, 24), "air": (246, 222, 104), "air_l": (255, 248, 190),
    # sapphire / water
    "sap_d": (14, 24, 104), "sap": (40, 92, 220), "sap_l": (130, 196, 255),
    # emerald / earth
    "em_d": (8, 62, 38), "em": (30, 150, 72), "em_l": (120, 222, 130),
    # amethyst (rare)
    "am_d": (66, 28, 120), "am": (150, 86, 222), "am_l": (208, 160, 255),
    # reversed (cool) ramps
    "rfire_d": (44, 24, 90), "rfire": (108, 76, 180), "rfire_l": (176, 148, 232),
    "rair_d": (24, 64, 92), "rair": (70, 150, 172), "rair_l": (160, 226, 228),
    "rwater_d": (8, 40, 76), "rwater": (20, 112, 150), "rwater_l": (100, 200, 222),
    "rearth_d": (24, 44, 60), "rearth": (70, 112, 124), "rearth_l": (150, 190, 184),
    # rat scrap (gray-green)
    "scrap_d": (40, 54, 46), "scrap": (104, 126, 100), "scrap_l": (170, 186, 150),
    # skin / wood
    "rose": (232, 128, 152), "rose_d": (160, 56, 96),
    "wood_d": (66, 40, 50), "wood": (122, 80, 66), "tan": (206, 164, 112),
}
P = {k: snap(v) for k, v in _RAW.items()}
FAST = {"lead", "night", "stone", "stone2"}
ELEMENTS = ("fire", "air", "water", "earth")
RAMP = {  # element -> (dark, mid, light)
    "fire": ("fire_d", "fire", "fire_l"),
    "air": ("air_d", "air", "air_l"),
    "water": ("sap_d", "sap", "sap_l"),
    "earth": ("em_d", "em", "em_l"),
    "gold": ("gold_d", "gold", "gold_l"),
    "ruby": ("ruby_d", "ruby", "ruby_l"),
    "sap": ("sap_d", "sap", "sap_l"),
    "em": ("em_d", "em", "em_l"),
    "am": ("am_d", "am", "am_l"),
    "scrap": ("scrap_d", "scrap", "scrap_l"),
    "rfire": ("rfire_d", "rfire", "rfire_l"),
    "rair": ("rair_d", "rair", "rair_l"),
    "rwater": ("rwater_d", "rwater", "rwater_l"),
    "rearth": ("rearth_d", "rearth", "rearth_l"),
}


def ramp(name, rev=False):
    n = ("r" + name) if rev and name in ELEMENTS else name
    return tuple(P[k] for k in RAMP[n])


# --------------------------------------------------------------------------- fonts
def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


_FC = {}


def F(kind):
    if kind not in _FC:
        _FC[kind] = {
            "body": lambda: font("PixelifySans.ttf", 12),
            "body16": lambda: font("PixelifySans.ttf", 16),
            "num24": lambda: font("PixelifySans.ttf", 24),
            "num32": lambda: font("PixelifySans.ttf", 32),
            "label": lambda: font("Jacquard12-Regular.ttf", 16),
            "title": lambda: font("Jacquard12-Regular.ttf", 24),
            "title32": lambda: font("Jacquard12-Regular.ttf", 32),
            "title48": lambda: font("Jacquard12-Regular.ttf", 48),
            "tiny": lambda: font("Silkscreen-Regular.ttf", 8),
        }[kind]()
    return _FC[kind]


def new_canvas(w, h, fill=None):
    img = Image.new("RGB", (w, h), P[fill] if isinstance(fill, str) else (fill or P["stone"]))
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    return img, d


def draw_of(img):
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    return d


def col(c):
    return P[c] if isinstance(c, str) else c


def R(d, x, y, w, h, c):
    if w > 0 and h > 0:
        d.rectangle([x, y, x + w - 1, y + h - 1], fill=col(c))


def box_frame(d, x, y, w, h, c):
    """1px hollow rectangle."""
    R(d, x, y, w, 1, c); R(d, x, y + h - 1, w, 1, c)
    R(d, x, y, 1, h, c); R(d, x + w - 1, y, 1, h, c)


def text_w(s, f):
    return int(round(F(f).getlength(s))) if isinstance(f, str) else int(round(f.getlength(s)))


def T(d, x, y, s, f="body", c="cream", shadow=None, outline=None, anchor="ls"):
    """Draw text with baseline at y (default). shadow/outline are palette names or colours."""
    fo = F(f) if isinstance(f, str) else f
    if anchor[0] == "r":
        x -= text_w(s, fo)
    elif anchor[0] == "m":
        x -= text_w(s, fo) // 2
    if outline is not None:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    d.text((x + dx, y + dy), s, font=fo, fill=col(outline), anchor="ls")
    elif shadow is not None:
        d.text((x + 1, y + 1), s, font=fo, fill=col(shadow), anchor="ls")
    d.text((x, y), s, font=fo, fill=col(c), anchor="ls")
    return x + text_w(s, fo)


# --------------------------------------------------------------------------- tiny bitmaps
def blit_mask(img, x, y, rows, cmap):
    """rows: list of strings; cmap: char -> colour (others transparent)."""
    px = img.load()
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in cmap:
                xx, yy = x + i, y + j
                if 0 <= xx < img.width and 0 <= yy < img.height:
                    px[xx, yy] = col(cmap[ch])


def outlined_icon(rows, tones, outline="lead"):
    """Build a bitmap (list of strings) from a body mask, adding an automatic 1px outline ring.
    rows use '#'=body 'o'=light 'x'=dark; returns (grid, cmap) with ring char 'K'."""
    h, w = len(rows), len(rows[0])
    grid = [["."] * (w + 2) for _ in range(h + 2)]
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                grid[j + 1][i + 1] = ch
    out = [r[:] for r in grid]
    for j in range(h + 2):
        for i in range(w + 2):
            if grid[j][i] == ".":
                for dj in (-1, 0, 1):
                    for di in (-1, 0, 1):
                        jj, ii = j + dj, i + di
                        if 0 <= jj < h + 2 and 0 <= ii < w + 2 and grid[jj][ii] != "." and (di == 0 or dj == 0):
                            out[j][i] = "K"
    # shading: body pixel with empty/outline up-left neighbour -> light edge, down-right -> dark edge
    res = [r[:] for r in out]
    for j in range(h + 2):
        for i in range(w + 2):
            if out[j][i] == "#":
                up = out[j - 1][i] in ".K" if j > 0 else True
                lf = out[j][i - 1] in ".K" if i > 0 else True
                dn = out[j + 1][i] in ".K" if j < h + 1 else True
                rt = out[j][i + 1] in ".K" if i < w + 1 else True
                if (up or lf) and not (dn or rt):
                    res[j][i] = "o"
                elif (dn and rt) and not (up or lf):
                    res[j][i] = "x"
    return ["".join(r) for r in res]


def icon_cmap(ramp3, outline="lead"):
    d, m, l = ramp3
    return {"K": outline, "#": m, "o": l, "x": d}


def icon_img(rows, ramp3, shade=True):
    """Return RGBA image for an auto-outlined icon (body mask rows)."""
    g = outlined_icon(rows, ramp3)
    h, w = len(g), len(g[0])
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cm = icon_cmap(ramp3)
    px = im.load()
    for j, row in enumerate(g):
        for i, ch in enumerate(row):
            if ch in cm:
                px[i, j] = col(cm[ch]) + (255,)
    return im


def paste_rgba(img, im, x, y, flip=False):
    if flip:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
    img.paste(im, (x, y), im)


# --------------------------------------------------------------------------- icons
M10 = {  # 10x10 body masks, '#' body 'o' highlight(inner) 'x' shadow
    "fire": [
        "....#.....",
        "...##.....",
        "...###..#.",
        "..####.##.",
        "..#####.##",
        ".##oo#####",
        ".#ooo#####",
        ".#oo######",
        ".########.",
        "..######..",
    ],
    "air": [
        ".........#",
        ".....#####",
        "....##o###",
        "....#o#o##",
        "...######.",
        "..######..",
        "..######..",
        "..#####...",
        ".##.......",
        "#.........",
    ],
    "water": [
        "....##....",
        "....##....",
        "...####...",
        "...####...",
        "..######..",
        ".########.",
        ".##o#####.",
        ".##o#####.",
        ".########.",
        "..######..",
    ],
    "earth": [
        "....#.....",
        "...###..#.",
        "..#o###.##",
        "..#o######",
        ".#oo######",
        ".#o#######",
        "##########",
        "##########",
        "##########",
        "##########",
    ],
    # statuses
    "singe": [
        "...#..#...",
        "#..#..#..#",
        ".#.####.#.",
        "..######..",
        "###oo####.",
        "..#oo###..",
        "..######..",
        ".#.####.#.",
        "#..#..#..#",
        "...#..#...",
    ],
    "puff": [
        "..........",
        "...###....",
        "..#####.#.",
        ".#######..",
        "##########",
        "###oo#####",
        "##o#######",
        ".########.",
        "..........",
        "..........",
    ],
    "drowsy": [
        "..#######.",
        "......##..",
        ".....##...",
        "....##....",
        "..#######.",
        "###.......",
        "..#.......",
        ".#........",
        "###.......",
        "..........",
    ],
    "curl": [
        "..######..",
        ".########.",
        "###....###",
        "##.####.##",
        "##.#..#.##",
        "##.#...###",
        "##.#######",
        ".##.......",
        "..########",
        "..........",
    ],
    "leap": [
        "....##....",
        "...####...",
        "..######..",
        ".########.",
        "...####...",
        "...####...",
        "...####...",
        "..........",
        ".########.",
        "..........",
    ],
    "claw": [
        "..#...#...",
        "..##..##..",
        "...##..##.",
        "...##..##.",
        "....##..##",
        "....##..##",
        ".....##.##",
        ".....##...",
        "..........",
        "..........",
    ],
    "heart": [
        "..........",
        ".###..###.",
        "#o####o###",
        "#o########",
        "##########",
        ".########.",
        "..######..",
        "...####...",
        "....##....",
        "..........",
    ],
    "coin": [
        "..######..",
        ".########.",
        "###oooo###",
        "###o##o###",
        "###o##o###",
        "###oooo###",
        "###o######",
        ".########.",
        "..######..",
        "..........",
    ],
}
ICON_RAMP = {
    "fire": "fire", "air": "air", "water": "water", "earth": "earth",
    "singe": "fire", "puff": "scrap", "drowsy": "sap", "curl": "am", "leap": "em",
    "claw": "ruby", "heart": "ruby", "coin": "gold",
}
_ICON_CACHE = {}


def icon(name, rev=False, scale=1):
    key = (name, rev, scale)
    if key not in _ICON_CACHE:
        rm = ICON_RAMP[name]
        r3 = ramp(rm, rev) if rm in ELEMENTS else ramp(rm)
        rows = M10[name]
        if scale > 1:
            rows = ["".join(c * scale for c in r) for r in rows for _ in range(scale)]
        _ICON_CACHE[key] = icon_img(rows, r3)
    return _ICON_CACHE[key]


def small_mask(name):
    """6x6 body mask derived from the 10x10 mask (min 50% coverage)."""
    rows = M10[name]
    out = []
    for j in range(6):
        r = ""
        for i in range(6):
            x0, x1 = i * 10 / 6, (i + 1) * 10 / 6
            y0, y1 = j * 10 / 6, (j + 1) * 10 / 6
            tot = cnt = 0
            for yy in range(int(y0), min(10, math.ceil(y1))):
                for xx in range(int(x0), min(10, math.ceil(x1))):
                    tot += 1
                    cnt += rows[yy][xx] != "."
            r += "#" if cnt * 2 >= tot else "."
        out.append(r)
    return out


_SMALL = {}


def pip(name, rev=False, size=12):
    """element glyph at 12x12 (size 12) or 8x8 (size 8)."""
    if size >= 12:
        return icon(name, rev)
    key = (name, rev)
    if key not in _SMALL:
        _SMALL[key] = icon_img(small_mask(name), ramp(name, rev))
    return _SMALL[key]


STAR = ["..#..", ".###.", "#####", ".###.", ".#.#."]
ARROW = ["..#..", "...#.", "#####", "...#.", "..#.."]
DOWN = ["#####", ".###.", "..#.."]
def _paw():
    m = Image.new("L", (16, 12), 0)
    dd = ImageDraw.Draw(m)
    for b in ((0, 4, 3, 8), (4, 0, 7, 5), (8, 0, 11, 5), (12, 4, 15, 8), (3, 6, 12, 11)):
        dd.ellipse(b, fill=255)
    return ["".join("#" if m.getpixel((i, j)) else "." for i in range(16)) for j in range(12)]


PAW = _paw()


def star(img, x, y, c="gold_l"):
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        blit_mask(img, x + dx, y + dy, STAR, {"#": "lead"})
    blit_mask(img, x, y, STAR, {"#": c})


def charm_img(kind):
    rows = {
        "catnip": ["..#..#..", ".##..##.", "###..###", ".######.", ".######.", "..####..", "...##...", "...#...."],
        "bell": ["...##...", "..####..", ".######.", ".######.", ".######.", "########", "........", "...##..."],
        "nine": ["..####..", ".######.", "########", "########", "########", "########", ".######.", "..####.."],
    }[kind]
    im = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    px = im.load()
    cm = {"catnip": ("em_d", "em", "em_l"), "bell": ("gold_d", "gold", "gold_l"), "nine": ("am_d", "am", "am_l")}[kind]
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "#":
                px[i, j] = col(cm[1]) + (255,)
    # ring + facets
    out = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    out.paste(im, (1, 1), im)
    ring = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    rp, op = ring.load(), out.load()
    for j in range(10):
        for i in range(10):
            if op[i, j][3] == 0:
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < 10 and 0 <= jj < 10 and op[ii, jj][3]:
                        rp[i, j] = col("lead") + (255,)
                        break
    out.alpha_composite(ring)
    op = out.load()
    # facet: highlight top-left, shade bottom-right
    for j in range(10):
        for i in range(10):
            if op[i, j][:3] == col(cm[1]):
                if j <= 3 and i <= 4 and (i + j) <= 5:
                    op[i, j] = col(cm[2]) + (255,)
                elif i + j >= 11:
                    op[i, j] = col(cm[0]) + (255,)
    if kind == "nine":  # tiny 9 inside the gem
        nine = ["###", "#.#", "###", "..#", "..#"]
        for j, r in enumerate(nine):
            for i, ch in enumerate(r):
                if ch == "#":
                    op[3 + i, 3 + j] = col("white") + (255,)
    if kind == "catnip":
        for (i, j) in ((4, 3), (5, 3), (4, 4), (5, 4), (4, 5), (5, 5), (4, 6), (5, 6)):
            op[i, j] = col("em_l") + (255,)
    if kind == "bell":
        for (i, j) in ((4, 8), (5, 8)):
            op[i, j] = col("lead") + (255,)
    return out


_CHARM = {}


def charm(kind):
    if kind not in _CHARM:
        _CHARM[kind] = charm_img(kind)
    return _CHARM[kind]


# --------------------------------------------------------------------------- glass
def _hash(a, b, seed):
    v = (a * 73856093) ^ (b * 19349663) ^ (seed * 83492791)
    v = (v ^ (v >> 13)) * 1274126177 & 0xFFFFFFFF
    return (v ^ (v >> 16)) & 0xFFFF


def glass(img, x, y, w, h, r3, cell=7, seed=1, weights=(1, 4, 2), lead=True, mask=None, offset=0):
    """Diamond-quarrel leaded glass: each cell picks one of (dark, mid, light)."""
    px = img.load()
    d, m, l = r3
    tones = [d] * weights[0] + [m] * weights[1] + [l] * weights[2]
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            if mask is not None and not mask(xx - x, yy - y):
                continue
            a, b = xx + yy + offset, xx - yy + offset
            if lead and (a % cell == 0 or b % cell == 0):
                px[xx, yy] = P["lead"]
            else:
                px[xx, yy] = tones[_hash(a // cell, b // cell, seed) % len(tones)]


def plate(d, x, y, w, h, fill="night", edge="stone2", lead=True, studs=True):
    """Inset stone plate: lead outline, stone highlight, dark fill (text lives here)."""
    if lead:
        R(d, x, y, w, h, "lead")
        R(d, x + 1, y + 1, w - 2, h - 2, edge)
        R(d, x + 2, y + 2, w - 4, h - 4, fill)
        if studs and w >= 40 and h >= 14:
            for (sx, sy) in ((x + 2, y + 2), (x + w - 4, y + 2), (x + 2, y + h - 4), (x + w - 4, y + h - 4)):
                R(d, sx, sy, 2, 2, "gold")
    else:
        R(d, x, y, w, h, fill)


def arch_top_y(x, w, rr):
    """Height (above springline) of a pointed arch of width w; rr = radius/width in [0.5,1]."""
    R_ = rr * w
    xm = min(x + 0.5, w - x - 0.5)
    return math.sqrt(max(R_ * R_ - (R_ - xm) ** 2, 0))


def arch_mask(w, h, rr=0.62):
    peak = arch_top_y(w / 2 - 0.5, w, rr)
    rise = min(peak, h)

    def m(x, y):
        top = h - 1 - 0  # unused
        t = arch_top_y(x, w, rr)
        # map arch height onto the vertical extent (springline at y = rise)
        yy = rise - t * (rise / peak)
        return y >= yy - 0.5
    return m


# --------------------------------------------------------------------------- sprites
SPRITE_POOL = [
    "lead", "ink", "night", "stone", "stone2", "slate", "silver", "white", "cream", "moon",
    "ruby_d", "ruby", "ruby_l", "rose", "rose_d",
    "fire_d", "fire", "fire_l", "gold_d", "gold", "gold_l", "air", "air_l",
    "sap_d", "sap", "sap_l", "em_d", "em", "em_l", "am_d", "am", "am_l",
    "scrap_d", "scrap", "scrap_l", "wood_d", "wood", "tan",
]


def _dist(a, b):
    rm = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return (2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db


def quantize(im, pool=SPRITE_POOL, cache=None):
    im = im.convert("RGBA")
    out = im.copy()
    px = out.load()
    cache = {} if cache is None else cache
    cols = [P[k] for k in pool]
    for j in range(im.height):
        for i in range(im.width):
            r, g, b, a = px[i, j]
            if a < 128:
                px[i, j] = (0, 0, 0, 0)
                continue
            k = (r >> 2, g >> 2, b >> 2)
            if k not in cache:
                cache[k] = min(cols, key=lambda c: _dist((r, g, b), c))
            px[i, j] = cache[k] + (255,)
    return out


def load_raw(name):
    return Image.open(os.path.join(HERE, "raw", name + ".png")).convert("RGBA")


def flood_outside(im):
    """True for transparent pixels connected to the left/right/top border (not the bottom middle)."""
    w, h = im.size
    px = im.load()
    seen = [[False] * w for _ in range(h)]
    stack = [(0, 0), (w - 1, 0), (0, h // 2), (w - 1, h // 2), (0, h - 1), (w - 1, h - 1)]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or seen[y][x] or px[x, y][3] > 0:
            continue
        seen[y][x] = True
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return seen


def domino_icon():
    """Domino 64x64: AI cat clipped to a pointed-arch window, interior filled with cobalt glass."""
    raw = load_raw("domino")
    px = raw.load()
    am0 = arch_mask(60, 64, 0.7)

    def am(x, y):
        return 0 <= x - 2 < 60 and 0 <= y < 64 and am0(x - 2, y)

    base = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    bg = Image.new("RGB", (64, 64), P["stone"])
    glass(bg, 0, 0, 64, 64, ramp("sap"), cell=8, seed=11, weights=(4, 4, 0), mask=am)
    bp, bq = bg.load(), base.load()
    for j in range(64):
        for i in range(64):
            if am(i, j):
                bq[i, j] = bp[i, j] + (255,)
                if not am(i - 1, j) or not am(i + 1, j) or not am(i, j - 1):
                    bq[i, j] = (0, 0, 0, 255)
    for j in range(64):
        for i in range(64):
            if am(i, j) and px[i, j][3] > 0 and (am(i - 1, j) and am(i + 1, j) and am(i, j - 1)):
                bq[i, j] = px[i, j]
    return quantize(base)


def clean_round(im, r=31.2):
    im = im.copy()
    px = im.load()
    for j in range(im.height):
        for i in range(im.width):
            if (i - 31.5) ** 2 + (j - 31.5) ** 2 > r * r:
                px[i, j] = (0, 0, 0, 0)
    return im


def rat_icon():
    return quantize(load_raw("grayrat"))


def zero_icon():
    return quantize(clean_round(load_raw("zero")))


def chubbs_icon():
    """Chubbs 96x96: AI king in a ruby/amber pointed-arch glass window."""
    raw = load_raw("chubbs")
    base = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    bg = Image.new("RGB", (96, 96), P["stone"])
    am = arch_mask(96, 96, 0.78)
    glass(bg, 0, 0, 96, 96, ramp("ruby"), cell=9, seed=5, weights=(4, 5, 0), mask=am)
    bp, bq = bg.load(), base.load()
    for j in range(96):
        for i in range(96):
            if am(i, j):
                bq[i, j] = bp[i, j] + (255,)
    # lead frame along the arch edge
    for j in range(96):
        for i in range(96):
            if am(i, j) and (not am(i - 1, j) or not am(i + 1, j) or not am(i, j - 1) or i in (0, 95)):
                bq[i, j] = (0, 0, 0, 255)
    base.alpha_composite(raw)
    return quantize(base)


_SPR = {}


def sprite(name):
    if name not in _SPR:
        _SPR[name] = {"domino": domino_icon, "rat": rat_icon, "zero": zero_icon, "chubbs": chubbs_icon}[name]()
    return _SPR[name]


# --------------------------------------------------------------------------- cards
def pip_layout(n):
    """(cx, cy, size) on a 32x32 art grid."""
    g = {
        1: [(16, 16, 24)],
        2: [(16, 9, 12), (16, 23, 12)],
        3: [(9, 9, 12), (23, 9, 12), (16, 23, 12)],
        4: [(9, 9, 12), (23, 9, 12), (9, 23, 12), (23, 23, 12)],
        5: [(7, 7, 8), (25, 7, 8), (16, 16, 8), (7, 25, 8), (25, 25, 8)],
        6: [(10, 7, 8), (22, 7, 8), (10, 16, 8), (22, 16, 8), (10, 25, 8), (22, 25, 8)],
        7: [(10, 7, 8), (22, 7, 8), (16, 11, 8), (10, 16, 8), (22, 16, 8), (10, 25, 8), (22, 25, 8)],
        8: [(10, 7, 8), (22, 7, 8), (16, 11, 8), (10, 16, 8), (22, 16, 8), (16, 21, 8), (10, 25, 8), (22, 25, 8)],
        9: [(6, 6, 8), (16, 6, 8), (26, 6, 8), (6, 16, 8), (16, 16, 8), (26, 16, 8), (6, 26, 8), (16, 26, 8), (26, 26, 8)],
        10: [(10, 5, 8), (22, 5, 8), (10, 12, 8), (22, 12, 8), (16, 8, 8), (16, 24, 8), (10, 20, 8), (22, 20, 8), (10, 27, 8), (22, 27, 8)],
    }
    return g[n]


def _blank(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def _solid(im, x, y, w, h, c):
    ImageDraw.Draw(im).rectangle([x, y, x + w - 1, y + h - 1], fill=col(c) + (255,))


RARITY = {"none": "white", "common": "sap_l", "rare": "am", "legendary": "gold_l", "curse": "ruby"}


def sun_art(S=32, rev=False):
    """The Sun: a tuxedo cat basking inside a golden rose of rays. Returns RGB image SxS."""
    img = Image.new("RGB", (S, S), P["fire_d"])
    d = draw_of(img)
    glass(img, 0, 0, S, S, ramp("fire", rev), cell=7, seed=9, weights=(3, 4, 1))
    cx = cy = S / 2 - 0.5
    ro, ri = S * 0.5, S * 0.3
    n = 12
    for k in range(n):
        a0 = 2 * math.pi * (k - 0.5) / n
        a1 = 2 * math.pi * (k + 0.5) / n
        am_ = 2 * math.pi * k / n
        pts = [(cx + ri * math.cos(a0), cy + ri * math.sin(a0)),
               (cx + ro * 1.02 * math.cos(am_), cy + ro * 1.02 * math.sin(am_)),
               (cx + ri * math.cos(a1), cy + ri * math.sin(a1))]
        d.polygon(pts, fill=P["gold_l"] if k % 2 == 0 else P["gold"], outline=P["lead"])
    r = S * 0.31
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=P["gold"], outline=P["lead"])
    r2 = r - 2
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=P["gold_l"])
    # cat head (left half black, right half white)
    hw, hh = S * 0.2, S * 0.16
    hy = cy + S * 0.03
    d.ellipse([cx - hw, hy - hh, cx + hw, hy + hh], fill=P["white"], outline=P["lead"])
    d.pieslice([cx - hw, hy - hh, cx + hw, hy + hh], 90, 270, fill=P["ink"], outline=P["lead"])
    e = S * 0.07
    d.polygon([(cx - hw, hy - hh * 0.5), (cx - hw * 0.95, hy - hh - e * 1.6), (cx - hw * 0.3, hy - hh * 0.9)], fill=P["ink"], outline=P["lead"])
    d.polygon([(cx + hw, hy - hh * 0.5), (cx + hw * 0.95, hy - hh - e * 1.6), (cx + hw * 0.3, hy - hh * 0.9)], fill=P["white"], outline=P["lead"])
    # happy closed eyes + nose
    ey = hy - 1
    d.line([(cx - hw * 0.65, ey), (cx - hw * 0.35, ey - 1), (cx - hw * 0.15, ey)], fill=P["gold_l"])
    d.line([(cx + hw * 0.15, ey), (cx + hw * 0.35, ey - 1), (cx + hw * 0.65, ey)], fill=P["lead"])
    d.point((round(cx), round(hy + hh * 0.35)), fill=P["ink"])
    d.point((round(cx - 1), round(hy + hh * 0.35)), fill=P["ink"])
    box_frame(d, 0, 0, S, S, "lead")
    return img


def scrap_icon(kind, size=20):
    """Pixel icon for rat scrap cards (RGBA, size x size)."""
    im = _blank(size, size)
    d = ImageDraw.Draw(im)
    L, S_, Sl = col("lead") + (255,), col("silver") + (255,), col("white") + (255,)
    Br = col("wood") + (255,)
    if kind == "sword":   # broken blade on a diagonal
        d.polygon([(3, 15), (13, 5), (15, 7), (9, 11), (5, 17)], fill=S_, outline=L)
        d.polygon([(14, 4), (17, 2), (16, 6)], fill=S_, outline=L)          # jagged break tip
        d.line([(2, 16), (6, 12)], fill=Br, width=2)                         # hilt/guard stub
        d.line([(1, 14), (4, 17)], fill=L, width=1)
        d.point((8, 9), fill=Sl)
    elif kind == "coin":
        d.ellipse([2, 2, size - 3, size - 3], fill=col("gold") + (255,), outline=L)
        d.ellipse([5, 5, size - 6, size - 6], outline=col("gold_d") + (255,))
        d.line([(10, 2), (8, 8), (11, 11), (9, 18)], fill=L)                 # crack
        d.point((6, 6), fill=col("gold_l") + (255,))
    elif kind == "cup":
        d.polygon([(4, 4), (16, 4), (14, 14), (6, 14)], fill=col("sap_l") + (255,), outline=L)
        d.rectangle([9, 14, 11, 17], fill=col("sap") + (255,), outline=L)
        d.rectangle([6, 17, 14, 18], fill=col("sap") + (255,), outline=L)
        d.polygon([(4, 7), (16, 7), (15, 13), (5, 13)], fill=col("sap") + (255,))
        d.point((17, 11), fill=col("sap_l") + (255,)); d.point((17, 13), fill=col("sap_l") + (255,))  # leak drops
    elif kind == "gnaw":
        d.polygon([(3, 2), (9, 2), (8, 14), (6, 17), (4, 14)], fill=col("cream") + (255,), outline=L)
        d.polygon([(11, 2), (17, 2), (16, 14), (14, 17), (12, 14)], fill=col("cream") + (255,), outline=L)
        d.line([(5, 4), (5, 9)], fill=col("white") + (255,)); d.line([(13, 4), (13, 9)], fill=col("white") + (255,))
    elif kind == "strength":   # chewed Major: paw print on a torn tablet
        d.polygon([(3, 2), (16, 2), (17, 7), (15, 13), (17, 18), (4, 18), (2, 10)], fill=col("am") + (255,), outline=L)
        for (x, y) in ((6, 6), (9, 5), (12, 6), (8, 11), (11, 11), (9, 14)):
            d.rectangle([x, y, x + 1, y + 1], fill=col("white") + (255,))
    return im


def scrap_card(kind="sword", n=3, bites=((29, 40), (0, 14))):
    """32x44 rat scrap: gray-green torn glass, bite-mark scallops, number top-left."""
    W_, H_ = 32, 44
    rnd = random.Random(7 + n + len(kind))
    pts = [(0, 1)]
    for x in range(5, W_ - 2, 6):
        pts.append((x, rnd.choice((0, 1, 2))))
    pts += [(W_ - 1, 1), (W_ - 1, H_ - 2)]
    for x in range(W_ - 6, 2, -6):
        pts.append((x, H_ - 1 - rnd.choice((0, 1, 2))))
    pts += [(0, H_ - 2)]
    msk = Image.new("L", (W_, H_), 0)
    ImageDraw.Draw(msk).polygon(pts, fill=255)
    lat = Image.new("RGB", (W_, H_), P["scrap"])
    glass(lat, 0, 0, W_, H_, ramp("scrap"), cell=6, seed=3 + n, weights=(1, 5, 2))
    im = _blank(W_, H_)
    im.paste(lat, (0, 0), msk)
    # number plate, art plate, icon
    _solid(im, 3, 3, 12, 11, "scrap_d")
    _solid(im, 5, 16, 22, 22, "scrap_d")
    im.alpha_composite(scrap_icon(kind, 20), (6, 17))
    dd = ImageDraw.Draw(im)
    dd.rectangle([3, 3, 14, 13], outline=col("lead") + (255,))
    dd.rectangle([5, 16, 26, 37], outline=col("lead") + (255,))
    num = _blank(12, 11)
    nd = ImageDraw.Draw(num)
    nd.fontmode = "1"
    nd.text((6, 10), str(n), font=F("body"), fill=col("cream") + (255,), anchor="ms")
    im.alpha_composite(num, (3, 3))
    # bite marks: scallops cut out of the corners, then the whole silhouette gets a lead outline
    for (bx, by) in bites:
        for (ox, oy, r) in ((0, 0, 3), (-3, 2, 2), (2, -3, 2)):
            dd.ellipse([bx + ox - r, by + oy - r, bx + ox + r, by + oy + r], fill=(0, 0, 0, 0))
    px = im.load()
    edge = []
    for j in range(H_):
        for i in range(W_):
            if px[i, j][3] and any(not (0 <= i + a < W_ and 0 <= j + b < H_) or px[i + a, j + b][3] == 0
                                   for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                edge.append((i, j))
    for (i, j) in edge:
        px[i, j] = col("lead") + (255,)
    return im


def card_back(mini=False):
    W_, H_ = (40, 54) if mini else (48, 64)
    im = _blank(W_, H_)
    rgb = Image.new("RGB", (W_, H_), P["lead"])
    d = draw_of(rgb)
    # gold ring + inner lead
    R(d, 1, 1, W_ - 2, H_ - 2, "gold")
    R(d, 2, 2, W_ - 4, H_ - 4, "lead")
    ix, iy, iw, ih = 3, 3, W_ - 6, H_ - 6
    glass(rgb, ix, iy, iw, ih, (P["sap_d"], P["sap"], P["sap"]), cell=6, seed=21, weights=(4, 3, 0))
    # cat-eye moon
    cx, cy = W_ // 2, H_ // 2 - 1
    r = 10 if not mini else 8
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=P["gold"], outline=P["lead"])
    d.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], fill=P["gold_l"])
    # crescent shading (right side darker)
    d.pieslice([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], -60, 60, fill=P["gold"])
    # vertical slit pupil
    pw = 2 if not mini else 1
    d.polygon([(cx, cy - r + 3), (cx + pw + 1, cy), (cx, cy + r - 3), (cx - pw - 1, cy)], fill=P["lead"])
    # corner stars
    for (sx, sy) in ((6, 6), (W_ - 11, 6), (6, H_ - 11), (W_ - 11, H_ - 11)):
        blit_mask(rgb, sx, sy, STAR, {"#": "gold_l"})
    im.paste(rgb, (0, 0))
    px = im.load()
    for (x, y) in ((0, 0), (W_ - 1, 0), (0, H_ - 1), (W_ - 1, H_ - 1)):
        px[x, y] = (0, 0, 0, 0)
    return im


def empty_slot(mini=False):
    W_, H_ = (40, 54) if mini else (48, 64)
    im = _blank(W_, H_)
    rgb = Image.new("RGB", (W_, H_), P["night"])
    d = draw_of(rgb)
    # dashed stone outline
    for x in range(1, W_ - 1):
        if (x // 3) % 2 == 0:
            d.point((x, 1), fill=P["stone2"]); d.point((x, H_ - 2), fill=P["stone2"])
    for y in range(1, H_ - 1):
        if (y // 3) % 2 == 0:
            d.point((1, y), fill=P["stone2"]); d.point((W_ - 2, y), fill=P["stone2"])
    box_frame(d, 0, 0, W_, H_, "lead")
    T(d, W_ // 2, H_ // 2 + 4, "--", "body", "slate", anchor="ms")
    im.paste(rgb, (0, 0))
    px = im.load()
    for (x, y) in ((0, 0), (W_ - 1, 0), (0, H_ - 1), (W_ - 1, H_ - 1)):
        px[x, y] = (0, 0, 0, 0)
    return im


def card(el="fire", n=4, stars=1, rarity="common", rev=False, charm_kind=None, mini=False,
         major=None):
    """Glass-panel card. el in ELEMENTS; major=(roman, art_fn) for a Major."""
    if mini:
        W_, H_, B, TOP, BOT, ART, PIPSZ = 40, 54, 2, 10, 10, 28, 8
    else:
        W_, H_, B, TOP, BOT, ART, PIPSZ = 48, 64, 3, 12, 12, 32, 12
    im = _blank(W_, H_)
    rgb = Image.new("RGB", (W_, H_), P["lead"])
    d = draw_of(rgb)
    rd, rm, rl = ramp(el, rev)
    ring = col(RARITY[rarity])
    d.rectangle([1, 1, W_ - 2, H_ - 2], fill=ring)
    d.rectangle([2, 2, W_ - 3, H_ - 3], fill=P["lead"])
    ix, iy, iw, ih = B, B, W_ - 2 * B, H_ - 2 * B
    if not mini:
        ix, iy, iw, ih = 3, 3, W_ - 6, H_ - 6
    # glass lattice fills the whole interior, plates overlay it
    glass(rgb, ix, iy, iw, ih, (rd, rm, rl), cell=6, seed=n * 7 + (3 if rev else 0) + len(el), weights=(1, 5, 2))
    d = draw_of(rgb)
    # top plate + bottom plate (dark element tint = readable text ground)
    R(d, ix, iy, iw, TOP, rm)
    R(d, ix, iy, iw, 1, rl)
    R(d, ix, iy + TOP, iw, 1, "lead")
    ay = iy + TOP + 1
    R(d, ix, ay + ART, iw, 1, "lead")
    by = ay + ART + 1
    R(d, ix, by, iw, BOT, rm)
    R(d, ix, by + BOT - 1, iw, 1, rd)
    ax = ix + (iw - ART) // 2
    # art window
    R(d, ax, ay, ART, ART, rd)
    art_rgba = _blank(ART, ART)
    if major is not None:
        art_rgb = major[1](ART, rev)
        art_rgba.paste(art_rgb, (0, 0))
    else:
        lat = Image.new("RGB", (ART, ART), rd)
        glass(lat, 0, 0, ART, ART, (rd, rd, rd), cell=8, seed=2, weights=(1, 0, 0))
        art_rgba.paste(lat, (0, 0))
        sc = ART / 32.0
        for (px_, py_, sz) in pip_layout(n):
            cxp, cyp = round(px_ * sc), round(py_ * sc)
            if sz == 24:
                g = icon(el, rev, 2) if not mini else pip(el, rev, 12)
            else:
                g = pip(el, rev, 12 if (sz == 12 and not mini) else 8)
            art_rgba.alpha_composite(g, (cxp - g.width // 2, cyp - g.height // 2))
        if rev:
            art_rgba = art_rgba.transpose(Image.FLIP_TOP_BOTTOM)
    rgb.paste(art_rgba, (ax, ay), art_rgba)
    d = draw_of(rgb)
    box_frame(d, ax - 1, ay - 1, ART + 2, ART + 2, "lead")
    # number / roman
    label = major[0] if major is not None else str(n)
    base_y = iy + TOP - (3 if not mini else 2)
    xx = T(d, ix + 2, base_y, label, "body", "white", outline="lead")
    if rev:
        blit_mask(rgb, xx + 2, iy + (TOP // 2), DOWN, {"#": rl})
    # stars
    if major is None and stars:
        sx = ix + iw - 2 - stars * 6 + 1
        for k in range(stars):
            star(rgb, sx + k * 6, iy + (TOP - 5) // 2, "gold_l")
    # bottom: element icon + charm gem
    if mini:
        g = pip(el, rev, 8)
        rgb.paste(g, (ix + 1, by + 1), g)
    else:
        g = pip(el, rev, 12)
        rgb.paste(g, (ix, by), g)
    if charm_kind:
        c_ = charm(charm_kind)
        rgb.paste(c_, (ix + iw - 10 - (0 if not mini else 0), by + (BOT - 10) // 2), c_)
    im.paste(rgb, (0, 0))
    px = im.load()
    for (x, y) in ((0, 0), (W_ - 1, 0), (0, H_ - 1), (W_ - 1, H_ - 1)):
        px[x, y] = (0, 0, 0, 0)
    return im


# --------------------------------------------------------------------------- UI parts
def poly_mask(w, h, pts):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    mp = m.load()
    return lambda x, y: 0 <= x < w and 0 <= y < h and mp[x, y] > 0


def stone_bg(img, y0=0, y1=H):
    """Dominant fast-fill stone (0x2929) with faint ashlar joints."""
    d = draw_of(img)
    R(d, 0, y0, img.width, y1 - y0, "stone")
    for k, y in enumerate(range(y0 + 15, y1, 16)):
        R(d, 0, y, img.width, 1, "ink")
        off = 0 if k % 2 == 0 else 24
        for x in range(off, img.width, 48):
            R(d, x, y - 15, 1, 15, "ink")


def hp_bar(img, x, y, w, h, cur, mx, tone="ruby", seg=None, flash=False):
    d = draw_of(img)
    rd, rm, rl = ramp(tone)
    R(d, x, y, w, h, "lead")
    ix, iy, iw, ih = x + 1, y + 1, w - 2, h - 2
    R(d, ix, iy, iw, ih, rd)
    fw = round(iw * cur / mx)
    R(d, ix, iy, fw, ih, "white" if flash else rm)
    R(d, ix, iy, fw, 1, rl if not flash else "white")
    if seg:
        for k in range(1, mx // seg + 1):
            xx = ix + round(iw * k * seg / mx)
            if xx < ix + iw - 1:
                R(d, xx, iy, 1, ih, "lead")


def chip(img, x, y, letter, tone):
    """11px glass button disc with a letter (A ruby / B sapphire / C emerald)."""
    d = draw_of(img)
    rd, rm, rl = ramp(tone)
    d.ellipse([x, y, x + 10, y + 10], fill=col("lead"))
    d.ellipse([x + 1, y + 1, x + 9, y + 9], fill=rm)
    d.pieslice([x + 1, y + 1, x + 9, y + 9], 20, 110, fill=rd)
    d.arc([x + 2, y + 2, x + 8, y + 8], 180, 280, fill=rl)
    T(d, x + 5, y + 9, letter, "body", "white", anchor="ms")


def gold_dot(d, x, y):
    R(d, x, y, 2, 2, "gold_l")


def draw_rich(img, x, y, parts, f="body", default="cream", outline=None):
    """Sequential layout. parts: str | ('c', colour, str) | ('f', font, colour, str) | ('icon', name) |
    ('star',) | ('arrow',) | ('dot',) | ('gap', n) | ('chip', letter, tone)."""
    d = draw_of(img)
    for p in parts:
        if isinstance(p, str):
            x = T(d, x, y, p, f, default, outline=outline)
        elif p[0] == "c":
            x = T(d, x, y, p[2], f, p[1], outline=outline)
        elif p[0] == "f":
            x = T(d, x, y, p[3], p[1], p[2], outline=outline)
        elif p[0] == "icon":
            im = icon(p[1]) if len(p) < 3 else p[2]
            paste_rgba(img, im, x, y - 10)
            x += im.width + 2
        elif p[0] == "star":
            star(img, x + 1, y - 7, "gold_l")
            x += 7
        elif p[0] == "arrow":
            blit_mask(img, x + 1, y - 7, ARROW, {"#": "gold_l"})
            x += 8
        elif p[0] == "dot":
            R(d, x + 3, y - 4, 2, 2, "gold")
            x += 8
        elif p[0] == "gap":
            x += p[1]
        elif p[0] == "chip":
            chip(img, x, y - 9, p[1], p[2])
            x += 14
    return x


def wrap(s, width, f="body"):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if text_w(t, f) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return lines


def lozenge(img, x, y, w, h, cut, tone, seed=4):
    """Hexagon-ended glass button frame; returns mask func for the inner plate region."""
    d = draw_of(img)
    pts = [(cut, 0), (w - 1 - cut, 0), (w - 1, h // 2 - 1), (w - 1, h // 2), (w - 1 - cut, h - 1), (cut, h - 1), (0, h // 2), (0, h // 2 - 1)]
    m = poly_mask(w, h, pts)
    glass(img, x, y, w, h, ramp(tone), cell=8, seed=seed, weights=(3, 5, 1), mask=m)
    px = img.load()
    for j in range(h):
        for i in range(w):
            if m(i, j) and (not m(i - 1, j) or not m(i + 1, j) or not m(i, j - 1) or not m(i, j + 1)):
                px[x + i, y + j] = P["lead"]
    return m


def paw_cursor(img, x, y):
    px = img.load()
    for j, row in enumerate(PAW):
        for i, ch in enumerate(row):
            if ch == "#":
                px[x + i, y + j] = P["gold_l"] if j < 8 else P["gold"]
    # outline
    for j in range(-1, len(PAW) + 1):
        for i in range(-1, len(PAW[0]) + 1):
            inside = 0 <= j < len(PAW) and 0 <= i < len(PAW[0]) and PAW[j][i] == "#"
            if not inside:
                for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    jj, ii = j + dj, i + di
                    if 0 <= jj < len(PAW) and 0 <= ii < len(PAW[0]) and PAW[jj][ii] == "#":
                        if 0 <= x + i < img.width and 0 <= y + j < img.height:
                            px[x + i, y + j] = P["lead"]
                        break


def tab(img, x, y, text, tone, h=15):
    """Jewel-glass section tab: hexagon-cornered, solid glass, lead outline, outlined lettering."""
    d = draw_of(img)
    w = text_w(text, "label") + 16
    pts = [(3, 0), (w - 4, 0), (w - 1, 3), (w - 1, h - 4), (w - 4, h - 1), (3, h - 1), (0, h - 4), (0, 3)]
    m = poly_mask(w, h, pts)
    px = img.load()
    rd, rm, rl = ramp(tone)
    for j in range(h):
        for i in range(w):
            if m(i, j):
                edge = not (m(i - 1, j) and m(i + 1, j) and m(i, j - 1) and m(i, j + 1))
                px[x + i, y + j] = P["lead"] if edge else (rl if j == 1 else rd if j >= h - 3 else rm)
    T(d, x + 8, y + h - 3, text, "label", "white", shadow="lead")
    return x + w


# --------------------------------------------------------------------------- SPREAD screen
def draw_spread(show_cursor=True):
    img, d = new_canvas(W, H, "stone")
    stone_bg(img)
    d = draw_of(img)

    # ---- enemy row
    rat = sprite("rat")
    img.paste(rat, (8, 1), rat)
    plate(d, 78, 3, 396, 60)
    T(d, 90, 30, "Gray Rat", "title", "gold_l", outline="lead")
    T(d, 90, 52, "HP", "body", "silver")
    hp_bar(img, 108, 44, 100, 10, 18, 18, "ruby", seg=3)
    T(d, 214, 53, "18/18", "body", "cream")
    tab(img, 266, 22, "Scraps", "scrap")
    scraps = [("sword", 3), ("sword", 3), ("coin", 4)]
    for i, (k, n) in enumerate(scraps):
        c_ = scrap_card(k, n, bites=((29, 40), (0, 14)) if i != 1 else ((30, 6), (2, 41)))
        img.paste(c_, (348 + i * 42, 9), c_)

    # ---- READING line
    plate(d, 8, 67, 464, 19)
    tab(img, 12, 70, "Reading", "ruby", 13)
    x = 92
    seq = [("Nuzzle x2",), ("Tail Tap x2",), ("Step x2",), ("Catwalk",)]
    parts = []
    for i, (s,) in enumerate(seq):
        if i:
            parts.append(("dot",))
        parts.append(("c", "cream" if i < 3 else "gold_l", s))
    draw_rich(img, x, 80, parts)

    # ---- SPREAD row
    xe = tab(img, 10, 87, "Spread", "gold")
    T(d, xe + 6, 99, "4/6", "body", "silver")
    sx0, sy, pitch = 14, 103, 58
    row = [
        card("fire", 3, 1, "none"),
        card("fire", 4, 1, "common", charm_kind="bell"),
        card("air", 5, 1, "rare", rev=True),
        card("water", 3, 1, "none"),
        empty_slot(),
        empty_slot(),
    ]
    for i, c_ in enumerate(row):
        img.paste(c_, (sx0 + i * pitch, sy), c_)
    # FIGHT button
    fx, fy, fw, fh = 366, 103, 100, 64
    m = lozenge(img, fx, fy, fw, fh, 14, "ruby", seed=8)
    inner = poly_mask(fw - 12, fh - 12, [(10, 0), (fw - 13 - 10, 0), (fw - 13, (fh - 12) // 2), (fw - 13 - 10, fh - 13), (10, fh - 13), (0, (fh - 12) // 2)])
    pl = Image.new("RGB", (fw - 12, fh - 12), P["lead"])
    pd = draw_of(pl)
    for j in range(fh - 12):
        for i in range(fw - 12):
            if inner(i, j):
                pl.putpixel((i, j), P["night"])
    # gold inner line
    pp = pl.load()
    for j in range(fh - 12):
        for i in range(fw - 12):
            if inner(i, j) and (not inner(i - 1, j) or not inner(i + 1, j) or not inner(i, j - 1) or not inner(i, j + 1)):
                pp[i, j] = P["gold"]
    msk = Image.new("L", pl.size, 0)
    mp_ = msk.load()
    for j in range(pl.height):
        for i in range(pl.width):
            if inner(i, j):
                mp_[i, j] = 255
    img.paste(pl, (fx + 6, fy + 6), msk)
    d = draw_of(img)
    T(d, fx + fw // 2, fy + 40, "Fight", "title", "gold_l", outline="lead", anchor="ms")
    chip(img, fx + fw // 2 - 5, fy + 44, "A", "ruby")

    # cursor: gold brackets on card 2 + paw
    cx = sx0 + 1 * pitch
    if show_cursor:
        select_brackets(img, cx, sy, 48, 64)
        paw_cursor(img, cx + 17, sy + 66)

    # ---- per-round line
    plate(d, 8, 183, 464, 16)
    tab(img, 12, 185, "Per round", "am", 13)
    draw_rich(img, 110, 195, [("icon", "claw"), ("c", "ruby_l", "DMG"), ("gap", 4), "38", ("gap", 14),
                               ("icon", "singe"), ("c", "fire_l", "SINGE"), ("gap", 4), "2", ("gap", 14),
                               ("icon", "heart"), ("c", "em_l", "HEAL"), ("gap", 4), "3", ("gap", 14),
                               ("icon", "curl"), ("c", "am_l", "CURL"), ("gap", 4), "0"])

    # ---- BOX row
    tab(img, 10, 212, "Box", "em")
    T(d, 16, 238, "2/6", "body", "silver")
    bx0, by, bp = 58, 203, 44
    box_row = [
        card("fire", 19, 0, "legendary", mini=True, major=("XIX", sun_art)),
        card("earth", 7, 1, "common", mini=True),
        empty_slot(True), empty_slot(True), empty_slot(True), empty_slot(True),
    ]
    for i, c_ in enumerate(box_row):
        img.paste(c_, (bx0 + i * bp, by), c_)
    # Zero's tip
    plate(d, 326, 203, 140, 54)
    lines = wrap("Zero: Fire next to Water? They'll hiss at each other.", 124)
    for i, ln in enumerate(lines[:4]):
        if i == 0 and ln.startswith("Zero:"):
            xx = T(d, 334, 216, "Zero:", "body", "moon")
            T(d, xx + 4, 216, ln[6:], "body", "silver")
        else:
            T(d, 334, 216 + i * 12, ln, "body", "silver")

    # ---- selected card detail
    plate(d, 8, 260, 464, 36)
    paste_rgba(img, icon("fire"), 15, 265)
    draw_rich(img, 32, 275, [("f", "label", "gold_l", "Fire Claw"), ("gap", 4), ("dot",), "Wands 4", ("gap", 6), ("star",), "1", ("gap", 8), ("c", "sap_l", "Upright")])
    draw_rich(img, 32, 290, ["Nuzzle +2", ("dot",), "Tail Tap +1", ("dot",), "Step +2", ("gap", 2), ("arrow",), ("f", "body16", "gold_l", "Power 9")])

    # ---- footer
    plate(d, 0, 298, W, 22, fill="night", edge="stone2")
    draw_rich(img, 10, 313, [("icon", "heart"), ("c", "silver", "Domino"), ("gap", 4), "HP 30/36", ("gap", 6)])
    hp_bar(img, 124, 306, 52, 8, 30, 36, "em", seg=6)
    draw_rich(img, 186, 313, [("icon", "coin"), ("c", "silver", "Treats"), ("gap", 4), ("c", "gold_l", "14")])
    draw_rich(img, 288, 313, [("chip", "A", "ruby"), "Pick up", ("gap", 8), ("chip", "B", "sap"), "Menu", ("gap", 8), ("chip", "C", "em"), "Info"])
    return img


def select_brackets(img, x, y, w, h, c="gold_l", dark="gold"):
    """Corner-bracket selection ring (2px, 8px arms) hugging the card, with lead edge."""
    d = draw_of(img)
    arm = 10
    for (ox, oy, w_, h_, cc) in (
        (-3, -3, arm, 2, c), (-3, -3, 2, arm, c),
        (w + 1 - (arm - 2), -3, arm, 2, c), (w + 1, -3, 2, arm, c),
        (-3, h + 1, arm, 2, c), (-3, h + 1 - (arm - 2), 2, arm, c),
        (w + 1 - (arm - 2), h + 1, arm, 2, c), (w + 1, h + 1 - (arm - 2), 2, arm, c),
    ):
        R(d, x + ox - 1, y + oy - 1, w_ + 2, h_ + 2, "lead")
    for (ox, oy, w_, h_, cc) in (
        (-3, -3, arm, 2, c), (-3, -3, 2, arm, c),
        (w + 1 - (arm - 2), -3, arm, 2, c), (w + 1, -3, 2, arm, c),
        (-3, h + 1, arm, 2, c), (-3, h + 1 - (arm - 2), 2, arm, c),
        (w + 1 - (arm - 2), h + 1, arm, 2, c), (w + 1, h + 1 - (arm - 2), 2, arm, c),
    ):
        R(d, x + ox, y + oy, w_, h_, cc)


# --------------------------------------------------------------------------- BATTLE screen
def lancet(img, x, y, w, h, r3, seed=1, rr=0.7, weights=(2, 4, 1), frame=True):
    """Pointed-arch leaded window with lead + stone frame."""
    m0 = arch_mask(w, h, rr)

    def m(i, j):
        return 0 <= i < w and 0 <= j < h and m0(i, j)

    glass(img, x, y, w, h, r3, cell=7, seed=seed, weights=weights, mask=m)
    px = img.load()
    for j in range(h):
        for i in range(w):
            if m(i, j) and (not m(i - 1, j) or not m(i + 1, j) or not m(i, j - 1) or j == h - 1):
                px[x + i, y + j] = P["lead"]
    if frame:
        for j in range(-1, h + 1):
            for i in range(-1, w + 1):
                if not m(i, j) and (m(i - 1, j) or m(i + 1, j) or m(i, j - 1) or m(i, j + 1)):
                    xx, yy = x + i, y + j
                    if 0 <= xx < img.width and 0 <= yy < img.height:
                        px[xx, yy] = P["stone2"]
    return m


def jar(img, x, y, w, h, tone, lid="gold", label=True):
    d = draw_of(img)
    rd, rm, rl = ramp(tone)
    R(d, x, y, w, h, "lead")
    R(d, x + 1, y + 2, w - 2, h - 3, rm)
    R(d, x + 1, y + 2, 2, h - 3, rl)
    R(d, x + w - 3, y + 2, 2, h - 3, rd)
    R(d, x - 1, y - 2, w + 2, 4, "lead")
    R(d, x, y - 1, w, 2, lid)
    if label and h > 12:
        R(d, x + 2, y + h // 2 - 2, w - 4, 5, "cream")
        R(d, x + 2, y + h // 2, w - 4, 1, "slate")


def shelf(img, x, y, w):
    d = draw_of(img)
    R(d, x, y, w, 5, "lead")
    R(d, x + 1, y + 1, w - 2, 3, "wood")
    R(d, x + 1, y + 1, w - 2, 1, "tan")
    R(d, x + 4, y + 5, 4, 8, "lead"); R(d, x + w - 8, y + 5, 4, 8, "lead")
    R(d, x + 5, y + 5, 2, 7, "wood_d"); R(d, x + w - 7, y + 5, 2, 7, "wood_d")


def cheese(img, cx, by, r=11):
    d = draw_of(img)
    d.pieslice([cx - r, by - 2 * r + 4, cx + r, by + 4], 180, 360, fill=P["gold"], outline=P["lead"])
    R(d, cx - r + 1, by - r + 2, 2 * r - 1, r - 1, "gold")
    R(d, cx - r, by - r + 3, 2 * r + 1, 1, "lead")
    R(d, cx - r, by - 1, 2 * r + 1, 1, "lead")
    for (ox, oy) in ((-5, -6), (3, -8), (6, -4), (-2, -2)):
        R(d, cx + ox, by + oy + 3, 3, 2, "gold_d")
    R(d, cx - r + 1, by - r + 4, 3, 2, "gold_l")


def hang_salami(img, x, y, ln=26):
    d = draw_of(img)
    R(d, x, y - 14, 1, 14, "slate")
    R(d, x - 4, y, 9, ln, "lead")
    R(d, x - 3, y + 1, 7, ln - 2, "rose_d")
    R(d, x - 3, y + 1, 2, ln - 2, "ruby")
    for k in range(5, ln, 6):
        R(d, x - 3, y + k, 7, 1, "lead")
    for (ox, oy) in ((1, 7), (-2, 14), (2, 19)):
        d.point((x + ox, y + oy), fill=col("cream"))


def floor_scene(img, y0, y1):
    d = draw_of(img)
    R(d, 0, y0, W, y1 - y0, "wood_d")
    # planks
    for k, y in enumerate(range(y0 + 7, y1, 7)):
        R(d, 0, y, W, 1, "lead")
        off = 0 if k % 2 == 0 else 40
        for x in range(off, W, 80):
            R(d, x, y - 7, 1, 7, "lead")
    R(d, 0, y0, W, 1, "lead")
    # coloured light pools cast by the glass (tinted plank cells, no blending)
    pools = [(120, "sap_d"), (212, "ruby_d"), (292, "gold_d")]
    for (px_, tone) in pools:
        pts = [(px_, y0 + 1), (px_ + 44, y0 + 1), (px_ + 30, y1 - 1), (px_ - 14, y1 - 1)]
        m = poly_mask(W, H, pts)
        px = img.load()
        for y in range(y0 + 1, y1 - 1):
            for x in range(max(0, px_ - 20), min(W, px_ + 50)):
                if m(x, y):
                    a, b = x + y, x - y
                    px[x, y] = P["lead"] if (a % 8 == 0 or b % 8 == 0) else P[tone]


def ledge(img, x, y, w, h=12):
    d = draw_of(img)
    R(d, x, y, w, h, "lead")
    R(d, x + 1, y + 1, w - 2, h - 2, "stone2")
    R(d, x + 1, y + 1, w - 2, 2, "slate")
    R(d, x + 1, y + h - 4, w - 2, 3, "stone")
    for xx in range(x + 14, x + w - 6, 22):
        R(d, xx, y + 3, 1, h - 6, "lead")


def claw_slash(img, x, y):
    """Three tapered Fire-Claw slashes (white core, orange rim, lead outline)."""
    d = draw_of(img)
    for k, ln in enumerate((50, 58, 48)):
        sx, sy = x + k * 13, y - k * 3
        dx, dy = 0.52, 0.85
        ex, ey = sx + dx * ln, sy + dy * ln
        px_, py_ = -dy, dx
        for hw, c, ext in ((4.2, "lead", 2), (3.0, "fire", 1), (1.5, "white", 0)):
            mx, my = sx + (ex - sx) * 0.35, sy + (ey - sy) * 0.35
            pts = [(sx - dx * ext, sy - dy * ext), (mx + px_ * hw, my + py_ * hw), (ex + dx * ext, ey + dy * ext), (mx - px_ * hw, my - py_ * hw)]
            d.polygon(pts, fill=P[c])


def sparks(img, pts, tone="fire_l"):
    d = draw_of(img)
    for (x, y, s) in pts:
        R(d, x - 1, y - 1, s + 2, s + 2, "lead")
    for (x, y, s) in pts:
        R(d, x, y, s, s, tone if s > 1 else "gold_l")


def chain_link(img, x0, y0, x1, y1, lift=8):
    """Gold tail-line between two cards with a lead outline and a diamond node."""
    d = draw_of(img)
    pts = []
    n = 80
    for k in range(n + 1):
        t = k / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t - math.sin(math.pi * t) * lift
        pts.append((round(x), round(y)))
    for (x, y) in pts:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            d.point((x + dx, y + dy), fill=P["lead"])
    for (x, y) in pts:
        d.point((x, y), fill=P["gold_l"])
    mx, my = pts[n // 2]
    d.polygon([(mx, my - 4), (mx + 4, my), (mx, my + 4), (mx - 4, my)], fill=P["lead"])
    d.polygon([(mx, my - 3), (mx + 3, my), (mx, my + 3), (mx - 3, my)], fill=P["gold_l"])
    d.point((mx, my), fill=P["white"])


def draw_battle():
    img, d = new_canvas(W, H, "stone")
    stone_bg(img)
    d = draw_of(img)
    floor_y = 226
    # ---- back wall dressing: pantry shelves
    shelf(img, 126, 186, 208)
    shelf(img, 132, 156, 196)
    for (x, w, h, t) in [(138, 12, 18, "ruby"), (156, 14, 14, "em"), (172, 12, 16, "gold"), (190, 16, 20, "sap"), (210, 12, 14, "ruby")]:
        jar(img, x, 156 - h + 1, w, h, t)
    cheese(img, 286, 156)
    for (x, w, h, t) in [(140, 14, 16, "em"), (160, 12, 20, "gold"), (180, 16, 14, "ruby"), (200, 12, 18, "sap"), (222, 14, 14, "em"), (244, 12, 20, "ruby")]:
        jar(img, x, 186 - h + 1, w, h, t)
    cheese(img, 300, 186, 9)
    floor_scene(img, floor_y, 246)
    # ---- ledges + characters
    ledge(img, 26, floor_y - 6, 84, 14)
    ledge(img, 338, floor_y - 6, 124, 14)
    dom = sprite("domino")
    img.paste(dom, (48, floor_y - 6 - 64), dom)          # lunging 8px toward the boss
    chu = sprite("chubbs")
    img.paste(chu, (352, floor_y - 6 - 96), chu)
    d = draw_of(img)
    claw_slash(img, 366, 142)
    sparks(img, [(358, 140, 3), (426, 140, 2), (440, 178, 3), (356, 190, 2), (414, 128, 1), (446, 158, 2), (376, 196, 2)], "fire_l")

    # ---- top bar: Chubbs
    plate(d, 4, 3, 472, 25)
    xx = T(d, 14, 22, "Chubbs", "title", "gold_l", outline="lead")
    T(d, xx + 6, 22, "the Pantry King", "label", "silver")
    T(d, 268, 21, "HP", "body", "silver")
    hp_bar(img, 284, 11, 96, 11, 54, 90, "ruby", seg=10)
    gx = 285 + round(94 * 54 / 90)
    R(d, gx, 12, round(94 * 9 / 90), 9, "white")             # ghost of the damage just dealt
    T(d, 386, 21, "54/90", "body", "cream")
    draw_rich(img, 424, 22, [("icon", "curl"), "0", ("gap", 6), ("icon", "singe"), "1"])

    # ---- enemy scrap row
    tab(img, 8, 34, "Chubbs's spread", "scrap")
    for i, ln in enumerate(["\"Mmm, fate smells delicious.", "Strength is in my belly now.\""]):
        T(d, 8, 62 + i * 12, ln, "body", "silver")
    row = [("sword", 6), ("cup", 8), ("strength", 8), ("gnaw", 3), ("coin", 8), ("sword", 6)]
    for i, (k, n) in enumerate(row):
        c_ = scrap_card(k, n, bites=((29, 40), (0, 14)) if i % 2 == 0 else ((30, 6), (2, 41)))
        img.paste(c_, (238 + i * 38, 32), c_)

    # ---- reading popup (chain escalates in size and colour)
    px0, py0, pw, ph = 100, 82, 280, 52
    plate(d, px0, py0, pw, ph, fill="night", edge="gold")
    xx = T(d, px0 + 12, py0 + 23, "Fire Claw", "title", "gold_l", outline="lead")
    blit_mask(img, xx + 6, py0 + 10, ARROW, {"#": "gold_l"})
    T(d, xx + 18, py0 + 23, "9!", "num24", "fire_l", outline="lead")
    T(d, px0 + pw - 12, py0 + 20, "Chain x3", "body", "silver", anchor="rs")
    cx_ = px0 + 12
    cx_ = T(d, cx_, py0 + 43, "Nuzzle +2", "body", "white")
    blit_mask(img, cx_ + 4, py0 + 35, ARROW, {"#": "gold"}); cx_ += 14
    cx_ = T(d, cx_, py0 + 43, "Step +2", "body16", "air", outline="lead")
    blit_mask(img, cx_ + 4, py0 + 35, ARROW, {"#": "gold"}); cx_ += 14
    T(d, cx_, py0 + 44, "Catwalk!", "title", "fire_l", outline="lead")

    # ---- damage number over Chubbs
    T(d, 410, 134, "-9", "num32", "fire_l", outline="lead")

    # ---- bottom: Domino's spread
    sx0, sy, pitch = 14, 255, 58
    row = [
        card("fire", 3, 1, "none"),
        card("fire", 4, 1, "common", charm_kind="bell"),
        card("air", 5, 1, "rare", rev=True),
        card("water", 3, 1, "none"),
    ]
    for i, c_ in enumerate(row):
        img.paste(c_, (sx0 + i * pitch, sy - (7 if i == 1 else 0)), c_)
    select_brackets(img, sx0 + pitch, sy - 7, 48, 64)
    chain_link(img, sx0 + 24, sy - 3, sx0 + pitch + 24, sy - 12, lift=6)
    sparks(img, [(sx0 + pitch + 8, sy - 22, 2), (sx0 + pitch + 38, sy - 20, 3), (sx0 + pitch + 22, sy - 26, 1)], "fire_l")
    # Domino status plate
    plate(d, 252, 252, 224, 64)
    R(d, 259, 259, 32, 32, "lead")
    img.paste(sprite("domino").crop((18, 6, 46, 34)).convert("RGB"), (261, 261))
    T(d, 300, 278, "Domino", "title", "gold_l", outline="lead")
    T(d, 466, 275, "Round 1", "body", "silver", anchor="rs")
    T(d, 300, 296, "HP", "body", "silver")
    hp_bar(img, 318, 287, 108, 11, 33, 36, "em", seg=6)
    T(d, 432, 296, "33/36", "body", "cream")
    draw_rich(img, 262, 311, [("chip", "A", "ruby"), ("c", "cream", "2x"), ("gap", 14), ("chip", "B", "sap"), ("c", "cream", "Skip")])
    return img


# --------------------------------------------------------------------------- style sheet
def rose(img, cx, cy, r, seed=3):
    """Rose-window medallion: two rings of jewel wedges, lead tracery, gold heart."""
    px = img.load()
    jew = [ramp("ruby"), ramp("sap"), ramp("gold"), ramp("em")]
    n1, n2 = 8, 16
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            dx, dy = x - cx + 0.0, y - cy + 0.0
            rr = math.hypot(dx, dy)
            if rr > r:
                continue
            ang = (math.atan2(dy, dx) + math.pi) / (2 * math.pi)
            if rr > r - 1.5:
                px[x, y] = P["lead"]
            elif rr < r * 0.2:
                px[x, y] = P["gold_l"] if rr < r * 0.12 else P["lead"]
            elif rr < r * 0.55:
                s = int(ang * n1 * 1.0)
                edge = abs((ang * n1) % 1 - 0) < 0.07 or abs((ang * n1) % 1 - 1) < 0.07
                px[x, y] = P["lead"] if edge or abs(rr - r * 0.55) < 1 else jew[s % 4][1 + (_hash(s, 1, seed) % 2)]
            else:
                s = int(ang * n2)
                f = (ang * n2) % 1
                edge = f < 0.06 or f > 0.94
                px[x, y] = P["lead"] if edge else jew[(s + 2) % 4][[0, 1, 1, 2][_hash(s, 7, seed) % 4]]


def swatch_cell(img, x, y, name, w=46):
    d = draw_of(img)
    c = P[name]
    R(d, x, y, w - 2, 20, "lead")
    R(d, x + 1, y + 1, w - 4, 18, c)
    if name in FAST:
        R(d, x + w - 8, y + 3, 3, 3, "gold_l")
    hx = "#%02X%02X%02X" % c
    T(d, x, y + 31, hx, "tiny", "silver")


def scaled(im, k):
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def sheet_plate(img, x, y, w, h, title):
    d = draw_of(img)
    plate(d, x, y, w, h)
    T(d, x + 14, y + 20, title, "label", "gold")
def story_frame(k):
    """One 216x140 frame of the card-play + reading-chain animation (k = 0..3)."""
    img, d = new_canvas(216, 140, "stone")
    stone_bg(img)
    d = draw_of(img)
    R(d, 0, 100, 216, 40, "wood_d")
    R(d, 0, 100, 216, 1, "lead")
    pitch, x0 = 52, 4
    row = [card("fire", 3, 1, "none"), card("fire", 4, 1, "common", charm_kind="bell"),
           card("air", 5, 1, "rare", rev=True), card("water", 3, 1, "none")]
    lift = 0 if k == 0 else 4
    shake = 2 if k == 3 else 0
    for i, c_ in enumerate(row):
        img.paste(c_, (x0 + i * pitch + shake, 66 - (lift if i == 1 else 0)), c_)
    select_brackets(img, x0 + pitch + shake, 66 - lift, 48, 64)
    if k == 1:   # white flash on the art window, element sparks
        R(d, x0 + pitch + 8, 66 - lift + 16, 32, 32, "white")
        sparks(img, [(x0 + pitch + 4, 40, 3), (x0 + pitch + 40, 36, 2), (x0 + pitch + 22, 28, 3),
                     (x0 + pitch + 12, 22, 1), (x0 + pitch + 34, 18, 2)], "fire_l")
    if k >= 2:
        chain_link(img, x0 + 24, 70, x0 + pitch + 24, 58, lift=7)
    if k == 2:
        T(d, 62, 38, "Nuzzle +2", "body", "white", outline="lead")
    if k == 3:
        T(d, 20, 22, "Step +2", "body16", "air", outline="lead")
        T(d, 104, 40, "Catwalk!", "title", "fire_l", outline="lead")
        T(d, 206, 20, "-9", "num24", "fire_l", outline="lead", anchor="rs")
    return img


def draw_sheet():
    SW, SH = 960, 1100
    img, d = new_canvas(SW, SH, "stone")
    stone_bg(img)
    d = draw_of(img)

    # ---- header
    plate(d, 8, 8, 944, 82)
    T(d, 28, 56, "Bell Tower Stained Glass", "title48", "gold_l", outline="lead")
    T(d, 30, 79, "Nine Lives Arcana as cathedral glass at midnight: jewel cells, bold black lead, near-black stone.", "body", "cream")
    rose(img, 896, 49, 34)

    # ---- palette
    sheet_plate(img, 8, 100, 484, 292, "Palette")
    T(d, 76, 120, "all %d colours RGB565-exact (hex = expanded RGB888)" % len(P), "body", "silver")
    groups = [
        ["lead", "night", "stone", "stone2", "ink", "slate", "silver", "white", "cream", "moon"],
        ["ruby_d", "ruby", "ruby_l", "fire_d", "fire", "fire_l", "gold_d", "gold", "gold_l", "air_d"],
        ["air", "air_l", "sap_d", "sap", "sap_l", "em_d", "em", "em_l", "am_d", "am"],
        ["am_l", "rfire_d", "rfire", "rfire_l", "rair_d", "rair", "rair_l", "rwater_d", "rwater", "rwater_l"],
        ["rearth_d", "rearth", "rearth_l", "scrap_d", "scrap", "scrap_l", "rose", "rose_d", "wood_d", "wood"],
        ["tan"],
    ]
    for gi, g in enumerate(groups):
        for ci, name in enumerate(g):
            swatch_cell(img, 20 + ci * 46, 132 + gi * 40, name)
    R(d, 74, 132 + 5 * 40 + 6, 3, 3, "gold_l")
    T(d, 82, 132 + 5 * 40 + 10, "= fast-fill colour (hi byte = lo byte)", "body", "silver")
    T(d, 82, 132 + 5 * 40 + 24, "0x0000 lead  0x0808 night  0x2929 stone  0x5252 stone2", "body", "slate")

    # ---- type
    sheet_plate(img, 500, 100, 452, 292, "Type")
    T(d, 514, 156, "Bell Tower Arcana", "title", "gold_l", outline="lead")
    T(d, 514, 174, "Jacquard 12 (OFL) - titles and names, 16 / 24 / 48 px", "body", "silver")
    T(d, 514, 196, "ABCDEFGHIJKLM NOPQRSTUVWXYZ", "label", "cream")
    T(d, 514, 214, "abcdefghijklm nopqrstuvwxyz", "label", "cream")
    T(d, 514, 246, "Pixelify Sans (OFL) - body 12 px, numbers 16-32 px", "body", "silver")
    T(d, 514, 264, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "body16", "cream")
    T(d, 514, 282, "abcdefghijklmnopqrstuvwxyz", "body16", "cream")
    T(d, 514, 300, "0123456789 +-x/:!?'\".,", "body16", "gold_l")
    R(d, 514, 310, 426, 1, "stone2")
    T(d, 514, 330, "Fire Claw", "label", "gold_l")
    draw_rich(img, 514, 349, ["Nuzzle +2", ("dot",), "Tail Tap +1", ("dot",), "Step +2", ("gap", 2), ("arrow",), ("f", "body16", "gold_l", "Power 9")])
    T(d, 514, 368, "Fire next to Water? They'll hiss at each other.", "body", "silver")
    T(d, 514, 384, "Silkscreen 8 (OFL): sheet captions only", "tiny", "slate")

    # ---- cards
    sheet_plate(img, 8, 402, 664, 218, "Cards")
    T(d, 62, 422, "48x64 spread  /  40x54 box  /  32x44 scrap", "body", "silver")
    cy0, cx = 434, 100
    fire4 = card("fire", 4, 1, "common", charm_kind="bell")
    s2 = scaled(fire4, 2)
    img.paste(s2, (cx, cy0), s2)
    left = [("number", (14, 14), 14), ("element", (14, 114), 114)]
    right = [("stars", (84, 14), 14), ("32x32 art", (80, 64), 64), ("charm gem", (84, 114), 114)]
    for lab, (ax, ay), ly in left:
        R(d, cx + ax - 1, cy0 + ay - 1, 3, 3, "gold_l")
        d.line([(cx + ax, cy0 + ay), (cx - 6, cy0 + ly)], fill=col("gold_l"))
        T(d, cx - 10, cy0 + ly + 4, lab, "body", "cream", anchor="rs")
    for lab, (ax, ay), ly in right:
        R(d, cx + ax - 1, cy0 + ay - 1, 3, 3, "gold_l")
        d.line([(cx + ax, cy0 + ay), (cx + 102, cy0 + ly)], fill=col("gold_l"))
        T(d, cx + 108, cy0 + ly + 4, lab, "body", "cream")
    cap_y = cy0 + 140
    T(d, cx, cap_y, "Fire 4 Upright", "body", "silver")
    T(d, cx, cap_y + 12, "common ring, Bell", "body", "slate")
    items = [
        (card("water", 3, 2, "none", rev=True, charm_kind="catnip"), "Water 3", "Reversed"),
        (card("fire", 19, 0, "legendary", major=("XIX", sun_art)), "XIX The Sun", "Major"),
        (card_back(), "Card back", "cat-eye moon"),
    ]
    ox = 288
    for im_, c1, c2 in items:
        s2 = scaled(im_, 2)
        img.paste(s2, (ox, cy0), s2)
        T(d, ox, cap_y, c1, "body", "silver")
        T(d, ox, cap_y + 12, c2, "body", "slate")
        ox += 98
    s2 = scaled(scrap_card("sword", 3), 2)
    img.paste(s2, (ox, cy0 + 20), s2)
    T(d, ox, cap_y, "Broken Sword 3", "body", "silver")
    T(d, ox, cap_y + 12, "rat scrap", "body", "slate")
    for i, (rn, rc) in enumerate((("none", "white"), ("common", "sap_l"), ("rare", "am"), ("legendary", "gold_l"), ("curse", "ruby"))):
        R(d, 22 + i * 62, cap_y + 28, 56, 5, "lead")
        R(d, 23 + i * 62, cap_y + 29, 54, 3, rc)
        T(d, 22 + i * 62, cap_y + 44, rn, "tiny", "silver")
    T(d, 340, cap_y + 44, "Reversed: art flipped + cool ramp (violet / teal / steel)", "body", "slate")

    # ---- icons
    sheet_plate(img, 680, 402, 272, 218, "Icons")
    for i, (n, lab) in enumerate((("fire", "Fire"), ("air", "Air"), ("water", "Water"), ("earth", "Earth"))):
        paste_rgba(img, scaled(icon(n), 3), 694 + i * 62, 432)
        T(d, 694 + i * 62, 482, lab, "body", "silver")
    for i, (n, lab) in enumerate((("singe", "Singe"), ("puff", "Puff"), ("drowsy", "Drowsy"), ("curl", "Curl"), ("leap", "Leap"))):
        paste_rgba(img, scaled(icon(n), 2), 694 + i * 50, 496)
        T(d, 694 + i * 50, 536, lab, "body", "silver")
    for i, (n, lab) in enumerate((("catnip", "Catnip"), ("bell", "Bell"), ("nine", "Nine Lives"))):
        paste_rgba(img, scaled(charm(n), 3), 694 + i * 82, 550)
        T(d, 694 + i * 82, 596, lab, "body", "silver")

    # ---- characters
    sheet_plate(img, 8, 630, 664, 252, "Saints of the Attic")
    T(d, 190, 650, "AI-drawn, palette-snapped, shown at 2x", "body", "silver")
    x_ = 24
    for n, cap in (("domino", "Domino"), ("zero", "Zero"), ("rat", "Gray Rat"), ("chubbs", "Chubbs, the Pantry King")):
        s = scaled(sprite(n), 2)
        img.paste(s, (x_, 664 + 192 - s.height), s)
        T(d, x_, 877, cap, "label", "gold_l")
        x_ += s.width + 14

    # ---- background samples
    sheet_plate(img, 680, 630, 272, 252, "Backgrounds")
    t1 = Image.new("RGB", (48, 48), P["stone"]); stone_bg(t1, 0, 48)
    t2 = Image.new("RGB", (48, 48), P["sap"]); glass(t2, 0, 0, 48, 48, ramp("sap"), cell=8, seed=2, weights=(2, 4, 1))
    t3 = Image.new("RGB", (48, 48), P["wood_d"]); dd3 = draw_of(t3)
    for k_, y in enumerate(range(6, 48, 7)):
        R(dd3, 0, y, 48, 1, "lead")
        for xk in range(0 if k_ % 2 == 0 else 20, 48, 40):
            R(dd3, xk, y - 6, 1, 6, "lead")
    for i, (t, cap) in enumerate(((t1, "ashlar"), (t2, "quarrel 8"), (t3, "planks"))):
        img.paste(t, (694 + i * 82, 656))
        T(d, 694 + i * 82, 718, cap, "body", "silver")
    bgc = Image.new("RGB", (244, 84), P["stone"])
    stone_bg(bgc, 0, 84)
    rose(bgc, 40, 40, 34)
    lancet(bgc, 96, 8, 30, 66, ramp("em"), seed=2, weights=(2, 4, 1))
    lancet(bgc, 134, 8, 30, 66, ramp("ruby"), seed=4, weights=(2, 4, 1))
    lancet(bgc, 172, 8, 30, 66, ramp("gold"), seed=6, weights=(2, 4, 1))
    bd = draw_of(bgc)
    R(bd, 0, 76, 244, 8, "wood_d")
    R(bd, 0, 76, 244, 1, "lead")
    img.paste(bgc, (694, 730))
    box_frame(d, 693, 729, 246, 86, "lead")
    T(d, 694, 834, "Dominant 0x2929 fast fill + flat plates", "body", "silver")
    T(d, 694, 848, "Glass lives in small vignettes and", "body", "slate")
    T(d, 694, 860, "cards; windows are 2-bit lead + fills.", "body", "slate")

    # ---- storyboard
    sheet_plate(img, 8, 892, 944, 200, "Animation")
    T(d, 98, 912, "card play + reading chain, frames at 1x (hardware blits only the card rects and the float text)", "body", "silver")
    caps = ["1  Lift 4 px + brackets", "2  White flash 2f + sparks", "3  Tail-line + name float", "4  Chain pop + 2 px shake"]
    for k in range(4):
        fx = 20 + k * 228
        img.paste(story_frame(k), (fx, 924))
        box_frame(d, fx - 1, 923, 218, 142, "lead")
        T(d, fx, 1080, caps[k], "body", "cream")
    return img


# --------------------------------------------------------------------------- validation + main
def check(img, name, expect=None):
    img = img.convert("RGB")
    cols = set(img.get_flattened_data()) if hasattr(img, "get_flattened_data") else set(img.getdata())
    bad = [c for c in cols if (((c[0] >> 3) << 3) | (c[0] >> 5), ((c[1] >> 2) << 2) | (c[1] >> 6), ((c[2] >> 3) << 3) | (c[2] >> 5)) != c]
    print(f"{name}: {img.size[0]}x{img.size[1]}, {len(cols)} colours, non-RGB565: {len(bad)}")
    if expect:
        assert img.size == expect, (name, img.size)
    assert not bad, bad[:5]


def main():
    spread, battle = draw_spread(), draw_battle()
    out = lambda n: os.path.join(HERE, n)
    spread.save(out("spread.png"))
    battle.save(out("battle.png"))
    spread.resize((W * 2, H * 2), Image.NEAREST).save(out("spread@2x.png"))
    battle.resize((W * 2, H * 2), Image.NEAREST).save(out("battle@2x.png"))
    sheet = draw_sheet()
    sheet.save(out("sheet.png"))
    check(spread, "spread.png", (W, H))
    check(battle, "battle.png", (W, H))
    check(sheet, "sheet.png")


if __name__ == "__main__":
    main()
