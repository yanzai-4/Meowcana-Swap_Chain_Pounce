"""32x32 cat-acting portraits for the 8 Major Arcana (GDD section 17). plate(key, reversed, element) returns RGBA.
Reversed = vertically flipped art remapped onto the cool palette (notes.md)."""
from PIL import Image, ImageDraw, ImageOps

from pal import P

ELEMENT = {"fool": "air", "magician": "air", "empress": "earth", "emperor": "fire", "chariot": "water",
           "strength": "fire", "hanged": "water", "sun": "fire"}


def canvas(bg):
    a = Image.new("RGBA", (32, 32), P[bg] + (255,))
    return a, ImageDraw.Draw(a)


def c(k):
    return P[k] + (255,)


def dot(a, x, y, k):
    if 0 <= x < 32 and 0 <= y < 32:
        a.putpixel((x, y), c(k))


def blob(d, box, fill, ink="night0"):
    x0, y0, x1, y1 = box
    if ink:
        d.ellipse([x0 - 1, y0 - 1, x1 + 1, y1 + 1], fill=c(ink))
    d.ellipse(box, fill=c(fill))


def tri(d, pts, fill, ink="night0"):
    if ink:
        d.polygon(pts, outline=c(ink), fill=c(ink))
    d.polygon(pts, fill=c(fill))


def ears(d, lx, rx, top, base, fur, inner="pink", w=3):
    """Two triangle ears: left ear tip at (lx, top), right at (rx, top), base row `base`."""
    tri(d, [(lx - w, base), (lx, top), (lx + w, base)], fur)
    tri(d, [(rx - w, base), (rx, top), (rx + w, base)], fur)
    if inner:
        dot(d._image, lx, top + 2, inner)
        dot(d._image, rx, top + 2, inner)


def eyes(a, y, lx, rx, col="night0", glint=True):
    for x in (lx, rx):
        dot(a, x, y, col)
        dot(a, x, y + 1, col)
    if glint:
        dot(a, lx, y, "moon")
        dot(a, rx, y, "moon")


def muzzle(a, cx, y, nose="pink"):
    dot(a, cx, y, nose)
    dot(a, cx - 1, y + 1, "night0")
    dot(a, cx + 1, y + 1, "night0")


def whiskers(a, lx, rx, y, col="silver2"):
    for dx in (1, 2, 3):
        dot(a, lx - dx, y, col)
        dot(a, rx + dx, y + (1 if dx == 3 else 0), col)


def stars(a, pts, k="gold4"):
    for x, y in pts:
        dot(a, x, y, k)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            dot(a, x + dx, y + dy, "gold2" if k == "gold4" else "silver1")


# ---------------------------------------------------------------- The Fool: Zero at the cliff edge
def fool():
    a, d = canvas("water2")
    d.rectangle([0, 0, 31, 9], fill=c("water1"))
    d.rectangle([0, 10, 31, 17], fill=c("water2"))
    d.rectangle([0, 18, 31, 24], fill=c("air2"))
    d.ellipse([21, 3, 29, 11], fill=c("gold4"))
    d.ellipse([22, 4, 28, 10], fill=c("amber3"))
    for x, y in ((4, 5), (7, 4), (6, 12), (12, 2)):
        d.line([(x, y), (x + 4, y)], fill=c("moon"))
    # cliff
    d.polygon([(0, 22), (19, 22), (19, 25), (17, 31), (0, 31)], fill=c("gold0"))
    d.rectangle([0, 22, 19, 23], fill=c("earth1"))
    d.line([(0, 22), (19, 22)], fill=c("earth2"))
    d.line([(19, 22), (19, 25)], fill=c("night0"))
    d.line([(17, 26), (18, 30)], fill=c("amber0"))
    # bindle on a stick
    d.line([(7, 9), (14, 17)], fill=c("amber0"), width=1)
    blob(d, (3, 5, 9, 11), "gold1")
    dot(a, 6, 11, "amber1")
    d.line([(4, 7), (8, 7)], fill=c("gold2"))
    # kitten (pale spectral fur)
    blob(d, (8, 15, 16, 22), "moon")
    blob(d, (12, 8, 21, 16), "moon")
    ears(d, 13, 19, 5, 10, "moon", "pink", 2)
    eyes(a, 12, 15, 19, "night0", False)
    dot(a, 20, 14, "pink")
    dot(a, 19, 15, "night0")
    d.rectangle([9, 21, 10, 22], fill=c("moon"))
    d.rectangle([13, 21, 14, 22], fill=c("moon"))
    # lifted paw over the void
    blob(d, (17, 18, 20, 20), "moon")
    # scarf (too big)
    d.rectangle([12, 15, 19, 17], fill=c("gold3"))
    d.line([(12, 15), (19, 15)], fill=c("gold4"))
    d.polygon([(12, 16), (6, 16), (3, 19), (9, 19)], fill=c("gold3"))
    d.polygon([(6, 16), (3, 19), (5, 20)], fill=c("amber1"))
    d.line([(7, 17), (10, 17)], fill=c("amber1"))
    # tail
    d.line([(8, 19), (5, 22)], fill=c("night0"))
    d.line([(8, 20), (5, 22)], fill=c("moon"))
    dot(a, 24, 20, "moon")
    dot(a, 26, 17, "moon")
    return a


