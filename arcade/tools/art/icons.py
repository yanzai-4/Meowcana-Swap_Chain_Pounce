"""Hand-authored pixel glyphs (string grids) for Moonlit Grimoire. Every glyph is drawn 1:1 in code."""
from PIL import Image
from pal import P

P["royal"] = (49, 36, 140)   # 0x3131 fast colour
P["royal0"] = (26, 20, 90)
P["royal1"] = (74, 58, 172)
from pal import snap
for _k in ("royal", "royal0", "royal1"):
    P[_k] = snap(P[_k])


def grid_image(rows, legend):
    w = max(len(r) for r in rows)
    im = Image.new("RGBA", (w, len(rows)), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in legend:
                im.putpixel((x, y), tuple(legend[ch]) + (255,))
    return im


def L(**kw):
    return {k: P[v] for k, v in kw.items()}


# ---------------------------------------------------------------- elements 9x9 (icon) and 7x7 (pip)
FIRE9 = ["....o....",
         "...oro...",
         "...orlo..",
         "..orllro.",
         ".orllyylo",
         ".orlyyylo",
         ".orryyyro",
         "..orrrro.",
         "...oooo.."]
AIR9 = ["......ooo",
"....oocwo",
"...occcco",
"..occwcco",
".occcwco.",
"occcwco..",
"ocwcco...",
"oo.oo....",
"o........"]
WATER9 = ["....o....",
          "...obo...",
          "...obo...",
          "..obbbo..",
          ".obwbbbbo",
          ".obwwbbbo",
          ".obbbbbbo",
          "..obbbbo.",
          "...ooooo."]
EARTH9 = ["...w.w...",
"....w....",
"..ooooo..",
".ogwgggo.",
"ogwggggdo",
"ogggggddo",
".odddddo.",
"..ooooo..",
"........."]
FIRE7 = ["...o...",
         "..olo..",
         "..orlo.",
         ".orlyro",
         ".orlyro",
         ".orrrro",
         "..ooo.."]
AIR7 = ["....ooo",
"..oocwo",
".occcco",
"occwco.",
"ocwco..",
"oo.o...",
"o......"]
WATER7 = ["...o...",
          "..obo..",
          "..obo..",
          ".obbbo.",
          ".obwbo.",
          ".obbbo.",
          "..ooo.."]
EARTH7 = ["..w.w..",
"...w...",
".ooooo.",
"ogwggdo",
"oggggdo",
".odddo.",
"..ooo.."]


def elem_legend(e):
    d = {"o": P["night0"]}
    if e == "fire":
        d.update(r=P["fire1"], l=P["fire2"], y=P["amber3"])
    elif e == "air":
        d.update(c=P["air1"], w=P["air2"])
    elif e == "water":
        d.update(b=P["water1"], w=P["water2"])
    else:
        d.update(g=P["earth1"], w=P["earth2"], d=P["earth0"])
    return d


ELEM9 = {"fire": FIRE9, "air": AIR9, "water": WATER9, "earth": EARTH9}
ELEM7 = {"fire": FIRE7, "air": AIR7, "water": WATER7, "earth": EARTH7}


def elem_icon(e, size=9, reversed_=False):
    rows = (ELEM9 if size == 9 else ELEM7)[e]
    leg = elem_legend(e)
    if reversed_:
        # cool, desaturated tint for reversed pips
        leg = dict(leg)
        for k, v in list(leg.items()):
            if k != "o":
                leg[k] = P["moon"] if k in "wy" else P["silver2"] if k == "l" else P["rair1"]
    return grid_image(rows, leg)


# ---------------------------------------------------------------- statuses 9x9
SINGE = ["....o....",
         "...oyo...",
         "...oyo...",
         ".ooayaoo.",
         "oyyyYyyyo",
         ".ooayaoo.",
         "...oyo...",
         "...oyo...",
         "....o...."]
PUFF = ["..ooooo..",
        ".oMMMMso.",
        "oMMMMMMso",
        "oMMMMMsso",
        "oMMMMssso",
        "oMMMsssso",
        ".oMsssso.",
        "..ooooo..",
        "........."]
DROWSY = ["ooooooooo",
          "owwwwwwwo",
          "ooooooowo",
          ".....owo.",
          "....owo..",
          "...owo...",
          ".owo.....",
          "owwwwwwwo",
          "ooooooooo"]
CURL = ["ggggggggg",
        "g.......g",
        "g.ggggg.g",
        "g.g...g.g",
        "g.g.g.g.g",
        "g.g.ggg.g",
        "g.g.....g",
        "g.ggggggg",
        "g........"]
LEAP = ["....o....",
        "...oyo...",
        "..oyyyo..",
        ".oyyyyyo.",
        "ooooyoooo",
        "....yo...",
        "...oyo...",
        "..oyo....",
        "..ooo...."]
STATUS = {
    "singe": (SINGE, L(o="night0", y="amber2", Y="amber3", a="amber1")),
    "puff": (PUFF, L(o="night0", M="moon", s="silver1")),
    "drowsy": (DROWSY, L(o="night0", w="water2")),
    "curl": (CURL, L(g="gold3")),
    "leap": (LEAP, L(o="night0", y="heal")),
}


def status_icon(name):
    rows, leg = STATUS[name]
    return grid_image(rows, leg)


# ---------------------------------------------------------------- charms 11x11
CATNIP = ["........oo.",
          ".......ogho",
          ".oo...ogggo",
          "ogho.ogggo.",
          "oggggoggo..",
          ".oggggoo...",
          "..ogggo....",
          "...ooho....",
          "....oho....",
          "....oho....",
          "....ooo...."]
BELL = [".....o.....",
        "....ooo....",
        "...ohhgo...",
        "..ohgggdo..",
        "..ogggggdo.",
        "..ogggggdo.",
        ".oggggggdgo",
        ".ooooooooo.",
        "...oodoo...",
        "....ooo....",
        "..........."]
NINE = ["oo.......oo",
        "oAo.....oAo",
        "oAAoooooAAo",
        "oAAAAAAAAAo",
        "oAhAAAAAAAo",
        "oAeeAAAeeAo",
        "oAAAAnAAAAo",
        ".oAAAAAAAo.",
        "..ooAAAoo..",
        "....ooo....",
        "..........."]
CHARM = {
    "catnip": (CATNIP, L(o="night0", g="earth1", h="earth2")),
    "bell": (BELL, L(o="night0", g="gold3", h="gold4", d="gold1")),
    "nine": (NINE, L(o="night0", A="amber2", h="amber3", e="night0", n="pink")),
}


def charm_icon(name):
    rows, leg = CHARM[name]
    im = grid_image(rows, leg)
    return im


GEM = ["..o..", ".ogo.", "ogwgo", ".ogo.", "..o.."]
GEM_COL = {"catnip": ("earth1", "earth2"), "bell": ("gold3", "gold4"), "nine": ("amber1", "amber3")}


def gem(name):
    a, b = GEM_COL[name]
    return grid_image(GEM, L(o="night0", g=a, w=b))


STAR5 = [".....", "..g..", ".ggg.", "ggggg", ".g.g."]
STAR5 = ["..g..", ".ggg.", "ggggg", ".ggg.", ".g.g."]


def star5(col="gold3", edge="night0"):
    return grid_image(STAR5, {"g": P[col]})


# ---------------------------------------------------------------- UI glyphs
PAW = ["....XXX.XXX....",
       "....XaX.XaX....",
       "XXX.XaX.XaX.XXX",
       "XaX.XXX.XXX.XaX",
       "XaX.........XaX",
       "XXXXXXXXXXXXXXX",
       "XXXaaaaaaaaaXXX",
       ".XXaalaaaaaaXX.",
       "..XaaaaaaaaaX..",
       "..XaaaaaaaaaX..",
       "...XXaaaaaXX...",
       ".....XXXXX....."]
PAW = ["....XXX.XXX....",
       "....XaX.XaX....",
       "XXX.XaX.XaX.XXX",
       "XaX.XXX.XXX.XaX",
       "XaXXXaaXaaXXXaX",
       "XXXaaaaaaaaaXXX",
       ".XXaalaaaaaaXX.",
       "..XaaaaaaaaaX..",
       "..XaaaaaaaaaX..",
       "...XXaaaaaXX...",
       ".....XXXXX....."]


def paw():
    return grid_image(PAW, L(X="night0", a="amber2", l="amber3"))


CORNER = ["gggggggggg",
          "gHHHHHHHHH",
          "gH........",
          "gH.gggg...",
          "gH.g......",
          "gH.g.hh...",
          "gH.g.h....",
          "gH.g......",
          "gH........",
          "gH........"]


def corner(col_a="gold2", col_b="gold1"):
    return grid_image(CORNER, {"g": P[col_a], "H": P[col_b], "h": P[col_a]})


def _c(col):
    return col if isinstance(col, tuple) else P[col]


TRI_DOWN = ["ooooooo", ".ooooo.", "..ooo..", "...o..."]
ARROW = ["....o....", ".....o...", "ooooooo..", ".....o...", "....o...."]


def arrow(col):
    return grid_image(["....o..", ".....o.", "ooooooo", ".....o.", "....o.."], {"o": _c(col)})


def tri_down(col):
    return grid_image(["ooooooo", ".ooooo.", "..ooo..", "...o..."], {"o": _c(col)})


def dot(col):
    return grid_image(["oo", "oo"], {"o": _c(col)})


def diamond(col):
    return grid_image(["..o..", ".ooo.", "ooooo", ".ooo.", "..o.."], {"o": _c(col)})


HEART9 = [".ooo.ooo.",
          "oRRRoRRRo",
          "oRhRRRRRo",
          "oRRRRRRRo",
          ".oRRRRRo.",
          "..oRRRo..",
          "...oRo...",
          "....o....",
          "........."]
TREAT9 = ["..oooo.o.",
          ".oyyyyooo",
          "oyhyyyyyo",
          ".oyyyyooo",
          "..oooo.o."]


def heart():
    return grid_image(HEART9, L(o="night0", R="red", h="amber3"))


def treat():
    return grid_image(TREAT9, L(o="night0", y="amber2", h="gold4"))
