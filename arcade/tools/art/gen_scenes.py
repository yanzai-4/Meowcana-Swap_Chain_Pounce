"""Full-screen and stage backdrops. Flat areas dominate (byte-RLE friendly); busy detail stays away from the zones
where sprites or UI redraw. Everything uses only the Moonlit palette (RGB565-exact)."""
import math
import random

from PIL import Image, ImageDraw

import icons
import ui
from pal import P
from ui import frame, paste, px, rect

W, H = 480, 320

# ---- coordinates other scenes rely on (also written to docs/assets.md) -------------------------------------------
ATTIC_FLOOR = 196
PARLOR_BELLS = [(292 + 20 * i, 66) for i in range(9)]          # top-left of each ui_bell (14x16)
PATH_STEP_X = [44 + 62 * i for i in range(6)] + [428]            # sockets x for steps 0-5 and the boss
PATH_Y, PATH_FORK_Y = 168, (128, 208)
DOC_LINES = [
    "- `bg_attic` (480x232): wall `night1` (0x2929); floor strip y 196-231 is flat `night0` (0x1044) with only a 1-px "
    "`gold0` edge on y 196; hero feet at y 222. Domino zone x 24-172, enemy zone x 268-472. To erase a sprite "
    "restore with `asset_region(BG_ATTIC, 0, x, y, x, y, w, h)` (always exact); a flat `night0` fill is also exact "
    "for the part of a sprite rectangle below y 197. The top 30 rows are flat `night1` (the UI plate covers them).",
    "- `bg_title`: the menu band y 232-319 is flat `night1`. Logo, moon and window occupy y 0-231.",
    "- `bg_parlor`: floor band y 232-319 is flat dark wood (`night0`); Granny Oriel and the table are "
    "baked. Nine Bells rail: draw `ui_bell` (14x16) frame 0/1 at these top-left positions: "
    + ", ".join(f"({x},{y})" for x, y in PARLOR_BELLS) + ". The rail art underneath is baked for all nine hooks.",
    "- `bg_path`: top band y 0-47 flat `night1` (UI title). Step sockets (ring r=11, `ui_node` 20x20 centers on them): "
    f"x = {PATH_STEP_X[:6]} for steps 0-5, boss socket x = {PATH_STEP_X[6]} (ring r=15); road y = {PATH_Y}; the two "
    f"choice rings of a step sit at (x, {PATH_FORK_Y[0]}) and (x, {PATH_FORK_Y[1]}); dotted connectors are baked.",
    "- `bg_end`: text band y 236-319 flat `night1`.",
]


def snap_rgb(im):
    return im.convert("RGBA")


def dust(im, box, seed, n, cols=("night2", "night3", "night3", "night4", "silver1")):
    x0, y0, x1, y1 = box
    rnd = random.Random(seed)
    for _ in range(n):
        x, y = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        col = rnd.choice(cols)
        px(im, x, y, P[col])
        if col == "silver1" and rnd.random() < 0.7:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if x0 <= x + dx < x1 and y0 <= y + dy < y1:
                    px(im, x + dx, y + dy, P["night3"])


def halo(im, cx, cy, r, bg="night1", col="night2", rx=None):
    rx = rx or r
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            if 0 <= x < im.width and 0 <= y < im.height:
                dist = (((x - cx) / (rx / r)) ** 2 + (y - cy) ** 2) ** 0.5
                if dist < r and (x + y) % 2 == 0 and im.getpixel((x, y)) == P[bg]:
                    im.putpixel((x, y), P[col])


def arch_window(im, x0, x1, ytop, ybot, sky="royal0", wood="gold0", rim="gold1"):
    d = ImageDraw.Draw(im)
    hw = (x1 - x0) // 2
    cx = (x0 + x1) // 2
    d.rectangle([x0 - 4, ytop + hw, x1 + 4, ybot + 4], fill=P[wood])
    d.ellipse([x0 - 4, ytop - 4, x1 + 4, ytop + 2 * hw + 4], fill=P[wood])
    d.rectangle([x0, ytop + hw, x1, ybot], fill=P[sky])
    d.ellipse([x0, ytop, x1, ytop + 2 * hw], fill=P[sky])
    d.arc([x0, ytop, x1, ytop + 2 * hw], 180, 360, fill=P[rim])
    d.line([(x0, ytop + hw), (x0, ybot)], fill=P[rim])
    d.line([(x1, ytop + hw), (x1, ybot)], fill=P[rim])
    return cx


