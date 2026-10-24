"""Drawing primitives: rich pixel text, panels, ornaments, cards. Everything is drawn 1:1 at native resolution."""
import os
import random
import re
from PIL import Image, ImageDraw, ImageFont, ImageOps

import icons
from pal import P, snap

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
_fc = {}


def font(name, size):
    key = (name, size)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(os.path.join(FONTS, name + ".ttf"), size)
    return _fc[key]


def BODY():
    return font("VT323-Regular", 16)


def TITLE():
    return font("Jacquard24-Regular", 24)


def SMALL():
    return font("Silkscreen-Regular", 8)


def NUM():
    return font("Jersey10-Regular", 10)


def D(im):
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    return d


def rect(im, x0, y0, x1, y1, col):
    ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], fill=col)


def frame(im, x0, y0, x1, y1, col):
    ImageDraw.Draw(im).rectangle([x0, y0, x1, y1], outline=col)


def px(im, x, y, col):
    if 0 <= x < im.width and 0 <= y < im.height:
        im.putpixel((x, y), col)


def paste(im, sprite, x, y, flipx=False, flipy=False, scale=1):
    s = sprite
    if flipx:
        s = ImageOps.mirror(s)
    if flipy:
        s = ImageOps.flip(s)
    if scale != 1:
        s = s.resize((s.width * scale, s.height * scale), Image.NEAREST)
    im.paste(s, (x, y), s if s.mode == "RGBA" else None)


# ---------------------------------------------------------------- rich text
TOKENS = {"{.}": 6, "{>}": 11, "{*}": 7, "{v}": 9}


def _parts(s):
    return [p for p in re.split(r"(\{[.>*v]\})", s) if p]


def text_w(s, f=None):
    f = f or BODY()
    w = 0
    for p in _parts(s):
        w += TOKENS[p] if p in TOKENS else int(f.getlength(p))
    return w


def text(im, x, y, s, col, f=None, outline=None, shadow=None, anchor="l"):
    """Draw text with baseline y. Inline tokens: {.} dot, {>} arrow, {*} star, {v} reversed triangle."""
    f = f or BODY()
    w = text_w(s, f)
    if anchor == "r":
        x -= w
    elif anchor == "m":
        x -= w // 2
    d = D(im)
    cx = x
    for p in _parts(s):
        if p in TOKENS:
            sp = {"{.}": icons.dot(col), "{>}": icons.arrow(col), "{*}": icons.star5("gold3"),
                  "{v}": icons.tri_down(col)}[p]
            oy = {"{.}": -6, "{>}": -9, "{*}": -9, "{v}": -9}[p]
            ox = {"{.}": 2, "{>}": 1, "{*}": 1, "{v}": 1}[p]
            if outline and p != "{*}":
                paste(im, icons.grid_image(["o" * sp.width] * sp.height, {"o": outline}) if False else sp, cx + ox, y + oy)
            else:
                paste(im, sp, cx + ox, y + oy)
            cx += TOKENS[p]
        else:
            if outline:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
                    d.text((cx + dx, y + dy), p, font=f, fill=outline, anchor="ls")
            if shadow:
                d.text((cx + 1, y + 1), p, font=f, fill=shadow, anchor="ls")
            d.text((cx, y), p, font=f, fill=col, anchor="ls")
            cx += int(f.getlength(p))
    return w


