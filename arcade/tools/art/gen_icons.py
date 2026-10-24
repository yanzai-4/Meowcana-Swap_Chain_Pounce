"""Icons, glyphs and small UI ornaments (hand-authored pixel grids, drawn 1:1; everything RGB565-exact)."""
from PIL import Image, ImageDraw, ImageOps

import icons
import ui
from icons import grid_image, L
from pal import P
from spec import CHARMS, ELEMENTS, LINKS, NODES, STATUSES


def lg(**kw):
    return {k: P[v] for k, v in kw.items()}


# ---------------------------------------------------------------- charms 8x8
CHARM8 = {
    "Catnip": (["...oo...",
                "..oggo..",
                ".ogghgo.",
                ".oggggo.",
                "..ogho..",
                "...oho..",
                "...oho..",
                "...ooo.."], lg(o="night0", g="earth1", h="earth2")),
    "Fish Bone": (["........",
                   "..o.o.o.",
                   ".owowowo",
                   "owwwwwwo",
                   ".owowowo",
                   "..o.o.o.",
                   "........",
                   "........"], lg(o="night0", w="moon")),
    "Paw Pad": (["oo.oo.oo",
                 "ppopopop",
                 "oo.oo.oo",
                 "..oppo..",
                 ".opppho.",
                 ".opppro.",
                 "..oooo..",
                 "........"], lg(o="night0", p="pink", h="moon", r="pink")),
    "Yarn": (["..oooo..",
              ".ovvvvo.",
              "ovwvovvo",
              "ovvovvvo",
              "ovovvwvo",
              "ovvvvvvo",
              ".ovvvvo.",
              "..oooo.."], lg(o="night0", v="purple", w="moon")),
    "Bell": (["...oo...",
              "..oggo..",
              ".oghggo.",
              ".ogggdo.",
              ".ogggdo.",
              "oggggddo",
              "oooooooo",
              "..oood.."], lg(o="night0", g="gold3", h="gold4", d="gold1")),
    "Moonlight": (["..oooo..",
                   ".owwwo..",
                   "owwo....",
                   "owo.....",
                   "owo.....",
                   "owwo..w.",
                   ".owwwwo.",
                   "..oooo.."], lg(o="night0", w="silver2")),
    "Nine Lives": (["o......o",
                    "oao..oao",
                    "oaaooaao",
                    "oaaaaaao",
                    "oanaanao",
                    ".oaaaao.",
                    "..oooo..",
                    "........"], lg(o="night0", a="amber2", n="night0")),
    "Rat Bite": (["........",
                  ".oo..oo.",
                  "orroorro",
                  "oorrrroo",
                  ".orwrwro",
                  ".orrrrro",
                  "..orrro.",
                  "...ooo.."], lg(o="night0", r="rat2", w="rat3")),
    "Fleas": (["........",
               "...oo...",
               "..orro..",
               ".orrrro.",
               ".orwrro.",
               "o.orro.o",
               ".o.oo.o.",
               "........"], lg(o="night0", r="red", w="pink")),
}
GEMCOL = {"Catnip": ("earth1", "earth2"), "Fish Bone": ("silver1", "moon"), "Paw Pad": ("pink", "moon"),
          "Yarn": ("purple", "moon"), "Bell": ("gold3", "gold4"), "Moonlight": ("water2", "moon"),
          "Nine Lives": ("amber2", "amber3"), "Rat Bite": ("rat2", "rat3"), "Fleas": ("red", "pink")}


def ui_charm():
    return [grid_image(*CHARM8[c]) for c in CHARMS]


def ui_gem():
    out = []
    for c in CHARMS:
        a, b = GEMCOL[c]
        out.append(grid_image(icons.GEM, L(o="night0", g=a, w=b)))
    return out


# ---------------------------------------------------------------- statuses 12x12
SINGE12 = ["....oo......",
           "...oyyo.....",
           "...oyyo..o..",
           "..oyYyyo.oo.",
           "..oyYYyoooyo",
           ".oyyYYyyoyyo",
           ".oyYYYYyyyyo",
           ".oyYYhYYyyyo",
           ".oyyYhhYyyao",
           "..oyyyyyyao.",
           "...oaaaaao..",
           "....ooooo..."]
