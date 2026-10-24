"""Moonlit Grimoire: reproduces spread.png, battle.png, the @2x versions and sheet.png.
Inputs: raw/{domino,chubbs,grayrat,zero}.png (PixelLab create-image-pixen) and fonts/*.ttf (Google Fonts, OFL).
Run: python render.py   (sprites are generated once by gen_sprites.py; this script never calls the network)."""
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

from PIL import Image, ImageDraw, ImageOps

FONT_FILES = {"jacquard24/Jacquard24-Regular": "Jacquard 24", "vt323/VT323-Regular": "VT323",
              "jersey10/Jersey10-Regular": "Jersey 10", "silkscreen/Silkscreen-Regular": "Silkscreen"}


def fetch_fonts():
    """Download the OFL pixel fonts (Google Fonts repo) into fonts/ when missing."""
    import urllib.request
    os.makedirs("fonts", exist_ok=True)
    for path in FONT_FILES:
        dest = os.path.join("fonts", path.split("/")[1] + ".ttf")
        if not os.path.exists(dest):
            urllib.request.urlretrieve(f"https://github.com/google/fonts/raw/main/ofl/{path}.ttf", dest)


fetch_fonts()

import icons
import ui
from pal import P, is565, to565
from ui import (BODY, TITLE, SMALL, corners, divider, draw_card, empty_slot, frame, moon_eye, paste, px, rect,
                scaled_text, text, text_w)

W, H = 480, 320


# ---------------------------------------------------------------- sprites
SPRITE_COLORS = sorted({v for k, v in P.items() if not (k.startswith("r") and not k.startswith("rat"))
                        and k not in ("royal", "royal0", "royal1", "blue", "purple")})


def sprite(name, flip=False, cool=False):
    """cool=True drops the green-ish dark colors from the mapping so black fur maps to indigo-black."""
    im = Image.open(f"raw/{name}.png").convert("RGBA")
    rgb = Image.new("RGB", im.size, P["night0"])
    rgb.paste(im, mask=im.split()[3])
    q = ui_quant(rgb, cool)
    a = im.split()[3].point(lambda v: 255 if v >= 128 else 0)
    out = q.convert("RGBA")
    out.putalpha(a)
    if flip:
        out = ImageOps.mirror(out)
    return out


def ui_quant(rgb, cool=False):
    from pal import quantize_to
    cols = SPRITE_COLORS
    if cool:
        drop = {P[k] for k in ("rat0", "rat1", "earth0", "earth1", "air0")}
        cols = [c for c in cols if c not in drop]
    return quantize_to(rgb, cols)


def trim(sp):
    return sp.crop(sp.getbbox())


# ---------------------------------------------------------------- shared chrome
def base_bg():
    im = Image.new("RGB", (W, H), P["night1"])
    ui.tile_fill(im, ui.star_tile())
    return im


def footer(im, left_bits, hints, y=313):
    """Footer: status on the left, context button hints on the right (always visible)."""
    x = 16
    for kind, val in left_bits:
        if kind == "name":
            x += text(im, x, y, val, P["gold3"]) + 10
        elif kind == "hp":
            paste(im, icons.heart(), x, y - 9)
            x += 12 + text(im, x + 12, y, val, P["silver2"]) + 12
        elif kind == "treat":
            paste(im, icons.treat(), x, y - 9)
            x += 12 + text(im, x + 12, y, val, P["silver2"]) + 12
        elif kind == "txt":
            x += text(im, x, y, val, P["silver1"]) + 12
    # right aligned hints
    widths = [14 + text_w(lbl) + 2 for _, lbl in hints]
    hx = W - 16 - sum(widths) - 10 * (len(hints) - 1)
    for (letter, lbl), w in zip(hints, widths):
        ui.hint(im, hx, y, letter, lbl)
        hx += w + 10


def hp_row(im, x, y, label, cur, mx, wbar):
    ui.bar(im, x, y, x + wbar, y + 8, cur / mx)
    text(im, x + wbar + 8, y + 9, f"{label} {cur}/{mx}" if mx else label, P["silver2"])


