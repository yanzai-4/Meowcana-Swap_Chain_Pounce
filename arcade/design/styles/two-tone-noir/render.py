"""Two-Tone Noir style board for "Nine Lives Arcana".

Reproduces spread.png, battle.png, their @2x versions and sheet.png from raw/ (PixelLab sprites)
and fonts/ (OFL pixel fonts). Everything else is drawn in code, pixel-perfect, 7 RGB565-exact colors.

    python render.py            # writes all PNGs next to this file
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
FONTS = os.path.join(HERE, "fonts")


# --------------------------------------------------------------------------- palette
def rgb565(word):
    r, g, b = word >> 11, (word >> 5) & 63, word & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)


# every value is a "fast fill" word (high byte == low byte) except the two neutrals, which are 0x0000 / 0xFFFF
INK = rgb565(0x0000)      # #000000  ink / night
PAPER = rgb565(0xFFFF)    # #FFFFFF  paper / moon
FIRE = rgb565(0xE0E0)     # #E71C00  vermilion
AIR = rgb565(0xE6E6)      # #E7DF31  saffron
WATER = rgb565(0x3D3D)    # #39A6EF  cyan-blue
EARTH = rgb565(0x4545)    # #42AA29  moss
GOLD = rgb565(0xE4E4)     # #E79E21  rarity gold / top chain
PALETTE = [("INK", 0x0000), ("PAPER", 0xFFFF), ("FIRE", 0xE0E0), ("AIR", 0xE6E6),
           ("WATER", 0x3D3D), ("EARTH", 0x4545), ("GOLD", 0xE4E4)]
ELEM = {"fire": FIRE, "air": AIR, "water": WATER, "earth": EARTH}


def hexs(c):
    return "#%02X%02X%02X" % c


# --------------------------------------------------------------------------- fonts
FONT_SOURCES = {"Jersey10-Regular": "jersey10", "Jersey15-Regular": "jersey15", "Jersey20-Regular": "jersey20",
                "Jersey25-Regular": "jersey25", "DotGothic16-Regular": "dotgothic16", "Jacquard24-Regular": "jacquard24"}


def ensure_fonts():
    """Download the six OFL fonts used (google/fonts repo) into fonts/ if missing, plus their OFL texts."""
    import urllib.request
    os.makedirs(FONTS, exist_ok=True)
    for fname, folder in FONT_SOURCES.items():
        for remote, local in ((fname + ".ttf", fname + ".ttf"), ("OFL.txt", "OFL-" + folder + ".txt")):
            path = os.path.join(FONTS, local)
            if not os.path.exists(path):
                urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/%s/%s" % (folder, remote), path)


_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(os.path.join(FONTS, name + ".ttf"), size)
    return _fc[key]


J15 = lambda: font("Jersey15-Regular", 15)      # card numbers, micro labels (cap 8)
J20 = lambda: font("Jersey20-Regular", 20)      # names, titles (cap 12)
J25 = lambda: font("Jersey25-Regular", 25)      # buttons, big numbers (cap 16)
BODY = lambda: font("DotGothic16-Regular", 16)   # body text: 8x16 cell (matches the hardware's 8x16 ASCII font), 56 chars = 448 px
JAC = lambda: font("Jacquard24-Regular", 24)    # wordmark, boss name, Major titles
CAP = {}


def cap(f):
    k = id(f)
    if k not in CAP:
        CAP[k] = -f.getbbox("H", anchor="ls")[1]
    return CAP[k]


def adv(ch, f):
    return int(round(f.getlength(ch)))


def tw(s, f, sp=0):
    """Width of a string drawn glyph by glyph with integer advances (what a baked bitmap font does)."""
    return sum(adv(ch, f) for ch in s) + sp * max(0, len(s) - 1)


def draw_str(d, x, yb, s, f, fill, sp=0):
    for ch in s:
        d.text((x, yb), ch, font=f, fill=fill, anchor="ls")
        x += adv(ch, f) + sp


def text(d, x, y, s, f, fill, sp=0, anchor="l"):
    """Draw text with its CAP-TOP at y (so layouts are grid-exact). anchor l/r/m on x."""
    w = tw(s, f, sp)
    if anchor == "r":
        x -= w
    elif anchor == "m":
        x -= w // 2
    draw_str(d, x, y + cap(f), s, f, fill, sp)
    return w


# --------------------------------------------------------------------------- canvas helpers
class Cv:
    def __init__(self, w, h, bg=INK):
        self.im = Image.new("RGB", (w, h), bg)
        self.d = ImageDraw.Draw(self.im)
        self.d.fontmode = "1"
        self.w, self.h = w, h

    def rect(self, x, y, w, h, c):
        if w > 0 and h > 0:
            self.d.rectangle([x, y, x + w - 1, y + h - 1], fill=c)

    def frame(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.im.putpixel((x, y), c)

    def hline(self, x, y, w, c):
        self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.rect(x, y, 1, h, c)

    def dotline(self, x, y, w, c, step=2, vertical=False):
        for i in range(0, w, step):
            self.px(x, y + i, c) if vertical else self.px(x + i, y, c)

    def blit(self, rows, x, y, fg, k=None, flip=False):
        """rows: ascii bitmap. '#' fg, 'k' knock-out (k colour), anything else transparent."""
        if flip:
            rows = rows[::-1]
        for j, r in enumerate(rows):
            for i, ch in enumerate(r):
                if ch == "#":
                    self.px(x + i, y + j, fg)
                elif ch == "k" and k is not None:
                    self.px(x + i, y + j, k)

    def paste(self, img, x, y):
        self.im.paste(img, (x, y), img if img.mode == "RGBA" else None)

    def text(self, *a, **k):
        return text(self.d, *a, **k)


BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def dither(cv, x, y, w, h, level, c1=PAPER, c2=INK, ox=0, oy=0):
    """Ordered 4x4 Bayer fill. level 0..16 = how many of 16 cells are c1."""
    for j in range(h):
        for i in range(w):
            cv.px(x + i, y + j, c1 if BAYER[(y + j + oy) % 4][(x + i + ox) % 4] < level else c2)


# --------------------------------------------------------------------------- icons (hand-drawn bitmaps)
def gen(w, h, fn):
    """Build an ascii bitmap from fn(x, y) -> '#', 'k' or '.' (pixel centres sampled)."""
    return ["".join(fn(x + 0.5, y + 0.5) for x in range(w)) for y in range(h)]


def inell(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0


ICON = {}
ICON["fire"] = [
    "......#.....",
    ".....##.....",
    "....###..#..",
    "....####.##.",
    "...#####.##.",
    "..######.###",
    "..#########.",
    ".####kk#####",
    ".###kkkk####",
    ".###kkkk####",
    "..###kk####.",
    "...######...",
]
ICON["air"] = [
    "............",
    "############",
    "############",
    "............",
    ".##########.",
    "............",
    "..########..",
    "............",
    "...######...",
    "....####....",
    ".....##.....",
    "............",
]
ICON["water"] = [
    ".....##.....",
    ".....##.....",
    "....####....",
    "....####....",
    "...######...",
    "..########..",
    "..########..",
    ".####k#####.",
    ".###k######.",
    ".###k######.",
    "..########..",
    "...######...",
]
ICON["earth"] = gen(12, 12, lambda x, y: ("." if not inell(x, y, 6, 6, 6, 6) else
                    "k" if (3.2 < ((x - 6) ** 2 + (y - 6) ** 2) ** .5 < 4.4) else "#"))
# statuses
ICON["singe"] = [
    "...#........",
    "..##...#....",
    "..###..##...",
    ".##.##.###..",
    ".#..###.##..",
    ".#...##..##.",
    ".##..#...##.",
    ".###.....#..",
    "..##....##..",
    "...##..##...",
    "....####....",
    ".....##.....",
]
ICON["puff"] = [
    "#...#..#...#",
    ".#..#..#..#.",
    "..#.####.#..",
    "...######...",
    "#.########.#",
    ".###k##k###.",
    "#####kk#####",
    ".##########.",
    "#.########.#",
    "...######...",
    "..#.####.#..",
    ".#..#..#..#.",
]
ICON["drowsy"] = gen(12, 12, lambda x, y: (
    "#" if (x > 7.5 and y < 4.5 and (y < 1.5 or y > 3 or abs(x - 11 + (y - 1.5) * 1.3) < 1.1)) else
    "#" if (inell(x, y, 5, 6.5, 5, 5) and not inell(x, y, 7.6, 5.2, 4.3, 4.3)) else "."))
ICON["curl"] = [
    "...######...",
    "..##....##..",
    ".##..##..##.",
    ".#..#..#..#.",
    "##.#.##.#.##",
    "#..#.#..#..#",
    "##.#.####.##",
    ".#..#.....#.",
    ".##..#####..",
    "..##........",
    "...########.",
    "............",
]
ICON["leap"] = gen(12, 12, lambda x, y: (
    "#" if ((y < 2 and x > 5) or (x > 10 and y < 7) or (abs((x - 1) + (y - 10)) < 1.0 and 0 < x < 11 and y > 0)
            or (abs((x - 2) + (y - 10)) < 1.0 and 1 < x < 11 and y > 0 and y < 11)) else
    "#" if (y > 10.5 and x < 5) else "."))
# charms 8x8
CHARM = {
    "catnip": [
        ".....##.",
        "....###.",
        ".##.##..",
        ".###.#..",
        "..###...",
        "...##...",
        "...#....",
        "...#....",
    ],
    "bell": [
        "...##...",
        "..####..",
        "..####..",
        ".######.",
        ".######.",
        "########",
        "........",
        "...##...",
    ],
    "nine": [
        ".##..##.",
        "########",
        "###kk###",
        "##k##k##",
        ".##kk##.",
        "..####..",
        "...##...",
        "........",
    ],
}
STAR7 = [
    "...#...",
    "...#...",
    "#######",
    ".#####.",
    "..###..",
    ".##.##.",
    ".#...#.",
]
PAW = gen(14, 13, lambda x, y: (
    "#" if (inell(x, y, 1.6, 6.8, 1.5, 2.1) or inell(x, y, 12.4, 6.8, 1.5, 2.1)
            or inell(x, y, 5.0, 2.6, 1.5, 2.2) or inell(x, y, 9.0, 2.6, 1.5, 2.2)
            or inell(x, y, 7, 10.2, 4.6, 2.8)) else "."))
# scrap icons 12x12
SCRAP = {
    "sword": [
        "..........##",
        ".........###",
        "........###.",
        ".......###..",
        "..#...###...",
        "..##.###....",
        "...####.....",
        "....##......",
        "...####.....",
        "..##..##....",
        ".##....#....",
        "##..........",
    ],
    "coin": [
        "...######...",
        "..########..",
        ".####kk####.",
        ".###k##k###.",
        "####k##k####",
        "####kk#k####",
        "####k#kk####",
        "####k##k####",
        ".###k##k###.",
        ".####kk####.",
        "..########..",
        "...######...",
    ],
    "cup": [
        ".##########.",
        ".##########.",
        ".#kkkkkkkk#.",
        ".#kkkkkkkk#.",
        ".##########.",
        "..########..",
        "..###k####..",
        "...######...",
        "....####....",
        ".....##.....",
        ".....##.....",
        "..########..",
    ],
    "gnaw": [
        "############",
        "#.##.##.##.#",
        ".#kk#kk#kk#.",
        "..#k..k..k..",
        "............",
        "..#k..k..k..",
        ".#kk#kk#kk#.",
        "#.##.##.##.#",
        "############",
        "............",
        "............",
        "............",
    ],
    "lion": [
        "..#.####.#..",
        ".##########.",
        "############",
        "###k####k###",
        "###kk##kk###",
        "####k##k####",
        "#####kk#####",
        "####k##k####",
        ".###kkkk###.",
        "..########..",
        "...######...",
        "....####....",
    ],
}


# --------------------------------------------------------------------------- sprites (PixelLab output -> strict 1-bit)
def onebit(name, rim=True, flip=False, contrast=(46, 214)):
    """Load raw/<name>.png -> RGBA made only of INK / PAPER. Mid-tones become 4x4 Bayer dither;
    rim=True adds a 1 px PAPER rim-light outside the silhouette so black fur reads on a black stage."""
    src = Image.open(os.path.join(RAW, name + ".png")).convert("RGBA")
    if flip:
        src = src.transpose(Image.FLIP_LEFT_RIGHT)
    w, h = src.size
    alpha = src.split()[3].point(lambda v: 255 if v > 110 else 0)
    gray = src.convert("L")
    lo, hi = contrast
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    po, ga, aa = out.load(), gray.load(), alpha.load()
    for y in range(h):
        for x in range(w):
            if aa[x, y]:
                t = (ga[x, y] - lo) / float(hi - lo)
                on = t >= 1 or (t > 0 and t > (BAYER[y % 4][x % 4] + .5) / 16)
                po[x, y] = (PAPER if on else INK) + (255,)
    if rim:
        for y in range(h):
            for x in range(w):
                if not aa[x, y]:
                    dark = any(0 <= x + dx < w and 0 <= y + dy < h and aa[x + dx, y + dy] and po[x + dx, y + dy][:3] == INK
                               for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                    if dark:
                        po[x, y] = PAPER + (255,)
    return out


def silhouette(img, color):
    """Solid-colour copy of an RGBA sprite (hurt flash / ghost shadows)."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(Image.new("RGBA", img.size, color + (255,)), (0, 0), img.split()[3])
    return out