# ---------------------------------------------------------------- I The Magician: Trick Cat
def magician():
    a, d = canvas("night3")
    d.rectangle([0, 22, 31, 31], fill=c("night2"))
    stars(a, [(5, 6), (27, 8), (24, 17)], "gold4")
    stars(a, [(7, 16)], "silver2")
    # table with the four suits
    d.rectangle([2, 23, 29, 25], fill=c("gold1"))
    d.line([(2, 23), (29, 23)], fill=c("gold3"))
    d.rectangle([4, 26, 6, 31], fill=c("gold0"))
    d.rectangle([25, 26, 27, 31], fill=c("gold0"))
    d.rectangle([3, 26, 28, 27], fill=c("amber0"))
    # body (black cat, silver rim light)
    blob(d, (9, 14, 23, 26), "night0", "night4")
    d.rectangle([14, 17, 18, 23], fill=c("moon"))
    d.line([(16, 17), (16, 18)], fill=c("amber1"))
    dot(a, 15, 19, "night0")
    dot(a, 17, 19, "night0")
    # head + hat
    blob(d, (10, 8, 22, 17), "night0", "night4")
    ears(d, 11, 21, 4, 10, "night0", "pink", 2)
    d.rectangle([11, 0, 21, 7], fill=c("night0"))
    d.rectangle([9, 7, 23, 8], fill=c("night0"))
    d.line([(11, 6), (21, 6)], fill=c("royal1"))
    d.line([(11, 5), (21, 5)], fill=c("gold3"))
    d.line([(9, 8), (23, 8)], fill=c("night4"))
    eyes(a, 11, 14, 18, "amber3", False)
    dot(a, 14, 12, "night0")
    dot(a, 18, 12, "night0")
    muzzle(a, 16, 14)
    whiskers(a, 12, 20, 14, "silver1")
    # raised wand paw
    d.line([(24, 16), (27, 6)], fill=c("gold3"), width=1)
    dot(a, 27, 5, "gold4")
    d.rectangle([23, 15, 25, 17], fill=c("night0"))
    dot(a, 24, 16, "moon")
    stars(a, [(27, 3)], "moon")
    # items on the table
    d.line([(5, 19), (5, 22)], fill=c("silver2"))
    dot(a, 5, 18, "moon")
    d.line([(3, 22), (7, 22)], fill=c("gold3"))
    d.polygon([(10, 20), (14, 20), (13, 22), (11, 22)], fill=c("water1"))
    d.line([(10, 20), (14, 20)], fill=c("water2"))
    d.line([(20, 22), (20, 19)], fill=c("amber1"))
    dot(a, 20, 18, "fire2")
    d.ellipse([25, 20, 28, 22], fill=c("gold3"))
    return a


