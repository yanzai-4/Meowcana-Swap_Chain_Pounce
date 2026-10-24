"""Repaint the held card of raw/domino_merge_b.png as a miniature card back (royal field, gold border, cat-eye moon).
Writes raw/domino_final_hand.png. Only pixels of the card's orange/gold slab are touched; fingers and gloves stay."""
import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import Image
import icons  # registers royal colors in P
from pal import P


def card_mask(im):
    px = im.load()
    def warm(x, y):
        r, g, b, a = px[x, y]
        return a > 0 and r - b >= 70 and r >= g and r >= 120
    seed = (45, 35)
    todo, seen = [seed], {seed}
    while todo:
        x, y = todo.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            n = (x + dx, y + dy)
            if n in seen or not (33 <= n[0] <= 53 and 27 <= n[1] <= 49):
                continue
            if warm(*n):
                seen.add(n)
                todo.append(n)
    return seen


# Held card as a leaning quad in sprite pixels (read off raw/domino_merge_b.png): TL, TR, BR, BL
TL, TR, BR, BL = (41.0, 28.0), (52.0, 28.0), (46.0, 47.0), (36.0, 47.0)


def build(src="raw/domino_merge_b.png", dst="raw/domino_final_hand.png"):
    im = Image.open(os.path.join(HERE, src)).convert("RGBA")
    old = card_mask(im)
    gold, gold_hi, gold_lo = P["gold3"], P["gold4"], P["gold1"]
    ink, royal, royal1 = P["night0"], P["royal"], P["royal1"]
    amber = P["amber2"]
    y0, y1 = TL[1], BL[1]

    def span(y):
        v = (y - y0) / (y1 - y0)
        return TL[0] + (BL[0] - TL[0]) * v, TR[0] + (BR[0] - TR[0]) * v

    def glove(x, y):
        r, g, b, a = im.getpixel((x, y))
        return a > 0 and min(r, g, b) > 170

    painted = set()
    for y in range(int(y0), int(y1) + 1):
        xl, xr = span(y)
        cx = (xl + xr) / 2.0
        for x in range(int(xl), int(xr) + 1):
            if glove(x, y):
                continue
            dl, dr, dt, db = x - xl, xr - x, y - y0, y1 - y
            m = min(dl, dr, dt, db)
            if m < 0.9:
                col = gold_hi if (x + y) % 3 == 0 else gold
            elif m < 1.9:
                col = ink
            else:
                col = royal1 if (x + y) % 4 == 0 else royal
                dx, dy = x - cx, y - (y0 + y1) / 2.0
                if dx * dx + (dy * 0.62) ** 2 <= 5.6:
                    col = gold
                    if abs(dx) <= 1.2 and abs(dy) <= 1.6:
                        col = amber
                    if abs(dx) < 0.7 and abs(dy) <= 2.2:
                        col = ink
                elif abs(dx) < 0.7 and abs(dy) in (6, 7, 8):
                    col = gold_lo       # ornament ticks above and below the eye
            im.putpixel((x, y), col + (255,))
            painted.add((x, y))
    # leftover slab pixels outside the clean quad become dark outline
    for p in old - painted:
        if not glove(*p):
            im.putpixel(p, ink + (255,))
    im.save(os.path.join(HERE, dst))
    return painted


if __name__ == "__main__":
    m = build()
    print("card pixels:", len(m))