def invert_sprite(img):
    px = img.load()
    out = img.copy()
    po = out.load()
    for y in range(img.height):
        for x in range(img.width):
            if px[x, y][3]:
                po[x, y] = (INK if px[x, y][:3] == PAPER else PAPER) + (255,)
    return out


def ghostify(img):
    """Zero is a ghost and the hardware has no alpha: thin ink lines and shading become a dotted checker,
    only solid dark clusters (eyes, nose) stay black."""
    w, h = img.size
    out = img.copy()
    po, px = out.load(), img.load()

    def dark(x, y):
        return 0 <= x < w and 0 <= y < h and px[x, y][3] and px[x, y][:3] == INK
    for y in range(h):
        for x in range(w):
            if dark(x, y) and sum(dark(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)) < 6:
                po[x, y] = (INK if (x + y) % 2 == 0 else PAPER) + (255,)
    return out


def content_box(img):
    return img.split()[3].getbbox()


# --------------------------------------------------------------------------- cards
def shrink(rows, n, thr=0.38):
    m = Image.new("L", (len(rows[0]), len(rows)), 0)
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "#":
                m.putpixel((i, j), 255)
    m = m.resize((n, n), Image.BOX)
    return ["".join("#" if m.getpixel((i, j)) > 255 * thr else "." for i in range(n)) for j in range(n)]


def scale2(rows):
    return ["".join(c * 2 for c in r) for r in rows for _ in (0, 1)]


PIPS = {}


AIR_SMALL = {8: ["########", "........", ".######.", "........", "..####..", "........", "...##...", "........"],
             6: ["######", "......", ".####.", "......", "..##..", "......"]}


def pip(elem, p):
    key = (elem, p)
    if key not in PIPS:
        if p == 12:
            PIPS[key] = ICON[elem]
        elif p == 24:
            PIPS[key] = scale2(ICON[elem])
        elif elem == "air":
            PIPS[key] = AIR_SMALL[p]
        else:
            PIPS[key] = shrink(ICON[elem], p)
    return PIPS[key]


