"""Card faces: Minor (pips), Major (cat portraits, see majors.py), rat scraps, curse, card back.
Faces are interior-only: the 2-px rim (ink edge + rarity colour) is drawn by the UI at runtime. Output sizes:
44x60 (card_*), 36x50 (card_s_*). The four outermost interior corner pixels are transparent."""
from PIL import Image, ImageDraw, ImageOps

import icons
import majors
import scraps
import ui
from pal import P
from spec import ELEMENTS, SCRAPS
from ui import D, font, frame, paste, px, rect

NUMERALS = {0: "0", 1: "I", 3: "III", 4: "IV", 7: "VII", 8: "VIII", 12: "XII", 19: "XIX"}
MAJOR_IDS = [(0, "fool"), (1, "magician"), (3, "empress"), (4, "emperor"), (7, "chariot"), (8, "strength"),
             (12, "hanged"), (19, "sun")]


def size_of(small):
    return (40, 54) if small else (48, 64)


def ace_plate(e, rev):
    dark, mid, light = ((P["r" + e + "0"], P["r" + e + "1"], P["silver2"]) if rev
                        else (P[e + "0"], P[e + "1"], P[e + "2"]))
    plate = Image.new("RGBA", (32, 32), dark + (255,))
    d = ImageDraw.Draw(plate)
    d.rectangle([2, 2, 29, 29], outline=mid)
    for cx, cy in ((2, 2), (29, 2), (2, 29), (29, 29)):
        d.point((cx, cy), fill=light)
    d.ellipse([3, 3, 28, 28], outline=P["gold1"])
    d.ellipse([5, 5, 26, 26], outline=P["gold2"])
    d.ellipse([6, 6, 25, 25], fill=mid)
    ic = icons.elem_icon(e, 9, rev)
    ic = ic.resize((18, 18), Image.NEAREST)
    plate.alpha_composite(ic, (7, 7))
    for sx, sy in ((6, 6), (25, 6), (6, 25), (25, 25)):
        d.point((sx, sy), fill=P["gold4"])
    for sx, sy in ((16, 3), (16, 28), (3, 16), (28, 16)):
        d.point((sx, sy), fill=P["gold3"])
    return ImageOps.flip(plate) if rev else plate


ELEM5 = {"fire": ["..o..", ".orlo", "orlyo", "orrro", ".ooo."],
         "air": ["..ooo", ".ocwo", "occco", "ocwo.", "oo..."],
         "water": ["..o..", ".obo.", "obwbo", "obbbo", ".ooo."],
         "earth": [".o.o.", "ooooo", "ogwgo", "oddgo", ".ooo."]}


def elem5(e, rev):
    leg = icons.elem_legend(e)
    if rev:
        leg = {k: (v if k == "o" else P["moon"] if k in "wy" else P["silver2"] if k == "l" else P["rair1"])
               for k, v in leg.items()}
    return icons.grid_image(ELEM5[e], leg)


def ten_plate(e, rev):
    dark, mid, light = ((P["r" + e + "0"], P["r" + e + "1"], P["silver2"]) if rev
                        else (P[e + "0"], P[e + "1"], P[e + "2"]))
    plate = Image.new("RGBA", (32, 32), dark + (255,))
    d = ImageDraw.Draw(plate)
    d.rectangle([2, 2, 29, 29], outline=mid)
    for cx, cy in ((2, 2), (29, 2), (2, 29), (29, 29)):
        d.point((cx, cy), fill=light)
    ic = elem5(e, rev)
    for cx, cy in [(8, y) for y in (6, 12, 19, 25)] + [(24, y) for y in (6, 12, 19, 25)] + [(16, 9), (16, 22)]:
        plate.alpha_composite(ic, (cx - 2, cy - 2))
    return ImageOps.flip(plate) if rev else plate


def minor_plate(e, n, rev):
    if n == 1:
        return ace_plate(e, rev)
    if n == 10:
        return ten_plate(e, rev)
    return ui.plate_minor(e, n, rev)


