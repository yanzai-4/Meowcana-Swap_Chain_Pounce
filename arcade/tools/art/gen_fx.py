"""Battle VFX sprites (transparent, RGB565-exact, no antialiasing)."""
import math

from PIL import Image, ImageDraw

import icons
import ui
from icons import grid_image
from pal import P


def blank(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def c(k):
    return P[k] + (255,)


def dot(im, x, y, k):
    if 0 <= x < im.width and 0 <= y < im.height:
        im.putpixel((int(x), int(y)), c(k))


def fx_slash():
    out = []
    # three claw strokes running from top-left to bottom-right, offset perpendicularly
    for f in range(4):
        im = blank(40, 40)
        d = ImageDraw.Draw(im)
        reach = (0.45, 1.0, 1.0, 1.0)[f]
        for k in (-1, 0, 1):
            ox, oy = k * 8, -k * 8
            x0, y0 = 4 + ox, 4 + oy
            x1, y1 = 35 + ox, 35 + oy
            ex, ey = x0 + (x1 - x0) * reach, y0 + (y1 - y0) * reach
            nx, ny = 0.707, -0.707
            wid = (3.0, 3.5, 2.0, 1.0)[f]
            # tapered blade: wide in the middle, pointed at both ends
            mx, my = (x0 + ex) / 2, (y0 + ey) / 2
            poly = [(x0, y0), (mx + nx * wid, my + ny * wid), (ex, ey), (mx - nx * wid, my - ny * wid)]
            if f == 3:
                for t in (0.15, 0.4, 0.65, 0.9):
                    px, py = x0 + (ex - x0) * t, y0 + (ey - y0) * t
                    dot(im, px, py, "silver1")
                continue
            d.polygon(poly, fill=c("silver1"))
            inner = [(x0 + 3, y0 + 3), (mx + nx * (wid - 1.2), my + ny * (wid - 1.2)), (ex - 3, ey - 3),
                     (mx - nx * (wid - 1.2), my - ny * (wid - 1.2))]
            if f < 3:
                d.polygon(inner, fill=c("moon"))
        out.append(im)
    return out


def fx_spark():
    out = []
    for f in range(4):
        im = blank(12, 12)
        cx = cy = 5
        rays = [(1, 0), (-1, 0), (0, 1), (0, -1), (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)]
        if f == 0:
            for rx, ry in rays[:4]:
                for t in (1, 2):
                    dot(im, round(cx + rx * t), round(cy + ry * t), "moon")
            dot(im, cx, cy, "moon")
        elif f == 1:
            for i, (rx, ry) in enumerate(rays):
                n = 4 if i < 4 else 3
                for t in range(1, n + 1):
                    k = "moon" if t <= 2 else "gold4"
                    dot(im, round(cx + rx * t + 0.0), round(cy + ry * t), k)
        elif f == 2:
            for i, (rx, ry) in enumerate(rays):
                for t in (3, 4, 5) if i < 4 else (3, 4):
                    dot(im, round(cx + rx * t), round(cy + ry * t), "gold4" if t == 3 else "amber3")
        else:
            for i, (rx, ry) in enumerate(rays):
                t = 5 if i < 4 else 4
                dot(im, round(cx + rx * t), round(cy + ry * t), "amber2")
        out.append(im)
    return out


def fx_part():
    out = []
    for e in ("fire", "air", "water", "earth"):
        for f in range(3):
            im = blank(8, 8)
            d = ImageDraw.Draw(im)
            if e == "fire":
                r = (3, 2, 1)[f]
                d.polygon([(4, 4 - r), (4 + r, 4), (4, 4 + r), (4 - r, 4)], fill=c("fire1" if f == 2 else "amber2"))
                if f < 2:
                    dot(im, 4, 4, "amber3" if f == 0 else "gold4")
            elif e == "air":
                ys = (5, 4, 3)[f]
                for i in range(6):
                    dot(im, 1 + i, ys + (1 if i in (2, 3) else 0) - (1 if i == 5 else 0), "air2" if f < 2 else "air1")
                if f == 0:
                    dot(im, 2, ys + 2, "moon")
            elif e == "water":
                if f == 0:
                    d.polygon([(4, 0), (6, 4), (5, 6), (3, 6), (2, 4)], fill=c("water2"))
                    dot(im, 3, 4, "moon")
                elif f == 1:
                    d.polygon([(4, 1), (5, 4), (4, 6), (3, 4)], fill=c("water1"))
                    dot(im, 4, 3, "water2")
                else:
                    d.polygon([(4, 2), (4, 4), (3, 5)], fill=c("water1"))
                    dot(im, 2, 6, "water2")
                    dot(im, 5, 6, "water2")
            else:
                sz = (3, 2, 2)[f]
                ox = (2, 3, 3)[f]
                oy = (1, 3, 4)[f]
                d.rectangle([ox, oy, ox + sz - 1, oy + sz - 1], fill=c("earth1"))
                dot(im, ox, oy, "earth2")
                dot(im, ox + sz, oy + sz, "earth0")
                if f > 0:
                    dot(im, 6 - f, 1 + f, "earth2")
            out.append(im)
    return out


def fx_heal():
    out = []
    for f, r in enumerate((1, 2, 1)):
        im = blank(8, 8)
        for i in range(-r, r + 1):
            dot(im, 4 + i, 4, "heal" if abs(i) < r else "earth2")
            dot(im, 4, 4 + i, "heal" if abs(i) < r else "earth2")
        dot(im, 4, 4, "moon")
        if f == 1:
            for x, y in ((1, 1), (6, 1), (1, 6), (6, 6)):
                dot(im, x, y, "heal")
        out.append(im)
    return out


def fx_curl():
    out = []
    for f in range(3):
        im = blank(16, 16)
        d = ImageDraw.Draw(im)
        r = (4, 6, 7)[f]
        col = ("gold4", "gold3", "gold2")[f]
        d.ellipse([8 - r, 8 - r, 7 + r, 7 + r], outline=c(col))
        if f < 2:
            d.ellipse([8 - r + 2, 8 - r + 2, 7 + r - 2, 7 + r - 2], outline=c("gold1"))
        for x, y in ((8 - r, 8 - r), (7 + r, 7 + r)):
            dot(im, x, y, "moon")
        # a gap in the ring keeps it a swirl instead of a plain circle
        dot(im, 7 + r, 7, "night1") if False else None
        out.append(im)
    return out


def fx_meow():
    out = []
    # frame 0: small spiky pop; frame 1: full bubble with MEOW!
    pop = blank(72, 30)
    d = ImageDraw.Draw(pop)
    pts = []
    for i in range(16):
        ang = math.radians(i * 22.5)
        r = 12 if i % 2 == 0 else 7
        pts.append((36 + r * 1.9 * math.cos(ang), 14 + r * math.sin(ang)))
    d.polygon(pts, fill=c("night0"))
    pts = []
    for i in range(16):
        ang = math.radians(i * 22.5)
        r = 10 if i % 2 == 0 else 5
        pts.append((36 + r * 1.9 * math.cos(ang), 14 + r * math.sin(ang)))
    d.polygon(pts, fill=c("gold4"))
    out.append(pop)
    im = blank(72, 30)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 71, 23], radius=6, fill=c("night0"))
    d.rounded_rectangle([1, 1, 70, 22], radius=5, fill=c("gold3"))
    d.rounded_rectangle([2, 2, 69, 21], radius=4, fill=c("moon"))
    d.polygon([(12, 22), (22, 22), (10, 29)], fill=c("night0"))
    d.polygon([(13, 22), (20, 22), (11, 27)], fill=c("moon"))
    d.line([(13, 22), (20, 22)], fill=c("moon"))
    f = ui.font("Jersey10-Regular", 20)
    d.fontmode = "1"
    w = f.getlength("MEOW!")
    for dx, dy in ((1, 1),):
        d.text((36 - w / 2 + dx, 20 + dy), "MEOW!", font=f, fill=c("gold2"), anchor="ls")
    d.text((36 - w / 2, 20), "MEOW!", font=f, fill=c("amber1"), anchor="ls")
    out.append(im)
    return out