def pip_layout(n, S):
    """-> (pip size, [(x, y) top-left inside an SxS window])."""
    if n == 1:
        return 24, [((S - 24) // 2, (S - 24) // 2)]
    p = {2: 12, 3: 8, 4: 12}.get(n, 8 if n <= 6 else 6)
    if S < 32:
        p = {2: 8, 4: 8}.get(n, p)
    cl, cr, cc = S * 0.29, S * 0.71, S * 0.5

    def X(c):
        return int(round(c - p / 2.0))

    def Y(i, k, m=None):
        m = 3 if m is None else m
        return int(round(m + i * (S - 2 * m - p) / float(k - 1))) if k > 1 else (S - p) // 2

    if n == 2:
        pos = [(X(cc), Y(0, 2, 4)), (X(cc), Y(1, 2, 4))]
    elif n == 3:
        pos = [(X(cc), Y(i, 3, 3)) for i in range(3)]
    elif n == 4:
        pos = [(X(c), Y(i, 2, 4)) for i in range(2) for c in (cl, cr)]
    elif n == 5:
        pos = [(X(c), Y(i, 2, 3)) for i in range(2) for c in (cl, cr)] + [(X(cc), Y(0, 1))]
    elif n == 6:
        pos = [(X(c), Y(i, 3, 3)) for i in range(3) for c in (cl, cr)]
    elif n == 7:
        pos = [(X(c), Y(i, 3, 3)) for i in range(3) for c in (cl, cr)] + [(X(cc), Y(0.5, 3, 3))]
    elif n == 8:
        pos = [(X(c), Y(i, 4, 2)) for i in range(4) for c in (cl, cr)]
    elif n == 9:
        pos = [(X(c), Y(i, 4, 2)) for i in range(4) for c in (cl, cr)] + [(X(cc), Y(1.5, 4, 2))]
    else:
        pos = ([(X(c), Y(i, 4, 2)) for i in range(4) for c in (cl, cr)]
               + [(X(cc), Y(0.5, 4, 2)), (X(cc), Y(2.5, 4, 2))])
    return p, pos


def art_sun(bg, sun, cat):
    """32x32 'Sunbeam Cat' portrait: a cat loafing on a windowsill, the sun is a cat's eye."""
    a = Cv(32, 32, bg)
    d = a.d
    cx, cy = 16, 9
    for k in range(12):                      # rays
        ang = k * math.pi / 6
        r1 = 13.5 if k % 2 == 0 else 11.5
        d.line([cx + math.cos(ang) * 8.5, cy + math.sin(ang) * 8.5,
                cx + math.cos(ang) * r1, cy + math.sin(ang) * r1], fill=sun)
    d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=sun)
    for y in range(cy - 7, cy + 8):          # slit pupil: the sun is a cat's eye
        t = 1 - abs(y - cy) / 7.0
        w = max(0, int(round(2.4 * t)))
        a.rect(cx - w, y, 2 * w + 1, 1, bg)
    a.rect(0, 29, 32, 3, cat)                               # sill
    d.ellipse([6, 22, 26, 36], fill=cat)                    # loaf body
    d.ellipse([11, 15, 21, 25], fill=cat)                   # head
    d.polygon([(11, 18), (11, 11), (15, 16)], fill=cat)     # ears
    d.polygon([(21, 18), (21, 11), (17, 16)], fill=cat)
    a.rect(13, 19, 2, 2, sun)                               # eyes
    a.rect(17, 19, 2, 2, sun)
    return a.im


def card(kind="minor", elem="fire", n=3, rev=False, stars=1, charm=None, rarity="none",
         numeral=None, size="L", art=None, ghost=False):
    """Return RGBA card. kind minor|major. size L=48x64 (spread/battle) S=40x54 (box)."""
    W, H, S = (48, 64, 32) if size == "L" else (40, 54, 26)
    fg = PAPER if rev else INK
    face = INK if rev else PAPER
    acc = ELEM[elem]
    c = Cv(W, H, face)
    c.frame(0, 0, W, H, PAPER)                                  # edge line (white card / white outline)
    if rarity in ("common", "rare"):
        c.frame(1, 1, W - 2, H - 2, fg)
    if rarity == "rare":
        for (sx, sy) in ((1, 1), (W - 2, 1), (1, H - 2), (W - 2, H - 2)):
            for k in range(3):
                for l in range(3 - k):
                    c.px(sx + (k if sx == 1 else -k), sy + (l if sy == 1 else -l), fg)
    if rarity == "legend":
        c.frame(0, 0, W, H, GOLD, 2)
    if rarity == "curse":
        c.frame(1, 1, W - 2, H - 2, FIRE)
    # header: number + stars
    label = numeral if numeral else str(n)
    c.text(4, 3, label, J15(), fg)
    for i in range(stars):
        c.blit(STAR7, W - 4 - 7 - i * 8, 3, fg)
    # art window
    wx, wy = (W - S) // 2, 14 if size == "L" else 12
    c.frame(wx - 1, wy - 1, S + 2, S + 2, fg)
    field = INK if rev else acc
    ink = acc if rev else INK
    c.rect(wx, wy, S, S, field)
    if kind == "minor":
        p, pos = pip_layout(n, S)
        for (px_, py_) in pos:
            rows = pip(elem, p)
            c.blit(rows, wx + px_, wy + py_, ink, k=field, flip=rev)
    else:
        img = art(field, PAPER if not rev else acc, ink if not rev else PAPER) if art else None
        if img is not None:
            if rev:
                img = img.transpose(Image.FLIP_TOP_BOTTOM)
            if S < 32:
                o = (32 - S) // 2
                img = img.crop((o, o, o + S, o + S))
            c.im.paste(img, (wx, wy))
    # element icon bottom-left, charm gem bottom-right
    iy = H - 15 if size == "L" else H - 14
    c.blit(ICON[elem], 5, iy, acc if rev else fg, k=face)
    if charm:
        gx, gy = W - 15, iy + 1
        c.rect(gx, gy, 10, 10, fg)
        c.blit(CHARM[charm], gx + 1, gy + 1, GOLD if charm == "nine" else face, k=fg)
    img = c.im.convert("RGBA")
    for (x, y) in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)):
        img.putpixel((x, y), (0, 0, 0, 0))
    return img


def scrap(kind="sword", n=3, size="M", bites=((0, 14), (31, 31)), chewed=False):
    """Rat scrap: no fate, so no colour. Torn halftone paper with bite marks. 32x44."""
    W, H = 32, 44
    c = Cv(W, H, PAPER)
    dither(c, 0, 0, W, H, 13, PAPER, INK)
    c.rect(3, 3, W - 6, H - 6, PAPER)
    c.frame(3, 3, W - 6, H - 6, INK)
    c.text(6, 6, str(n), J15(), INK)
    c.rect(8, 19, 16, 16, PAPER)
    c.blit(SCRAP[kind], 10, 21, INK, k=PAPER)
    c.frame(8, 19, 16, 16, INK)
    img = c.im.convert("RGBA")
    px = img.load()
    # torn top edge, torn bottom edge
    rnd = random.Random(7 + n)
    for x in range(W):
        for y in range(rnd.randint(1, 3)):
            px[x, y] = (0, 0, 0, 0)
        for y in range(H - rnd.randint(0, 2), H):
            px[x, y] = (0, 0, 0, 0)
    for (bx, by) in bites:
        for y in range(H):
            for x in range(W):
                if (x - bx) ** 2 + (y - by) ** 2 <= 11:
                    px[x, y] = (0, 0, 0, 0)
    # 1px paper outline around the silhouette so it reads on black
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    po = out.load()
    for y in range(H):
        for x in range(W):
            if px[x, y][3]:
                po[x, y] = px[x, y]
    for y in range(H):
        for x in range(W):
            if px[x, y][3] and any(not (0 <= x + dx < W and 0 <= y + dy < H) or not px[x + dx, y + dy][3]
                                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                po[x, y] = PAPER + (255,)
    return out


def chewed_card(elem="fire", icon="lion"):
    """A stolen Major in a rat's hand: reversed (black), chewed edges, keeps its element colour."""
    W, H = 32, 44
    c = Cv(W, H, INK)
    c.frame(0, 0, W, H, PAPER)
    c.rect(4, 5, W - 8, 24, ELEM[elem])
    c.frame(3, 4, W - 6, 26, PAPER)
    c.blit(SCRAP[icon], 10, 11, INK, k=ELEM[elem])
    c.blit(ICON[elem], 4, 31, ELEM[elem], k=INK)
    c.blit(STAR7, W - 11, 33, PAPER)
    img = c.im.convert("RGBA")
    px = img.load()
    for (bx, by) in ((31, 6), (0, 38), (31, 40)):
        for y in range(H):
            for x in range(W):
                if (x - bx) ** 2 + (y - by) ** 2 <= 14:
                    px[x, y] = (0, 0, 0, 0)
    return img


def card_back(size="L"):
    W, H = (48, 64) if size == "L" else ((40, 54) if size == "S" else (32, 44))
    c = Cv(W, H, INK)
    c.frame(0, 0, W, H, PAPER)
    c.frame(3, 3, W - 6, H - 6, PAPER)
    cx, cy = (W - 1) / 2.0, (H - 1) / 2.0
    for y in range(4, H - 4):
        for x in range(4, W - 4):
            dx, dy = x - cx, y - cy
            r = (dx * dx + dy * dy) ** .5
            sc = W / 48.0
            lens = abs(dy) <= 8 * sc * max(0, 1 - (dx / (13.0 * sc)) ** 2)
            if lens:
                slit = abs(dx) <= (0.6 + 2.4 * sc * max(0, 1 - abs(dy) / (8.0 * sc)))
                c.px(x, y, INK if slit else GOLD)
            elif r < 17 * sc and BAYER[y % 4][x % 4] < 3 * (1 - r / (17.0 * sc)) * 4:
                c.px(x, y, PAPER)
    c.px(int(cx - 3), int(cy - 3), PAPER)
    for k in range(8):                                    # rays
        ang = k * math.pi / 4 + math.pi / 8
        for t in range(int(18 * W / 48), int(21 * W / 48) + 1):
            c.px(int(round(cx + math.cos(ang) * t)), int(round(cy + math.sin(ang) * t * 1.15)), PAPER)
    for (qx, qy) in ((8, 8), (W - 9, 8), (8, H - 9), (W - 9, H - 9)):             # corner diamonds
        for (ox, oy) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            c.px(qx + ox, qy + oy, PAPER)
    img = c.im.convert("RGBA")
    for (x, y) in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)):
        img.putpixel((x, y), (0, 0, 0, 0))
    return img