# ---------------------------------------------------------------- III The Empress: Mama Cat
def empress():
    a, d = canvas("earth1")
    d.rectangle([0, 0, 31, 12], fill=c("earth0"))
    d.ellipse([-4, 5, 36, 40], fill=c("earth1"))
    for x in range(1, 31, 4):
        d.line([(x, 28), (x, 24)], fill=c("amber2"))
        dot(a, x, 23, "gold3")
        dot(a, x - 1, 24, "gold3")
    d.rectangle([0, 29, 31, 31], fill=c("earth0"))
    # body (calico)
    blob(d, (6, 15, 26, 30), "air2")
    d.ellipse([7, 20, 14, 28], fill=c("amber2"))
    d.ellipse([20, 17, 25, 22], fill=c("night0"))
    d.ellipse([11, 23, 21, 30], fill=c("moon"))
    # kitten on her lap
    blob(d, (13, 22, 20, 28), "night0", "night0")
    d.polygon([(14, 22), (14, 20), (16, 22)], fill=c("night0"))
    d.polygon([(19, 22), (19, 20), (17, 22)], fill=c("night0"))
    dot(a, 15, 24, "amber3")
    dot(a, 18, 24, "amber3")
    dot(a, 16, 26, "pink")
    # head + crown
    blob(d, (9, 7, 23, 18), "air2")
    ears(d, 10, 22, 4, 10, "air2", "pink", 3)
    d.ellipse([9, 7, 14, 12], fill=c("amber2"))
    eyes(a, 12, 13, 19, "night0", False)
    d.line([(13, 12), (14, 12)], fill=c("night0"))
    d.line([(18, 12), (19, 12)], fill=c("night0"))
    dot(a, 16, 14, "pink")
    dot(a, 15, 15, "night0")
    dot(a, 17, 15, "night0")
    dot(a, 11, 14, "pink")
    dot(a, 21, 14, "pink")
    d.polygon([(11, 6), (21, 6), (20, 3), (18, 5), (16, 1), (14, 5), (12, 3)], fill=c("gold3"))
    d.line([(11, 6), (21, 6)], fill=c("gold2"))
    dot(a, 16, 3, "red")
    dot(a, 12, 5, "water2")
    dot(a, 20, 5, "water2")
    # pearl necklace
    for x in range(11, 22, 2):
        dot(a, x, 18 + (1 if 13 < x < 19 else 0), "moon")
    return a


# ---------------------------------------------------------------- IV The Emperor: Box King
def emperor():
    a, d = canvas("fire0")
    for x in range(0, 32, 8):
        d.rectangle([x, 0, x + 3, 12], fill=c("fire1"))
    d.line([(0, 13), (31, 13)], fill=c("gold1"))
    # scepter
    d.line([(26, 9), (26, 25)], fill=c("gold3"))
    d.ellipse([24, 5, 28, 9], fill=c("gold3"))
    dot(a, 26, 7, "red")
    # cat
    blob(d, (10, 6, 22, 16), "amber2")
    ears(d, 11, 21, 2, 8, "amber2", "pink", 3)
    for x in (13, 16, 19):
        d.line([(x, 6), (x, 8)], fill=c("amber1"))
    eyes(a, 10, 13, 19, "night0", False)
    dot(a, 13, 10, "amber3")
    dot(a, 19, 10, "amber3")
    d.rectangle([14, 12, 18, 14], fill=c("air2"))
    dot(a, 16, 12, "pink")
    dot(a, 15, 13, "night0")
    dot(a, 17, 13, "night0")
    whiskers(a, 12, 20, 13, "moon")
    d.polygon([(11, 5), (21, 5), (20, 2), (18, 4), (16, 0), (14, 4), (12, 2)], fill=c("gold3"))
    d.line([(11, 5), (21, 5)], fill=c("gold2"))
    dot(a, 16, 2, "red")
    # robe + paws on armrests
    d.rectangle([11, 16, 21, 20], fill=c("fire1"))
    d.rectangle([11, 16, 21, 16], fill=c("moon"))
    for x in (12, 15, 18, 20):
        dot(a, x, 16, "night0")
    # the box throne
    d.polygon([(4, 18), (28, 18), (27, 31), (5, 31)], fill=c("amber1"))
    d.polygon([(4, 18), (9, 18), (9, 31), (5, 31)], fill=c("amber0"))
    d.polygon([(23, 18), (28, 18), (27, 31), (23, 31)], fill=c("amber0"))
    d.rectangle([4, 18, 28, 19], fill=c("gold1"))
    d.rectangle([4, 18, 28, 18], fill=c("gold3"))
    d.rectangle([14, 21, 18, 31], fill=c("gold3"))
    d.line([(14, 21), (14, 31)], fill=c("gold4"))
    d.rectangle([10, 21, 13, 24], fill=c("amber1"))
    d.rectangle([19, 21, 22, 24], fill=c("amber1"))
    blob(d, (9, 18, 13, 22), "amber2", None)
    blob(d, (19, 18, 23, 22), "amber2", None)
    d.line([(4, 19), (4, 31)], fill=c("night0"))
    d.line([(28, 19), (27, 31)], fill=c("night0"))
    d.line([(5, 31), (27, 31)], fill=c("night0"))
    for x, y in ((7, 24), (7, 27), (25, 25)):
        dot(a, x, y, "amber0")
        dot(a, x + 1, y, "amber0")
    return a