def card_core(small, e=None, rev=False, label="", art=None, major=False, scrap=False, ink=None):
    """Full-size card canvas (rim colors are placeholders; only the interior is exported)."""
    W, H = size_of(small)
    if scrap:
        edge, body, filig, inkc = P["rat0"], P["rat1"], P["rat2"], P["rat3"]
    else:
        dark, mid, light = ((P["r" + e + "0"], P["r" + e + "1"], P["silver2"]) if rev
                            else (P[e + "0"], P[e + "1"], P[e + "2"]))
        edge, body, filig = P["night0"], mid, light
        inkc = P["night0"] if (e == "air" and not rev) else P["moon"]
    c = Image.new("RGBA", (W, H), edge + (255,))
    rect(c, 2, 2, W - 3, H - 3, body)
    frame(c, 3, 3, W - 4, H - 4, filig)
    for cx, cy in ((3, 3), (W - 4, 3), (3, H - 4), (W - 4, H - 4)):
        px(c, cx, cy, edge)
        px(c, cx + (1 if cx < W // 2 else -1), cy + (1 if cy < H // 2 else -1), filig)
    pw, ptop = (26, 14) if small else (32, 15)
    pxl = (W - pw) // 2
    if small:
        art = art.crop((3, 3, 29, 29))
    plate_edge = P["rat2"] if scrap else (P["gold2"] if major else P["gold1"])
    frame(c, pxl - 1, ptop - 1, pxl + pw, ptop + pw, plate_edge)
    c.paste(art, (pxl, ptop))
    if label:
        f = font("VT323-Regular", 16)
        if label == "0":   # VT323's zero loses its top row at 1-bit; draw it by hand
            y0 = 2 if small else 3
            for yy in range(y0, y0 + 10):
                for xx in ((6, 7) if yy in (y0, y0 + 9) else (5, 8)):
                    px(c, xx, yy, inkc)
        else:
            D(c).text((5, 12 if small else 13), label, font=f, fill=inkc, anchor="ls")
    if not scrap:
        by = H - 14 if not small else H - 12
        paste(c, icons.elem_icon(e, 7 if small else 9, rev), 6, by)
        if rev:
            paste(c, icons.tri_down("silver2"), W // 2 - 3, by + (3 if not small else 1))
    return c


def interior(card):
    W, H = card.size
    box = card.crop((2, 2, W - 2, H - 2))
    iw, ih = box.size
    for x, y in ((0, 0), (iw - 1, 0), (0, ih - 1), (iw - 1, ih - 1)):
        box.putpixel((x, y), (0, 0, 0, 0))
    return box


def minor_face(def_id, small, rev):
    e = ELEMENTS[def_id // 10]
    n = def_id % 10 + 1
    art = minor_plate(e, n, rev)
    label = "A" if n == 1 else str(n)
    return interior(card_core(small, e, rev, label, art))


def major_face(def_id, small, rev):
    num, key = MAJOR_IDS[def_id - 40]
    e = majors.ELEMENT[key]
    art = majors.plate(key, rev, e)
    card = card_core(small, e, rev, NUMERALS[num], art, major=True)
    return interior(card)


def face(def_id, small, rev):
    return major_face(def_id, small, rev) if def_id >= 40 else minor_face(def_id, small, rev)


def card_set(small, rev):
    return lambda: [face(i, small, rev) for i in range(48)]


def scrap_set(small):
    def build():
        out = []
        for i, kind in enumerate(SCRAPS):
            card = card_core(small, art=scraps.art(kind), scrap=True)
            scraps.bite_edges(card, i)
            out.append(interior(card))
        return out
    return build


def chewed_set():
    out = []
    for def_id in (44, 41, 45):
        card = card_core(True, majors.ELEMENT[MAJOR_IDS[def_id - 40][1]], True, NUMERALS[MAJOR_IDS[def_id - 40][0]],
                         majors.plate(MAJOR_IDS[def_id - 40][1], True, majors.ELEMENT[MAJOR_IDS[def_id - 40][1]]),
                         major=True)
        scraps.bite_edges(card)
        out.append(interior(card))
    return out


def droppings(small):
    def build():
        W, H = size_of(small)
        c = card_core(small, art=scraps.art("droppings", curse=True), scrap=True)
        d = ImageDraw.Draw(c)
        # curse tint: darker body, red studs
        for x in range(2, W - 2):
            for y in range(2, H - 2):
                if c.getpixel((x, y))[:3] == P["rat1"]:
                    c.putpixel((x, y), P["rat0"] + (255,))
        frame(c, 3, 3, W - 4, H - 4, P["red"])
        for cx, cy in ((3, 3), (W - 4, 3), (3, H - 4), (W - 4, H - 4)):
            px(c, cx, cy, P["night0"])
        return [interior(c)]
    return build


def back(small):
    def build():
        c = Image.new("RGB", size_of(small), P["night1"])
        ui.card_back(c, 0, 0, small)
        c = c.convert("RGBA")
        W, H = c.size
        for x, y in ((0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)):
            c.putpixel((x, y), (0, 0, 0, 0))
        return [c]
    return build


GENERATORS = {
    "card_u": card_set(False, False), "card_r": card_set(False, True),
    "card_s_u": card_set(True, False), "card_s_r": card_set(True, True),
    "scrap": scrap_set(False), "scrap_s": scrap_set(True), "card_chewed_s": chewed_set,
    "card_droppings": droppings(False), "card_droppings_s": droppings(True),
    "card_back": back(False), "card_back_s": back(True),
}