def slot(w=48, h=64, held=False):
    """Empty slot: dotted outline. held=True -> ghost of the picked-up card (denser dots + paw)."""
    c = Cv(w, h, INK)
    step = 2
    for i in range(0, w, step):
        c.px(i, 0, PAPER)
        c.px(i, h - 1, PAPER)
    for j in range(0, h, step):
        c.px(0, j, PAPER)
        c.px(w - 1, j, PAPER)
    cx, cy = w // 2, h // 2
    for (x, y) in ((cx - 2, cy), (cx - 1, cy), (cx, cy), (cx + 1, cy)):
        c.px(x, y, PAPER)
    img = c.im.convert("RGBA")
    px = img.load()
    for y in range(h):
        for x in range(w):
            if px[x, y][:3] == INK:
                px[x, y] = (0, 0, 0, 0)
    return img


# --------------------------------------------------------------------------- UI kit
ARROW = [
    "....#...",
    ".....#..",
    "#######.",
    ".....#..",
    "....#...",
]
CLAW = gen(12, 12, lambda x, y: "#" if any(abs((x - 1 - 2.2 * i) - (11 - y) * 0.55) < 0.8 and y > 0.5 for i in range(3)) else ".")


def T(cv, x, yb, s, f, color, sp=0, anchor="l"):
    """Baseline-anchored text (yb = baseline row)."""
    w = tw(s, f, sp)
    if anchor == "r":
        x -= w
    elif anchor == "m":
        x -= w // 2
    draw_str(cv.d, x, yb, s, f, color, sp)
    return w


def rich(cv, x, yb, parts, anchor="l"):
    """parts: ('t',str,font,color[,sp]) ('sep',color) ('arrow',color) ('star',color) ('icon',name,color) ('gap',n)"""
    def width(p):
        k = p[0]
        if k == "t":
            return tw(p[1], p[2], p[4] if len(p) > 4 else 0)
        return {"sep": 4, "arrow": 9, "star": 7, "icon": 12, "gap": p[1] if len(p) > 1 else 0}[k] if k != "gap" else p[1]
    total = sum(width(p) for p in parts)
    if anchor == "r":
        x -= total
    for p in parts:
        k = p[0]
        if k == "t":
            T(cv, x, yb, p[1], p[2], p[3], p[4] if len(p) > 4 else 0)
        elif k == "sep":
            cv.rect(x + 1, yb - 6, 2, 2, p[1])
        elif k == "arrow":
            cv.blit(ARROW, x, yb - 7, p[1])
        elif k == "star":
            cv.blit(STAR7, x, yb - 7, p[1])
        elif k == "icon":
            cv.blit(ICON[p[1]], x, yb - 10, p[2], k=INK)
        x += width(p)
    return total


