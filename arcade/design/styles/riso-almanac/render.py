#!/usr/bin/env python3
"""Woodcut Riso Almanac - reproduces every PNG of this style direction.

Inputs : raw/*.png (PixelLab sprites, see gen_sprites.py), fonts/*.ttf (downloaded on first run).
Outputs: spread.png battle.png spread@2x.png battle@2x.png sheet.png  (all RGB565-exact).
Everything except the four AI sprites is drawn here, pixel by pixel, at native resolution.
"""
import os, math, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageChops

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW, FONTS = os.path.join(ROOT, "raw"), os.path.join(ROOT, "fonts")

# --------------------------------------------------------------------------- fonts
GF = "https://github.com/google/fonts/raw/main/ofl/"
FONT_FILES = {
    "Jacquard24-Regular.ttf": GF + "jacquard24/Jacquard24-Regular.ttf",
    "Jersey10-Regular.ttf": GF + "jersey10/Jersey10-Regular.ttf",
}
os.makedirs(FONTS, exist_ok=True)
for fn, url in FONT_FILES.items():
    if not os.path.exists(os.path.join(FONTS, fn)):
        urllib.request.urlretrieve(url, os.path.join(FONTS, fn))
F13 = ImageFont.truetype(os.path.join(FONTS, "Jersey10-Regular.ttf"), 13)   # body, cap 7
F16 = ImageFont.truetype(os.path.join(FONTS, "Jersey10-Regular.ttf"), 16)   # emphasis, cap 9
F20 = ImageFont.truetype(os.path.join(FONTS, "Jersey10-Regular.ttf"), 20)   # numerals, cap 11 (2x of 10)
JQ = ImageFont.truetype(os.path.join(FONTS, "Jacquard24-Regular.ttf"), 24)  # blackletter display

# --------------------------------------------------------------------------- palette (RGB565 exact)
def snap(r, g, b):
    r5, g6, b5 = round(r * 31 / 255), round(g * 63 / 255), round(b * 31 / 255)
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))

def to565(c):
    return ((c[0] >> 3) << 11) | ((c[1] >> 2) << 5) | (c[2] >> 3)

PAL_SRC = {
    # name:      (r, g, b)         role
    "ink":      (0, 0, 0),         # carbon black (fast fill 0x0000)
    "paper":    (247, 223, 181),   # warm newsprint (fast fill 0xF6F6)
    "bone":     (255, 244, 220),   # bright paper: highlights, white fur
    "paper2":   (233, 203, 156),   # panel shade
    "paper3":   (201, 166, 118),   # foxing / deep shade
    "verm":     (255, 74, 44),     # spot ink 1: fluorescent vermilion
    "verm_d":   (176, 32, 36),
    "verm_t":   (252, 176, 142),
    "teal":     (0, 132, 140),     # spot ink 2: teal
    "teal_d":   (0, 70, 92),
    "teal_t":   (150, 208, 198),
    "plum":     (98, 36, 78),      # overprint verm x teal / Rare
    "straw":    (252, 230, 124),   # Air / sun / cheese
    "straw_t":  (252, 240, 170),
    "gold":     (222, 160, 40),    # Legendary / bell / crown
    "moss":     (84, 140, 76),     # Earth ink (teal x straw overprint)
    "moss_d":   (40, 88, 60),
    "moss_t":   (190, 212, 140),
    "scrap":    (146, 166, 138),   # rat scraps
    "scrap_d":  (84, 104, 84),
    "scrap_t":  (196, 206, 176),
    "cool":     (170, 194, 206),   # Reversed
    "cool_t":   (214, 226, 230),
}
PAL = {k: snap(*v) for k, v in PAL_SRC.items()}
globals().update({k.upper(): v for k, v in PAL.items()})
PALSET = set(PAL.values())
LEG = {"#": INK, "r": VERM, "R": VERM_D, "t": TEAL, "T": TEAL_D, "y": STRAW, "g": GOLD, "m": MOSS, "M": MOSS_D,
       "w": BONE, "p": PAPER, "l": PAPER2, "s": SCRAP, "S": SCRAP_D, "c": COOL, "o": VERM_T, "u": TEAL_T}

# --------------------------------------------------------------------------- primitives
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

def new_img(w, h, fill=None):
    im = Image.new("RGB", (w, h), fill or PAPER)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    return im, d

def R(d, x, y, w, h, fill):
    if w > 0 and h > 0:
        d.rectangle([x, y, x + w - 1, y + h - 1], fill=fill)

def frame(d, x, y, w, h, c):
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=c)

def dith(img, x, y, w, h, c1, c2, lvl):
    """Ordered dither: lvl 0..16 = share of c2 (c1 elsewhere)."""
    px = img.load()
    for j in range(y, y + h):
        for i in range(x, x + w):
            if 0 <= i < img.width and 0 <= j < img.height:
                px[i, j] = c2 if BAYER[j % 4][i % 4] < lvl else c1

def hatch(img, x, y, w, h, c, step=3, phase=0, anti=False):
    px = img.load()
    for j in range(y, y + h):
        for i in range(x, x + w):
            if 0 <= i < img.width and 0 <= j < img.height:
                v = (i - j) if anti else (i + j)
                if (v + phase) % step == 0:
                    px[i, j] = c

def bitmap(img, x, y, rows, flipv=False, split=None, tint=None):
    """Draw ascii bitmap. split=(dx,dy): colour layer is printed offset from the ink layer (misregistration)."""
    if flipv:
        rows = rows[::-1]
    px = img.load()
    mode = img.mode
    def put(i, j, col):
        if 0 <= i < img.width and 0 <= j < img.height:
            px[i, j] = col + (255,) if mode == "RGBA" else col
    for pass_ in ((0, 1) if split else (2,)):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == ".":
                    continue
                col = LEG[ch]
                if tint:
                    col = tint.get(col, col)
                if pass_ == 2:
                    put(x + i, y + j, col)
                elif pass_ == 0 and ch != "#":
                    put(x + i + split[0], y + j + split[1], col)
                elif pass_ == 1 and ch == "#":
                    put(x + i, y + j, col)

def TW(s, font, sp=0):
    return sum(font.getlength(ch) + sp for ch in s) - sp if sp else font.getlength(s)

def T(d, x, y, s, font, fill, sp=0, anchor="l"):
    """Text at baseline y. anchor l/m/r."""
    w = TW(s, font, sp)
    if anchor == "m":
        x -= w // 2
    elif anchor == "r":
        x -= w
    x = int(x)
    if not sp:
        d.text((x, y), s, font=font, fill=fill, anchor="ls")
    else:
        for ch in s:
            d.text((int(x), y), ch, font=font, fill=fill, anchor="ls")
            x += font.getlength(ch) + sp
    return w

def TM(d, x, y, s, font, ink, spot, sp=0, anchor="l", off=(1, 1)):
    """Misregistered print: spot ink pass offset by 1px, black pass on top."""
    w = TW(s, font, sp)
    xx = x - (w // 2 if anchor == "m" else w if anchor == "r" else 0)
    T(d, xx + off[0], y + off[1], s, font, spot, sp)
    T(d, xx, y, s, font, ink, sp)
    return w

def smallcaps(d, x, y, s, fill, anchor="l"):
    return T(d, x, y, s.upper(), F13, fill, sp=1, anchor=anchor)

def hrule(d, x, y, w, thick=2, c=INK):
    R(d, x, y, w, thick, c)

def dotted(d, x, y, w, c=INK, step=2):
    for i in range(0, w, step * 2):
        R(d, x + i, y, step, 1, c)

STAR5 = ["..#..", ".###.", "#####", ".###.", ".#.#."]
STAR7 = ["...#...", "...#...", "..###..", "#######", ".#####.", "..###..", ".##.##."]
DIAM = ["..#..", ".###.", "#####", ".###.", "..#.."]

def diamond(d, cx, cy, r, fill):
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=fill)

def star(img, x, y, col=INK, big=False):
    rows = STAR7 if big else STAR5
    px = img.load()
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "#":
                px[x + i, y + j] = col + (255,) if img.mode == "RGBA" else col