def sill(im, x0, x1, y):
    rect(im, x0 - 10, y, x1 + 10, y + 4, P["gold1"])
    rect(im, x0 - 10, y, x1 + 10, y, P["gold2"])
    rect(im, x0 - 10, y + 5, x1 + 10, y + 6, P["night0"])


def crescent_sky(im, cx, cy, r, sky="royal0", stars=()):
    ui.crescent(im, cx, cy, r, "silver2", sky, dx=max(3, r // 2))
    for sx, sy in stars:
        px(im, sx, sy, P["moon"])
    ui.sparkle(im, cx - r - 6, cy + 2, "silver2", 2)


def roof_silhouette(im, x0, x1, y):
    d = ImageDraw.Draw(im)
    d.polygon([(x0, y + 20), (x0, y + 8), (x0 + (x1 - x0) // 4, y), (x0 + (x1 - x0) // 2, y + 10),
               (x0 + 3 * (x1 - x0) // 4, y + 2), (x1, y + 9), (x1, y + 20)], fill=P["night0"])


def cat_silhouette(im, x, y, ear_hat=False):
    """Tiny sitting cat silhouette (night0), feet at (x, y)."""
    d = ImageDraw.Draw(im)
    d.ellipse([x - 4, y - 9, x + 4, y], fill=P["night0"])
    d.ellipse([x - 3, y - 15, x + 3, y - 8], fill=P["night0"])
    d.polygon([(x - 3, y - 12), (x - 3, y - 18), (x, y - 14)], fill=P["night0"])
    d.polygon([(x + 3, y - 12), (x + 3, y - 18), (x, y - 14)], fill=P["night0"])
    d.line([(x + 4, y - 2), (x + 9, y - 6), (x + 8, y - 12)], fill=P["night0"], width=2)
    px(im, x - 2, y - 11, P["amber3"])
    px(im, x + 2, y - 11, P["amber3"])
    if ear_hat:
        d.polygon([(x - 4, y - 14), (x + 4, y - 14), (x + 1, y - 26)], fill=P["night0"])
        px(im, x, y - 19, P["gold3"])


def logo(im, cx, y, s, f, k, col, edge, shadow):
    ui.scaled_text(im, cx + k, y + k, s, P[shadow], f, k, outline=P[shadow], anchor="m")
    ui.scaled_text(im, cx, y, s, P[col], f, k, outline=P["night0"], anchor="m")
    # inner highlight: re-draw the glyphs without outline in a lighter tone on the upper rows
    return None


# ---------------------------------------------------------------- bg_attic
def attic():
    im = Image.new("RGB", (480, 232), P["night1"])
    floor, bottom = ATTIC_FLOOR, 232
    d = ImageDraw.Draw(im)
    dust(im, (0, 38, 480, floor - 4), 3, 46, ("night2", "night2", "night3"))
    # wall seams only in the calm middle (away from the fighters)
    for x in (212, 276):
        rect(im, x, 66, x, floor - 1, P["night0"])
        for y in range(76, floor, 26):
            px(im, x + 1, y, P["night2"])
            px(im, x + 1, y + 1, P["night2"])
    # rafters
    rect(im, 0, 30, 479, 36, P["gold0"])
    rect(im, 0, 36, 479, 36, P["night0"])
    rect(im, 0, 30, 479, 30, P["gold1"])
    d.polygon([(0, 36), (0, 62), (6, 62), (60, 36)], fill=P["gold0"])
    d.line([(0, 62), (58, 36)], fill=P["night0"])
    d.polygon([(480, 36), (480, 62), (474, 62), (420, 36)], fill=P["gold0"])
    d.line([(479, 62), (418, 36)], fill=P["night0"])
    # moonbeam (flat polygon)
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
    # shelves + jars (right edge)
    for sy in (112, 160):
        rect(im, 446, sy, 479, sy + 3, P["gold0"])
        rect(im, 446, sy + 3, 479, sy + 3, P["night0"])
        rect(im, 448, sy + 4, 449, sy + 10, P["gold0"])
    for jx, jy, col in ((450, 112, "earth0"), (462, 112, "amber0"), (472, 112, "rat1"), (452, 160, "water0"),
                        (466, 160, "fire0")):
        h = 14
        rect(im, jx, jy - h, jx + 8, jy - 1, P[col])
        rect(im, jx + 1, jy - h, jx + 7, jy - h, P["gold1"])
        rect(im, jx + 1, jy - h + 3, jx + 2, jy - 3, P["night3"])
    # flat floor strip
    rect(im, 0, floor, 479, bottom - 1, P["night0"])
    rect(im, 0, floor, 479, floor, P["gold0"])
    # book stack + candle between the fighters
    rect(im, 232, 200, 258, 211, P["fire0"]); rect(im, 232, 200, 258, 200, P["fire1"]); rect(im, 232, 205, 258, 205, P["gold1"])
    rect(im, 236, 192, 256, 199, P["water0"]); rect(im, 236, 192, 256, 192, P["water1"]); rect(im, 240, 196, 252, 196, P["gold1"])
    ui.candle(im, 244, 191, 10)
    for yy in range(160, 192):
        for xx in range(216, 274):
            dist = ((xx - 246) ** 2 + (yy - 172) ** 2) ** 0.5
            if dist < 26 and (xx + yy) % 2 == 0 and im.getpixel((xx, yy)) == P["night1"]:
                im.putpixel((xx, yy), P["night2"])
    return [im.convert("RGBA")]


# ---------------------------------------------------------------- bg_title
def title():
    im = Image.new("RGB", (W, H), P["night1"])
    d = ImageDraw.Draw(im)
    dust(im, (0, 0, W, 232), 5, 70)
    # curtains (royal) at both sides, narrow so the wordmark has the full width
    CW = 36
    for side in (0, 1):
        x0 = 0 if side == 0 else W - CW
        rect(im, x0, 0, x0 + CW - 1, 231, P["royal0"])
        for i in range(0, CW, 8):
            xx = x0 + i
            rect(im, xx + 2, 0, xx + 3, 231, P["royal"])
            rect(im, xx + 3, 0, xx + 3, 231, P["royal1"])
        edge = x0 + CW - 1 if side == 0 else x0
        rect(im, edge, 0, edge, 231, P["gold1"])
        rect(im, x0, 0, x0 + CW - 1, 3, P["gold2"])
    # tie-backs
    for x0 in (14, W - 22):
        rect(im, x0 - 4, 96, x0 + 12, 99, P["gold2"])
        rect(im, x0 - 4, 99, x0 + 12, 99, P["gold0"])
        paste(im, icons.diamond("gold3"), x0 + 2, 94)
    # arched window with the cat-eye moon
    cx = 240
    arch_window(im, cx - 56, cx + 56, 8, 112, "royal0")
    dust(im, (cx - 54, 14, cx + 54, 110), 21, 18, ("night3", "night4", "silver1", "moon"))
    ui.moon_eye(im, cx, 54, 28)
    rect(im, cx - 56, 112, cx + 56, 118, P["gold1"])
    rect(im, cx - 56, 112, cx + 56, 112, P["gold2"])
    rect(im, cx - 56, 119, cx + 56, 120, P["night0"])
    roof_silhouette(im, cx - 56, cx + 56, 96)
    cat_silhouette(im, cx - 30, 108)
    cat_silhouette(im, cx + 24, 108, ear_hat=True)
    # logo: single wide wordmark with a gold ramp (shadow, ink outline, face, highlight row)
    lf = ui.TITLE()
    k, base = 4, 204
    logo(im, cx + 3 * k + 4, base, "Meowcana", lf, k, "gold3", "gold1", "gold0")
    face = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ui.scaled_text(face, cx + 3 * k + 4, base, "Meowcana", P["gold4"], lf, k, anchor="m")
    for y in range(H):                      # lighter top rows, darker belly, so the wordmark reads as embossed
        for x in range(W):
            if face.getpixel((x, y))[3]:
                if y < base - 44:
                    im.putpixel((x, y), P["gold4"])
                elif y > base - 8:
                    im.putpixel((x, y), P["gold2"])
    # divider flourish beneath the wordmark
    rect(im, cx - 120, 214, cx - 12, 214, P["gold1"])
    rect(im, cx + 12, 214, cx + 120, 214, P["gold1"])
    rect(im, cx - 120, 215, cx - 12, 215, P["gold0"])
    rect(im, cx + 12, 215, cx + 120, 215, P["gold0"])
    paste(im, icons.diamond("gold3"), cx - 2, 212)
    paste(im, icons.diamond("gold1"), cx - 128, 212)
    paste(im, icons.diamond("gold1"), cx + 124, 212)
    # letter-spaced subtitle
    sub = "Swap. Chain. Pounce."
    bf = ui.BODY()
    sw = sum(ui.text_w(ch, bf) + 2 for ch in sub) - 2
    sx = cx - sw // 2
    for ch in sub:
        ui.text(im, sx, 230, ch, P["silver2"], bf)
        sx += ui.text_w(ch, bf) + 2
    # flat menu band (fast fill colour)
    rect(im, 0, 232, W - 1, H - 1, P["night1"])
    return [im.convert("RGBA")]


# ---------------------------------------------------------------- bg_parlor
def granny(im, cx, base):
    """Granny Oriel asleep over the table: shawl, bun, glasses, folded arms. cx center, base = table top y."""
    d = ImageDraw.Draw(im)
    # chair back
    d.rounded_rectangle([cx - 52, base - 100, cx + 52, base + 4], radius=14, fill=P["amber0"])
    d.rounded_rectangle([cx - 46, base - 94, cx + 46, base - 4], radius=11, fill=P["gold0"])
    d.arc([cx - 46, base - 94, cx + 46, base - 10], 200, 340, fill=P["gold1"])
    # shawl over shoulders (upright, seated)
    d.ellipse([cx - 42, base - 52, cx + 42, base + 14], fill=P["night0"])
    d.ellipse([cx - 40, base - 50, cx + 40, base + 12], fill=P["royal1"])
    d.ellipse([cx - 32, base - 44, cx + 32, base + 12], fill=P["royal"])
    for i in range(-3, 4):
        d.line([(cx + i * 9, base - 36), (cx + i * 11, base + 4)], fill=P["royal0"])
    for sx, sy in ((cx - 26, base - 24), (cx + 20, base - 20), (cx - 8, base - 12), (cx + 30, base - 30)):
        px(im, sx, sy, P["gold3"])
        px(im, sx + 1, sy, P["gold2"])
    # shawl collar V
    d.polygon([(cx - 14, base - 50), (cx + 14, base - 50), (cx, base - 30)], fill=P["night0"])
    d.polygon([(cx - 12, base - 50), (cx + 12, base - 50), (cx, base - 33)], fill=P["gold1"])
    # bun with moon hairpin
    d.ellipse([cx - 11, base - 102, cx + 11, base - 82], fill=P["night0"])
    d.ellipse([cx - 9, base - 100, cx + 9, base - 84], fill=P["silver2"])
    d.line([(cx - 5, base - 96), (cx + 5, base - 92)], fill=P["silver1"])
    d.line([(cx - 5, base - 92), (cx + 5, base - 96)], fill=P["silver1"])
    d.ellipse([cx + 4, base - 100, cx + 10, base - 94], fill=P["moon"])
    d.ellipse([cx + 6, base - 101, cx + 12, base - 95], fill=P["gold0"])
    # head: white hair, face, outline
    d.ellipse([cx - 25, base - 92, cx + 25, base - 40], fill=P["night0"])
    d.ellipse([cx - 23, base - 90, cx + 23, base - 42], fill=P["silver2"])      # hair
    d.ellipse([cx - 18, base - 82, cx + 18, base - 40], fill=P["pink"])         # face
    d.rectangle([cx - 18, base - 82, cx + 18, base - 78], fill=P["silver2"])
    d.ellipse([cx - 19, base - 90, cx + 19, base - 74], fill=P["silver2"])      # hairline fringe
    d.rectangle([cx - 17, base - 77, cx + 17, base - 75], fill=P["pink"])
    # closed eyes inside round glasses
    for ex in (cx - 9, cx + 9):
        d.ellipse([ex - 7, base - 73, ex + 7, base - 59], outline=P["gold3"])
        d.arc([ex - 4, base - 70, ex + 4, base - 62], 20, 160, fill=P["night0"])
    d.line([(cx - 2, base - 66), (cx + 2, base - 66)], fill=P["gold3"])
    # cheeks, nose, soft smile
    px(im, cx - 13, base - 55, P["fire2"])
    px(im, cx - 12, base - 55, P["fire2"])
    px(im, cx + 12, base - 55, P["fire2"])
    px(im, cx + 13, base - 55, P["fire2"])
    px(im, cx, base - 60, P["amber1"])
    d.arc([cx - 6, base - 57, cx + 6, base - 49], 20, 160, fill=P["night0"])
    # hands folded on the table holding a tarot card
    d.ellipse([cx - 22, base - 20, cx + 22, base + 4], fill=P["night0"])
    d.ellipse([cx - 20, base - 18, cx + 20, base + 2], fill=P["royal1"])
    d.rectangle([cx - 5, base - 26, cx + 5, base - 8], fill=P["night0"])
    d.rectangle([cx - 4, base - 25, cx + 4, base - 9], fill=P["moon"])
    px(im, cx, base - 17, P["gold2"])
    d.ellipse([cx - 14, base - 14, cx - 3, base - 5], fill=P["night0"])
    d.ellipse([cx - 13, base - 13, cx - 4, base - 6], fill=P["pink"])
    d.ellipse([cx + 3, base - 14, cx + 14, base - 5], fill=P["night0"])
    d.ellipse([cx + 4, base - 13, cx + 13, base - 6], fill=P["pink"])
    # Zz
    z = ["wwww", "..w.", ".w..", "wwww"]
    paste(im, icons.grid_image(z, {"w": P["silver2"]}), cx + 44, base - 86)
    big = icons.grid_image(["wwwwww", "....w.", "...w..", "..w...", ".w....", "wwwwww"], {"w": P["moon"]})
    paste(im, big, cx + 54, base - 104)


def parlor():
    im = Image.new("RGB", (W, H), P["night1"])
    d = ImageDraw.Draw(im)
    floor_y, wain = 232, 176
    dust(im, (0, 0, W, wain), 9, 50)
    # wallpaper stripes
    for x in range(8, W, 32):
        rect(im, x, 0, x, wain - 1, P["night2"])
    # wainscot
    rect(im, 0, wain, W - 1, floor_y - 1, P["night0"])
    rect(im, 0, wain, W - 1, wain, P["gold1"])
    rect(im, 0, wain + 1, W - 1, wain + 1, P["gold0"])
    for x in range(0, W, 48):
        frame(im, x + 6, wain + 8, x + 41, floor_y - 8, P["night2"])
    # floor: flat dark wood band (menu zone)
    rect(im, 0, floor_y, W - 1, H - 1, P["night0"])
    rect(im, 0, floor_y, W - 1, floor_y, P["gold0"])
    # window with moon (left)
    wx0, wx1 = 28, 108
    arch_window(im, wx0, wx1, 24, 150, "royal0")
    crescent_sky(im, 70, 62, 13, "royal0", ((44, 50), (90, 44), (52, 96), (84, 108), (96, 80), (40, 120)))
    rect(im, 67, 24, 68, 150, P["gold1"])
    rect(im, wx0, 88, wx1, 89, P["gold1"])
    sill(im, wx0, wx1, 154)
    # Nine Bells rail (right): board, nine brass hooks, tiny plaque
    rail_x0, rail_x1 = PARLOR_BELLS[0][0] - 14, PARLOR_BELLS[-1][0] + 28
    rect(im, rail_x0, 52, rail_x1, 62, P["gold0"])
    rect(im, rail_x0, 52, rail_x1, 53, P["gold1"])
    rect(im, rail_x0, 62, rail_x1, 62, P["night0"])
    for x, y in PARLOR_BELLS:
        rect(im, x + 6, 62, x + 7, 66, P["gold2"])
        px(im, x + 6, 62, P["gold4"])
    # shelf with books under the rail (decor, right)
    rect(im, rail_x0 + 8, 126, rail_x1 - 8, 129, P["gold0"])
    for i, (bw, col) in enumerate(((7, "fire0"), (6, "water0"), (8, "earth0"), (6, "amber0"), (7, "royal1"),
                                    (6, "fire0"), (8, "water0"))):
        bx = rail_x0 + 14 + sum(((7, 6, 8, 6, 7, 6, 8)[:i]))+ i * 2
        rect(im, bx, 108 + (i % 3) * 2, bx + bw - 1, 125, P[col])
        rect(im, bx, 108 + (i % 3) * 2, bx, 125, P["night0"])
        rect(im, bx + 1, 112 + (i % 3) * 2, bx + bw - 2, 112 + (i % 3) * 2, P["gold1"])
    # reading table with cloth and a candle (center)
    tcx, ty = 236, 196
    granny(im, tcx, ty)
    d.ellipse([tcx - 110, ty - 8, tcx + 110, ty + 24], fill=P["night0"])
    d.ellipse([tcx - 108, ty - 6, tcx + 108, ty + 20], fill=P["royal"])
    d.ellipse([tcx - 108, ty - 6, tcx + 108, ty + 10], fill=P["royal1"])
    d.arc([tcx - 100, ty - 3, tcx + 100, ty + 14], 10, 170, fill=P["gold2"])
    for x in range(tcx - 104, tcx + 105, 8):
        yy = ty + 16 - int(((x - tcx) / 108.0) ** 2 * 6)
        rect(im, x, yy + 3, x + 1, yy + 6, P["gold2"])
    rect(im, tcx - 84, ty + 22, tcx - 78, floor_y + 20, P["gold0"])
    rect(im, tcx + 78, ty + 22, tcx + 84, floor_y + 20, P["gold0"])
    # crystal ball and candle on the cloth
    d.ellipse([tcx + 58, ty - 24, tcx + 80, ty - 2], fill=P["night0"])
    d.ellipse([tcx + 59, ty - 23, tcx + 79, ty - 3], fill=P["water1"])
    d.ellipse([tcx + 62, ty - 20, tcx + 70, ty - 12], fill=P["water2"])
    px(im, tcx + 64, ty - 19, P["moon"])
    rect(im, tcx + 62, ty - 3, tcx + 76, ty, P["gold1"])
    ui.candle(im, tcx - 90, ty - 2, 12)
    halo(im, tcx - 88, ty - 28, 30)
    # tarot cards laid out
    for i in range(3):
        card = Image.new("RGB", (14, 20), P["night1"])
        ui.rect(card, 0, 0, 13, 19, P["gold2"])
        ui.rect(card, 1, 1, 12, 18, P["royal"])
        ui.moon_eye(card, 7, 10, 4) if False else None
        paste(card, icons.diamond("gold3"), 4, 7)
        im.paste(card, (tcx - 62 + i * 18, ty + 2 + (i % 2)))
    return [im.convert("RGBA")]


# ---------------------------------------------------------------- bg_path
def path():
    im = Image.new("RGB", (W, H), P["night1"])
    d = ImageDraw.Draw(im)
    dust(im, (0, 48, W, 232), 13, 60)
    # rafters and bunting
    rect(im, 0, 48, W - 1, 53, P["gold0"])
    rect(im, 0, 48, W - 1, 48, P["gold1"])
    rect(im, 0, 54, W - 1, 54, P["night0"])
    for x in range(30, W, 90):
        d.line([(x, 54), (x + 4, 70)], fill=P["gold0"])
    flags = ["red", "water1", "earth1", "amber2", "purple", "gold3"]
    for i in range(0, 5):
        x0 = 20 + i * 98
        d.line([(x0, 58), (x0 + 90, 58)], fill=P["night3"])
        for j in range(7):
            fx = x0 + 6 + j * 12
            col = P[flags[(i + j) % len(flags)]]
            d.polygon([(fx, 59), (fx + 8, 59), (fx + 4, 69)], fill=col)
    # cobweb corner
    for r in (10, 20, 30):
        d.arc([-r, -r + 48, r, r + 48], 270, 360, fill=P["night3"])
    for a in (0, 22, 45, 68, 90):
        d.line([(0, 48), (int(34 * math.sin(math.radians(a))), 48 + int(34 * math.cos(math.radians(a))))],
               fill=P["night3"])
    # attic clutter silhouettes along the bottom (night0)
    rect(im, 0, 262, W - 1, H - 1, P["night0"])
    rect(im, 0, 262, W - 1, 262, P["gold0"])
    d.rectangle([20, 238, 66, 262], fill=P["night0"])
    d.rectangle([24, 218, 60, 238], fill=P["night0"])
    d.rectangle([80, 244, 130, 262], fill=P["night0"])
    d.line([(80, 250), (130, 250)], fill=P["night1"])
    d.polygon([(190, 262), (190, 234), (200, 226), (220, 226), (230, 234), (230, 262)], fill=P["night0"])
    d.rectangle([330, 236, 376, 262], fill=P["night0"])
    d.line([(330, 244), (376, 244)], fill=P["night1"])
    d.ellipse([400, 226, 428, 262], fill=P["night0"])
    d.polygon([(436, 262), (440, 228), (460, 228), (466, 262)], fill=P["night0"])
    for x, y in ((26, 244), (36, 224), (338, 242), (445, 236), (88, 250)):
        px(im, x, y, P["night2"])
    # moonlight spill
    d.polygon([(380, 54), (440, 54), (470, 232), (350, 232)], fill=P["night1"])
    # the road: dotted gold line through every step socket
    y = PATH_Y
    for x in range(PATH_STEP_X[0] - 20, PATH_STEP_X[6] + 28):
        if (x // 3) % 2 == 0:
            px(im, x, y - 1, P["gold1"])
            px(im, x, y, P["gold2"])
            px(im, x, y + 1, P["gold1"])
    # choice rings and dotted connectors (fork above and below each step)
    for sx in PATH_STEP_X[:6]:
        for fy in PATH_FORK_Y:
            steps = 14
            for i in range(0, steps, 2):
                t = i / steps
                px(im, int(sx), int(y + (fy - y) * t), P["night3"])
            d.ellipse([sx - 11, fy - 11, sx + 11, fy + 11], outline=P["night3"])
            d.ellipse([sx - 1, fy - 1, sx + 1, fy + 1], outline=P["night2"])
    # sockets on the road
    for i, sx in enumerate(PATH_STEP_X):
        r = 15 if i == 6 else 11
        d.ellipse([sx - r - 1, y - r - 1, sx + r + 1, y + r + 1], fill=P["night0"])
        d.ellipse([sx - r, y - r, sx + r, y + r], outline=P["gold1" if i < 6 else "gold3"], fill=P["night0"])
        d.ellipse([sx - r + 3, y - r + 3, sx + r - 3, y + r - 3], outline=P["night2"])
    # boss glow
    sx = PATH_STEP_X[6]
    for yy in range(y - 30, y + 31):
        for xx in range(sx - 30, sx + 31):
            if ((xx - sx) ** 2 + (yy - y) ** 2) ** 0.5 < 30 and (xx + yy) % 2 == 0 and im.getpixel((xx, yy)) == P["night1"]:
                im.putpixel((xx, yy), P["night2"])
    sx = PATH_STEP_X[6]
    d.ellipse([sx - 16, y - 16, sx + 16, y + 16], outline=P["gold3"], fill=P["night0"])
    d.ellipse([sx - 13, y - 13, sx + 13, y + 13], outline=P["gold1"])
    return [im.convert("RGBA")]


# ---------------------------------------------------------------- bg_end
def end():
    im = Image.new("RGB", (W, H), P["night1"])
    d = ImageDraw.Draw(im)
    dust(im, (0, 0, W, 236), 17, 80)
    cx = 240
    arch_window(im, cx - 100, cx + 100, 10, 148, "royal0")
    dust(im, (cx - 98, 20, cx + 98, 146), 33, 40, ("night3", "night4", "silver1", "moon", "moon"))
    ui.crescent(im, cx - 36, 62, 26, "silver2", "royal0", dx=11)
    ui.sparkle(im, cx - 66, 50, "moon", 3)
    ui.sparkle(im, cx + 50, 38, "silver2", 2)
    ui.sparkle(im, cx + 74, 84, "silver2", 2)
    # distant roofline with a crown-shaped chimney (the Rat King is still out there)
    d.polygon([(cx - 100, 150), (cx - 100, 118), (cx - 60, 104), (cx - 20, 120), (cx + 20, 108), (cx + 60, 124),
               (cx + 100, 112), (cx + 100, 150)], fill=P["night0"])
    d.polygon([(cx + 52, 124), (cx + 52, 110), (cx + 57, 116), (cx + 62, 106), (cx + 67, 116), (cx + 72, 110),
               (cx + 72, 124)], fill=P["night0"])
    px(im, cx + 62, 112, P["amber2"])
    px(im, cx + 56, 119, P["amber2"])
    px(im, cx + 68, 119, P["amber2"])
    sill(im, cx - 100, cx + 100, 152)
    rect(im, cx - 100, 148, cx + 100, 152, P["gold1"])
    # closed grimoire on the sill with a gold cat-eye moon
    bx0, bx1, by0, by1 = cx - 44, cx + 44, 170, 222
    rect(im, bx0 - 6, by1 + 1, bx1 + 6, by1 + 8, P["gold0"])
    rect(im, bx0 - 6, by1 + 1, bx1 + 6, by1 + 1, P["gold1"])
    rect(im, bx0 - 6, by1 + 9, bx1 + 6, by1 + 9, P["night0"])
    d.rectangle([bx0 - 1, by0 - 1, bx1 + 1, by1 + 1], fill=P["night0"])
    d.rectangle([bx0, by0, bx1, by1], fill=P["royal"])
    d.rectangle([bx0, by0, bx0 + 8, by1], fill=P["royal0"])
    for yy in range(by0 + 6, by1, 12):
        rect(im, bx0, yy, bx0 + 8, yy, P["gold1"])
    d.rectangle([bx0 + 14, by0 + 6, bx1 - 6, by1 - 6], outline=P["gold2"])
    d.rectangle([bx0 + 17, by0 + 9, bx1 - 9, by1 - 9], outline=P["gold1"])
    ui.corners(im, bx0 + 14, by0 + 6, bx1 - 6, by1 - 6)
    ui.moon_eye(im, (bx0 + 14 + bx1 - 6) // 2, (by0 + by1) // 2, 12)
    d.rectangle([bx1 - 18, by1, bx1 - 14, by1 + 12], fill=P["red"])
    d.polygon([(bx1 - 18, by1 + 12), (bx1 - 14, by1 + 12), (bx1 - 16, by1 + 8)], fill=P["night1"])
    # candle burning low on the right + feather quill on the left
    ui.candle(im, cx + 74, by1 + 1, 8)
    halo(im, cx + 76, by1 - 26, 28)
    d.polygon([(cx - 92, by1 + 1), (cx - 66, by1 - 8), (cx - 62, by1 - 5), (cx - 88, by1 + 1)], fill=P["silver2"])
    d.line([(cx - 92, by1 + 1), (cx - 66, by1 - 8)], fill=P["moon"])
    d.line([(cx - 92, by1 + 1), (cx - 96, by1 + 5)], fill=P["night0"])
    rect(im, 0, 236, W - 1, H - 1, P["night1"])
    return [im.convert("RGBA")]


GENERATORS = {"bg_attic": attic, "bg_title": title, "bg_parlor": parlor, "bg_path": path, "bg_end": end}