def keycap(cv, x, y, letter, fg=INK, bg=PAPER):
    """12x12 round button glyph with the letter knocked out."""
    for j in range(12):
        for i in range(12):
            if inell(i + .5, j + .5, 6, 6, 6, 6):
                cv.px(x + i, y + j, bg)
    f = J15()
    cv.d.text((x + 6 - tw(letter, f) // 2 + (0 if letter != "A" else 0), y + 2 + cap(f)), letter, font=f, fill=fg, anchor="ls")


def hints(cv, xr, y, items):
    """Footer button hints right-aligned to xr; y = top of keycap."""
    f = BODY()
    widths = [12 + 5 + tw(lbl, f) for _, lbl in items]
    x = xr - (sum(widths) + 14 * (len(items) - 1))
    for (k, lbl), w in zip(items, widths):
        keycap(cv, x, y, k)
        T(cv, x + 17, y + 11, lbl, f, PAPER)
        x += w + 14


def section(cv, x, y, s, x2):
    """Small spaced caps label with a dotted rule running to x2."""
    w = T(cv, x, y + 11, s, LBL(), PAPER)
    cv.dotline(x + w + 6, y + 5, x2 - (x + w + 6), PAPER, 2)


def hpbar(cv, x, y, w, h, cur, mx, seg=6, color=PAPER, flash=None):
    cv.frame(x, y, w, h, PAPER)
    iw, ih = w - 4, h - 4
    fill = int(round(iw * cur / float(mx)))
    cv.rect(x + 2, y + 2, iw, ih, INK)
    cv.rect(x + 2, y + 2, fill, ih, color)
    for sx in range(x + 2 + seg, x + 2 + fill, seg):
        cv.vline(sx - 1, y + 2, ih, INK)
    if flash:                                   # recently lost HP: hatched chunk
        a, b = fill, min(iw, fill + flash)
        dither(cv, x + 2 + a, y + 2, b - a, ih, 6, PAPER, INK)



def bracket(cv, x, y, w, h, c=PAPER, arm=7, t=2):
    """Corner brackets = the paw cursor's focus frame."""
    for (sx, sy, dx, dy) in ((x, y, 1, 1), (x + w - 1, y, -1, 1), (x, y + h - 1, 1, -1), (x + w - 1, y + h - 1, -1, -1)):
        for k in range(arm):
            for l in range(t):
                cv.px(sx + dx * k, sy + dy * l, c)
                cv.px(sx + dx * l, sy + dy * k, c)


def fight_button(cv, x, y, w, h):
    """Primary action: the one solid-white slab on the screen."""
    cv.rect(x, y, w, h, PAPER)
    for (cx_, cy_) in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        cv.px(cx_, cy_, INK)
    cv.frame(x + 3, y + 3, w - 6, h - 6, INK)
    T(cv, x + w // 2, y + h // 2 + 9, "FIGHT", J25(), INK, sp=1, anchor="m")
    cv.blit(PAW, x + w // 2 - 7, y + 9, INK)
    cv.blit(CLAW, x + 9, y + h - 21, INK)
    cv.blit(CLAW, x + w - 21, y + h - 21, INK)


def medal(cv, x, y, kind="cat"):
    """12x12 two-tone medallion: Domino = half white / half black. Rat = dithered (no fate)."""
    for j in range(12):
        for i in range(12):
            if not inell(i + .5, j + .5, 6, 6, 6, 6):
                continue
            edge = not inell(i + .5, j + .5, 6, 6, 5, 5)
            if kind == "cat":
                cv.px(x + i, y + j, PAPER if (edge or i < 6) else INK)
            else:
                cv.px(x + i, y + j, PAPER if (edge or BAYER[j % 4][i % 4] < 8) else INK)


def paw_cursor(cv, cx, y):
    """Paw with a black keyline so it reads on white card and black table alike."""
    for j in range(len(PAW)):
        for i in range(len(PAW[0])):
            if PAW[j][i] == "#":
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        cv.px(cx - 7 + i + dx, y + j + dy, INK)
    cv.blit(PAW, cx - 7, y, PAPER)


# --------------------------------------------------------------------------- screens
SPREAD_CARDS = [
    dict(elem="fire", n=3, rev=False, stars=1, rarity="none"),
    dict(elem="fire", n=4, rev=False, stars=1, charm="catnip", rarity="common"),
    dict(elem="air", n=5, rev=True, stars=1, charm="bell", rarity="common"),
    dict(elem="water", n=3, rev=False, stars=1, rarity="none"),
    None, None,
]
LBL = lambda: font("Jersey10-Regular", 20)     # section labels: Jersey 10 at 2x (bold, unambiguous R/D/M)
FISH = gen(12, 12, lambda x, y: ("k" if (abs(x - 2.6) < .6 and abs(y - 5.2) < .6) else
                                 "#" if (inell(x, y, 5, 6, 5, 3.4) or (x > 8.6 and abs(y - 6) < (x - 8.2) * 1.5)) else "."))


def build_spread():
    cv = Cv(480, 320, INK)
    L, R = 16, 464
    # ---- enemy band
    rat = onebit("rat", flip=True, contrast=(24, 170))
    bb = content_box(rat)
    cv.paste(rat, L - bb[0], 57 - bb[3])
    medal(cv, 96, 7, "rat")
    T(cv, 114, 18, "GRAY RAT", J20(), PAPER, sp=1)
    T(cv, 96, 40, "HP", LBL(), PAPER)
    hpbar(cv, 122, 30, 100, 10, 18, 18)
    T(cv, 230, 40, "18/18", BODY(), PAPER)
    for i, (k, n) in enumerate((("sword", 3), ("sword", 3), ("coin", 4))):
        cv.paste(scrap(k, n), R - 32 - (2 - i) * 40, 7)
    cv.hline(L, 59, R - L, PAPER)
    # ---- reading
    T(cv, L, 77, "READING", LBL(), PAPER)
    rich(cv, 98, 77, [("t", "Nuzzle x2", BODY(), PAPER), ("gap", 6), ("sep", PAPER), ("gap", 6),
                      ("t", "Tail Tap x2", BODY(), PAPER), ("gap", 6), ("sep", PAPER), ("gap", 6),
                      ("t", "Step x2", BODY(), PAPER), ("gap", 6), ("sep", PAPER), ("gap", 6),
                      ("t", "Catwalk", BODY(), GOLD), ("gap", 6), ("star", GOLD)])
    # ---- spread row
    section(cv, L, 84, "SPREAD 4/6", 352)
    sel = 1
    for i, spec in enumerate(SPREAD_CARDS):
        cv.paste(card("minor", **spec) if spec else slot(), 20 + 56 * i, 100)
    cx = 20 + 56 * sel
    bracket(cv, cx - 4, 97, 56, 70, PAPER)
    paw_cursor(cv, cx + 24, 156)
    fight_button(cv, 360, 100, R - 360, 64)
    # ---- per round
    T(cv, L, 184, "PER ROUND", LBL(), PAPER)
    stats = [("DMG", "38", PAPER, "claw"), ("SINGE", "2", FIRE, "singe"), ("HEAL", "3", WATER, "water"), ("CURL", "0", EARTH, "curl")]
    for i, (lbl, val, col, ic) in enumerate(stats):
        x = 112 + 88 * i
        cv.blit(CLAW if ic == "claw" else ICON[ic], x, 173, col, k=INK)
        w = T(cv, x + 17, 184, lbl, LBL(), PAPER)
        T(cv, x + 17 + w + 5, 184, val, J20(), col)
    # ---- box row + wallet
    section(cv, L, 192, "BOX 2/6", 352)
    box = [dict(kind="major", elem="fire", numeral="XIX", art=art_sun, rarity="legend", charm="nine", size="S"),
           dict(kind="minor", elem="earth", n=7, rarity="none", size="S"), None, None, None, None]
    for i, spec in enumerate(box):
        cv.paste(card(**spec) if spec else slot(40, 54), 24 + 56 * i, 206)
    section(cv, 368, 192, "TREATS", R)
    cv.blit(FISH, 372, 216, GOLD, k=INK)
    T(cv, 392, 232, "14", J25(), GOLD)
    # ---- detail
    rich(cv, L, 277, [("icon", "fire", FIRE), ("gap", 6), ("t", "Fire Claw", J20(), PAPER), ("gap", 8), ("sep", PAPER), ("gap", 8),
                      ("t", "Wands 4", BODY(), PAPER), ("gap", 12), ("star", PAPER), ("gap", 2), ("t", "1", BODY(), PAPER), ("gap", 12),
                      ("t", "Upright", BODY(), PAPER)])
    rich(cv, L, 294, [("t", "Nuzzle +2", BODY(), PAPER), ("gap", 6), ("sep", PAPER), ("gap", 6), ("t", "Tail Tap +1", BODY(), PAPER),
                      ("gap", 6), ("sep", PAPER), ("gap", 6), ("t", "Step +2", BODY(), PAPER), ("gap", 10), ("arrow", PAPER), ("gap", 10),
                      ("t", "Power", BODY(), PAPER), ("gap", 8), ("t", "9", J20(), FIRE)])
    # ---- footer
    cv.hline(L, 299, R - L, PAPER)
    medal(cv, L, 304, "cat")
    T(cv, 34, 316, "Domino", BODY(), PAPER)
    T(cv, 90, 316, "HP", BODY(), PAPER)
    hpbar(cv, 112, 307, 56, 8, 30, 36)
    T(cv, 176, 316, "30/36", BODY(), PAPER)
    hints(cv, R, 304, [("A", "Pick up"), ("B", "Menu"), ("C", "Info")])
    return cv.im




def attic(cv, top=58, floor=198):
    """1-bit attic pantry: beam, posts, cobweb, arched night window with crescent moon, moonlight cast on the floor,
    hanging pantry goods and planks. White line-art and sparse Bayer dither on black: cheap to store and to draw."""
    d = cv.d
    W = cv.w
    cv.rect(0, top, W, 3, PAPER)                                  # ceiling beam + shaded underside
    dither(cv, 0, top + 3, W, 4, 5, PAPER, INK)
    for px_ in (0, W - 10):                                       # side posts: black fill, white inner edge
        cv.rect(px_, top, 10, floor - top, INK)
    cv.vline(9, top, floor - top, PAPER)
    cv.vline(W - 10, top, floor - top, PAPER)
    for r in (14, 26, 38):                                        # cobweb, top-left
        d.arc([10 - r, top + 3 - r, 10 + r, top + 3 + r], 0, 90, fill=PAPER)
    for a in (12, 38, 64):
        d.line([10, top + 3, 10 + 44 * math.cos(math.radians(a)), top + 3 + 44 * math.sin(math.radians(a))], fill=PAPER)
    # arched window: dark night pane, white frame, cross mullion, crescent moon
    wx0, wx1, wy0, wy1 = 46, 106, top + 12, top + 84
    d.rectangle([wx0, wy0 + 30, wx1, wy1], fill=PAPER)
    d.pieslice([wx0, wy0, wx1, wy0 + 60], 180, 360, fill=PAPER)
    pane0, pane1 = wx0 + 4, wx1 - 4
    d.rectangle([pane0, wy0 + 30, pane1, wy1 - 4], fill=INK)
    d.pieslice([pane0, wy0 + 4, pane1, wy0 + 56], 180, 360, fill=INK)
    xm = (wx0 + wx1) // 2
    cv.rect(xm - 1, wy0 + 4, 2, wy1 - wy0 - 7, PAPER)             # vertical mullion
    cv.rect(pane0, wy0 + 46, pane1 - pane0 + 1, 2, PAPER)         # transom
    for y in range(wy0 + 5, wy1 - 5):                             # crescent moon in the upper right pane
        for x in range(xm + 3, pane1):
            if inell(x, y, xm + 17, wy0 + 24, 10, 10) and not inell(x, y, xm + 21, wy0 + 21, 9, 9):
                cv.px(x, y, PAPER)
    for (sx, sy) in ((xm - 22, wy0 + 20), (xm - 12, wy0 + 34), (xm + 12, wy0 + 40), (xm - 18, wy0 + 60), (xm + 18, wy0 + 64)):
        cv.px(sx, sy, PAPER)
        cv.px(sx + 1, sy, PAPER)
    cv.rect(wx0 - 3, wy1 + 1, wx1 - wx0 + 7, 3, PAPER)            # sill
    # moonlight cast on the floor: parallelogram of sparse dither, window bars as shadows
    ys0 = wy1 + 4
    for y in range(ys0, floor):
        t = (y - ys0) / float(floor - ys0)
        sh = int(120 * t)
        for x in range(wx0 + sh, wx1 + sh + 1):
            if x >= W - 10 or x < 10:
                continue
            bar = abs(x - (xm + sh)) <= 1 or (int(0.72 * (floor - ys0)) <= y - ys0 <= int(0.72 * (floor - ys0)) + 1)
            if BAYER[y % 4][x % 4] < 3 and not bar and cv.im.getpixel((x, y)) == INK:
                cv.px(x, y, PAPER)
    # pantry goods hanging from the beam: salami, garlic braid, ham
    def blob(cx, cy, rx, ry, lvl):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if inell(x + .5, y + .5, cx, cy, rx, ry):
                    edge = not inell(x + .5, y + .5, cx, cy, rx - 1.2, ry - 1.2)
                    cv.px(x, y, PAPER if (edge or BAYER[y % 4][x % 4] < lvl) else INK)
    cv.vline(312, top + 7, 12, PAPER)
    blob(312, top + 31, 5, 12, 6)
    for ty in (top + 24, top + 32, top + 40):
        cv.hline(307, ty, 11, INK)
    cv.vline(338, top + 7, 8, PAPER)
    for k, by in enumerate((top + 19, top + 28)):
        blob(338 + (3 if k % 2 else -3), by, 5, 5, 3)
        cv.vline(338 + (3 if k % 2 else -3), by - 8, 3, PAPER)
    cv.vline(362, top + 7, 8, PAPER)
    blob(362, top + 24, 9, 8, 5)
    cv.rect(360, top + 31, 5, 5, PAPER)
    # floor: edge line + planks
    cv.rect(0, floor, W, 2, PAPER)
    dither(cv, 0, floor + 2, W, 12, 2, PAPER, INK)
    rnd = random.Random(3)
    for y in (floor + 5, floor + 10):
        cv.hline(0, y, W, INK)
        x = rnd.randint(0, 40)
        while x < W:
            cv.vline(x, y - 5, 5, INK)
            x += rnd.randint(50, 96)


def burst(cv, cx, cy, r1, r2, n, fill, outline):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = math.pi * i / n + 0.3
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8))
    cv.d.polygon(pts, fill=outline)
    inner = []
    for i in range(n * 2):
        r = (r1 - 3) if i % 2 == 0 else (r2 - 2)
        a = math.pi * i / n + 0.3
        inner.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.8))
    cv.d.polygon(inner, fill=fill)