# ---------------------------------------------------------------- VII The Chariot: Zoomies Cat
def chariot():
    a, d = canvas("water0")
    d.rectangle([0, 24, 31, 31], fill=c("water1"))
    d.rectangle([0, 24, 31, 24], fill=c("water2"))
    for y, x0, x1 in ((6, 1, 10), (11, 3, 12), (16, 0, 8), (21, 2, 9)):
        d.line([(x0, y), (x1, y)], fill=c("water2"))
        d.line([(x0 + 2, y + 1), (x1 - 3, y + 1)], fill=c("moon"))
    stars(a, [(26, 5), (21, 9)], "gold4")
    # cat head with goggles and a streaming scarf
    blob(d, (13, 7, 25, 17), "silver1")
    ears(d, 14, 24, 3, 9, "silver1", "pink", 3)
    for x in (16, 19, 22):
        d.line([(x, 7), (x, 9)], fill=c("night4"))
    d.rectangle([14, 10, 18, 13], fill=c("night0"))
    d.rectangle([20, 10, 24, 13], fill=c("night0"))
    d.rectangle([15, 11, 17, 12], fill=c("gold3"))
    d.rectangle([21, 11, 23, 12], fill=c("gold3"))
    dot(a, 15, 11, "moon")
    dot(a, 21, 11, "moon")
    d.rectangle([18, 11, 20, 11], fill=c("night0"))
    d.rectangle([17, 14, 22, 16], fill=c("moon"))
    dot(a, 20, 14, "pink")
    d.line([(19, 16), (21, 16)], fill=c("night0"))
    dot(a, 20, 16, "red")
    d.polygon([(14, 17), (24, 17), (24, 19), (14, 19)], fill=c("red"))
    d.polygon([(14, 17), (8, 15), (3, 19), (9, 20), (14, 19)], fill=c("red"))
    d.line([(6, 17), (13, 18)], fill=c("fire2"))
    # cardboard chariot
    d.polygon([(8, 19), (28, 19), (27, 27), (9, 27)], fill=c("amber1"))
    d.rectangle([8, 19, 28, 20], fill=c("gold3"))
    d.rectangle([8, 26, 28, 27], fill=c("amber0"))
    d.rectangle([15, 21, 21, 25], fill=c("gold1"))
    d.line([(15, 21), (21, 21)], fill=c("gold2"))
    d.line([(8, 19), (9, 27)], fill=c("night0"))
    d.line([(28, 19), (27, 27)], fill=c("night0"))
    for cx in (13, 24):
        blob(d, (cx - 3, 26, cx + 3, 31), "night0", None)
        d.ellipse([cx - 1, 28, cx + 1, 30], fill=c("gold3"))
    for x, y in ((2, 27), (5, 29), (6, 25)):
        dot(a, x, y, "water2")
        dot(a, x + 1, y, "water2")
    return a