PUFF12 = ["...oooooo...",
          "..oMMMMMMo..",
          ".oMMMMMMMMo.",
          "oMMkMMMMkMMo",
          "oMMMMMMMMMso",
          "oMMMMMMMMssso"[:12],
          "oMMMMMMMsssso"[:12],
          ".oMMMMMsssso",
          ".ooMMMssssoo"[:12],
          "..oossssssoo"[:12],
          "...o.oooo.o.",
          "............"]
DROWSY12 = ["oooooooooooo",
            "owwwwwwwwwwo",
            "oooooooowwwo",
            ".......owwo.",
            "......owwo..",
            ".....owwo...",
            "....owwo....",
            "...owwo.....",
            "..owwooooooo",
            "..owwwwwwwwo",
            "..oooooooooo",
            "............"]
CURL12 = ["gggggggggggg",
          "g..........g",
          "g.gggggggg.g",
          "g.g......g.g",
          "g.g.gggg.g.g",
          "g.g.g..g.g.g",
          "g.g.g.gg.g.g",
          "g.g.g....g.g",
          "g.g.ggggggg.",
          "g.g.........",
          "g.gggggggggg",
          "g..........."]
LEAP12 = ["....oooo....",
          "...oyyyyo...",
          "..oyyhyyyo..",
          ".oyyyhyyyyo.",
          "oooooyyyoooo",
          "....oyyyo...",
          "....oyyo....",
          "...oyyyo....",
          "..oyyyo.....",
          ".oyyyo......",
          ".oyyo.......",
          "..ooo......."]
STAT12 = {"singe": (SINGE12, lg(o="night0", y="amber2", Y="amber3", a="amber1", h="gold4")),
          "puff": (PUFF12, lg(o="night0", M="moon", s="silver1", k="night0")),
          "drowsy": (DROWSY12, lg(o="night0", w="water2")),
          "curl": (CURL12, lg(g="gold3")),
          "leap": (LEAP12, lg(o="night0", y="heal", h="moon"))}


def ui_status():
    out = []
    for s in STATUSES:
        rows, leg = STAT12[s]
        out.append(grid_image([r.ljust(12, ".")[:12] for r in rows], leg))
    return out


def ui_status_s():
    return [icons.status_icon(s) for s in STATUSES]


# ---------------------------------------------------------------- element icons
def ui_elem():
    return [icons.elem_icon(e, 9) for e in ELEMENTS]


def ui_elem_s():
    return [icons.elem_icon(e, 7) for e in ELEMENTS]


# ---------------------------------------------------------------- tiny glyphs
def ui_corner():
    return [icons.corner()]


def ui_diamond():
    return [icons.diamond("gold3"), icons.diamond("gold1")]


def ui_star():
    return [icons.star5("gold3"), icons.star5("night3")]


def ui_paw():
    return [icons.paw()]


def ui_heart():
    return [icons.heart()]


def ui_treat():
    rows = ["..ooooo..",
            ".oyyyyyo.",
            "oyhyyyyyo",
            "oyyyyyyyo",
            ".oyyyyyo.",
            "..ooooo.."]
    rows = ["...oo.oo.",
            "..oyyooyo",
            ".oyhyyyyo",
            "oyyyyyyo.",
            ".oyyyyoyo",
            "..oyyoooo",
            "...oo...."]
    fish = ["........o",
            "..ooo..oo",
            ".oyyyooyo",
            "oyhyyyyyo",
            ".oyyyoyyo",
            "..ooo.oo.",
            ".......o."]
    im = grid_image(fish, L(o="night0", y="amber2", h="gold4"))
    out = Image.new("RGBA", (9, 9), (0, 0, 0, 0))
    out.paste(im, (0, 1))
    return [out]


def ui_arrow():
    return [icons.arrow("silver2"), icons.arrow("amber3")]


def ui_tri_down():
    return [icons.tri_down("silver2"), icons.tri_down("amber3")]


def ui_btn():
    out = []
    for letter in "ABC":
        im = Image.new("RGB", (13, 13), P["night1"])
        ui.button_gem(im, 6, 6, letter)
        a = Image.new("L", (13, 13), 0)
        ImageDraw.Draw(a).ellipse([0, 0, 12, 12], fill=255)
        rgba = im.convert("RGBA")
        rgba.putalpha(a)
        out.append(rgba)
    return out


def ui_bracket():
    rows = ["aaaaaaa",
            "aaaaaaa",
            "aa.....",
            "aa.....",
            "aa.....",
            "aa.....",
            "aa....."]
    rows = ["aaaaaa.",
            "abbbbb.",
            "ab.....",
            "ab.....",
            "ab.....",
            "ab.....",
            "......."]
    return [grid_image(rows, lg(a="amber3", b="amber1"))]