def speed_lines(cv, cx, cy, box, seed=5, n=26):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for i in range(n):
        a = rnd.uniform(0, math.tau)
        r0, r1 = rnd.uniform(46, 70), rnd.uniform(90, 230)
        pts = [(cx + math.cos(a) * r0, cy + math.sin(a) * r0 * .8), (cx + math.cos(a) * r1, cy + math.sin(a) * r1 * .8)]
        steps = int(max(abs(pts[1][0] - pts[0][0]), abs(pts[1][1] - pts[0][1])))
        for s in range(steps):
            t = s / float(max(1, steps))
            x = int(pts[0][0] + (pts[1][0] - pts[0][0]) * t)
            y = int(pts[0][1] + (pts[1][1] - pts[0][1]) * t)
            if x0 <= x < x1 and y0 <= y < y1 and (s % 7 != 6):
                cv.px(x, y, PAPER)


def slashes(cv, x0, y0, x1, y1, n=3, gap=9):
    """Claw marks: tapered white wedges."""
    for i in range(n):
        ox = i * gap
        a = (x0 + ox, y0)
        b = (x1 + ox - 6, y1)
        cv.d.polygon([a, (a[0] + 5, a[1]), b, (b[0] - 1, b[1] + 2)], fill=PAPER)


def big_number(cv, cx, cy, s, fill, scale=2, halo=PAPER):
    f = J25()
    w, h = tw(s, f) + 2, 24
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    md.fontmode = "1"
    draw_str(md, 1, 20, s, f, 255)
    m = m.resize((w * scale, h * scale), Image.NEAREST)
    outl = m.filter(ImageFilter.MaxFilter(5))
    hal = m.filter(ImageFilter.MaxFilter(9))
    x, y = cx - m.width // 2, cy - m.height // 2
    for layer, col in ((hal, halo), (outl, INK), (m, fill)):
        cv.im.paste(Image.new("RGB", layer.size, col), (x, y), layer.point(lambda v: 255 if v > 127 else 0))


