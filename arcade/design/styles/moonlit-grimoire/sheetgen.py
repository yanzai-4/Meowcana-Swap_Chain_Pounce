"""Style sheet (sheet.png, 960 x 1130). Imported by render.py."""
from PIL import Image, ImageDraw

import icons
import ui
from pal import P, to565, is565
from ui import BODY, TITLE, draw_card, card_back, paste, rect, frame, text, text_w, scaled_text, divider

SW, SH = 960, 1600


def hexs(rgb):
    return "#%02X%02X%02X" % rgb


def section(im, x, y, w, title):
    text(im, x, y + 18, title, P["gold3"], TITLE())
    rect(im, x, y + 24, x + w, y + 24, P["gold0"])
    paste(im, icons.diamond("gold3"), x + w // 2 - 2 if False else x + text_w(title, TITLE()) + 8, y + 22)


def at2(im, sp, x, y, k=2):
    paste(im, sp, x, y, scale=k)


def build():
    import render as R
    im = Image.new("RGB", (SW, SH), P["night1"])
    ui.tile_fill(im, ui.star_tile(48, 48, 11, 7))

    # ------------------------------------------------ header
    ui.moon_eye(im, 56, 52, 26)
    scaled_text(im, 100, 66, "Moonlit Grimoire", P["gold3"], TITLE(), 2)
    text(im, 102, 86, "A luxurious occult tarot deck at midnight: indigo base, antique-gold filigree, moonlight-silver highlights,", P["silver2"])
    text(im, 102, 102, "and one candle-amber accent. Calm, ornate, premium. Gold is reserved for focus and rarity.", P["silver2"])
    divider(im, 20, SW - 21, 116)

    # ------------------------------------------------ palette
    section(im, 20, 124, 440, "Palette")
    rows = [("night / moon", ["night0", "night1", "night2", "night3", "night4", "silver1", "silver2", "moon"]),
            ("gold / amber", ["gold0", "gold1", "gold2", "gold3", "gold4", "amber1", "amber2", "amber3"]),
            ("elements", ["fire1", "air1", "water1", "earth1", "fire2", "air2", "water2", "earth2"]),
            ("cool + scrap", ["rfire1", "rair1", "rwater1", "rearth1", "rat1", "rat2", "rat3", "pink"]),
            ("rarity / back", ["blue", "purple", "red", "heal", "royal", "royal1", "fire0", "water0"])]
    y = 160
    for cap, names in rows:
        text(im, 20, y + 8, cap, P["night4"])
        y += 12
        for i, n in enumerate(names):
            x = 20 + i * 56
            rect(im, x, y, x + 50, y + 22, P[n])
            frame(im, x, y, x + 50, y + 22, P["night0"])
            text(im, x + 2, y + 34, hexs(P[n]), P["silver2"])
            assert is565(P[n])
        y += 46
    text(im, 20, y + 4, "night1 = 0x2929 and royal = 0x3131 are fast-fill colors (high byte = low byte).", P["amber3"])
    text(im, 20, y + 20, "All swatches are RGB565-exact. Full set: %d colors; each screen uses 39-41." % len(P), P["silver1"])

    # ------------------------------------------------ typography
    section(im, 500, 124, 440, "Typography")
    text(im, 500, 166, "DISPLAY  Jacquard 24 (OFL)", P["night4"])
    text(im, 500, 196, "Nine Lives Arcana", P["gold3"], TITLE())
    text(im, 500, 226, "Fire Claw  {.}  Chubbs  {.}  Catwalk!", P["gold4"], TITLE())
    text(im, 500, 248, "BODY  VT323 16 px, no anti-aliasing (OFL)", P["night4"])
    scaled_text(im, 500, 276, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", P["silver2"], BODY(), 1)
    scaled_text(im, 500, 296, "abcdefghijklmnopqrstuvwxyz", P["silver2"], BODY(), 1)
    scaled_text(im, 500, 316, "0123456789 + - x / : . , ! ? %", P["silver2"], BODY(), 1)
    text(im, 500, 342, "NUMERALS  Jersey 10 (OFL) for damage numbers", P["night4"])
    scaled_text(im, 500, 380, "0123456789", P["gold4"], ui.font("Jersey10-Regular", 20), 1)
    text(im, 500, 406, "Card effect sample (body, 56 chars max):", P["night4"])
    text(im, 500, 424, "Nuzzle +2 {.} Tail Tap +1 {.} Step +2 {>} Power 9", P["silver2"])
    text(im, 500, 440, "Fire Claw {.} Wands 4 {*}1 Upright", P["silver1"])

    # ------------------------------------------------ card anatomy
    ay = 474
    section(im, 20, ay, SW - 40, "Card anatomy")
    cy = ay + 40
    cards = [("Fire 4 Upright", dict(e="fire", num=4, stars=1, rarity="common", charm="catnip")),
             ("Water 3 Reversed", dict(e="water", num=3, stars=1, rev=True, rarity="rare", charm="bell")),
             ("XIX The Sun", dict(e="fire", major=("XIX", "sun"), rarity="legendary", charm="nine")),
             ("Broken Sword 3", dict(scrap=(3, "sword"))),
             ("Card back", None)]
    for i, (nm, kw) in enumerate(cards):
        x = 24 + i * 112
        tmp = Image.new("RGB", (48, 64), P["night1"])
        if kw is None:
            card_back(tmp, 0, 0)
        else:
            draw_card(tmp, 0, 0, bg=P["night1"], **kw)
        tmp = tmp.resize((96, 128), Image.NEAREST)
        im.paste(tmp, (x, cy))
        text(im, x + 48, cy + 146, nm, P["silver2"], anchor="m")
    # numbered callouts on the first card (2x coords)
    marks = [(1, 24 + 6, cy + 10), (2, 24 + 84, cy + 8), (3, 24 + 48, cy + 62), (4, 24 + 14, cy + 114), (5, 24 + 82, cy + 112)]
    legend = ["1  number (Roman numerals for Major)", "2  stars (gold, 1 to 3)", "3  32x32 art: pips (Minor), cat (Major)",
              "4  element icon", "5  charm gem: Catnip / Bell / Nine Lives",
              "Base color = element: Fire orange-red,", "Air pale yellow, Water blue, Earth green",
              "Reversed: art flipped + cool palette", "Rat scrap: gray-green, bite marks, no element"]
    for n, mx, my in marks:
        ImageDraw.Draw(im).ellipse([mx - 5, my - 5, mx + 5, my + 5], fill=P["night0"], outline=P["amber2"])
        text(im, mx - 2, my + 3, str(n), P["amber3"], ui.font("Silkscreen-Regular", 8))
    ly = cy + 10
    for line in legend:
        text(im, 590, ly, line, P["silver2"] if line[0].isdigit() else P["silver1"])
        ly += 15
    ly += 2
    for i, (nm, col) in enumerate((("silver", "silver2"), ("blue", "blue"), ("purple", "purple"), ("gold", "gold3"), ("red", "red"))):
        rect(im, 590 + i * 70, ly, 590 + i * 70 + 62, ly + 5, P[col])
        text(im, 590 + i * 70, ly + 18, nm, P["night4"])

    # ------------------------------------------------ icons
    iy = cy + 200
    section(im, 20, iy, SW - 40, "Icons")
    gy = iy + 40
    x = 24
    groups = [("element", [("Fire", icons.elem_icon("fire")), ("Air", icons.elem_icon("air")), ("Water", icons.elem_icon("water")), ("Earth", icons.elem_icon("earth"))]),
              ("status", [("Singe", icons.status_icon("singe")), ("Puff", icons.status_icon("puff")), ("Drowsy", icons.status_icon("drowsy")),
                          ("Curl", icons.status_icon("curl")), ("Leap", icons.status_icon("leap"))]),
              ("charm", [("Catnip", icons.charm_icon("catnip")), ("Bell", icons.charm_icon("bell")), ("Nine Lives", icons.charm_icon("nine"))])]
    for cap, items in groups:
        text(im, x, gy + 6, cap, P["night4"])
        xx = x
        for nm, ic in items:
            k = 4 if ic.width <= 9 else 3
            ox = xx + (46 - ic.width * k) // 2
            paste(im, ic, ox, gy + 16 + (44 - ic.height * k) // 2, scale=k)
            text(im, xx + 23, gy + 76, nm, P["silver2"], anchor="m")
            xx += 62 if nm != "Nine Lives" else 80
        x = xx + 22
    # ui glyphs
    ux = 24
    for nm, g in (("paw cursor", icons.paw()), ("flourish", icons.corner())):
        paste(im, g, ux, gy + 108, scale=2)
        text(im, ux + g.width, gy + 142, nm, P["silver2"], anchor="m")
        ux += 110
    paste(im, icons.heart(), ux, gy + 112, scale=2); text(im, ux + 9, gy + 142, "HP", P["silver2"], anchor="m"); ux += 70
    paste(im, icons.treat(), ux, gy + 112, scale=2); text(im, ux + 9, gy + 142, "Treats", P["silver2"], anchor="m"); ux += 80
    ui.moon_eye(im, ux + 20, gy + 124, 18); text(im, ux + 20, gy + 156, "cat-eye moon", P["silver2"], anchor="m"); ux += 100
    for i, l in enumerate("ABC"):
        ui.button_gem(im, ux + i * 22 + 8, gy + 120, l)
    text(im, ux + 30, gy + 142, "button hints", P["silver2"], anchor="m")

    # ------------------------------------------------ characters
    chy = gy + 176
    section(im, 20, chy, 700, "Characters (2x)")
    sx = 24
    base = chy + 48
    for nm, key, flip in (("Domino", "domino_final_hand", False), ("Zero", "zero", False), ("Gray Rat", "grayrat", False), ("Chubbs, the Pantry King", "chubbs", False)):
        sp = R.sprite(key, flip, cool=key.startswith("domino"))
        k = 2
        by = base + 192
        ImageDraw.Draw(im).ellipse([sx + 4, by - 8, sx + sp.width * k - 4, by + 4], fill=P["night0"])
        paste(im, sp, sx, by - sp.height * k, scale=k)
        w = sp.width * k
        text(im, sx + w // 2, by + 22, nm if len(nm) < 12 else "Chubbs", P["gold3"], anchor="m")
        if key == "zero":
            text(im, sx + w // 2, by + 36, "the Fool", P["night4"], anchor="m")
        sx += w + 6
    # backgrounds / tiles
    tx = 740
    section(im, tx, chy, 200, "Tiles")
    tile = ui.star_tile(32, 32, 7, 6)
    big = Image.new("RGB", (96, 64), P["night1"])
    ui.tile_fill(big, tile)
    paste(im, big, tx, base, scale=2)
    frame(im, tx - 1, base - 1, tx + 192, base + 128, P["gold0"])
    text(im, tx, base + 146, "star-dust tile 32x32", P["silver1"])
    scene = Image.new("RGB", (480, 232))
    R.attic(scene)
    win = scene.crop((96, 38, 168, 126))
    paste(im, win, tx, base + 162)
    frame(im, tx - 1, base + 161, tx + 72, base + 250, P["gold0"])
    text(im, tx + 90, base + 178, "attic window", P["silver1"])
    text(im, tx + 90, base + 192, "(code-drawn)", P["night4"])
    lat = Image.new("RGB", (48, 64), P["night1"])
    card_back(lat, 0, 0)
    paste(im, lat.crop((8, 8, 24, 24)), tx + 90, base + 202, scale=3)
    text(im, tx + 90, base + 266, "lattice 16x16", P["silver1"])

    # ------------------------------------------------ storyboard
    sy0 = base + 192 + 96
    section(im, 20, sy0, SW - 40, "Signature animation: play a card, link the reading, crit")
    frames = [
        ("1  Lift +4 px, gold bracket", dict(lift=4, popup=False, dmg=0, slash=False, particles=False), (0, 188, 228, 316)),
        ("2  White flash 2 f + element sparks", dict(lift=4, popup=False, dmg=0, slash=False, particles=False, card_flash=True, sparks=True), (0, 188, 228, 316)),
        ("3  Link: popup tab climbs a tier", dict(lift=4, popup=True, dmg=0, slash=False, particles=False, sparks=True), (80, 70, 308, 198)),
        ("4  Crit: shake 2 px x4, number x2", dict(lift=4, popup=True, dmg=34, slash=True, particles=True, shake=(2, 0)), (244, 92, 472, 220)),
    ]
    fx = 20
    for cap, kw, box in frames:
        fr = R.battle(**kw).crop(box)
        im.paste(fr, (fx, sy0 + 40))
        frame(im, fx - 1, sy0 + 39, fx + 228, sy0 + 168, P["gold1"])
        text(im, fx, sy0 + 186, cap, P["silver2"])
        fx += 236
    return finish(im.crop((0, 0, SW, sy0 + 40 + 128 + 70)))


def finish(im):
    frame(im, 4, 4, im.width - 5, im.height - 5, P["gold0"])
    ui.corners(im, 4, 4, im.width - 5, im.height - 5)
    cols = set(im.getdata())
    assert all(is565(c) for c in cols), "non-565 colour in sheet"
    im.save("sheet.png")
    print("sheet.png", im.size, len(cols), "colors")
    return im