# ---------------------------------------------------------------- VIII Strength: Lionheart
def strength():
    import math
    a, d = canvas("royal0")
    stars(a, [(5, 5), (27, 4)], "gold3")
    d.rectangle([0, 26, 31, 31], fill=c("night2"))
    d.line([(0, 26), (31, 26)], fill=c("night3"))
    cx, cy = 16, 18
    for rr, ink, fill in ((14, 1, 0), (13, 0, 1)):
        pts = []
        for i in range(24):
            ang = math.radians(i * 15)
            r = rr if i % 2 == 0 else rr - 3
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        d.polygon(pts, fill=c("night0") if ink else c("fire1"))
    d.ellipse([6, 8, 26, 28], fill=c("fire1"))
    for i in range(0, 24, 2):
        ang = math.radians(i * 15 + 8)
        dot(a, round(cx + 9 * math.cos(ang)), round(cy + 9 * math.sin(ang)), "fire2")
        dot(a, round(cx + 10 * math.cos(ang + 0.2)), round(cy + 10 * math.sin(ang + 0.2)), "amber2")
    blob(d, (11, 12, 21, 23), "air2")
    ears(d, 11, 21, 4, 12, "amber2", "pink", 3)
    for x in (14, 16, 18):
        d.line([(x, 12), (x, 13)], fill=c("amber1"))
    for ex in (13, 17):
        d.line([(ex, 17), (ex + 2, 17)], fill=c("night0"))
        dot(a, ex, 16, "night0")
        dot(a, ex + 2, 16, "night0")
    dot(a, 16, 19, "pink")
    d.line([(14, 21), (16, 20)], fill=c("night0"))
    d.line([(16, 20), (18, 21)], fill=c("night0"))
    dot(a, 12, 20, "pink")
    dot(a, 20, 20, "pink")
    whiskers(a, 11, 21, 19, "moon")
    d.ellipse([10, 1, 15, 4], outline=c("gold4"))
    d.ellipse([16, 1, 21, 4], outline=c("gold4"))
    return a


# ---------------------------------------------------------------- XII The Hanged Man: Upside-Down Cat
def hanged():
    a, d = canvas("water0")
    for x in range(0, 32, 6):
        dot(a, x + 2, 26, "water1")
        dot(a, x + 3, 27, "water1")
    d.rectangle([0, 29, 31, 31], fill=c("water1"))
    # cat tree: perch bar with sisal post
    d.rectangle([2, 4, 29, 6], fill=c("gold1"))
    d.line([(2, 4), (29, 4)], fill=c("gold3"))
    d.line([(2, 7), (29, 7)], fill=c("night0"))
    d.rectangle([26, 7, 28, 31], fill=c("gold0"))
    for y in range(9, 31, 3):
        d.line([(26, y), (28, y)], fill=c("gold1"))
    # cat drawn upright, then flipped so the hind paws grip the bar
    cat = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cat)
    blob(cd, (9, 14, 21, 26), "silver1")
    cd.ellipse([12, 18, 18, 25], fill=c("moon"))
    blob(cd, (8, 4, 22, 15), "silver1")
    ears(cd, 10, 20, 1, 7, "silver1", "pink", 2)
    cd.rectangle([8, 9, 12, 12], fill=c("night4"))
    cd.line([(12, 11), (13, 11)], fill=c("night0"))
    cd.line([(17, 11), (18, 11)], fill=c("night0"))
    cd.rectangle([12, 12, 18, 14], fill=c("moon"))
    cat.putpixel((15, 12), P["pink"] + (255,))
    cat.putpixel((14, 13), P["night0"] + (255,))
    cat.putpixel((16, 13), P["night0"] + (255,))
    for lx in (10, 18):
        blob(cd, (lx, 25, lx + 3, 30), "silver1")
        cd.rectangle([lx, 29, lx + 3, 31], fill=c("moon"))
    cd.line([(21, 22), (25, 18), (24, 13)], fill=c("night0"), width=2)
    cd.line([(21, 22), (25, 18), (24, 13)], fill=c("silver1"), width=1)
    cd.ellipse([6, 1, 24, 6], outline=c("gold4"))
    cat = ImageOps.flip(cat)
    cat = cat.crop((0, 0, 32, 32))
    a.alpha_composite(cat, (0, 7 - 1 - 0))
    # rope loops around the paws
    d.line([(10, 7), (13, 7)], fill=c("amber2"))
    d.line([(18, 7), (21, 7)], fill=c("amber2"))
    return a