def chip(cv, x, cy, label, f, fg, bg, bord, padx, h):
    w = tw(label, f) + padx * 2
    y = cy - h // 2
    cv.rect(x - 1, y - 1, w + 2, h + 2, INK)
    cv.rect(x, y, w, h, bord)
    cv.rect(x + 1, y + 1, w - 2, h - 2, bg)
    T(cv, x + padx, cy + cap(f) // 2, label, f, fg)
    return w


BATTLE_CARDS = [
    dict(elem="fire", n=3, rev=False, stars=1, rarity="none"),
    dict(elem="fire", n=4, rev=False, stars=1, charm="catnip", rarity="common"),
    dict(elem="air", n=5, rev=True, stars=1, charm="bell", rarity="common"),
    dict(elem="water", n=3, rev=False, stars=1, rarity="none"),
]


def build_battle(phase=3):
    """phase 0 lift+flash | 1 claw swipe + first link | 2 full chain | 3 impact + damage (the shipped frame) | 4 hurt flash."""
    cv = Cv(480, 320, INK)
    L, R = 16, 464
    attic(cv, top=58, floor=198)
    if phase >= 2:
        speed_lines(cv, 420, 150, (112, 64, 470, 196), seed=11, n=20)       # impact lines (behind sprites)
    chubbs = onebit("chubbs", flip=False)
    shake = {3: 2, 4: 4}.get(phase, 0)
    if phase == 4:
        chubbs = invert_sprite(chubbs)
    cv.paste(chubbs, 368 + shake, 112)
    domino = onebit("domino")
    cv.paste(domino, 36, 138)
    if phase >= 1:
        slashes(cv, 190, 156, 330, 192, n=3, gap=10)                         # claw marks
    if phase >= 3:
        burst(cv, 420, 104, 40, 26, 9, PAPER, INK)
        big_number(cv, 420, 104, "12", AIR, scale=2, halo=INK)
        for i in range(3):                                                    # claw marks land on the boss
            sx, sy = 388 + i * 14, 128
            pts = [(sx, sy), (sx + 8, sy), (sx + 36, sy + 62), (sx + 31, sy + 63)]
            cv.d.polygon(pts, fill=PAPER, outline=INK, width=1)
    # ---- top band: Chubbs
    hp = 54 if phase >= 3 else 72
    T(cv, L, 22, "Chubbs", JAC(), PAPER)
    T(cv, 108, 21, "the Pantry King", BODY(), PAPER)
    T(cv, L, 38, "HP", LBL(), PAPER)
    hpbar(cv, 44, 28, 120, 10, hp, 90, seg=6, flash=18 if phase >= 3 else None)
    T(cv, 170, 38, "%d/90" % hp, BODY(), PAPER)
    cv.blit(ICON["singe"], L, 42, FIRE, k=INK)
    T(cv, L + 16, 54, "Singe 2", BODY(), PAPER)
    cv.blit(ICON["drowsy"], L + 90, 42, WATER, k=INK)
    T(cv, L + 106, 54, "Drowsy 1", BODY(), PAPER)
    scraps = [("sword", 6), ("cup", 8), "chewed", ("gnaw", 3), ("coin", 8), ("sword", 6)]
    active = 1
    for i, s in enumerate(scraps):
        x = R - 32 - (5 - i) * 38
        img = chewed_card("fire", "lion") if s == "chewed" else scrap(s[0], s[1], bites=((0, 10 + 7 * i), (31, 30 - 3 * i)))
        cv.paste(img, x, 5)
    ax = R - 32 - (5 - active) * 38
    bracket(cv, ax - 3, 2, 38, 50, PAPER, arm=5, t=1)
    # ---- reading chain: a staircase (Number Path!), every link one size up, the last one gold
    if phase >= 1:
        chip(cv, 126, 78, "Nuzzle +2", BODY(), PAPER, INK, PAPER, 9, 22)
    if phase >= 2:
        chip(cv, 148, 105, "Step +2", J20(), INK, PAPER, PAPER, 6, 26)
        w3 = chip(cv, 170, 136, "Catwalk!", J25(), INK, GOLD, PAPER, 8, 32)
        cv.blit(STAR7, 170 + w3 + 6, 124, GOLD)
        cv.blit(STAR7, 170 + w3 + 14, 134, GOLD)
        cv.blit(STAR7, 170 + w3 + 6, 144, GOLD)
    # ---- Domino's row: active card raised + bracket + wind streaks (Air)
    act = 2
    for i, spec in enumerate(BATTLE_CARDS):
        img = card("minor", **spec)
        if i == act and phase == 0:                                         # play: lift + white flash
            img = Image.new("RGBA", img.size, PAPER + (255,))
        cv.paste(img, 20 + 56 * i, (210 if phase == 0 else 214) if i == act else 222)
    ax = 20 + 56 * act
    bracket(cv, ax - 4, 210, 56, 72, PAPER, arm=6, t=2)
    if phase >= 1:
        for (ox, oy, ln) in ((2, 205, 12), (18, 201, 16), (36, 206, 10)):
            cv.hline(ax + ox, oy, ln, AIR)
            cv.hline(ax + ox + ln, oy, 2, AIR)
            cv.px(ax + ox + ln + 3, oy - 1, AIR)
    # ---- now playing
    section(cv, 272, 212, "NOW PLAYING", R - 72)
    T(cv, R, 223, "Round 1", BODY(), PAPER, anchor="r")
    x = 272
    x += T(cv, x, 247, "Ambush", J20(), AIR) + 8
    w = tw("Reversed", BODY()) + 14
    cv.rect(x, 236, w, 16, PAPER)
    cv.rect(x + 1, 237, w - 2, 14, INK)
    T(cv, x + 7, 249, "Reversed", BODY(), PAPER)
    rich(cv, 272, 266, [("t", "Swords 5", BODY(), PAPER), ("gap", 8), ("star", PAPER), ("t", "1", BODY(), PAPER)])
    T(cv, 272, 283, "P+2 hit, ignores Curl.", BODY(), PAPER)
    # ---- footer
    cv.hline(L, 294, R - L, PAPER)
    medal(cv, L, 301, "cat")
    T(cv, 34, 313, "Domino", BODY(), PAPER)
    T(cv, 90, 313, "HP", BODY(), PAPER)
    hpbar(cv, 112, 304, 88, 8, 33, 36)
    T(cv, 206, 313, "33/36", BODY(), PAPER)
    cv.blit(ICON["curl"], 262, 301, EARTH, k=INK)
    T(cv, 278, 313, "Curl 3", BODY(), PAPER)
    hints(cv, R, 301, [("A", "2x"), ("B", "Skip")])
    return cv.im


# --------------------------------------------------------------------------- style sheet
def scaled(img, k):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)