def scaled_text(im, x, y, s, col, f, k, outline=None, anchor="l"):
    """Render text on a scratch layer at native size then scale by integer k (chunky headline)."""
    w = text_w(s, f) + 4
    h = 40
    lay = Image.new("RGBA", (w + 4, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.fontmode = "1"
    if outline:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                ld.text((3 + dx, 30 + dy), s, font=f, fill=outline, anchor="ls")
    ld.text((3, 30), s, font=f, fill=col, anchor="ls")
    lay = lay.resize((lay.width * k, lay.height * k), Image.NEAREST)
    bx = x - (lay.width // 2 if anchor == "m" else 0)
    im.paste(lay, (bx - 3 * k, y - 30 * k), lay)
    return w * k


# ---------------------------------------------------------------- ornaments
def star_tile(w=32, h=32, seed=7, density=6):
    """Sparse star-dust tile on the fast background colour."""
    t = Image.new("RGB", (w, h), P["night1"])
    rnd = random.Random(seed)
    cols = [P["night2"], P["night2"], P["night3"], P["night4"], P["silver1"]]
    for _ in range(density):
        x, y = rnd.randrange(1, w - 1), rnd.randrange(1, h - 1)
        c = rnd.choice(cols)
        t.putpixel((x, y), c)
        if c in (P["silver1"],) and rnd.random() < 0.8:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                t.putpixel((x + dx, y + dy), P["night3"])
    return t


def tile_fill(im, tile, box=None):
    x0, y0, x1, y1 = box or (0, 0, im.width, im.height)
    for y in range(y0, y1, tile.height):
        for x in range(x0, x1, tile.width):
            im.paste(tile.crop((0, 0, min(tile.width, x1 - x), min(tile.height, y1 - y))), (x, y))


def corners(im, x0, y0, x1, y1, a="gold2", b="gold1"):
    c = icons.corner(a, b)
    paste(im, c, x0, y0)
    paste(im, c, x1 - c.width + 1, y0, flipx=True)
    paste(im, c, x0, y1 - c.height + 1, flipy=True)
    paste(im, c, x1 - c.width + 1, y1 - c.height + 1, flipx=True, flipy=True)


def panel(im, x0, y0, x1, y1, fill="night0", edge="gold1", orn=True):
    if fill:
        rect(im, x0, y0, x1, y1, P[fill])
    frame(im, x0, y0, x1, y1, P[edge])
    if orn:
        corners(im, x0 - 1, y0 - 1, x1 + 1, y1 + 1)


def divider(im, x0, x1, y, mid=True):
    rect(im, x0, y, x1, y, P["gold0"])
    cx = (x0 + x1) // 2
    if mid:
        rect(im, cx - 14, y, cx + 14, y, P["night1"])
        paste(im, icons.diamond("gold3"), cx - 2, y - 2)
        rect(im, cx - 14, y, cx - 5, y, P["gold1"])
        rect(im, cx + 5, y, cx + 14, y, P["gold1"])


def crescent(im, cx, cy, r, col="silver2", bg="night1", dx=None):
    d = ImageDraw.Draw(im)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=P[col])
    dx = dx if dx is not None else max(2, r // 2)
    d.ellipse([cx - r + dx + 1, cy - r - 1, cx + r + dx + 1, cy + r - 1], fill=P[bg])


def _lens(cx, cy, hw, hh):
    pts = []
    for i in range(-hw, hw + 1):
        t = i / hw
        pts.append((cx + i, cy - round(hh * (1 - t * t) ** 0.8)))
    for i in range(hw, -hw - 1, -1):
        t = i / hw
        pts.append((cx + i, cy + round(hh * (1 - t * t) ** 0.8)))
    return pts


def moon_eye(im, cx, cy, r, ring="gold3", field="gold2", pupil="night0", bg=None):
    """Gold cat-eye moon: ringed disc, almond lens, amber iris, slit pupil."""
    d = ImageDraw.Draw(im)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=P["gold1"])
    d.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=P[ring])
    d.ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], fill=P[field])
    hw, hh = r - 3, max(3, int((r - 3) * 0.62))
    d.polygon(_lens(cx, cy, hw, hh), fill=P["night0"])
    d.polygon(_lens(cx, cy, hw - 1, hh - 1), fill=P["amber3"])
    d.polygon(_lens(cx, cy, hw - 3, max(1, hh - 3)), fill=P["amber2"])
    d.rectangle([cx - 1, cy - hh + 1, cx, cy + hh - 1], fill=P[pupil])
    px(im, cx - 3, cy - 2, P["gold4"]); px(im, cx - 4, cy - 1, P["gold4"])