def fleuron(d, cx, y, c=INK, spot=VERM):
    """tiny printer's ornament  - o -  centred at cx"""
    R(d, cx - 12, y + 2, 8, 1, c)
    R(d, cx + 5, y + 2, 8, 1, c)
    diamond(d, cx, y + 2, 2, spot)
    d.point((cx, y + 2), fill=c)

# --------------------------------------------------------------------------- icons / pips (ascii)
PIP = {
    "fire": ["....#....", "...#r#...", "...#rr#..", "..#rrr#..", ".#rryrr#.", ".#ryyyr#.", ".#ryyyr#.", "..#ryr#..", "...###..."],
    "air": ["....#....", "...#y#...", "...#y#...", "..#yyy#..", "#yyyyyyy#", "..#yyy#..", "...#y#...", "...#y#...", "....#...."],
    "water": ["....#....", "...#t#...", "..#ttt#..", "..#ttt#..", ".#ttwtt#.", ".#ttwtt#.", ".#ttttt#.", "..#ttt#..", "...###..."],
    "earth": ["......##.", "....#mmm#", "...#mmmm#", "..#mmMmm#", ".#mmMmm#.", ".#mMmmm#.", "#mmmmm#..", "##mm##...", "#.##....."],
}
PIP_LAYOUT = {
    1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)], 4: [(0, 0), (2, 0), (0, 2), (2, 2)],
    5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)], 6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)],
    7: [(0, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (2, 2)],
    8: [(0, 0), (1, 0), (2, 0), (0, 1), (2, 1), (0, 2), (1, 2), (2, 2)],
    9: [(c, r) for r in range(3) for c in range(3)],
}
ELEM_BASE = {"fire": VERM_T, "air": STRAW_T, "water": TEAL_T, "earth": MOSS_T}
ELEM_INK = {"fire": VERM, "air": GOLD, "water": TEAL, "earth": MOSS}
COOL_MAP = {VERM: TEAL_D, STRAW: COOL_T, GOLD: TEAL, MOSS: TEAL, TEAL: TEAL_D, MOSS_D: TEAL_D, BONE: BONE}