def big_text(cv, x, y, s, f, color, k=2, anchor="l"):
    """Text rendered at native size then pixel-doubled (crisp wordmarks). y = cap-top of the scaled text."""
    w, ch = tw(s, f) + 4, cap(f)
    m = Image.new("L", (w, ch + ch // 2), 0)
    md = ImageDraw.Draw(m)
    md.fontmode = "1"
    draw_str(md, 1, ch, s, f, 255)
    m = m.resize((m.width * k, m.height * k), Image.NEAREST).point(lambda v: 255 if v > 127 else 0)
    if anchor == "r":
        x -= w * k
    elif anchor == "m":
        x -= (w * k) // 2
    cv.im.paste(Image.new("RGB", m.size, color), (x, y), m)
    return w * k


def tile_plank():
    t = Cv(16, 16, INK)
    t.hline(0, 15, 16, PAPER)
    for y in range(0, 15, 2):
        t.px(8, y, PAPER)
    t.px(3, 5, PAPER)
    return t.im


def tile_dots():
    t = Cv(16, 16, INK)
    for (x, y) in ((3, 3), (11, 9), (7, 13), (13, 2)):
        t.px(x, y, PAPER)
    return t.im


def tile_bayer(level):
    t = Cv(16, 16, INK)
    dither(t, 0, 0, 16, 16, level, PAPER, INK)
    return t.im


def tile_hatch():
    t = Cv(16, 16, INK)
    for y in range(16):
        for x in range(16):
            if (x + y) % 4 == 0:
                t.px(x, y, PAPER)
    return t.im


def blit_k(cv, rows, x, y, k, fg, kk=INK):
    """Draw an ascii icon scaled by integer k."""
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            c = fg if ch == "#" else (kk if ch == "k" else None)
            if c is not None:
                cv.rect(x + i * k, y + j * k, k, k, c)


def build_sheet():
    W, H = 960, 1378
    cv = Cv(W, H, INK)
    M = 24
    B = BODY()
    # ---- A header
    big_text(cv, M, 16, "Nine Lives Arcana", JAC(), PAPER, k=2)
    T(cv, M + 2, 80, "The Cats and the Rat King", B, PAPER)
    T(cv, W - M, 34, "TWO-TONE NOIR", J25(), PAPER, sp=2, anchor="r")
    T(cv, W - M, 56, "1-bit ink and moonlight. Colour only where fate speaks:", B, PAPER, anchor="r")
    T(cv, W - M, 73, "one hue per element, one gold for rarity.", B, PAPER, anchor="r")
    T(cv, W - M, 90, "Reversed cards invert black and white.", B, PAPER, anchor="r")
    cv.dotline(M, 100, W - 2 * M, PAPER, 2)
    # ---- B palette
    section(cv, M, 110, "PALETTE  7 COLOURS, ALL RGB565-EXACT FAST-FILL WORDS", W - M)
    names = {"INK": "Ink / night", "PAPER": "Paper / moon", "FIRE": "Fire vermilion", "AIR": "Air saffron",
             "WATER": "Water cyan-blue", "EARTH": "Earth moss", "GOLD": "Gold, rarity"}
    cols = {"INK": INK, "PAPER": PAPER, "FIRE": FIRE, "AIR": AIR, "WATER": WATER, "EARTH": EARTH, "GOLD": GOLD}
    for i, (nm, word) in enumerate(PALETTE):
        x = M + 130 * i
        c = cols[nm]
        cv.rect(x, 140, 114, 42, c)
        cv.frame(x - 1, 139, 116, 44, PAPER)
        T(cv, x + 8, 168, "Aa", J20(), INK if nm != "INK" else PAPER)
        T(cv, x, 202, names[nm], B, PAPER)
        T(cv, x, 220, "%s 0x%04X" % (hexs(c), word), B, PAPER)
    # ---- C type + icons
    section(cv, M, 238, "TYPE  OFL, BAKED TO BITMAP", 500)
    T(cv, M, 278, "FIGHT  Ambush  12", J25(), PAPER)
    T(cv, 336, 278, "Jersey 25 / 20", B, PAPER)
    T(cv, M, 302, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", B, PAPER)
    T(cv, M + 224, 302, "abcdefghijklmnopqrstuvwxyz", B, PAPER)
    T(cv, M, 320, "0123456789 +-x/%:.,!?'", B, PAPER)
    T(cv, M + 200, 320, "Nuzzle +2 | Step +2", B, PAPER)
    T(cv, M, 338, "Fire Claw  Activate: Deal P damage. Then inflict 1 Singe.", B, PAPER)
    T(cv, M, 366, "Chubbs, the Pantry King", JAC(), PAPER)
    T(cv, 372, 366, "Jacquard 24", B, PAPER)
    T(cv, M, 388, "DotGothic16 body: 8x16 cell, 56 chars = 448 px", B, PAPER)
    section(cv, 520, 238, "ICONS  SHOWN 2X AND 3X", W - M)
    for i, e in enumerate(("fire", "air", "water", "earth")):
        blit_k(cv, ICON[e], 524 + 56 * i, 266, 2, ELEM[e])
        T(cv, 524 + 56 * i + 12, 312, e.capitalize(), B, PAPER, anchor="m")
    for i, (k_, nm) in enumerate((("catnip", "Catnip"), ("bell", "Bell"), ("nine", "Nine Lives"))):
        blit_k(cv, CHARM[k_], 760 + 68 * i, 266, 3, GOLD if k_ == "nine" else PAPER)
        T(cv, 760 + 68 * i + 12, 312, nm, B, PAPER, anchor="m")
    for i, (k_, col) in enumerate((("singe", FIRE), ("puff", PAPER), ("drowsy", WATER), ("curl", EARTH), ("leap", AIR))):
        blit_k(cv, ICON[k_], 524 + 56 * i, 336, 2, col)
        T(cv, 524 + 56 * i + 12, 382, k_.capitalize(), B, PAPER, anchor="m")
    blit_k(cv, CLAW, 524 + 56 * 5, 336, 2, PAPER)
    T(cv, 524 + 56 * 5 + 12, 382, "Damage", B, PAPER, anchor="m")
    medal(cv, 524 + 56 * 6 + 2, 340, "cat")
    medal(cv, 524 + 56 * 6 + 20, 340, "rat")
    T(cv, 524 + 56 * 6 + 16, 382, "Two-tone", B, PAPER, anchor="m")
    # ---- D cards
    section(cv, M, 406, "CARDS  48x64, SHOWN 2x", W - M)
    deck = [
        (card("minor", "fire", 4, False, 1, "catnip", "common"), "Minor Fire 4", "Upright common"),
        (card("minor", "water", 3, True, 1, "bell", "rare"), "Minor Water 3", "Reversed rare"),
        (card("major", "fire", numeral="XIX", art=art_sun, rarity="legend", charm="nine"), "Major XIX", "The Sun, gold"),
        (scrap("sword", 3), "Rat scrap", "Broken Sword 3"),
        (card_back("L"), "Card back", "Cat-eye moon"),
    ]
    for i, (img, l1, l2) in enumerate(deck):
        x = M + 128 * i
        im2 = scaled(img, 2)
        cv.paste(im2, x + (96 - im2.width) // 2, 438 + (128 - im2.height) // 2)
        T(cv, x, 588, l1, B, PAPER)
        T(cv, x, 606, l2, B, PAPER)
    lg = ["Top-left: number / Roman",
          "Top-right: stars, 1 to 3",
          "Window: 32x32 pips or cat",
          "Bottom-left: element icon",
          "Bottom-right: charm gem",
          "Edge lines = rarity:",
          "  1 none, 2 common,",
          "  studs rare, gold legendary",
          "Reversed = black card,",
          "accent ink, art flipped."]
    for j, ln in enumerate(lg):
        T(cv, 688, 456 + 18 * j, ln, B, PAPER)
    # ---- E characters
    section(cv, M, 636, "CHARACTERS  SHOWN 2x", W - M)
    chars = [("domino", False, (46, 214), 24, "Domino", "tuxedo hero"),
             ("zero", False, (46, 214), 164, "Zero", "ghost: dither"),
             ("rat", True, (24, 170), 304, "Gray Rat", "no fate, no hue"),
             ("chubbs", True, (46, 214), 444, "Chubbs", "the Pantry King")]
    for (n, fl, ct, x, nm, sub) in chars:
        img = onebit(n, flip=fl, contrast=ct)
        if n == "zero":
            img = ghostify(img)
        im2 = scaled(img, 2)
        cv.paste(im2, x, 664 + (192 - im2.height) // 2)
        T(cv, x, 874, nm, B, PAPER)
        T(cv, x, 892, sub, B, PAPER)
    for k_, ln in enumerate(("Domino's coat is the icon:", "half white, half black.", "Reversed cards invert", "the same split.",
                             "Rats are dither only:", "born without fate or hue.")):
        T(cv, 688, 692 + 18 * k_, ln, B, PAPER)
    medal(cv, 688, 812, "cat")
    medal(cv, 706, 812, "rat")
    # ---- F backdrop and tiles
    section(cv, M, 930, "BACKDROP 1x  AND  TILES 16x16 SHOWN 4x", W - M)
    bgc = Cv(480, 214, INK)
    attic(bgc, top=0, floor=140)
    cv.im.paste(bgc.im.crop((0, 0, 400, 150)), (M, 962))
    tiles = [(tile_plank(), "Plank"), (tile_dots(), "Star dots"), (tile_bayer(3), "Moon 3/16"),
             (tile_bayer(8), "Shade 8/16"), (tile_hatch(), "Bite hatch")]
    for i, (t, nm) in enumerate(tiles):
        x = 448 + 100 * i
        cv.paste(scaled(t.convert("RGBA"), 4), x, 962)
        cv.frame(x - 1, 961, 66, 66, PAPER)
        T(cv, x, 1046, nm, B, PAPER)
    T(cv, 448, 1074, "Full 480x320 scene at 1 bit = 19.2 KB.", B, PAPER)
    T(cv, 448, 1092, "Solid ink/paper runs use fast fills.", B, PAPER)
    T(cv, 448, 1110, "64-colour art would cost 40-120 KB.", B, PAPER)
    # ---- G storyboard
    section(cv, M, 1136, "SIGNATURE ANIMATION  PLAY, READ THE CHAIN, LAND THE HIT", W - M)
    frames = [(0, (0, 140, 220, 290), "1 Lift + white flash", "card up 4px, 2 frames"),
              (2, (96, 62, 316, 212), "2 Chain grows", "links size up, last gold"),
              (3, (260, 60, 480, 210), "3 Impact", "number x2, speed lines"),
              (4, (260, 60, 480, 210), "4 Hurt flash", "sprite inverts, HP hatches")]
    for i, (ph, box, l1, l2) in enumerate(frames):
        x = M + 232 * i
        cv.paste(build_battle(ph).crop(box), x, 1168)
        cv.frame(x - 1, 1167, 222, 152, PAPER)
        T(cv, x, 1342, l1, B, PAPER)
        T(cv, x, 1360, l2, B, PAPER)
        if i < 3:
            cv.blit(ARROW, x + 224, 1241, PAPER)
    return cv.im


# --------------------------------------------------------------------------- main
def check(im, name):
    allowed = set(c for c in (INK, PAPER, FIRE, AIR, WATER, EARTH, GOLD))
    got = set(c for _, c in im.getcolors(1 << 20))
    bad = got - allowed
    assert not bad, "%s has off-palette colours %s" % (name, sorted(bad)[:5])
    for (r, g, b) in got:                                     # RGB565 round-trip
        w = (r >> 3) << 11 | (g >> 2) << 5 | (b >> 3)
        assert rgb565(w) == (r, g, b), "%s: %s is not RGB565-exact" % (name, (r, g, b))
    return len(got)


def main():
    ensure_fonts()
    out = {}
    out["spread"] = build_spread()
    out["battle"] = build_battle(3)
    for name in ("spread", "battle"):
        im = out[name]
        assert im.size == (480, 320), im.size
        im.save(os.path.join(HERE, name + ".png"))
        scaled(im, 2).save(os.path.join(HERE, name + "@2x.png"))
    sheet = build_sheet()
    sheet.save(os.path.join(HERE, "sheet.png"))
    for name, im in (("spread", out["spread"]), ("battle", out["battle"]), ("sheet", sheet)):
        print("%-7s %s  %d colours, RGB565-exact" % (name, im.size, check(im, name)))


if __name__ == "__main__":
    main()