def fx_hiss():
    from PIL import ImageFilter
    out = []
    for f in range(2):
        m = Image.new("L", (24, 24), 0)
        d = ImageDraw.Draw(m)
        d.arc([4, 5, 22, 28], 180, 360, fill=255, width=5)
        d.rectangle([4, 16, 6, 22], fill=255)
        d.rectangle([19, 16, 21, 22], fill=255)
        d.ellipse([1, 11, 9, 19], fill=255)
        d.polygon([(1, 12), (2, 7), (5, 11)], fill=255)
        d.polygon([(5, 11), (8, 7), (9, 13)], fill=255)
        d.line([(21, 16), (22, 9), (20, 4)], fill=255, width=2)
        tall = 3 if f == 0 else 4
        for x in (9, 12, 15, 18):
            d.polygon([(x - 1, 8), (x, 8 - tall), (x + 1, 8)], fill=255)
        ring = m.filter(ImageFilter.MaxFilter(3))
        im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        fur = P["amber2"] if f == 0 else P["amber3"]
        for y in range(24):
            for x in range(24):
                if m.getpixel((x, y)):
                    im.putpixel((x, y), fur + (255,))
                elif ring.getpixel((x, y)):
                    im.putpixel((x, y), P["night0"] + (255,))
        for x, y, k in ((3, 14, "night0"), (7, 14, "night0"), (3, 16, "night0"), (4, 16, "night0"), (5, 16, "night0"),
                        (6, 16, "night0"), (4, 17, "moon"), (6, 17, "moon"), (2, 11, "amber1"), (7, 11, "amber1")):
            dot(im, x, y, k)
        dot(im, 3, 13, "red")
        dot(im, 7, 13, "red")
        out.append(im)
    return out


def fx_bite():
    """Bite crescent (night0 hole with moon teeth) for a card corner; opens toward the lower right."""
    m = Image.new("L", (14, 14), 0)
    d = ImageDraw.Draw(m)
    d.ellipse([0, 0, 13, 13], fill=255)
    d.ellipse([5, 3, 19, 17], fill=0)
    im = blank(14, 14)
    for y in range(14):
        for x in range(14):
            if m.getpixel((x, y)):
                im.putpixel((x, y), c("night0"))
    # teeth along the inner edge
    for x, y in ((6, 3), (5, 4), (4, 6), (4, 8), (5, 10), (6, 11)):
        dot(im, x, y, "moon")
    for x, y in ((7, 4), (6, 5), (6, 8), (7, 10)):
        dot(im, x, y, "silver1")
    for x, y in ((2, 4), (1, 7), (2, 10)):
        dot(im, x, y, "red")
    return [im]


GENERATORS = {"fx_slash": fx_slash, "fx_spark": fx_spark, "fx_part": fx_part, "fx_heal": fx_heal,
              "fx_curl": fx_curl, "fx_meow": fx_meow, "fx_hiss": fx_hiss, "fx_bite": fx_bite}