def candle(im, x, y_bottom, h=14, flame=True, tall_flame=5):
    rect(im, x, y_bottom - h, x + 4, y_bottom, P["silver2"])
    rect(im, x + 3, y_bottom - h, x + 4, y_bottom, P["silver1"])
    rect(im, x, y_bottom - h, x + 4, y_bottom - h, P["moon"])
    px(im, x + 2, y_bottom - h - 1, P["night0"])
    if flame:
        fy = y_bottom - h - 2
        rect(im, x + 2, fy - tall_flame + 1, x + 2, fy, P["amber2"])
        rect(im, x + 1, fy - 2, x + 3, fy, P["amber2"])
        rect(im, x + 2, fy - 3, x + 2, fy, P["amber3"])
        px(im, x + 2, fy - tall_flame, P["amber1"])
        px(im, x + 2, fy - 1, P["gold4"])


def sparkle(im, x, y, col="moon", r=2):
    px(im, x, y, P[col])
    for i in range(1, r + 1):
        for dx, dy in ((i, 0), (-i, 0), (0, i), (0, -i)):
            px(im, x + dx, y + dy, P[col] if i == 1 else P["silver1"])


def bar(im, x0, y0, x1, y1, frac, fill="fire1", hi="fire2", back="night0", edge="gold1"):
    frame(im, x0, y0, x1, y1, P[edge])
    rect(im, x0 + 1, y0 + 1, x1 - 1, y1 - 1, P[back])
    w = int((x1 - x0 - 2) * frac)
    if w > 0:
        rect(im, x0 + 1, y0 + 1, x0 + w, y1 - 1, P[fill])
        rect(im, x0 + 1, y0 + 1, x0 + w, y0 + 1, P[hi])
    # tick marks
    n = 4
    for i in range(1, n):
        tx = x0 + 1 + (x1 - x0 - 2) * i // n
        px(im, tx, y1 - 1, P["night3"] if tx > x0 + w else P["night0"])


def button_gem(im, cx, cy, letter):
    d = ImageDraw.Draw(im)
    d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=P["gold1"])
    d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=P["night0"])
    d.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=P["night2"])
    text(im, cx - 2, cy + 3, letter, P["gold4"], font("Silkscreen-Regular", 8))


def hint(im, x, y, letter, label):
    button_gem(im, x + 6, y - 4, letter)
    return 14 + text(im, x + 16, y, label, P["silver2"]) + 2


# ---------------------------------------------------------------- cards
RARITY = {"none": "silver2", "common": "blue", "rare": "purple", "legendary": "gold3", "curse": "red"}
PIPS = {
    1: [(16, 16)], 2: [(16, 9), (16, 23)], 3: [(16, 7), (16, 16), (16, 25)],
    4: [(9, 9), (23, 9), (9, 23), (23, 23)], 5: [(9, 9), (23, 9), (16, 16), (9, 23), (23, 23)],
    6: [(9, 7), (23, 7), (9, 16), (23, 16), (9, 25), (23, 25)],
    7: [(9, 7), (23, 7), (9, 16), (23, 16), (9, 25), (23, 25), (16, 11)],
    8: [(9, 7), (23, 7), (9, 16), (23, 16), (9, 25), (23, 25), (16, 11), (16, 21)],
    9: [(9, 7), (16, 7), (23, 7), (9, 16), (16, 16), (23, 16), (9, 25), (16, 25), (23, 25)],
}


def _ink(e, rev):
    """Number colour that reads on the card face."""
    return P["night0"] if (e == "air" and not rev) else P["moon"]


