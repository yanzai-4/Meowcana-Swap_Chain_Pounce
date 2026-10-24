"""32x32 art plates for the rat scrap cards (gray-green field, cold palette) and chewed-edge helpers."""
from PIL import Image, ImageDraw

from icons import grid_image
from pal import P
from ui import px


def _g(rows, **leg):
    return grid_image(rows, {k: P[v] for k, v in leg.items()})


def _blit(a, rows, ox, oy, **leg):
    a.alpha_composite(_g(rows, **leg), (ox, oy))


def base(curse=False):
    a = Image.new("RGBA", (32, 32), P["rat0"] + (255,))
    ImageDraw.Draw(a).rectangle([2, 2, 29, 29], outline=P["rat1"])
    return a


def art(kind, curse=False):
    a = base()
    d = ImageDraw.Draw(a)
    c = lambda k: P[k]
    if kind == "broken_sword":
        d.polygon([(8, 25), (19, 9), (21, 11), (11, 27)], fill=c("rat3"))
        d.polygon([(19, 9), (21, 11), (22, 8)], fill=c("moon"))
        d.line([(9, 24), (19, 10)], fill=c("moon"))
        d.polygon([(23, 13), (26, 16), (24, 19), (22, 16)], fill=c("rat2"))
        d.polygon([(21, 11), (23, 13), (22, 16), (20, 13)], fill=c("rat0"))
        d.rectangle([6, 24, 12, 26], fill=c("amber1"))
        d.rectangle([5, 27, 8, 29], fill=c("amber0"))
        d.line([(14, 21), (16, 22)], fill=c("rat0"))
    elif kind == "gnaw":
        d.rectangle([5, 21, 26, 27], fill=c("gold0"))
        d.line([(5, 21), (26, 21)], fill=c("gold1"))
        for x, r in ((8, 2), (15, 3), (23, 2)):
            d.ellipse([x - r, 21 - r + 1, x + r, 21 + r + 1], fill=c("rat0"))
        for tx in (10, 17):
            d.rectangle([tx, 7, tx + 5, 17], fill=c("moon"))
            d.rectangle([tx + 4, 7, tx + 5, 17], fill=c("rat3"))
            d.rectangle([tx, 7, tx + 5, 7], fill=c("rat3"))
            d.line([(tx, 18), (tx + 5, 18)], fill=c("night0"))
            d.line([(tx, 7), (tx, 18)], fill=c("night0"))
            d.line([(tx + 5, 7), (tx + 5, 18)], fill=c("night0"))
        d.rectangle([6, 5, 25, 6], fill=c("pink"))
        d.line([(6, 7), (25, 7)], fill=c("night0"))
        for x, y in ((9, 29), (13, 28), (20, 29), (24, 28)):
            px(a, x, y, c("gold1"))
    elif kind == "burnt_wand":
        d.line([(8, 26), (21, 10)], fill=c("night0"), width=4)
        d.line([(8, 26), (21, 10)], fill=c("amber0"), width=2)
        d.line([(10, 24), (13, 21)], fill=c("gold1"))
        d.polygon([(21, 11), (26, 7), (24, 13)], fill=c("fire1"))
        d.polygon([(22, 11), (25, 8), (24, 12)], fill=c("amber2"))
        px(a, 25, 9, c("gold4"))
        for x, y in ((24, 5), (22, 3), (25, 2), (21, 6)):
            px(a, x, y, c("rat2"))
        for x, y in ((12, 23), (15, 20), (18, 16), (17, 18)):
            px(a, x, y, c("rat0"))
    elif kind == "cracked_coin":
        d.ellipse([8, 8, 24, 24], fill=c("gold1"))
        d.ellipse([10, 10, 22, 22], fill=c("gold3"))
        d.ellipse([13, 13, 19, 19], fill=c("gold1"))
        d.line([(14, 14), (18, 18)], fill=c("gold3"))
        d.polygon([(22, 9), (26, 6), (25, 12)], fill=c("rat0"))
        for pts in (((15, 9), (17, 13), (15, 16), (18, 20), (16, 24)),):
            d.line(pts, fill=c("night0"))
        px(a, 11, 12, c("gold4"))
        px(a, 12, 11, c("gold4"))
    elif kind == "leaky_cup":
        d.polygon([(9, 7), (23, 7), (20, 20), (12, 20)], fill=c("rat3"))
        d.rectangle([14, 20, 18, 23], fill=c("rat2"))
        d.rectangle([11, 23, 21, 24], fill=c("rat2"))
        d.polygon([(9, 7), (23, 7), (22, 11), (10, 11)], fill=c("water1"))
        d.line([(10, 8), (14, 8)], fill=c("water2"))
        d.line([(16, 11), (15, 15)], fill=c("rat0"))
        d.line([(15, 15), (17, 19)], fill=c("rat0"))
        for x, y in ((14, 14), (15, 17), (19, 21)):
            px(a, x, y, c("water1"))
        d.ellipse([13, 26, 19, 28], fill=c("water1"))
        d.line([(14, 26), (16, 26)], fill=c("water2"))
        px(a, 18, 20, c("water2"))
        px(a, 17, 22, c("water1"))
    elif kind == "bite_mark":
        d.rectangle([7, 7, 24, 24], fill=c("rat3"))
        d.rectangle([7, 7, 24, 7], fill=c("moon"))
        d.rectangle([9, 11, 18, 11], fill=c("rat1"))
        d.rectangle([9, 14, 20, 14], fill=c("rat1"))
        # bite out of the lower-right corner: scalloped
        for cx, cy, r in ((22, 19, 5), (19, 24, 4), (24, 14, 3), (15, 26, 3)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c("rat0"))
        d.rectangle([20, 24, 31, 31], fill=c("rat0"))
        d.rectangle([25, 19, 31, 31], fill=c("rat0"))
        d.rectangle([1, 28, 31, 29], fill=c("rat1"))
        d.rectangle([29, 2, 29, 29], fill=c("rat1"))
        for x, y in ((24, 22), (26, 24), (19, 18), (18, 21)):
            px(a, x, y, c("moon"))
        d.rectangle([2, 2, 29, 29], outline=c("rat1"))
        _blit(a, ["ooo.ooo", "owo.owo", ".w...w."], 13, 24, o="night0", w="moon")
    elif kind == "snatch":
        d.ellipse([9, 15, 23, 29], fill=c("gold1"))
        d.ellipse([11, 17, 21, 27], fill=c("gold3"))
        d.line([(13, 19), (14, 19)], fill=c("gold4"))
        d.ellipse([15, 22, 17, 24], fill=c("gold1"))
        d.ellipse([7, 4, 25, 14], fill=c("night0"))
        d.ellipse([8, 5, 24, 13], fill=c("rat2"))
        for x in (9, 13, 17, 21):
            d.rectangle([x - 1, 11, x + 3, 19], fill=c("night0"))
            d.rectangle([x, 11, x + 2, 18], fill=c("rat2"))
            d.line([(x + 2, 11), (x + 2, 18)], fill=c("rat1"))
            d.polygon([(x, 19), (x + 2, 19), (x + 1, 23)], fill=c("moon"))
        d.line([(10, 7), (14, 7)], fill=c("rat3"))
    elif kind == "burrow":
        d.polygon([(3, 27), (6, 17), (12, 12), (20, 12), (26, 17), (29, 27)], fill=c("gold0"))
        d.polygon([(5, 27), (8, 19), (13, 14), (19, 14), (24, 19), (27, 27)], fill=c("amber0"))
        d.ellipse([10, 17, 22, 28], fill=c("night0"))
        d.rectangle([10, 24, 22, 29], fill=c("rat0"))
        d.rectangle([3, 27, 29, 29], fill=c("gold0"))
        d.ellipse([12, 20, 14, 21], fill=c("amber3"))
        d.ellipse([18, 20, 20, 21], fill=c("amber3"))
        px(a, 15, 24, c("pink"))
        for x, y in ((8, 16), (22, 15), (6, 21), (25, 22)):
            px(a, x, y, c("gold1"))
        d.line([(15, 6), (16, 9)], fill=c("rat3"))
        d.line([(9, 8), (11, 11)], fill=c("rat2"))
        d.line([(23, 8), (21, 11)], fill=c("rat2"))
    elif kind == "droppings":
        d.ellipse([7, 20, 25, 28], fill=c("amber0"))
        d.ellipse([9, 15, 23, 24], fill=c("amber0"))
        d.ellipse([12, 10, 20, 18], fill=c("amber0"))
        d.polygon([(14, 11), (16, 5), (18, 11)], fill=c("amber0"))
        d.arc([7, 20, 25, 28], 180, 360, fill=c("gold0"))
        d.line([(10, 25), (22, 25)], fill=c("gold0"))
        d.line([(12, 19), (20, 19)], fill=c("gold0"))
        d.line([(14, 13), (18, 13)], fill=c("gold0"))
        px(a, 12, 21, c("amber1"))
        px(a, 13, 21, c("amber1"))
        px(a, 14, 16, c("amber1"))
        px(a, 15, 12, c("amber1"))
        d.ellipse([7, 20, 25, 28], outline=c("night0")) if False else None
        eye = c("red") if curse else c("moon")
        d.rectangle([12, 22, 13, 23], fill=eye)
        d.rectangle([18, 22, 19, 23], fill=eye)
        px(a, 12, 23, c("night0")) if not curse else None
        for x, y in ((6, 8), (25, 12), (24, 6)):
            px(a, x, y, c("rat3"))
            px(a, x + 1, y, c("rat3"))
        for pts in (((9, 12), (8, 9), (9, 6)), ((23, 15), (24, 12), (23, 9))):
            d.line(pts, fill=c("rat2"))
    elif kind == "fleas":
        d.ellipse([11, 14, 21, 22], fill=c("amber0"))
        d.ellipse([12, 15, 20, 21], fill=c("fire0"))
        d.ellipse([8, 15, 13, 20], fill=c("amber0"))
        px(a, 10, 17, c("amber3"))
        d.line([(21, 19), (26, 12)], fill=c("amber0"))
        d.line([(26, 12), (28, 17)], fill=c("amber0"))
        for x in (13, 16, 19):
            d.line([(x, 22), (x - 1, 26)], fill=c("amber0"))
        d.line([(12, 14), (9, 10)], fill=c("amber0"))
        d.line([(9, 10), (6, 11)], fill=c("amber0"))
        for x, y in ((14, 17), (17, 16), (18, 19)):
            px(a, x, y, c("fire1"))
        for x, y in ((5, 24), (8, 26), (24, 25), (26, 22), (4, 6), (27, 7)):
            px(a, x, y, c("rat3"))
    elif kind == "sleep_dust":
        d.polygon([(9, 17), (23, 17), (25, 27), (7, 27)], fill=c("gold1"))
        d.polygon([(11, 17), (21, 17), (22, 20), (10, 20)], fill=c("amber0"))
        d.rectangle([13, 13, 19, 17], fill=c("gold0"))
        d.line([(12, 12), (20, 12)], fill=c("gold3"))
        d.line([(12, 22), (20, 22)], fill=c("gold3"))
        px(a, 12, 24, c("gold3"))
        for x, y, col in ((6, 9, "water2"), (10, 6, "moon"), (15, 4, "water2"), (21, 7, "moon"),
                          (25, 10, "water2"), (13, 9, "water1"), (19, 10, "water1"), (24, 5, "moon")):
            px(a, x, y, c(col))
        _blit(a, ["wwww", "..w.", ".w..", "wwww"], 22, 18, w="water2")
        _blit(a, ["www", ".w.", "www"], 4, 20, w="water1")
    else:
        raise KeyError(kind)
    return a


def bite_edges(card, seed=0):
    """Paint scalloped dents along the right edge and top-right corner (ink color)."""
    W, H = card.size
    d = ImageDraw.Draw(card)
    spots = [(W - 1, 10, 5), (W - 4, 1, 4), (W - 1, H - 22, 3)]
    if seed % 2:
        spots = [(0, 12, 4), (W - 2, H - 4, 4), (W - 1, 20, 3)]
    for bx, by, r in spots:
        d.ellipse([bx - r, by - r, bx + r, by + r], fill=P["night0"] + (255,))
    for bx, by in ((W - 8, 8), (W - 7, 14), (W - 5, H - 24), (W - 5, H - 19)):
        px(card, bx, by, P["rat0"] + (255,) if False else P["night0"] + (255,))