def stat_chip(im, x, y, icon, label, col):
    if icon is not None:
        paste(im, icon, x, y - 9)
        x += 12
    return 12 * (icon is not None) + text(im, x, y, label, P[col])


# ---------------------------------------------------------------- Spread
def spread():
    im = base_bg()
    frame(im, 2, 2, W - 3, H - 3, P["gold0"])
    corners(im, 2, 2, W - 3, H - 3)

    # --- enemy row
    ui.panel(im, 16, 9, 74, 61, fill="night0", orn=False)
    rat = trim(sprite("grayrat"))
    paste(im, rat, 16 + (59 - rat.width) // 2 + 1, 61 - rat.height - 2)
    text(im, 88, 36, "Gray Rat", P["gold3"], TITLE())
    ui.bar(im, 88, 44, 188, 52, 1.0)
    text(im, 196, 53, "HP 18", P["silver2"])
    for i, (num, kind) in enumerate([(3, "sword"), (3, "sword"), (4, "coin")]):
        draw_card(im, 328 + 48 * i, 6, scrap=(num, kind), small=True, bg=P["night1"])
    divider(im, 16, W - 17, 66)

    # --- reading
    text(im, 16, 82, "READING", P["gold3"])
    x = 16 + text_w("READING") + 12
    for i, (n, hot) in enumerate([("Nuzzle x2", 0), ("Tail Tap x2", 0), ("Step x2", 0), ("Catwalk", 1)]):
        if i:
            x += text(im, x, 82, "{.}", P["gold1"]) + 6
        x += text(im, x, 82, n, P["gold4"] if hot else P["silver2"]) + 6
    divider(im, 16, W - 17, 88)

    # --- spread row
    text(im, 16, 101, "SPREAD 4/6", P["gold3"])
    cx = W - 16
    chips = [(None, "PER ROUND", "night4"), (None, "DMG 38", "amber3"), (icons.status_icon("singe"), "SINGE 2", "amber2"),
             (icons.heart(), "HEAL 3", "heal"), (icons.status_icon("curl"), "CURL 0", "silver2")]
    widths = [12 * (c[0] is not None) + text_w(c[1]) for c in chips]
    x = cx - sum(widths) - 14 * (len(chips) - 1)
    for c, w in zip(chips, widths):
        stat_chip(im, x, 101, c[0], c[1], c[2])
        x += w + 14

    slots = [("fire", 3, 1, False, "common", None), ("fire", 4, 1, False, "common", "catnip"),
             ("air", 5, 1, True, "rare", None), ("water", 3, 1, False, "none", "bell")]
    for i in range(6):
        sx = 18 + 58 * i
        if i < len(slots):
            e, n, s, r, rar, ch = slots[i]
            draw_card(im, sx, 106, e, n, s, rev=r, rarity=rar, charm=ch)
        else:
            empty_slot(im, sx, 106)
    # FIGHT plaque
    ui.panel(im, 372, 106, 463, 169, fill="night0", edge="gold2", orn=False)
    frame(im, 374, 108, 461, 167, P["gold0"])
    corners(im, 372, 106, 463, 169)
    moon_eye(im, 417, 128, 11)
    text(im, 417, 158, "Fight", P["gold4"], TITLE(), anchor="m")
    rect(im, 391, 162, 443, 162, P["amber1"])
    # cursor: gold brackets + paw under the card
    cx0, cy0 = 18 + 58, 106
    for (bx, by, dx, dy) in ((cx0 - 4, cy0 - 4, 1, 1), (cx0 + 51, cy0 - 4, -1, 1), (cx0 - 4, cy0 + 67, 1, -1), (cx0 + 51, cy0 + 67, -1, -1)):
        rect(im, min(bx, bx + 5 * dx), by, max(bx, bx + 5 * dx), by, P["amber3"])
        rect(im, bx, min(by, by + 5 * dy), bx, max(by, by + 5 * dy), P["amber3"])
    paste(im, icons.paw(), cx0 + 24 - 7, 173)

    # --- box row
    text(im, 16, 197, "BOX 2/6", P["gold3"])
    text(im, 16, 211, "spare cards", P["night4"])
    for i in range(6):
        bx = 100 + 46 * i - 28
        bx = 90 + 46 * i - 18 + 18
        if i == 0:
            draw_card(im, bx, 186, "fire", major=("XIX", "sun"), rarity="legendary", small=True, charm="nine")
        elif i == 1:
            draw_card(im, bx, 186, "earth", 7, 2, small=True, rarity="rare")
        else:
            empty_slot(im, bx, 186, small=True)
    # candle-lit vignette on the right of the box row
    ui.candle(im, 384, 239, 17)
    ui.candle(im, 450, 239, 13)
    moon_eye(im, 417, 211, 15)
    ui.crescent(im, 417, 211, 0, "night1") if False else None
    for sx, sy in ((396, 190), (440, 192), (407, 232), (428, 230)):
        ui.sparkle(im, sx, sy, "silver2", 1)
    divider(im, 16, W - 17, 244)

    # --- selected card detail
    ui.panel(im, 16, 249, W - 17, 290, fill="night0")
    text(im, 30, 270, "Fire Claw", P["gold3"], TITLE())
    tx = 30 + text_w("Fire Claw", TITLE()) + 10
    text(im, tx, 269, "{.} Wands 4 {*}1 Upright", P["silver2"])
    text(im, 30, 285, "Nuzzle +2 {.} Tail Tap +1 {.} Step +2 {>}", P["silver1"])
    wx = 30 + text_w("Nuzzle +2 {.} Tail Tap +1 {.} Step +2 {>}") + 6
    text(im, wx, 285, "Power 9", P["amber3"])

    footer(im, [("name", "Domino"), ("hp", "HP 30/36"), ("treat", "Treats 14")],
           [("A", "Pick up"), ("B", "Menu"), ("C", "Info")])
    return im


# ---------------------------------------------------------------- Battle
def attic(im, floor=196, bottom=232):
    rect(im, 0, 0, W - 1, bottom - 1, P["night1"])
    # wall seams
    for x in range(12, W, 40):
        rect(im, x, 30, x, floor - 1, P["night0"])
        for y in range(40, floor, 26):
            px(im, x + 1, y, P["night2"])
            px(im, x + 1, y + 1, P["night2"])
    ui.tile_fill(im, ui.star_tile(40, 40, 3, 4), (0, 30, W, 31)) if False else None
    # rafters
    d = ImageDraw.Draw(im)
    rect(im, 0, 30, W - 1, 36, P["gold0"])
    rect(im, 0, 36, W - 1, 36, P["night0"])
    rect(im, 0, 30, W - 1, 30, P["gold1"])
    d.polygon([(0, 36), (0, 62), (6, 62), (60, 36)], fill=P["gold0"])
    d.line([(0, 62), (58, 36)], fill=P["night0"])
    d.polygon([(W, 36), (W, 62), (W - 6, 62), (W - 60, 36)], fill=P["gold0"])
    d.line([(W - 1, 62), (W - 62, 36)], fill=P["night0"])
    # moonbeam on the floor (flat polygon, no blending)
    d.polygon([(100, 126), (164, 126), (252, floor), (40, floor)], fill=P["night2"])
    # attic window with moon
    wx0, wx1, wy0, wy1 = 100, 164, 44, 126
    d.rectangle([wx0 - 3, wy0 + 30, wx1 + 3, wy1 + 6], fill=P["gold0"])
    d.ellipse([wx0 - 3, wy0 - 3, wx1 + 3, wy0 + 61], fill=P["gold0"])
    d.rectangle([wx0, wy0 + 30, wx1, wy1], fill=P["royal0"])
    d.ellipse([wx0, wy0, wx1, wy0 + 60], fill=P["royal0"])
    ui.crescent(im, 140, 76, 14, "silver2", "royal0", dx=7)
    for sx, sy in ((112, 62), (121, 90), (150, 100), (127, 112), (156, 60)):
        px(im, sx, sy, P["moon"])
    ui.sparkle(im, 118, 78, "silver2", 2)
    rect(im, 131, wy0, 132, wy1, P["gold1"])
    rect(im, wx0, 88, wx1, 89, P["gold1"])
    d.arc([wx0, wy0, wx1, wy0 + 60], 180, 360, fill=P["gold2"])
    rect(im, wx0 - 6, wy1 + 4, wx1 + 6, wy1 + 8, P["gold1"])
    rect(im, wx0 - 6, wy1 + 8, wx1 + 6, wy1 + 9, P["night0"])
    # shelves + jars (right) and sacks
    for sy in (112, 160):
        rect(im, 446, sy, W - 1, sy + 3, P["gold0"])
        rect(im, 446, sy + 3, W - 1, sy + 3, P["night0"])
        rect(im, 448, sy + 4, 449, sy + 10, P["gold0"])
    for jx, jy, col in ((450, 112, "earth0"), (462, 112, "amber0"), (472, 112, "rat1"), (452, 160, "water0"), (466, 160, "fire0")):
        h = 14
        rect(im, jx, jy - h, jx + 8, jy - 1, P[col])
        rect(im, jx + 1, jy - h, jx + 7, jy - h, P["gold1"])
        rect(im, jx + 1, jy - h + 3, jx + 2, jy - 3, P["night3"])
    # floor
    rect(im, 0, floor, W - 1, bottom - 1, P["night0"])
    rect(im, 0, floor, W - 1, floor, P["gold0"])
    for i, y in enumerate(range(floor + 6, bottom, 7)):
        rect(im, 0, y, W - 1, y, P["night1"])
    for x in range(20, W, 56):
        rect(im, x, floor + 1, x, floor + 5, P["night1"])
    # book stack + candle (warm light source) between the fighters
    rect(im, 232, 200, 258, 211, P["fire0"]); rect(im, 232, 200, 258, 200, P["fire1"]); rect(im, 232, 205, 258, 205, P["gold1"])
    rect(im, 236, 192, 256, 199, P["water0"]); rect(im, 236, 192, 256, 192, P["water1"]); rect(im, 240, 196, 252, 196, P["gold1"])
    ui.candle(im, 244, 191, 10)
    # dithered candle halo
    for yy in range(160, 192):
        for xx in range(216, 274):
            dist = ((xx - 246) ** 2 + (yy - 172) ** 2) ** 0.5
            if dist < 26 and (xx + yy) % 2 == 0 and im.getpixel((xx, yy)) == P["night1"]:
                im.putpixel((xx, yy), P["night2"])
    # sack + cheese by Chubbs
    d.ellipse([300, 190, 338, 216], fill=P["gold0"]); d.arc([300, 190, 338, 216], 200, 340, fill=P["gold1"])
    d.polygon([(312, 188), (326, 188), (322, 194), (316, 194)], fill=P["night0"])
    d.pieslice([416, 196, 450, 224], 180, 270, fill=P["gold3"])
    d.pieslice([416, 196, 450, 224], 180, 270, outline=P["night0"])


def lift_glow(im, box, col="amber3"):
    x0, y0, x1, y1 = box
    frame(im, x0 - 2, y0 - 2, x1 + 2, y1 + 2, P[col])
    frame(im, x0 - 3, y0 - 3, x1 + 3, y1 + 3, P["amber1"])
    for cx, cy in ((x0 - 3, y0 - 3), (x1 + 3, y0 - 3), (x0 - 3, y1 + 3), (x1 + 3, y1 + 3)):
        ui.sparkle(im, cx, cy, "gold4", 2)


def battle(lift=4, popup=True, dmg=34, slash=True, particles=True, card_flash=False, sparks=False, shake=(0, 0), chain=3, hero="domino_final_hand", hero_cool=True):
    im = Image.new("RGB", (W, H), P["night1"])
    attic(im)

    # --- top enemy plate
    rect(im, 0, 0, W - 1, 29, P["night0"])
    rect(im, 0, 29, W - 1, 29, P["gold1"])
    rect(im, 0, 28, W - 1, 28, P["gold0"])
    text(im, 14, 24, "Chubbs, the Pantry King", P["gold3"], TITLE())
    ui.bar(im, 316, 7, 463, 16, 62 / 90, fill="fire1", hi="fire2")
    px(im, 316 + 74, 8, P["moon"]); px(im, 316 + 74, 15, P["moon"])    # Still Hungry threshold (50%)
    text(im, 463, 27, "HP 62/90", P["silver2"], anchor="r")
    x = 14
    paste(im, icons.status_icon("curl"), x, 33)
    x += 12 + text(im, x + 12, 42, "Curl 0", P["silver2"]) + 14
    paste(im, icons.status_icon("singe"), x, 33)
    text(im, x + 12, 42, "Singe 1", P["amber2"])

    # --- enemy scrap row (right)
    en = [(6, "sword"), (8, "cup"), ("VIII", "strength"), ("3", "gnaw"), (8, "coin"), (6, "sword")]
    for i, (n, k) in enumerate(en):
        draw_card(im, 204 + 44 * i, 34, scrap=(n, k), small=True, bg=P["night1"], rev=False)
    nx = 204 + 44 * 3
    frame(im, nx - 2, 32, nx + 41, 89, P["silver2"])
    px(im, nx + 20, 91, P["silver2"]); rect(im, nx + 18, 90, nx + 22, 90, P["silver2"]); rect(im, nx + 19, 91, nx + 21, 91, P["silver2"])

    # --- fighters
    dom = sprite(hero, cool=hero_cool)
    cb = sprite("chubbs")
    db, cbb = dom.getbbox(), cb.getbbox()
    FEET = 222
    dx = 64 - (db[0] + db[2]) // 2 + shake[0]
    dy = FEET - db[3] + shake[1]
    cxs = 396 - (cbb[0] + cbb[2]) // 2 + shake[0]
    cys = FEET + 2 - cbb[3] + shake[1]
    d = ImageDraw.Draw(im)
    d.ellipse([64 - 28 + shake[0], FEET - 4, 64 + 28 + shake[0], FEET + 3], fill=P["night0"])
    d.ellipse([396 - 46 + shake[0], FEET - 3, 396 + 46 + shake[0], FEET + 6], fill=P["night0"])
    paste(im, dom, dx, dy)
    paste(im, cb, cxs, cys)
    top, hgt = cys + cbb[1], cbb[3] - cbb[1]
    if slash:
        for k in range(3):
            ox = 396 - 14 + k * 10 + shake[0]
            y0 = top + int(hgt * 0.50)
            d.line([(ox, y0), (ox + 18, y0 + 34)], fill=P["night0"], width=4)
            d.line([(ox, y0), (ox + 18, y0 + 34)], fill=P["moon"], width=2)
    if particles:
        for sx, sy in ((354, top + 20), (440, top + 40), (350, top + 80), (444, top + 76), (372, top - 6)):
            ui.sparkle(im, sx, sy, "amber3", 2)

    # --- chain popup
    if popup:
        px0, py0, px1, py1 = 100, 98, 286, 142
        ui.panel(im, px0, py0, px1, py1, fill="night0", edge="gold2", orn=False)
        frame(im, px0 + 2, py0 + 2, px1 - 2, py1 - 2, P["gold0"])
        corners(im, px0, py0, px1, py1)
        tab = "CHAIN x%d" % chain
        tw = text_w(tab) + 16
        tcx = (px0 + px1) // 2
        rect(im, tcx - tw // 2, py0 - 7, tcx + tw // 2, py0 + 5, P["night0"])
        frame(im, tcx - tw // 2, py0 - 7, tcx + tw // 2, py0 + 5, P["amber1"])
        text(im, tcx, py0 + 3, tab, P["amber3"], anchor="m")
        text(im, tcx, py0 + 21, "Nuzzle +2 {>} Step +2 {>}", P["silver2"], anchor="m")
        text(im, tcx, py0 + 40, "Catwalk!", P["gold4"], TITLE(), anchor="m")
        # "paw prints" connecting the two cards
    # --- damage number
    if dmg:
        bx, by = 318, 172
        ui.sparkle(im, bx - 38, by - 30, "gold4", 3)
        ui.sparkle(im, bx + 40, by - 34, "amber3", 2)
        ui.sparkle(im, bx - 40, by + 8, "amber3", 2)
        jf = ui.font("Jersey10-Regular", 20)
        scaled_text(im, bx, by + 16, str(dmg), P["amber1"], jf, 2, outline=P["night0"], anchor="m")
        scaled_text(im, bx, by + 14, str(dmg), P["gold4"], jf, 2, outline=None, anchor="m")

    # --- bottom: player cards + reading panel
    rect(im, 0, 232, W - 1, H - 1, P["night1"])
    ui.tile_fill(im, ui.star_tile(), (0, 234, W, H))
    rect(im, 0, 232, W - 1, 232, P["gold1"])
    rect(im, 0, 233, W - 1, 233, P["gold0"])
    prow = [("fire", 3, False, "common", None), ("fire", 4, False, "common", "catnip"),
            ("air", 5, True, "rare", None), ("water", 3, False, "none", "bell")]
    for i, (e, n, r, rar, ch) in enumerate(prow):
        x = 16 + 46 * i
        y = 238 - (lift if i == 1 else 0)
        if i == 1 and lift:
            lift_glow(im, (x, y, x + 39, y + 53))
        draw_card(im, x, y, e, n, 1, rev=r, rarity=rar, charm=ch, small=True, bg=P["night1"])
        if i == 1 and card_flash:
            rect(im, x + 2, y + 2, x + 37, y + 51, P["moon"])
            frame(im, x, y, x + 39, y + 53, P["gold4"])
        if i == 1 and sparks:
            for sx, sy, c in ((x + 6, y - 10, "amber3"), (x + 18, y - 17, "fire2"), (x + 31, y - 9, "amber3"), (x + 12, y - 24, "gold4"),
                              (x + 27, y - 27, "amber2"), (x + 38, y - 18, "fire2")):
                rect(im, sx, sy - 1, sx + 1, sy, P[c])
    # chain link between card 1 and 2 (tail line with a gem)
    # reading panel
    ui.panel(im, 212, 240, W - 17, 290, fill="night0")
    text(im, 224, 259, "READING", P["gold3"])
    text(im, W - 28, 259, "Round 1", P["silver1"], anchor="r")
    text(im, 224, 279, "Nuzzle +2 {>} Step +2 {>}", P["silver2"])
    text(im, 224 + text_w("Nuzzle +2 {>} Step +2 {>}") + 4, 279, "Catwalk!", P["gold4"])

    # --- footer
    divider(im, 16, W - 17, 296, mid=False)
    x = 16
    x += text(im, x, 313, "Domino", P["gold3"]) + 10
    ui.bar(im, x, 305, x + 80, 313, 33 / 36, fill="heal", hi="moon")
    x += 88
    text(im, x, 313, "HP 33/36", P["silver2"])
    widths = [14 + text_w("2x") + 2, 14 + text_w("Skip") + 2]
    hx = W - 16 - sum(widths) - 12
    for (letter, lbl), w in zip((("A", "2x"), ("B", "Skip")), widths):
        ui.hint(im, hx, 313, letter, lbl)
        hx += w + 12
    return im


# ---------------------------------------------------------------- output
def check(im, name):
    cols = set(im.getdata())
    bad = [c for c in cols if not is565(c)]
    print(f"{name}: {im.size}, {len(cols)} colors, non-565: {len(bad)}")
    assert im.size == (W, H) or name.startswith("sheet")
    assert not bad


def main():
    import finalhand
    finalhand.build()          # raw/domino_merge_b.png -> raw/domino_final_hand.png (card-back repaint)
    for name, fn in (("spread", spread), ("battle", battle)):
        im = fn()
        check(im, name)
        im.save(f"{name}.png")
        im.resize((W * 2, H * 2), Image.NEAREST).save(f"{name}@2x.png")
    if os.path.exists("sheetgen.py"):
        import sheetgen
        sheetgen.build()


if __name__ == "__main__":
    main()