def plate_minor(e, n, rev, size=32):
    d0, m, l = None, None, None
    dark, mid, light = (P["r" + e + "0"], P["r" + e + "1"], P["silver2"]) if rev else (P[e + "0"], P[e + "1"], P[e + "2"])
    plate = Image.new("RGBA", (32, 32), dark + (255,))
    pd = ImageDraw.Draw(plate)
    # inner thin arch lines + star dust for a tarot-plate feel
    pd.rectangle([2, 2, 29, 29], outline=mid)
    for cx, cy in ((2, 2), (29, 2), (2, 29), (29, 29)):
        pd.point((cx, cy), fill=light)
    rnd = random.Random(n * 13 + len(e))
    for _ in range(5):
        pd.point((rnd.randrange(4, 28), rnd.randrange(4, 28)), fill=mid)
    sz = 9 if n <= 4 else 7
    ic = icons.elem_icon(e, sz, rev)
    for (cx, cy) in PIPS[n]:
        plate.alpha_composite(ic, (cx - sz // 2, cy - sz // 2))
    if rev:
        plate = ImageOps.flip(plate)
    return plate


def art_sun():
    a = Image.new("RGBA", (32, 32), P["amber0"] + (255,))
    d = ImageDraw.Draw(a)
    for i, c in enumerate(("amber0", "amber1", "amber1")):
        pass
    d.rectangle([0, 0, 31, 9], fill=P["fire0"])
    d.rectangle([0, 10, 31, 17], fill=P["amber0"])
    d.rectangle([0, 18, 31, 24], fill=P["amber1"])
    d.ellipse([9, 3, 23, 17], fill=P["amber3"])
    d.ellipse([11, 5, 21, 15], fill=P["gold4"])
    for ang_pts in ((16, 0, 16, 2), (16, 19, 16, 20), (4, 10, 6, 10), (26, 10, 28, 10), (7, 1, 8, 3), (24, 1, 23, 3)):
        d.line(ang_pts, fill=P["amber3"])
    # sill
    d.rectangle([0, 25, 31, 31], fill=P["gold0"])
    d.line([0, 25, 31, 25], fill=P["gold2"])
    # cat belly-up
    d.ellipse([7, 19, 25, 27], fill=P["night0"])
    d.ellipse([9, 20, 23, 26], fill=P["moon"])
    d.ellipse([4, 17, 11, 23], fill=P["night0"])
    d.polygon([(4, 18), (4, 15), (7, 17)], fill=P["night0"])
    d.polygon([(8, 17), (10, 15), (10, 18)], fill=P["night0"])
    px(a, 6, 19, P["amber2"]); px(a, 8, 19, P["amber2"])
    for x in (12, 15, 19):
        d.line([x, 18, x, 20], fill=P["moon"])
        px(a, x, 17, P["night0"])
    d.line([24, 24, 28, 22], fill=P["night0"])
    return a


def art_scrap(kind):
    a = Image.new("RGBA", (32, 32), P["rat0"] + (255,))
    d = ImageDraw.Draw(a)
    d.rectangle([2, 2, 29, 29], outline=P["rat1"])
    if kind == "sword":
        d.polygon([(8, 25), (19, 9), (21, 11), (11, 27)], fill=P["rat3"])
        d.polygon([(19, 9), (21, 11), (22, 8)], fill=P["moon"])
        d.line([(9, 24), (19, 10)], fill=P["moon"])
        d.polygon([(23, 13), (26, 16), (24, 19), (22, 16)], fill=P["rat2"])   # broken shard
        d.rectangle([6, 24, 12, 26], fill=P["amber1"])
        d.rectangle([5, 27, 8, 29], fill=P["amber0"])
        d.line([(14, 21), (16, 22)], fill=P["rat0"])
    elif kind == "coin":
        d.ellipse([8, 8, 24, 24], fill=P["gold1"])
        d.ellipse([10, 10, 22, 22], fill=P["gold3"])
        d.ellipse([13, 13, 19, 19], fill=P["gold1"])
        d.polygon([(22, 9), (26, 6), (25, 12)], fill=P["rat0"])   # chipped edge
    elif kind == "cup":
        d.polygon([(9, 9), (23, 9), (20, 22), (12, 22)], fill=P["rat3"])
        d.rectangle([14, 22, 18, 25], fill=P["rat2"]); d.rectangle([11, 25, 21, 26], fill=P["rat2"])
        d.polygon([(9, 9), (23, 9), (22, 13), (10, 13)], fill=P["water1"])
        d.line([(16, 13), (15, 17)], fill=P["rat0"]); d.line([(15, 17), (17, 21)], fill=P["rat0"])
    elif kind == "gnaw":
        d.rectangle([7, 9, 25, 14], fill=P["rat3"]); d.rectangle([7, 18, 25, 23], fill=P["rat3"])
        for x in (9, 14, 19, 24):
            d.polygon([(x - 2, 14), (x + 2, 14), (x, 17)], fill=P["rat3"])
            d.polygon([(x - 2, 18), (x + 2, 18), (x, 15)], fill=P["rat3"])
        d.rectangle([7, 14, 25, 18], fill=P["rat0"]) if False else None
    elif kind == "strength":
        d.ellipse([8, 9, 24, 24], fill=P["rat2"])
        d.polygon([(8, 14), (8, 6), (14, 10)], fill=P["rat2"]); d.polygon([(24, 14), (24, 6), (18, 10)], fill=P["rat2"])
        d.rectangle([12, 14, 13, 16], fill=P["night0"]); d.rectangle([19, 14, 20, 16], fill=P["night0"])
        d.polygon([(15, 19), (18, 19), (16, 21)], fill=P["pink"])
        d.polygon([(14, 24), (17, 24), (16, 29)], fill=P["rat0"])
    return a


def draw_card(im, x, y, e=None, num=None, stars=1, rev=False, rarity="none", charm=None, major=None, scrap=None,
              small=False, bg=None, dim=False):
    """48x64 (or 40x54 when small) tarot card. major=(roman, art) ; scrap=(label_num, art_kind)."""
    bg = bg or P["night1"]
    W, H = (40, 54) if small else (48, 64)
    c = Image.new("RGB", (W, H), bg)
    if scrap:
        edge, body, filig, ink = P["rat0"], P["rat1"], P["rat2"], P["rat3"]
        rim = P["rat2"]
    else:
        dark, mid, light = (P["r" + e + "0"], P["r" + e + "1"], P["silver2"]) if rev else (P[e + "0"], P[e + "1"], P[e + "2"])
        rim = P[RARITY[rarity]]
        body, filig, ink = mid, light, _ink(e, rev)
        edge = P["night0"]
    rect(c, 0, 0, W - 1, H - 1, rim)
    rect(c, 1, 1, W - 2, H - 2, edge)
    rect(c, 2, 2, W - 3, H - 3, body)
    # inner filigree line with gaps at the corners + corner studs
    frame(c, 3, 3, W - 4, H - 4, filig)
    for cx, cy in ((3, 3), (W - 4, 3), (3, H - 4), (W - 4, H - 4)):
        px(c, cx, cy, edge)
        px(c, cx + (1 if cx < W // 2 else -1), cy + (1 if cy < H // 2 else -1), filig)
    # clipped corners
    for cx, cy in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)):
        px(c, cx, cy, bg)
    # art plate
    if small:
        pw, ptop = 26, 14
    else:
        pw, ptop = 32, 15
    pxl = (W - pw) // 2
    if scrap:
        art = art_scrap(scrap[1])
    elif major:
        art = art_sun() if major[1] == "sun" else art_scrap("strength")
        if rev:
            art = ImageOps.flip(art)
    else:
        art = plate_minor(e, num, rev)
    if small:
        art = art.crop((3, 3, 29, 29))
    frame(c, pxl - 1, ptop - 1, pxl + pw, ptop + pw, P["gold1"] if not scrap else P["rat2"])
    c.paste(art, (pxl, ptop), art if art.mode == "RGBA" else None)
    # number / stars
    f = font("VT323-Regular", 16)
    label = str(num) if not major and not scrap else (major[0] if major else str(scrap[0]))
    if scrap:
        ink_c = P["rat3"]
    else:
        ink_c = ink
    D(c).text((5, 13 if not small else 12), label, font=f, fill=ink_c, anchor="ls")
    if not scrap and not major:
        for i in range(stars):
            paste(c, icons.star5(), W - 8 - 6 * i, 5)
    # reversed marker
    if rev:
        paste(c, icons.tri_down("silver2"), W // 2 - 3, 6 if not small else 5)
    # bottom row
    by = H - 14 if not small else H - 11
    if not scrap and e:
        paste(c, icons.elem_icon(e, 7 if small else 9, rev), 6, by if not small else by - 1)
    if not scrap and charm:
        paste(c, icons.gem(charm), W - 12, by + (2 if not small else 1))
    if scrap:
        # tooth-notch glyph
        for i in range(3):
            px(c, 7 + i * 3, H - 8, P["rat3"]); px(c, 7 + i * 3, H - 7, P["rat3"]); px(c, 8 + i * 3, H - 8, P["rat3"])
        # bite marks cut into the right edge and top-right corner
        d = ImageDraw.Draw(c)
        for (bx, by_, r) in ((W - 1, 8, 5), (W - 4, -1, 4), (W - 1, H - 22, 3)):
            d.ellipse([bx - r, by_ - r, bx + r, by_ + r], fill=bg)
        for (bx, by_) in ((W - 8, 6), (W - 7, 12), (W - 5, H - 24), (W - 5, H - 19)):
            px(c, bx, by_, P["rat0"])
    if dim:
        pass
    im.paste(c, (x, y))
    return (x, y, x + W - 1, y + H - 1)


def empty_slot(im, x, y, small=False, col="night3"):
    W, H = (40, 54) if small else (48, 64)
    for i in range(0, W, 4):
        px(im, x + i, y, P[col]); px(im, x + i + 1, y, P[col])
        px(im, x + i, y + H - 1, P[col]); px(im, x + i + 1, y + H - 1, P[col])
    for j in range(0, H, 4):
        px(im, x, y + j, P[col]); px(im, x, y + j + 1, P[col])
        px(im, x + W - 1, y + j, P[col]); px(im, x + W - 1, y + j + 1, P[col])
    sparkle(im, x + W // 2, y + H // 2, "night4", 1)


def card_back(im, x, y, small=False, bg=None):
    bg = bg or P["night1"]
    W, H = (40, 54) if small else (48, 64)
    c = Image.new("RGB", (W, H), bg)
    rect(c, 0, 0, W - 1, H - 1, P["gold2"])
    rect(c, 1, 1, W - 2, H - 2, P["night0"])
    rect(c, 2, 2, W - 3, H - 3, P["royal"])
    # diamond lattice
    for i in range(-H, W + H, 8):
        ImageDraw.Draw(c).line([(i, 2), (i + H, H - 3)], fill=P["royal1"])
        ImageDraw.Draw(c).line([(i, H - 3), (i + H, 2)], fill=P["royal1"])
    rect(c, 2, 2, W - 3, 4, P["royal"]); rect(c, 2, H - 5, W - 3, H - 3, P["royal"])
    frame(c, 3, 3, W - 4, H - 4, P["gold2"])
    frame(c, 5, 5, W - 6, H - 6, P["gold1"])
    for cx, cy in ((7, 7), (W - 8, 7), (7, H - 8), (W - 8, H - 8)):
        paste(c, icons.diamond("gold3"), cx - 2, cy - 2)
    r = 11 if not small else 9
    rect(c, W // 2 - r - 3, H // 2 - r - 3, W // 2 + r + 3, H // 2 + r + 3, P["royal0"])
    frame(c, W // 2 - r - 3, H // 2 - r - 3, W // 2 + r + 3, H // 2 + r + 3, P["gold1"])
    moon_eye(c, W // 2, H // 2, r)
    im.paste(c, (x, y))