def tri_icon(kind, size=11):
    """Alchemical element roundel (fire up, air up+bar, water down, earth down+bar)."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, size - 1, size - 1], fill=ELEM_INK[kind] + (255,), outline=INK + (255,))
    c = (size - 1) / 2
    top, bot = (2, size - 4) if size == 11 else (2, size - 3)
    half = (size - 5) // 2
    up = kind in ("fire", "air")
    if up:
        pts = [(c, top), (c - half, bot), (c + half, bot)]
    else:
        pts = [(c - half, top + 1), (c + half, top + 1), (c, bot + 1)]
    d.polygon(pts, outline=BONE + (255,))
    d.line([pts[0], pts[1]], fill=BONE + (255,))
    d.line([pts[0], pts[2]], fill=BONE + (255,))
    d.line([pts[1], pts[2]], fill=BONE + (255,))
    if kind in ("air", "earth"):
        y = int(top + (bot - top) * (0.6 if up else 0.45)) + (0 if up else 1)
        d.line([(c - half + 1, y), (c + half - 1, y)], fill=BONE + (255,))
    return im

def icon_rows(name):
    return ICON_ASCII[name]

ICON_ASCII = {
    "flame": PIP["fire"],
    "puff": ["....#.#....", "..#.#w#.#..", "...#www#...", "#.#wwwww#.#", ".#wwwwwww#.", "#.#wwwww#.#", ".#wwwwwww#.", "#.#.#w#.#.#", "...#.#.#...", "...........", "..........."],
    "drowsy": ["..#####....", "....##.....", "...##......", "..#####....", ".......####", "........##.", ".......##..", "......####.", "...........", "...........", "..........."],
    "curl": ["...#####...", "..#TTTTT#..", ".#TT###TT#.", ".#T#...#T#.", ".#T#.#.#T#.", ".#T#.##.#T#", ".#TT#..#TT#", "..#TTTTTT#.", "...######..", "...........", "..........."],
    "leap": [".....#.....", "....#t#....", "...#ttt#...", "..#ttttt#..", ".####t####.", "....#t#....", "....#t#....", "....#t#....", "....###....", "...........", "#.#.#.#.#.#"],
    "catnip": [".....#.....", "....#m#....", "...#mmm#...", "..#.#M#.#..", ".#m#.M.#m#.", "#mmm#M#mmm#", ".#m#.M.#m#.", "..#..M..#..", ".....M.....", ".....M.....", "....###...."],
    "bell": [".....#.....", "....###....", "...#ggg#...", "..#gggwg#..", "..#ggwgg#..", "..#ggggg#..", ".#ggggggg#.", ".#ggggggg#.", "###########", "....#g#....", ".....#....."],
    "nine": ["..###.###..", ".#rrr#rrr#.", "#rrrrrrrrr#", "#rrrrrrrrr#", "#rrrrrrrrr#", ".#rrrrrrr#.", "..#rrrrr#..", "...#rrr#...", "....#r#....", ".....#.....", "..........."],
}

def make_icon(name, size=11):
    if name in ("fire", "air", "water", "earth"):
        return tri_icon(name, size)
    rows = icon_rows(name if name != "singe" else "flame")
    im = Image.new("RGBA", (11, 11), (0, 0, 0, 0))
    if name == "singe":
        bitmap(im, 1, 1, rows, tint={VERM: INK, STRAW: VERM, VERM_D: INK})
        for p in ((8, 1), (9, 3), (0, 5)):
            im.putpixel(p, INK + (255,))
        return im
    bitmap(im, 0, 0, rows)
    if name == "nine":
        for (i, j) in [(4, 2), (5, 2), (6, 2), (4, 3), (6, 3), (4, 4), (5, 4), (6, 4), (6, 5), (6, 6), (5, 6), (4, 6)]:
            im.putpixel((i, j), BONE + (255,))
        im.putpixel((4, 6), (0, 0, 0, 0))
        im.putpixel((5, 6), BONE + (255,))
    return im

def paw_cursor():
    """Cat-paw print used as the cursor (17x16)."""
    im = Image.new("RGBA", (17, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for (cx, cy) in ((2, 6), (6, 2), (11, 2), (15, 6)):
        d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=INK + (255,))
        d.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=VERM + (255,))
    d.ellipse([3, 8, 13, 15], fill=INK + (255,))
    d.ellipse([4, 9, 12, 14], fill=VERM + (255,))
    d.point((7, 10), fill=BONE + (255,))
    return im


# --------------------------------------------------------------------------- cards
def put_rgba(img, im, x, y):
    img.paste(im, (x, y), im)

def sun_art(c):
    """32x32 woodcut sun over a sunbathing cat (Major XIX). c = RGBA image 32x32 (opaque bone)."""
    d = ImageDraw.Draw(c)
    cx, cy = 16, 13
    for k in range(16):
        a = k * math.pi / 8
        r0, r1 = 8, (15 if k % 2 == 0 else 12)
        p0 = (cx + math.cos(a) * r0, cy + math.sin(a) * r0)
        p1 = (cx + math.cos(a) * r1, cy + math.sin(a) * r1)
        d.line([(round(p0[0]) + 1, round(p0[1]) + 1), (round(p1[0]) + 1, round(p1[1]) + 1)], fill=VERM + (255,), width=2)
        d.line([(round(p0[0]), round(p0[1])), (round(p1[0]), round(p1[1]))], fill=INK + (255,))
    d.ellipse([cx - 7 + 1, cy - 7 + 1, cx + 7 + 1, cy + 7 + 1], fill=VERM + (255,))
    d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=STRAW + (255,), outline=INK + (255,))
    for ex in (cx - 4, cx + 2):
        d.line([(ex, cy - 2), (ex + 2, cy - 2)], fill=INK + (255,))
        d.point((ex, cy - 1), fill=INK + (255,))
        d.point((ex + 2, cy - 1), fill=INK + (255,))
    d.line([(cx - 1, cy + 1), (cx + 1, cy + 1)], fill=VERM_D + (255,))
    d.arc([cx - 4, cy + 1, cx + 4, cy + 6], 20, 160, fill=INK + (255,))
    d.point((cx - 5, cy + 2), fill=VERM + (255,)); d.point((cx + 5, cy + 2), fill=VERM + (255,))
    # sill + cat loaf, belly up white patch
    d.rectangle([0, 28, 31, 31], fill=INK + (255,))
    d.rectangle([0, 27, 31, 27], fill=PAPER3 + (255,))
    d.ellipse([6, 20, 26, 29], fill=INK + (255,))
    d.ellipse([10, 23, 22, 29], fill=BONE + (255,))
    d.ellipse([21, 17, 29, 25], fill=INK + (255,))
    d.polygon([(22, 18), (22, 14), (25, 17)], fill=INK + (255,))
    d.polygon([(27, 18), (28, 14), (29, 18)], fill=INK + (255,))
    d.point((26, 21), fill=BONE + (255,))
    d.arc([2, 21, 10, 29], 90, 270, fill=INK + (255,))
    return c

def sword_art(c):
    d = ImageDraw.Draw(c)
    I, S, B = INK + (255,), SCRAP_D + (255,), BONE + (255,)
    d.polygon([(8, 25), (21, 11), (24, 14), (11, 28)], fill=B, outline=I)             # blade (snapped)
    d.polygon([(20, 12), (22, 10), (23, 13)], fill=SCRAP_T + (255,))
    d.line([(10, 25), (21, 13)], fill=S)
    d.polygon([(2, 20), (7, 17), (13, 25), (9, 30)], fill=S, outline=I)                # crossguard
    d.line([(2, 28), (7, 23)], fill=I, width=2)                                       # grip
    d.polygon([(25, 4), (29, 3), (27, 8)], fill=B, outline=I)                         # tip, flying off
    for (x, y) in ((24, 9), (27, 11), (22, 7)):
        d.point((x, y), fill=I)
    return c

def coin_art(c):
    d = ImageDraw.Draw(c)
    I = INK + (255,)
    d.ellipse([5, 5, 26, 26], fill=SCRAP_T + (255,), outline=I)
    d.ellipse([8, 8, 23, 23], outline=SCRAP_D + (255,))
    d.line([(16, 5), (14, 11), (18, 16), (13, 20), (15, 26)], fill=I)
    d.polygon([(27, 21), (23, 23), (24, 27), (29, 26)], fill=BONE + (255,), outline=I)
    return c

def cup_art(c):
    d = ImageDraw.Draw(c)
    I = INK + (255,)
    d.polygon([(8, 7), (24, 7), (21, 18), (17, 21), (15, 21), (11, 18)], fill=BONE + (255,), outline=I)
    d.polygon([(10, 11), (22, 11), (21, 14), (11, 14)], fill=TEAL_T + (255,))
    d.rectangle([14, 21, 18, 25], fill=SCRAP_D + (255,), outline=I)
    d.rectangle([9, 25, 23, 27], fill=SCRAP_D + (255,), outline=I)
    d.line([(15, 12), (13, 16), (14, 17)], fill=I)
    for (x, y) in ((11, 20), (10, 23), (12, 24)):
        d.rectangle([x, y, x + 1, y + 1], fill=TEAL + (255,))
    return c

def gnaw_art(c):
    d = ImageDraw.Draw(c)
    I = INK + (255,)
    for ox in (5, 17):
        d.polygon([(ox, 6), (ox + 9, 6), (ox + 9, 22), (ox + 5, 26), (ox, 22)], fill=BONE + (255,), outline=I)
        d.line([(ox + 2, 8), (ox + 2, 19)], fill=SCRAP_T + (255,))
    d.polygon([(2, 3), (8, 3), (5, 8)], fill=SCRAP_D + (255,))
    for (x, y) in ((14, 28), (22, 28), (27, 5), (4, 28)):
        d.point((x, y), fill=I)
    return c

def strength_art(c):
    d = ImageDraw.Draw(c)
    I = INK + (255,)
    d.ellipse([9, 12, 23, 27], fill=BONE + (255,), outline=I)
    d.polygon([(9, 16), (9, 8), (15, 12)], fill=I)
    d.polygon([(23, 16), (23, 8), (17, 12)], fill=I)
    d.rectangle([13, 18, 14, 19], fill=I); d.rectangle([18, 18, 19, 19], fill=I)
    d.polygon([(15, 22), (18, 22), (16, 24)], fill=VERM + (255,))
    for pts in (((7, 6), (12, 3), (16, 6), (20, 3), (25, 6)),):
        d.line(list(pts), fill=VERM + (255,), width=2)
        d.line([(x, y - 1) for (x, y) in pts], fill=I)
    return c

SCRAP_ART = {"sword": sword_art, "coin": coin_art, "cup": cup_art, "gnaw": gnaw_art}

def cut_bites(card, spots):
    a0 = card.split()[3]
    for (cx, cy, r) in spots:
        outer = Image.new("L", card.size, 0); ImageDraw.Draw(outer).ellipse([cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1], fill=255)
        inner = Image.new("L", card.size, 0); ImageDraw.Draw(inner).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
        ink = Image.new("RGBA", card.size, INK + (255,))
        card.paste(ink, (0, 0), ImageChops.multiply(outer, a0))
        a0 = ImageChops.subtract(a0, inner)
    card.putalpha(a0)
    return card

RARITY = {None: BONE, "common": TEAL, "rare": PLUM, "legend": GOLD, "curse": VERM}

def gem(d, x, y, col, s=7):
    """charm gem, s x s diamond with ink outline"""
    c = s // 2
    d.polygon([(x + c, y), (x + s - 1, y + c), (x + c, y + s - 1), (x, y + c)], fill=col + (255,), outline=INK + (255,))
    d.point((x + c, y + c - 1), fill=BONE + (255,))

CHARM_COL = {"catnip": MOSS, "bell": GOLD, "nine": VERM}

def card(kind="minor", elem="fire", n=4, stars=1, rev=False, rarity=None, charm=None, w=48, h=64, roman=None,
         scrap=None, bites=True, major="sun", chewed=False):
    mini = h == 54
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.fontmode = "1"
    I = INK + (255,)
    if kind == "back":
        return card_back(w, h)
    if kind == "scrap":
        base, win, ringc, numc = SCRAP, SCRAP_T, BONE, INK
    elif rev:
        base, win, ringc, numc = COOL, COOL_T, RARITY[rarity], INK
    else:
        base, win, ringc, numc = ELEM_BASE[elem], BONE, RARITY[rarity], INK
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=2, fill=I)
    d.rounded_rectangle([1, 1, w - 2, h - 2], radius=1, fill=ringc + (255,))
    d.rectangle([2, 2, w - 3, h - 3], fill=base + (255,))
    # base: faint woodcut hatch in the lower margin
    wy = 9 if mini else 13
    wx = (w - 34) // 2
    d.rectangle([wx, wy, wx + 33, wy + 33], fill=I)
    art = Image.new("RGBA", (32, 32), win + (255,))
    ad = ImageDraw.Draw(art)
    # window shading: halftone shadow along bottom-right, like a plate printed with a tint block
    tmp = Image.new("RGB", (32, 32), win)
    ground = SCRAP if kind == "scrap" else (COOL if rev else ELEM_BASE[elem])
    if kind != "major":
        hatch(tmp, 0, 0, 32, 32, ground, 3, 0, anti=True)
    dith(tmp, 0, 26, 32, 6, win, ground, 8) if kind == "major" else None
    art.paste(tmp, (0, 0))
    if kind == "minor":
        tint = COOL_MAP if rev else None
        if n == 1:
            big = Image.new("RGBA", (9, 9), (0, 0, 0, 0))
            bitmap(big, 0, 0, PIP[elem], split=(1, 1), tint=tint)
            big = big.resize((18, 18), Image.NEAREST)
            art.paste(big, (7, 7), big)
        else:
            for (cx, cy) in PIP_LAYOUT[n]:
                bitmap(art, 2 + cx * 10, 2 + cy * 10, PIP[elem], split=(1, 1), tint=tint)
    elif kind == "major":
        (sun_art if major == "sun" else strength_art)(art)
        if rev:
            art = art.transpose(Image.FLIP_TOP_BOTTOM)
    elif kind == "scrap":
        SCRAP_ART[scrap](art)
    if rev and kind == "minor":
        art = art.transpose(Image.FLIP_TOP_BOTTOM)
        # restore the shading side after the flip is fine: print is simply turned upside down
    c.paste(art, (wx + 1, wy + 1))
    # number / roman top-left
    txt = roman if roman else str(n)
    f = F13 if (mini or roman) else F16
    d.text((4 if not mini else 3, wy - 2 if not mini else 8), txt, font=f, fill=numc + (255,), anchor="ls")
    # stars top-right
    if kind != "scrap" and stars:
        for i in range(stars):
            star(c, w - 6 - 6 * i - 1, 3, INK)
    # bottom row
    by = wy + 36 if not mini else wy + 35
    if kind in ("minor", "major"):
        ic = make_icon(elem, 11 if not mini else 9)
        c.paste(ic, (3, by - (0 if not mini else 1)), ic)
        if charm:
            gem(d, w - 11, by + (1 if not mini else 0), CHARM_COL[charm], 7)
        if rev:
            d.polygon([(w // 2 - 3, by + 2), (w // 2 + 3, by + 2), (w // 2, by + 6)], fill=TEAL_D + (255,))
        else:
            diamond(d, w // 2, by + 4, 2, INK + (255,))
    elif kind == "scrap":
        for i in range(3):
            d.polygon([(4 + i * 4, by + 1), (7 + i * 4, by + 1), (5 + i * 4 + (0), by + 6)], fill=BONE + (255,), outline=I)
    if (kind == "scrap" or chewed) and bites:
        cut_bites(c, [(w - 1, 3, 5), (0, h - 10, 4), (w - 12, h - 1, 3)] if not mini else [(w - 1, 3, 4), (0, h - 8, 3)])
    return c

def card_back(w=48, h=64):
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    I = INK + (255,)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=2, fill=I)
    d.rounded_rectangle([1, 1, w - 2, h - 2], radius=1, fill=BONE + (255,))
    d.rectangle([2, 2, w - 3, h - 3], fill=TEAL_D + (255,))
    tmp = Image.new("RGB", (w, h), TEAL_D)
    hatch(tmp, 4, 4, w - 8, h - 8, TEAL, 4, 0)
    hatch(tmp, 4, 4, w - 8, h - 8, TEAL, 4, 0, anti=True)
    c.paste(tmp.crop((4, 4, w - 4, h - 4)), (4, 4))
    d.rectangle([3, 3, w - 4, h - 4], outline=BONE + (255,))
    cx, cy = w // 2, h // 2
    d.ellipse([cx - 12 + 1, cy - 12 + 1, cx + 12 + 1, cy + 12 + 1], fill=VERM + (255,))
    d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=STRAW + (255,), outline=I)
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=GOLD + (255,), outline=I)
    d.ellipse([cx - 2, cy - 11, cx + 2, cy + 11], fill=I)                  # slit pupil
    d.point((cx - 5, cy - 3), fill=BONE + (255,)); d.point((cx - 5, cy - 4), fill=BONE + (255,))
    for (sx, sy) in ((7, 8), (w - 11, 8), (7, h - 12), (w - 11, h - 12)):
        star(c, sx, sy, STRAW)
    return c

def empty_slot(w=48, h=64, label=True):
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = c.load()
    d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=2, fill=PAPER2 + (255,))
    for x in range(w):
        for y in (0, h - 1):
            px[x, y] = INK + (255,) if (x // 2) % 2 == 0 else PAPER2 + (255,)
    for y in range(h):
        for x in (0, w - 1):
            px[x, y] = INK + (255,) if (y // 2) % 2 == 0 else PAPER2 + (255,)
    d.fontmode = "1"
    if label:
        d.text((w // 2, h // 2 + 4), "--", font=F16, fill=PAPER3 + (255,), anchor="ms")
    return c

# --------------------------------------------------------------------------- AI sprites -> woodcut palette
_SP = {}
def sprite(name, height=None, dark=INK, light=BONE, lo=70, hi=190, flip=False):
    """PixelLab PNG -> 2-ink print: luminance becomes ordered-dither between two inks. Binary alpha."""
    key = (name, height, dark, light, lo, hi, flip)
    if key in _SP:
        return _SP[key]
    im = Image.open(os.path.join(RAW, name + ".png")).convert("RGBA")
    im = im.crop(im.getbbox())
    if height and im.height != height:
        s = height / im.height
        im = im.resize((max(1, round(im.width * s)), height), Image.LANCZOS)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    px, op = im.load(), out.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            L = 0.3 * r + 0.59 * g + 0.11 * b
            if r > 170 and g > 140 and b < 135 and r - b > 90:      # cheese / crown gold
                op[x, y] = (STRAW if L > 200 else GOLD) + (255,)
                continue
            t = min(1.0, max(0.0, (L - lo) / (hi - lo)))
            op[x, y] = (light if t > (BAYER[y % 4][x % 4] + 0.5) / 16 else dark) + (255,)
    _SP[key] = out
    return out

def spot_shadow(img, sp, x, y, col, off=(2, 2)):
    img.paste(col, (x + off[0], y + off[1], x + off[0] + sp.width, y + off[1] + sp.height), sp.split()[3])

def place(img, sp, x, y, shadow=None, off=(2, 2)):
    if shadow:
        spot_shadow(img, sp, x, y, shadow, off)
    img.paste(sp, (x, y), sp)

# --------------------------------------------------------------------------- UI pieces
def seg_bar(img, d, x, y, cur, mx, sw, h, col=VERM, ghost=0, tick=5, edge=INK):
    w = mx * sw
    R(d, x - 1, y - 1, w + 2, h + 2, edge)
    R(d, x, y, w, h, BONE)
    R(d, x, y, cur * sw, h, col)
    if ghost:
        hatch(img, x + cur * sw, y, ghost * sw, h, INK, 2, 0)
    for i in range(1, mx):
        if i % tick == 0:
            R(d, x + i * sw - 1, y, 1, h, INK)

def btn(d, x, y, letter, col):
    """round button glyph 14x14 with letter"""
    d.ellipse([x, y, x + 13, y + 13], fill=INK)
    d.ellipse([x + 1, y + 1, x + 12, y + 12], fill=col)
    T(d, x + 7, y + 10, letter, F13, INK, anchor="m")

def bullet(d, x, y, col=VERM):
    d.rectangle([x, y, x + 2, y + 2], fill=col)
    d.point((x + 1, y + 1), fill=INK)

def chain_text(d, x, y, parts, font, cols, gap=9):
    for i, p in enumerate(parts):
        w = T(d, x, y, p, font, cols[i])
        x += w
        if i < len(parts) - 1:
            bullet(d, int(x) + gap // 2 - 1, y - 5, VERM)
            x += gap
    return x

def panel(d, x, y, w, h, fill=BONE, shadow=INK, off=2):
    R(d, x + off, y + off, w, h, shadow)
    R(d, x, y, w, h, INK)
    R(d, x + 1, y + 1, w - 2, h - 2, fill)

def stat_icon(img, name, x, y):
    ic = make_icon(name)
    img.paste(ic, (x, y), ic)

# --------------------------------------------------------------------------- SPREAD
def spread():
    img, d = new_img(480, 320, PAPER)
    # ---- enemy band ---------------------------------------------------------
    R(d, 6, 3, 56, 52, INK)
    R(d, 7, 4, 54, 50, TEAL_T)
    dith(img, 7, 38, 54, 16, TEAL_T, TEAL, 5)
    rat = sprite("grayrat", height=44, lo=65, hi=195)
    place(img, rat, 7 + (54 - rat.width) // 2, 4 + 50 - rat.height - 1, shadow=TEAL_D, off=(2, 1))
    TM(d, 70, 24, "Gray Rat", JQ, INK, VERM)
    T(d, 70, 43, "HP", F13, INK)
    T(d, 85, 44, "18", F16, INK)
    seg_bar(img, d, 107, 36, 18, 18, 4, 8)
    T(d, 70, 55, "Chews paper. Fears the cat.", F13, INK)
    smallcaps(d, 332, 20, "The Rat's Hand", TEAL_D, anchor="r")
    T(d, 332, 34, "scraps have no element", F13, INK, anchor="r")
    for i in range(3):
        put_rgba(img, card("scrap", n=(3, 3, 4)[i], scrap=("sword", "sword", "coin")[i], w=40, h=54), 340 + 44 * i, 2)
    hrule(d, 0, 58, 480, 2)
    # ---- reading strip ------------------------------------------------------
    R(d, 0, 61, 480, 18, INK)
    R(d, 2, 63, 60, 16, VERM_D)
    R(d, 0, 61, 60, 17, VERM)
    smallcaps(d, 30, 74, "Reading", INK, anchor="m")
    chain_text(d, 72, 75, ["Nuzzle x2", "Tail Tap x2", "Step x2", "Catwalk"], F16, [BONE, BONE, BONE, STRAW], gap=11)
    # ---- spread row ---------------------------------------------------------
    smallcaps(d, 10, 89, "The Spread", INK)
    T(d, 408, 90, "4/6", F16, VERM_D, anchor="r")
    dotted(d, 84, 86, 300, INK)
    specs = [dict(elem="fire", n=3, rarity="common"), dict(elem="fire", n=4, stars=1),
             dict(elem="air", n=5, rev=True, rarity="common", charm="catnip"),
             dict(elem="water", n=3, stars=2, rarity="rare", charm="bell")]
    FOCUS = 1
    CY = 98
    for i in range(6):
        x, y = 10 + 56 * i, CY
        if i < 4:
            if i == FOCUS:
                y -= 4
                R(d, x - 4, y - 4, 56, 72, INK)
                R(d, x - 3, y - 3, 54, 70, VERM)
                R(d, x - 1, y - 1, 50, 66, INK)
                R(d, x + 1, y + 1, 46, 62, PAPER)
            put_rgba(img, card("minor", **specs[i]), x, y)
        else:
            put_rgba(img, empty_slot(), x, y)
    # FIGHT
    R(d, 350, CY + 4, 64, 64, INK)
    R(d, 346, CY, 64, 64, INK)
    R(d, 348, CY + 2, 60, 60, VERM)
    R(d, 349, CY + 3, 58, 58, VERM)
    frame(d, 350, CY + 4, 56, 56, BONE)
    TM(d, 378, CY + 34, "Fight", JQ, BONE, INK, anchor="m")
    btn(d, 371, CY + 41, "A", BONE)
    put_rgba(img, paw_cursor(), 10 + 56 * FOCUS + 24 - 8, 165)
    # sidebar --------------------------------------------------------------
    R(d, 418, 82, 56, 160, INK)
    R(d, 418, 82, 56, 13, TEAL_D)
    R(d, 419, 95, 54, 146, BONE)
    T(d, 446, 92, "Per Round", F13, BONE, anchor="m")
    rows = [("DMG", "38", None), ("SINGE", "2", "singe"), ("HEAL", "3", None), ("CURL", "0", "curl")]
    for k, (lab, val, ic) in enumerate(rows):
        y = 96 + k * 36
        if k == 0:
            R(d, 421, y + 1, 52, 34, VERM_D)
            R(d, 420, y, 52, 34, VERM)
        smallcaps(d, 424, y + 12, lab, INK)
        T(d, 424, y + 31, val, F20, INK)
        if ic:
            stat_icon(img, ic, 456, y + 20)
        elif lab == "HEAL":
            R(d, 460, y + 21, 3, 9, MOSS); R(d, 457, y + 24, 9, 3, MOSS)
        else:
            for a in range(8):
                ang = a * math.pi / 4
                d.line([(461 + math.cos(ang) * 2, y + 25 + math.sin(ang) * 2), (461 + math.cos(ang) * 5, y + 25 + math.sin(ang) * 5)], fill=INK)
        if k < 3:
            dotted(d, 421, y + 35, 52, INK)
    # ---- box row -------------------------------------------------------------
    smallcaps(d, 10, 189, "The Box", INK)
    T(d, 408, 191, "2/6", F16, VERM_D, anchor="r")
    dotted(d, 64, 186, 320, INK)
    box = [card("major", elem="fire", roman="XIX", stars=3, rarity="legend", charm="nine", w=40, h=54),
           card("minor", "earth", 7, 1, w=40, h=54)]
    for i in range(6):
        x, y = 10 + 44 * i, 192
        put_rgba(img, box[i] if i < 2 else empty_slot(40, 54, label=False), x, y)
    smallcaps(d, 346, 210, "Night I", TEAL_D, anchor="m")
    T(d, 346, 224, "The Dusty Attic", F13, INK, anchor="m")
    fleuron(d, 346, 230)
    T(d, 346, 244, "Zero is hungry.", F13, INK, anchor="m")
    # ---- detail panel --------------------------------------------------------
    panel(d, 8, 249, 448, 44, BONE, VERM)
    TM(d, 16, 270, "Fire Claw", JQ, INK, VERM)
    ic = make_icon("fire"); img.paste(ic, (112, 260), ic)
    T(d, 127, 270, "Wands 4", F16, INK)
    star(img, 181, 262, INK)
    T(d, 189, 270, "1", F16, INK)
    R(d, 206, 259, 48, 14, INK)
    T(d, 230, 270, "Upright", F13, BONE, anchor="m")
    ex = chain_text(d, 16, 287, ["Nuzzle +2", "Tail Tap +1", "Step +2"], F16, [INK] * 3, gap=11)
    dotted(d, int(ex) + 8, 284, 376 - int(ex) - 8, INK)
    d.polygon([(378, 281), (386, 281), (386, 278), (392, 283), (386, 288), (386, 285), (378, 285)], fill=INK)
    R(d, 398, 253, 52, 36, INK)
    R(d, 399, 254, 50, 34, VERM)
    smallcaps(d, 424, 265, "Power", INK, anchor="m")
    T(d, 424, 285, "9", F20, INK, anchor="m")
    # ---- footer ----------------------------------------------------------------
    R(d, 0, 298, 480, 22, INK)
    R(d, 0, 296, 480, 2, VERM)
    T(d, 8, 314, "Domino", F16, BONE)
    T(d, 56, 314, "HP", F13, STRAW)
    T(d, 70, 314, "30/36", F16, BONE)
    seg_bar(img, d, 106, 307, 30, 36, 2, 6, col=VERM)
    T(d, 192, 314, "Treats", F13, STRAW)
    d.ellipse([224, 305, 234, 315], fill=GOLD, outline=BONE)
    T(d, 242, 314, "14", F16, BONE)
    x = 284
    for (letter, col, label) in (("A", VERM, "Pick up"), ("B", TEAL_T, "Menu"), ("C", STRAW, "Info")):
        btn(d, x, 303, letter, col)
        w = T(d, x + 18, 314, label, F16, BONE)
        x += 18 + w + 10
    return img


# --------------------------------------------------------------------------- BATTLE
def glow(img, cx, cy, r, c_in, c_out):
    px = img.load()
    for y in range(max(0, cy - r), min(img.height, cy + r + 1)):
        for x in range(max(0, cx - r), min(img.width, cx + r + 1)):
            dist = math.hypot(x - cx, y - cy)
            if dist < r:
                lvl = int(16 * (1 - dist / r) * 1.2)
                if BAYER[y % 4][x % 4] < lvl:
                    px[x, y] = c_in

def starburst(d, cx, cy, r_out, r_in, n, fill, outline=INK, rot=0.0):
    pts = []
    for k in range(n * 2):
        a = rot + k * math.pi / n
        r = r_out if k % 2 == 0 else r_in
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    d.polygon(pts, fill=fill, outline=outline)

def sunburst(img, cx, cy, r, n, c1, c2, rot=0.0):
    px = img.load()
    for y in range(max(0, cy - r), min(img.height, cy + r + 1)):
        for x in range(max(0, cx - r), min(img.width, cx + r + 1)):
            dx, dy = x - cx, y - cy
            dist = math.hypot(dx, dy)
            if dist < r:
                a = (math.atan2(dy, dx) + rot) % (2 * math.pi)
                wedge = int(a / (2 * math.pi) * n * 2)
                col = c1 if wedge % 2 == 0 else c2
                if dist > r - 10 and BAYER[y % 4][x % 4] < (dist - (r - 10)) * 1.6:
                    col = c2
                px[x, y] = col

def attic_bg(img, d):
    """Pantry attic: plank wall, moon window, hanging lamp, shelf, floorboards. All primitives, no tiles needed."""
    R(d, 0, 26, 480, 172, PAPER)
    for y in range(40, 198, 16):                       # plank seams
        R(d, 0, y, 480, 1, PAPER2)
        off = (y // 16 % 3) * 53
        for x in range(off % 160, 480, 160):
            R(d, x, y - 16 + 1, 1, 15, PAPER2)
    dith(img, 0, 26, 18, 172, PAPER, PAPER3, 3)
    dith(img, 462, 26, 18, 172, PAPER, PAPER3, 3)
    # light shaft from the moon window
    for y in range(96, 198):
        t = (y - 96) / 102
        x0, x1 = int(34 - 26 * t), int(92 + 40 * t)
        for x in range(x0, x1):
            if BAYER[y % 4][x % 4] < 5:
                img.putpixel((x, y), BONE)
    # round window with cat-eye moon
    d.ellipse([30, 32, 94, 96], fill=INK)
    d.ellipse([34, 36, 90, 92], fill=TEAL_D)
    hatch(img, 36, 38, 52, 52, TEAL, 4, 0)
    d.ellipse([46, 44, 76, 74], fill=VERM)
    d.ellipse([45, 43, 75, 73], fill=STRAW, outline=INK)
    d.ellipse([58, 45, 62, 71], fill=INK)
    R(d, 60, 36, 3, 56, INK)
    R(d, 34, 63, 56, 3, INK)
    d.ellipse([30, 32, 94, 96], outline=INK)
    # hanging lamp
    R(d, 176, 26, 2, 16, INK)
    glow(img, 177, 56, 26, STRAW, PAPER)
    d.polygon([(168, 52), (186, 52), (181, 41), (173, 41)], fill=INK)
    d.ellipse([172, 52, 182, 60], fill=STRAW, outline=INK)
    # shelf under the enemy cards
    R(d, 204, 85, 272, 4, INK)
    R(d, 204, 89, 272, 1, PAPER3)
    for bx in (212, 330, 450):
        d.polygon([(bx, 89), (bx + 10, 89), (bx, 99)], fill=INK)
    # floor
    R(d, 0, 198, 480, 30, PAPER2)
    R(d, 0, 198, 480, 2, INK)
    for k, y in enumerate((209, 219)):
        R(d, 0, y, 480, 1, PAPER3)
        for x in range((k * 37) % 61, 480, 61):
            R(d, x, y + 1, 1, 9, PAPER3)
    dith(img, 0, 200, 480, 6, PAPER2, PAPER3, 6)
    hrule(d, 0, 228, 480, 2)

def ribbon(img, d, x0, x1, y, h=30):
    tail = 14
    d.polygon([(x0 - tail, y + 6), (x0 + 6, y + 6), (x0 + 6, y + h + 6), (x0 - tail, y + h + 6), (x0 - tail + 7, y + h // 2 + 6)], fill=VERM_D, outline=INK)
    d.polygon([(x1 + tail, y + 6), (x1 - 6, y + 6), (x1 - 6, y + h + 6), (x1 + tail, y + h + 6), (x1 + tail - 7, y + h // 2 + 6)], fill=VERM_D, outline=INK)
    R(d, x0 + 2, y + 2, x1 - x0, h, VERM)
    R(d, x0, y, x1 - x0, h, INK)
    R(d, x0 + 2, y + 2, x1 - x0 - 4, h - 4, INK)
    frame(d, x0 + 3, y + 3, x1 - x0 - 6, h - 6, BONE)

def battle():
    img, d = new_img(480, 320, PAPER)
    attic_bg(img, d)
    # top bar: boss name + HP
    R(d, 0, 0, 480, 26, INK)
    R(d, 0, 26, 480, 2, VERM)
    TM(d, 8, 21, "Chubbs, the Pantry King", JQ, BONE, VERM)
    T(d, 262, 18, "HP", F13, STRAW)
    seg_bar(img, d, 278, 9, 52, 90, 1, 9, col=VERM, ghost=14, tick=10, edge=BONE)
    T(d, 386, 19, "52/90", F16, BONE)
    stat_icon(img, "singe", 428, 7); T(d, 441, 19, "1", F16, BONE)
    stat_icon(img, "curl", 455, 7); T(d, 468, 19, "0", F16, BONE)
    # enemy hand on the shelf
    hand = [dict(kind="scrap", n=6, scrap="sword"), dict(kind="scrap", n=8, scrap="cup"),
            dict(kind="major", roman="VIII", major="strength", rev=True, chewed=True, elem="fire", stars=0),
            dict(kind="scrap", n=3, scrap="gnaw"), dict(kind="scrap", n=8, scrap="coin"), dict(kind="scrap", n=6, scrap="sword")]
    for i, spec in enumerate(hand):
        put_rgba(img, card(w=40, h=54, **spec), 208 + 44 * i, 30)
    # halos
    d.ellipse([12, 120, 100, 208], fill=TEAL)
    d.ellipse([8, 116, 104, 212], outline=TEAL)
    sunburst(img, 420, 152, 70, 18, VERM_T, PAPER, rot=0.1)
    # fighters
    dom = sprite("domino", lo=100, hi=175)
    place(img, dom, 24, 198 - dom.height + 2, shadow=TEAL_D, off=(3, 2))
    chub = sprite("chubbs", lo=60, hi=205)
    place(img, chub, 376, 204 - chub.height, shadow=VERM_D, off=(3, 2))
    # damage: starburst + 2x numerals
    starburst(d, 324, 120, 34, 22, 14, VERM, INK, rot=0.2)
    starburst(d, 322, 118, 32, 20, 14, STRAW, INK, rot=0.2)
    num = Image.new("RGBA", (40, 14), (0, 0, 0, 0)); nd = ImageDraw.Draw(num); nd.fontmode = "1"
    nd.text((1, 12), "38", font=F20, fill=VERM + (255,), anchor="ls")
    nd.text((0, 11), "38", font=F20, fill=INK + (255,), anchor="ls")
    num = num.crop(num.getbbox())
    num = num.resize((num.width * 2, num.height * 2), Image.NEAREST)
    img.paste(num, (322 - num.width // 2, 118 - num.height // 2), num)
    # reading chain ribbon, sized to its text; each link is bigger and hotter than the last
    w1, w2, w3 = TW("Nuzzle +2", F16), TW("Step +2", F16), TW("Catwalk!", JQ)
    total = int(w1 + w2 + w3 + 40)
    rx0 = 236 - total // 2 - 16
    ry = 156
    ribbon(img, d, rx0, rx0 + total + 32, ry)
    x = rx0 + 16
    x += T(d, x, ry + 19, "Nuzzle +2", F16, BONE) + 6
    d.polygon([(x, ry + 11), (x + 7, ry + 15), (x, ry + 19)], fill=STRAW); x += 14
    x += T(d, x, ry + 19, "Step +2", F16, STRAW) + 6
    d.polygon([(x, ry + 11), (x + 7, ry + 15), (x, ry + 19)], fill=VERM); x += 14
    TM(d, x, ry + 22, "Catwalk!", JQ, VERM, BONE)
    # player band
    hatch(img, 0, 230, 480, 74, PAPER2, 4, 0)
    for i in range(6):
        x, y = 8 + 52 * i, 238
        if i < 4:
            spec = [dict(elem="fire", n=3, rarity="common"), dict(elem="fire", n=4, stars=1),
                    dict(elem="air", n=5, rev=True, rarity="common", charm="catnip"),
                    dict(elem="water", n=3, stars=2, rarity="rare", charm="bell")][i]
            if i == 1:
                y -= 4
                R(d, x - 4, y - 4, 56, 72, INK)
                R(d, x - 3, y - 3, 54, 70, VERM)
                R(d, x - 1, y - 1, 50, 66, INK)
                R(d, x + 1, y + 1, 46, 62, STRAW)
            put_rgba(img, card("minor", **spec), x, y)
        else:
            put_rgba(img, empty_slot(label=False), x, y)
    panel(d, 330, 236, 142, 62, BONE, VERM)
    TM(d, 338, 258, "Domino", JQ, INK, VERM)
    T(d, 338, 275, "HP", F13, INK)
    seg_bar(img, d, 354, 268, 33, 36, 3, 8, col=VERM)
    T(d, 338, 292, "33/36", F16, INK)
    stat_icon(img, "leap", 394, 283); T(d, 407, 292, "1", F16, INK)
    stat_icon(img, "curl", 424, 283); T(d, 437, 292, "0", F16, INK)
    R(d, 0, 304, 480, 16, INK)
    T(d, 8, 316, "Round 1", F16, BONE)
    T(d, 70, 316, "Reading 2 of 4", F16, STRAW)
    btn(d, 392, 305, "A", VERM)
    x = 410 + T(d, 410, 316, "2x", F16, BONE) + 10
    btn(d, x, 305, "B", TEAL_T)
    T(d, x + 18, 316, "Skip", F16, BONE)
    return img

# --------------------------------------------------------------------------- STYLE SHEET
def up(img, s=2):
    return img.resize((img.width * s, img.height * s), Image.NEAREST)

def paste_up(dst, src, x, y, s=2):
    big = up(src, s)
    dst.paste(big, (x, y), big if big.mode == "RGBA" else None)
    return big.size

def big_text(d_img, x, y, s, font, ink, spot, scale=2, off=(1, 1)):
    """Display text rendered at native size then scaled (chunky headline)."""
    w = int(TW(s, font)) + 4
    t = Image.new("RGBA", (w, 34), (0, 0, 0, 0))
    td = ImageDraw.Draw(t); td.fontmode = "1"
    td.text((2 + off[0], 24 + off[1]), s, font=font, fill=spot + (255,), anchor="ls")
    td.text((2, 24), s, font=font, fill=ink + (255,), anchor="ls")
    t = up(t, scale)
    d_img.paste(t, (x, y - 24 * scale), t)
    return t.width

def story_frame(i):
    im, d = new_img(104, 64, PAPER)
    mini_a = card("minor", "fire", 4, 1, w=40, h=54)
    mini_b = card("minor", "air", 5, 1, w=40, h=54, rev=True)
    if i == 0:
        put_rgba(im, mini_a, 8, 6); put_rgba(im, mini_b, 56, 6)
        put_rgba(im, paw_cursor(), 20, 46)
    elif i == 1:
        flash = card("minor", "fire", 4, 1, w=40, h=54)
        px = flash.load()
        for yy in range(flash.height):
            for xx in range(flash.width):
                if px[xx, yy][3]:
                    px[xx, yy] = BONE + (255,) if 10 < yy < 46 and 8 < xx < 33 else px[xx, yy]
        put_rgba(im, mini_b, 56, 6); put_rgba(im, flash, 8, 2)
        for (sx, sy) in ((4, 4), (50, 2), (46, 24), (2, 32), (48, 44), (30, 0)):
            d.rectangle([sx, sy, sx + 1, sy + 1], fill=VERM)
        d.rectangle([4, 56, 7, 57], fill=INK)
    elif i == 2:
        put_rgba(im, mini_a, 8, 2); put_rgba(im, mini_b, 56, 6)
        for (px_, py_) in ((50, 40), (54, 33), (50, 26), (54, 19)):      # paw-print trail between the cards
            d.rectangle([px_, py_, px_ + 2, py_ + 2], fill=VERM); d.point((px_ - 1, py_ - 1), fill=VERM)
        R(d, 24, 21, 56, 14, INK)
        T(d, 52, 32, "Nuzzle +2", F16, BONE, anchor="m")
    else:
        R(d, 0, 0, 104, 64, PAPER)
        starburst(d, 70, 26, 26, 16, 12, VERM, INK, rot=0.2)
        starburst(d, 69, 25, 24, 14, 12, STRAW, INK, rot=0.2)
        T(d, 69, 32, "38", F20, INK, anchor="m")
        ribbon(im, d, 8, 96, 40, h=20)
        TM(d, 52, 57, "Catwalk!", JQ, VERM, BONE, anchor="m")
    frame(d, 0, 0, 104, 64, INK)
    return im

def sheet():
    W, H = 960, 1040
    img, d = new_img(W, H, PAPER)
    # print furniture: double frame
    R(d, 10, 10, W - 20, 3, INK); R(d, 10, H - 13, W - 20, 3, INK)
    R(d, 10, 10, 3, H - 20, INK); R(d, W - 13, 10, 3, H - 20, INK)
    R(d, 16, 16, W - 32, 1, INK); R(d, 16, H - 17, W - 32, 1, INK)
    R(d, 16, 16, 1, H - 32, INK); R(d, W - 17, 16, 1, H - 32, INK)
    # ---- masthead
    big_text(img, 30, 62, "Nine Lives Arcana", JQ, INK, VERM, scale=2)
    smallcaps(d, 32, 88, "Direction 04", VERM_D)
    T(d, 124, 89, "Woodcut Riso Almanac", F20, INK)
    T(d, 30, 112, "An 18th-century folk almanac, risograph-printed in black, vermilion and teal.", F16, INK)
    T(d, 30, 130, "Hard rules, blackletter heads, halftone shade, one pixel of misregistration.", F16, INK)
    put_rgba(img, up(card("back"), 2), 826, 24)
    put_rgba(img, up(card("minor", "fire", 4, 1, rarity="common"), 2), 716, 24)
    # ---- palette
    y0 = 160
    smallcaps(d, 30, y0, "Palette (hex, RGB565)", INK)
    dotted(d, 30, y0 + 5, 318, INK)
    order = ["ink", "paper", "bone", "paper2", "paper3", "plum", "verm", "verm_d", "verm_t", "teal", "teal_d", "teal_t",
             "straw", "straw_t", "gold", "moss", "moss_d", "moss_t", "scrap", "scrap_d", "scrap_t", "cool", "cool_t"]
    for k, nm in enumerate(order):
        col, row = k % 3, k // 3
        x, y = 30 + col * 108, y0 + 14 + row * 17
        R(d, x, y, 18, 12, INK); R(d, x + 1, y + 1, 16, 10, PAL[nm])
        c = PAL[nm]
        T(d, x + 23, y + 11, "#%02X%02X%02X %04X" % (c[0], c[1], c[2], to565(c)), F16, INK)
    # ---- type
    x0 = 380
    smallcaps(d, x0, y0, "Type", INK)
    dotted(d, x0, y0 + 5, 290, INK)
    T(d, x0, y0 + 24, "Jacquard 24, display (OFL)", F13, VERM_D)
    for k, line in enumerate(["ABCDEFGHIJKLM", "NOPQRSTUVWXYZ", "abcdefghijklm", "nopqrstuvwxyz", "0123456789"]):
        TM(d, x0, y0 + 48 + k * 24, line, JQ, INK, VERM)
    T(d, x0, y0 + 178, "Jersey 10 at 16 and 20, body (OFL)", F13, VERM_D)
    T(d, x0, y0 + 195, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", F16, INK)
    T(d, x0, y0 + 211, "abcdefghijklmnopqrstuvwxyz 0123456789", F16, INK)
    T(d, x0, y0 + 230, "Nuzzle +2 . Tail Tap +1 . Step +2 -> Power 9", F16, INK)
    # ---- icons
    x1 = 700
    smallcaps(d, x1, y0, "Icons", INK)
    dotted(d, x1, y0 + 5, 236, INK)
    groups = [("Elements", ["fire", "air", "water", "earth"], ["Fire", "Air", "Water", "Earth"]),
              ("Statuses", ["singe", "puff", "drowsy", "curl", "leap"], ["Singe", "Puff", "Drowsy", "Curl", "Leap"]),
              ("Charms", ["catnip", "bell", "nine"], ["Catnip", "Bell", "Nine Lives"])]
    gy = y0 + 20
    for (gname, names, labels) in groups:
        T(d, x1, gy + 6, gname, F13, TEAL_D)
        for k, nm in enumerate(names):
            cx = x1 + k * 47
            paste_up(img, make_icon(nm), cx, gy + 12)
            T(d, cx + 11, gy + 50, labels[k], F13, INK, anchor="m")
        gy += 62
    paste_up(img, paw_cursor(), x1, gy + 4)
    T(d, x1 + 44, gy + 26, "paw cursor", F13, INK)
    # ---- card plates + anatomy
    y1 = 420
    smallcaps(d, 30, y1, "Card plates (48x64), double size", INK)
    dotted(d, 30, y1 + 5, 650, INK)
    plates = [(card("minor", "fire", 4, 1, rarity="common", charm="bell"), "Fire 4 Upright"),
              (card("minor", "water", 3, 2, rev=True, rarity="rare", charm="catnip"), "Water 3 Reversed"),
              (card("major", elem="fire", roman="XIX", stars=3, rarity="legend", charm="nine"), "XIX The Sun"),
              (card("scrap", n=3, scrap="sword"), "Broken Sword 3"),
              (card("back"), "Card back")]
    cy = y1 + 22
    for k, (c, lab) in enumerate(plates):
        x = 46 + k * 130
        paste_up(img, c, x, cy)
        T(d, x + 48, cy + 144, lab, F13, INK, anchor="m")
    cx = 700
    smallcaps(d, cx, y1, "Anatomy", INK)
    dotted(d, cx, y1 + 5, 236, INK)
    notes = ["number (Roman on Majors)", "stars", "art window 32x32, tint hatch", "element roundel (alchemy)",
             "charm gem", "rarity ring (bone/teal/plum/gold)", "Reversed: art flipped, teal inks"]
    marks = [(-14, 14, 4, 14), (110, 10, 90, 10), (110, 62, 80, 62), (-14, 108, 4, 108), (110, 116, 76, 116), (110, 38, 92, 38)]
    for k, t in enumerate(notes):
        yy = y1 + 26 + k * 18
        d.ellipse([cx, yy - 10, cx + 12, yy + 2], fill=VERM, outline=INK)
        T(d, cx + 7, yy, str(k + 1), F13, INK, anchor="m")
        T(d, cx + 18, yy, t, F16, INK)
    for k, (mx, my, tx, ty) in enumerate(marks):
        X, Y, TX, TY = 46 + mx, cy + my, 46 + tx, cy + ty
        d.line([(X, Y), (TX, TY)], fill=INK)
        d.ellipse([X - 6, Y - 6, X + 6, Y + 6], fill=VERM, outline=INK)
        T(d, X + 1, Y + 4, str(k + 1), F13, INK, anchor="m")
    # ---- characters at 2x
    y2 = 612
    smallcaps(d, 30, y2 - 12, "Cast, shown at double size", INK)
    dotted(d, 30, y2 - 7, 650, INK)
    cast = [("domino", dict(lo=100, hi=175), "Domino", TEAL, TEAL_D), ("zero", dict(dark=TEAL_D, light=BONE, lo=90, hi=175), "Zero", TEAL_T, TEAL_D),
            ("grayrat", dict(lo=65, hi=195), "Gray Rat", TEAL_T, TEAL_D), ("chubbs", dict(lo=60, hi=205), "Chubbs", VERM_T, VERM_D)]
    x = 36
    floor = y2 + 206
    for (nm, kw, lab, plate, shade) in cast:
        sp = sprite(nm, **kw)
        big = up(sp, 2)
        r = max(big.width, big.height) // 2 + 8
        ccx, ccy = x + big.width // 2, floor - big.height // 2
        d.ellipse([ccx - r, ccy - r, ccx + r, ccy + r], fill=plate)
        img.paste(shade, (x + 4, floor - big.height + 3, x + 4 + big.width, floor + 3), big.split()[3])
        img.paste(big, (x, floor - big.height), big)
        T(d, ccx, floor + 20, lab, F16, INK, anchor="m")
        x += big.width + 26
    # ---- tiles + background crop
    xt = 700
    smallcaps(d, xt, y2 - 12, "Tiles + backdrop", INK)
    dotted(d, xt, y2 - 7, 236, INK)
    tiles = []
    for kind in range(4):
        t, td = new_img(16, 16, PAPER)
        if kind == 0:
            R(td, 0, 7, 16, 1, PAPER3); R(td, 8, 0, 1, 7, PAPER3); R(td, 3, 8, 1, 8, PAPER3)
        elif kind == 1:
            hatch(t, 0, 0, 16, 16, INK, 3, 0)
        elif kind == 2:
            dith(t, 0, 0, 16, 16, PAPER, VERM, 5)
        else:
            hatch(t, 0, 0, 16, 16, TEAL, 4, 0); hatch(t, 0, 0, 16, 16, TEAL, 4, 0, anti=True)
        tiles.append(t)
    for k, t in enumerate(tiles):
        paste_up(img, t, xt + k * 60 + 1, y2 + 3, 3)
        frame(d, xt + k * 60, y2 + 2, 50, 50, INK)
    for k, lb in enumerate(["plank", "woodcut", "halftone", "lattice"]):
        T(d, xt + k * 60 + 25, y2 + 66, lb, F13, INK, anchor="m")
    bd = backdrop_only().crop((0, 26, 232, 140))
    paste_up(img, bd, xt, y2 + 78, 1)
    frame(d, xt - 1, y2 + 77, 234, 116, INK)
    T(d, xt, y2 + 206, "Attic backdrop: 27 KB as byte-RLE", F16, INK)
    # ---- storyboard
    y3 = 878
    smallcaps(d, 30, y3 - 14, "Signature motion: lift, link, chain, hit", INK)
    dotted(d, 30, y3 - 9, 900, INK)
    caps = ["1  Paw picks up the card", "2  Lift 4 px, paper flash", "3  Paw trail, name floats", "4  Chain banner, 2x hit number"]
    for i in range(4):
        fr = story_frame(i)
        x = 30 + i * 226
        paste_up(img, fr, x, y3, 2)
        frame(d, x - 1, y3 - 1, 210, 130, INK)
        T(d, x, y3 + 146, caps[i], F16, INK)
        if i < 3:
            d.polygon([(x + 212, y3 + 56), (x + 223, y3 + 64), (x + 212, y3 + 72)], fill=VERM, outline=INK)
    return img

# --------------------------------------------------------------------------- verification + output
def verify(name, im):
    im = im.convert("RGB")
    cols = im.getcolors(1 << 20)
    bad = [c for n, c in cols if (c[0] & 7, c[1] & 3, c[2] & 7) != (c[0] >> 5, c[1] >> 6, c[2] >> 5)]
    print("%-14s %dx%d colors=%d rgb565-exact=%s" % (name, im.width, im.height, len(cols), not bad))
    assert not bad, bad
    return len(cols)

def rle_size(im, bits=4):
    """Rough flash estimate for a full-screen 16-colour bitmap: raw 4bpp and a simple (count,index) RLE."""
    idx = {}
    px = list(im.convert("RGB").getdata())
    for p in px:
        idx.setdefault(p, len(idx))
    runs, prev, n = 0, None, 0
    for p in px:
        if p == prev and n < 255:
            n += 1
        else:
            runs += 1
            prev, n = p, 1
    return len(px) * bits // 8, runs * 2 + len(idx) * 2

def backdrop_only():
    img, d = new_img(480, 320, PAPER)
    attic_bg(img, d)
    return img

def main():
    s = spread(); b = battle(); sh = sheet()
    s.save(os.path.join(ROOT, "spread.png")); b.save(os.path.join(ROOT, "battle.png"))
    up(s).save(os.path.join(ROOT, "spread@2x.png")); up(b).save(os.path.join(ROOT, "battle@2x.png"))
    sh.save(os.path.join(ROOT, "sheet.png"))
    for n, im in (("spread", s), ("battle", b), ("spread@2x", up(s)), ("battle@2x", up(b)), ("sheet", sh)):
        verify(n, im)
    raw4, rle = rle_size(backdrop_only())
    print("attic backdrop (480x320): 4bpp raw %d B, byte-RLE %d B" % (raw4, rle))
    raw4, rle = rle_size(b)
    print("battle full frame        : 4bpp raw %d B, byte-RLE %d B" % (raw4, rle))

if __name__ == "__main__":
    main()