def ui_moon_eye():
    frames = []
    for lid in (0, 1, 2):
        im = Image.new("RGB", (23, 23), P["night1"])
        ui.moon_eye(im, 11, 11, 11)
        rgba = im.convert("RGBA")
        a = Image.new("L", (23, 23), 0)
        ImageDraw.Draw(a).ellipse([0, 0, 22, 22], fill=255)
        rgba.putalpha(a)
        if lid:
            d = ImageDraw.Draw(rgba)
            # eyelid: gold field closes over the lens from top and bottom
            h = 3 if lid == 1 else 6
            for y in range(7, 7 + h):
                d.line([(4, y), (18, y)], fill=P["gold2"] + (255,))
                d.line([(4, 22 - y), (18, 22 - y)], fill=P["gold2"] + (255,))
            if lid == 2:
                d.line([(5, 11), (17, 11)], fill=P["night0"] + (255,))
                d.line([(5, 10), (17, 10)], fill=P["gold1"] + (255,))
        frames.append(rgba)
    return frames


def ui_moon_eye_s():
    im = Image.new("RGB", (15, 15), P["night1"])
    ui.moon_eye(im, 7, 7, 7)
    rgba = im.convert("RGBA")
    a = Image.new("L", (15, 15), 0)
    ImageDraw.Draw(a).ellipse([0, 0, 14, 14], fill=255)
    rgba.putalpha(a)
    return [rgba]


def ui_candle():
    out = []
    for tall in (5, 3):
        im = Image.new("RGB", (5, 20), P["night1"])
        ui.candle(im, 0, 19, 13, True, tall)
        rgba = im.convert("RGBA")
        px = rgba.load()
        for y in range(20):
            for x in range(5):
                if rgba.getpixel((x, y))[:3] == P["night1"]:
                    px[x, y] = (0, 0, 0, 0)
        out.append(rgba)
    return out


def ui_sparkle():
    out = []
    for c in ("moon", "silver1"):
        im = Image.new("RGBA", (5, 5), (0, 0, 0, 0))
        for x, y in ((2, 0), (2, 1), (2, 2), (2, 3), (2, 4), (0, 2), (1, 2), (3, 2), (4, 2)):
            im.putpixel((x, y), P["silver1"] + (255,) if (x, y) not in ((2, 2),) else P[c] + (255,))
        for x, y in ((2, 1), (1, 2), (3, 2), (2, 3)):
            im.putpixel((x, y), P[c] + (255,))
        out.append(im)
    return out


def ui_tut_arrow():
    up = ["....a....",
          "...aaa...",
          "..aaaaa..",
          ".aaaaaaa.",
          "...aba...",
          "...aba...",
          "...aba...",
          "...aba...",
          "...ooo..."]
    up = ["....o....",
          "...oao...",
          "..oaaao..",
          ".oaaaaao.",
          "ooooaoooo",
          "...oaao..",
          "...oaao..",
          "...oaao..",
          "....ooo.."]
    im = grid_image(up, lg(o="night0", a="amber3"))
    return [im, ImageOps.flip(im), im.rotate(90), im.rotate(-90)]


def _box(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def _disc(im, cx, cy, r, ring, fill):
    d = ImageDraw.Draw(im)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=P[ring] + (255,))
    d.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=P[fill] + (255,))


# ---------------------------------------------------------------- Night Path nodes 20x20
def _node_base(dim, ring="gold2", fill="night0"):
    im = _box(20, 20)
    if dim:
        ring, fill = "night3", "night1"
    ImageDraw.Draw(im).ellipse([0, 0, 19, 19], fill=P["night0"] + (255,))
    _disc(im, 9.5 if False else 10, 10, 9, ring, fill)
    return im


def _paste_grid(im, rows, leg, ox, oy):
    g = grid_image(rows, leg)
    im.alpha_composite(g, (ox, oy))