# ---------------------------------------------------------------- XIX The Sun: Sunbeam Cat
def sun():
    a, d = canvas("amber0")
    d.rectangle([0, 0, 31, 9], fill=c("fire0"))
    d.rectangle([0, 10, 31, 17], fill=c("amber0"))
    d.rectangle([0, 18, 31, 24], fill=c("amber1"))
    d.ellipse([8, 1, 24, 17], fill=c("amber2"))
    d.ellipse([10, 3, 22, 15], fill=c("amber3"))
    d.ellipse([12, 5, 20, 13], fill=c("gold4"))
    for x0, y0, x1, y1 in ((16, 0, 16, 1), (4, 9, 6, 9), (26, 9, 28, 9), (6, 2, 8, 4), (24, 2, 26, 4),
                           (6, 16, 8, 14), (24, 16, 26, 14), (16, 18, 16, 19)):
        d.line([(x0, y0), (x1, y1)], fill=c("amber3"))
    # windowsill
    d.rectangle([0, 25, 31, 31], fill=c("gold0"))
    d.line([(0, 25), (31, 25)], fill=c("gold2"))
    d.line([(0, 26), (31, 26)], fill=c("gold1"))
    # cat belly-up in the sun
    blob(d, (6, 18, 26, 27), "night0", None)
    d.ellipse([8, 19, 24, 26], fill=c("moon"))
    blob(d, (2, 15, 11, 24), "night0", None)
    d.ellipse([3, 16, 10, 23], fill=c("night0"))
    d.polygon([(3, 17), (3, 13), (6, 16)], fill=c("night0"))
    d.polygon([(8, 16), (10, 13), (10, 17)], fill=c("night0"))
    dot(a, 5, 18, "amber3")
    dot(a, 8, 18, "amber3")
    dot(a, 6, 20, "pink")
    d.line([(4, 20), (3, 21)], fill=c("moon"))
    for x in (13, 16, 20):
        d.line([(x, 17), (x, 19)], fill=c("moon"))
        dot(a, x, 16, "night0")
        dot(a, x, 17, "moon") if False else None
    d.line([(24, 24), (29, 21)], fill=c("night0"), width=2)
    d.line([(24, 24), (29, 21)], fill=c("night4"))
    dot(a, 14, 22, "night0")
    dot(a, 18, 22, "night0")
    stars(a, [(27, 6), (4, 6)], "gold4")
    return a


PLATES = {"fool": fool, "magician": magician, "empress": empress, "emperor": emperor, "chariot": chariot,
          "strength": strength, "hanged": hanged, "sun": sun}


def cool(art, e):
    """Remap onto the Reversed palette of element e by luminance."""
    ramp = [P["night0"], P["r" + e + "0"], P["r" + e + "1"], P["silver1"], P["silver2"], P["moon"]]
    cuts = [30, 80, 125, 165, 215]
    out = art.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, al = px[x, y]
            lum = (r * 30 + g * 59 + b * 11) // 100
            i = sum(lum >= t for t in cuts)
            px[x, y] = ramp[i] + (255,)
    return out


def plate(key, rev, e):
    art = PLATES[key]()
    if rev:
        art = ImageOps.flip(cool(art, e))
    return art