def node_icon(kind, dim):
    im = _node_base(dim, "gold2" if kind != "elite" and kind != "boss" else ("red" if kind == "elite" else "gold3"))
    c = (lambda k, dk="night4": dk if dim else k)
    if kind == "fight":
        d = ImageDraw.Draw(im)
        col = P[c("silver2")] + (255,)
        d.line([(6, 14), (14, 6)], fill=col, width=2)
        d.line([(6, 6), (14, 14)], fill=col, width=2)
        d.rectangle([4, 14, 6, 16], fill=P[c("gold3")] + (255,))
        d.rectangle([13, 14, 16, 16], fill=P[c("gold3")] + (255,))
    elif kind == "elite":
        rows = ["..ooooooo..",
                ".owwwwwwwo.",
                "owwwwwwwwwo",
                "owoowwwoowo",
                "owoowwwoowo",
                "owwwwowwwwo",
                ".owwwwwwwo.",
                "..owowowo..",
                "...ooooo..."]
        _paste_grid(im, rows, lg(o="night0", w=c("moon", "night4")), 4, 5)
        ImageDraw.Draw(im).point((8, 8), fill=P["red"] + (255,) if not dim else P["night3"] + (255,))
    elif kind == "stall":
        rows = ["..........",
                "rrwwrrwwrr",
                "rrwwrrwwrr",
                "oooooooooo",
                ".gg....gg.",
                ".gg.yy.gg.",
                ".gg.yy.gg.",
                ".gggggggg."]
        _paste_grid(im, rows, lg(o="night0", r=c("red", "night3"), w=c("moon", "night4"), g=c("gold1", "night2"),
                                 y=c("gold3", "night4")), 5, 6)
    elif kind == "encounter":
        d = ImageDraw.Draw(im)
        d.fontmode = "1"
        d.text((10, 11), "?", font=ui.font("Jersey10-Regular", 20), fill=P[c("gold4", "night4")] + (255,), anchor="mm")
    elif kind == "cat_bed":
        rows = ["..........",
                ".oooooooo.",
                "owwwwwwwwo",
                "owpppppwwo",
                "owppoppwwo",
                ".owwwwwwo.",
                "..oooooo.."]
        _paste_grid(im, rows, lg(o="night0", w=c("water1", "night3"), p=c("pink", "night4")), 5, 7)
        _paste_grid(im, ["www", "..w", ".w.", "www"], lg(w=c("silver2", "night4")), 13, 2)
    elif kind == "box":
        rows = ["oooooooooo",
                "oyyyyyyyyo",
                "oooooooooo",
                "oyyyyyyyyo",
                "oyyooooyyo",
                "oyyyyyyyyo",
                "oooooooooo"]
        _paste_grid(im, rows, lg(o="night0", y=c("amber2", "night3")), 5, 6)
        ImageDraw.Draw(im).point((10, 11), fill=P["night0"] + (255,))
    elif kind == "boss":
        rows = ["o...o...o",
                "ooo.oyo.ooo"[:9],
                "oyoooyooyo"[:9],
                "oyyyyyyyo",
                "oyyhyyhyo",
                "oyyyyyyyo",
                "ooooooooo"]
        rows = ["o...o...o",
                "oo.ooo.oo",
                "oyooyoyoo"[:9],
                "oyyyyyyyo",
                "oyhyyyhyo",
                "oyyyyyyyo",
                "ooooooooo"]
        rows = ["o...o...o",
                "oyo.oyo.oyo"[:9],
                "oyyoyyyoyy"[:9],
                "oyyyyyyyo",
                "oyyhyyhyo",
                "oyyyyyyyo",
                "ooooooooo"]
        _paste_grid(im, rows, lg(o="night0", y=c("gold3", "night4"), h=c("red", "night3")), 5, 6)
    return im


def ui_node():
    return [node_icon(k, False) for k in NODES]


def ui_node_dim():
    return [node_icon(k, True) for k in NODES]


# ---------------------------------------------------------------- Nine Bells
BELLG = ["......oo......",
         ".....oggo.....",
         "....oghggo....",
         "...oghgggdo...",
         "...ogggggdo...",
         "...ogggggdo...",
         "..oghggggddo..",
         "..ogggggggdo..",
         ".oggggggggddo.",
         ".oggggggggddo.",
         "oggggggggggddo",
         "oooooooooooooo",
         "....oodddoo...",
         ".....ooooo...."]


def ui_bell():
    rows = [r.ljust(14, ".") for r in BELLG]
    rows.append("..............")
    rows.append("..............")
    dark = grid_image(rows, lg(o="night0", g="night3", h="night4", d="night2"))
    lit = grid_image(rows, lg(o="night0", g="gold3", h="gold4", d="gold1"))
    # clapper glint on the lit bell
    lit.putpixel((6, 12), P["amber3"] + (255,))
    return [dark, lit]


# ---------------------------------------------------------------- reading links 9x9
LINKG = {
    "nuzzle": (["..oo.oo..",
                ".orroorro"[:9],
                "orhrrrrro"[:9],
                "orrrrrrro"[:9],
                ".orrrrro.",
                "..orrro..",
                "...oro...",
                "....o...."], lg(o="night0", r="red", h="pink")),
    "tail_tap": (["......ooo",
                  ".....oyyo",
                  "....oyyo.",
                  "...oyyo..",
                  "oo.oyo...",
                  "oyooyo...",
                  ".oyyo....",
                  "..oo....."], lg(o="night0", y="amber3")),
    "hiss": (["..o...o..",
              ".ooo.ooo.",
              "oyyyoyyyo",
              "oyyyyyyyo",
              ".oyoyoyo.",
              "..oyyyo..",
              ".ooyoyoo.",
              ".o.ooo.o."], lg(o="night0", y="fire2")),
    "step": (["........o",
              ".......oo",
              ".....ooyo",
              "....oyyyo",
              "..ooyyoo.",
              ".oyyyo...",
              "ooyyoo...",
              "oyyo....."], lg(o="night0", y="gold3")),
    "mirror": (["...ooo...",
                "..owwwo..",
                ".owcwwwo.",
                ".owwwwwo.",
                "..owwwo..",
                "...ooo...",
                "...oyo...",
                "..ooyoo.."], lg(o="night0", w="silver2", c="moon", y="gold2")),
    "litter": (["..o...o..",
                ".opo.opo.",
                "..o...o..",
                "....o....",
                "...opo...",
                "....o....",
                ".o.....o.",
                "opo...opo"], lg(o="night0", p="pink")),
    "journey": (["...ooo...",
                 "..oyyyo..",
                 ".oyhyyyo.",
                 ".oyyyyyo.",
                 "..oyyyo..",
                 "...ooo...",
                 "..o...o..",
                 ".oyo.oyo."], lg(o="night0", y="gold3", h="gold4")),
}


def ui_link():
    out = []
    for k in LINKS:
        rows, leg = LINKG[k]
        out.append(grid_image([r.ljust(9, ".") for r in rows] + ["........."] * (9 - len(rows)), leg))
    return out


def ui_star_dust():
    return [ui.star_tile().convert("RGBA")]


def ui_plaque_fight():
    out = []
    for focus in (False, True):
        im = Image.new("RGB", (92, 64), P["night1"])
        edge = "amber3" if focus else "gold2"
        ui.rect(im, 0, 0, 91, 63, P["night0"])
        ui.frame(im, 0, 0, 91, 63, P["gold1" if not focus else "amber1"])
        ui.frame(im, 2, 2, 89, 61, P[edge])
        ui.rect(im, 3, 3, 88, 60, P["night2" if not focus else "night2"])
        ui.corners(im, 0, 0, 91, 63, "gold3" if not focus else "amber3", "gold1" if not focus else "amber1")
        ui.moon_eye(im, 46, 21, 11)
        w = ui.text_w("Fight", ui.TITLE())
        ui.text(im, 46 - w // 2, 55, "Fight", P["gold4"] if focus else P["gold3"], ui.TITLE(), shadow=P["night0"])
        rgba = im.convert("RGBA")
        out.append(rgba)
    return out


GENERATORS = {
    "ui_corner": ui_corner, "ui_diamond": ui_diamond, "ui_star": ui_star, "ui_gem": ui_gem, "ui_charm": ui_charm,
    "ui_elem": ui_elem, "ui_elem_s": ui_elem_s, "ui_status": ui_status, "ui_status_s": ui_status_s,
    "ui_paw": ui_paw, "ui_heart": ui_heart, "ui_treat": ui_treat, "ui_arrow": ui_arrow,
    "ui_tri_down": ui_tri_down, "ui_btn": ui_btn, "ui_bracket": ui_bracket, "ui_moon_eye": ui_moon_eye,
    "ui_moon_eye_s": ui_moon_eye_s, "ui_candle": ui_candle, "ui_sparkle": ui_sparkle,
    "ui_plaque_fight": ui_plaque_fight, "ui_tut_arrow": ui_tut_arrow, "ui_node": ui_node,
    "ui_node_dim": ui_node_dim, "ui_bell": ui_bell, "ui_link": ui_link, "ui_star_dust": ui_star_dust,
}
