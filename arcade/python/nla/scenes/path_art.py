"""Small code-drawn illustrations for the Path node scenes (no baked asset exists for them).

Every function paints opaque shapes with a handful of fill ops (circles, rects, triangles) at an origin, on the flat
ground color, so a full repaint costs little and nothing needs a backdrop restore:

    bed_parts(ox, oy)           Domino asleep on a cushion, hat beside him: [(rect, paint)] pieces (area 200 x 84)
    box_closed(scr, cx, base)   cardboard box with taped lid; box_open_back / box_open_front / box_mouth / box_body
    crate(scr, ox, oy)          Zero's reading booth: a crate with a sign
    yarn(scr, cx, cy, r)        a red ball of yarn with a trailing thread
    catnip(scr, cx, base)       a catnip plant in a floor crack
    page(scr, ox, oy)           a torn tarot page
"""

from nla.ui import theme as T


def bed_parts(ox, oy):
    """The bed scene as [(rect, paint fn, est_ms)] so a scene can paint one piece per frame budget (order matters).
    The estimates are the pieces' slow-pixel cost at 180 px/ms plus the op setup."""

    def cushion_left(scr):
        scr.fill_rect(ox + 14, oy + 72, 60, 6, T.NIGHT0)                # shadow
        scr.fill_circle(ox + 24, oy + 54, 20, T.AMBER0)
        scr.fill_rect(ox + 24, oy + 34, 50, 40, T.AMBER0)

    def cushion_mid(scr):
        scr.fill_rect(ox + 74, oy + 72, 52, 6, T.NIGHT0)
        scr.fill_rect(ox + 74, oy + 34, 52, 40, T.AMBER0)

    def cushion_right(scr):
        scr.fill_rect(ox + 126, oy + 72, 60, 6, T.NIGHT0)
        scr.fill_circle(ox + 176, oy + 54, 20, T.AMBER0)
        scr.fill_rect(ox + 126, oy + 34, 50, 40, T.AMBER0)

    def cushion_trim(scr):
        scr.fill_rect(ox + 20, oy + 40, 160, 6, T.AMBER1)
        scr.fill_rect(ox + 28, oy + 62, 144, 3, T.GOLD0)

    def loaf_tail(scr):
        for x, y in ((150, 56), (156, 60), (156, 66), (150, 69), (140, 70), (128, 70)):    # tail round the front
            scr.fill_circle(ox + x, oy + y, 5, T.NIGHT0)
        scr.fill_circle(ox + 124, oy + 70, 4, T.MOON)

    def loaf(scr):
        scr.fill_circle(ox + 130, oy + 46, 17, T.NIGHT0)
        scr.fill_circle(ox + 106, oy + 36, 23, T.NIGHT0)
        scr.fill_circle(ox + 84, oy + 44, 19, T.NIGHT0)
        scr.fill_rect(ox + 84, oy + 46, 46, 16, T.NIGHT0)

    def head_skull(scr):
        scr.fill_circle(ox + 62, oy + 44, 17, T.NIGHT0)
        scr.fill_triangle(ox + 48, oy + 36, ox + 50, oy + 18, ox + 62, oy + 30, T.NIGHT0)
        scr.fill_triangle(ox + 76, oy + 36, ox + 76, oy + 18, ox + 64, oy + 30, T.NIGHT0)
        scr.fill_triangle(ox + 52, oy + 33, ox + 52, oy + 24, ox + 59, oy + 31, T.PINK)
        scr.fill_triangle(ox + 73, oy + 33, ox + 73, oy + 24, ox + 66, oy + 31, T.PINK)

    def head_face(scr):
        scr.fill_circle(ox + 62, oy + 52, 9, T.MOON)
        scr.fill_circle(ox + 52, oy + 47, 5, T.MOON)
        scr.fill_rect(ox + 59, oy + 48, 6, 2, T.PINK)
        scr.line(ox + 53, oy + 42, ox + 58, oy + 44, T.AMBER3)         # closed eyes
        scr.line(ox + 66, oy + 44, ox + 71, oy + 42, T.AMBER3)
        scr.fill_circle(ox + 82, oy + 62, 6, T.MOON)                    # front paws
        scr.fill_circle(ox + 96, oy + 63, 6, T.MOON)

    def hat(scr):
        scr.fill_triangle(ox + 156, oy + 36, ox + 186, oy + 36, ox + 176, oy + 4, T.ROYAL1)
        scr.fill_triangle(ox + 176, oy + 4, ox + 186, oy + 36, ox + 172, oy + 36, T.ROYAL)
        scr.fill_rect(ox + 150, oy + 34, 42, 5, T.ROYAL0)
        scr.fill_rect(ox + 160, oy + 30, 22, 3, T.GOLD2)
        scr.fill_circle(ox + 172, oy + 22, 2, T.GOLD4)

    return [((ox + 4, oy + 32, 74, 48), cushion_left, 35), ((ox + 74, oy + 34, 52, 46), cushion_mid, 25),
            ((ox + 126, oy + 32, 74, 48), cushion_right, 35), ((ox, oy + 38, 200, 28), cushion_trim, 40),
            ((ox + 120, oy + 50, 44, 26), loaf_tail, 30), ((ox + 40, oy + 12, 110, 54), loaf, 40),
            ((ox + 44, oy + 16, 36, 46), head_skull, 32),
            ((ox + 46, oy + 40, 58, 30), head_face, 32),
            ((ox + 148, oy + 2, 46, 40), hat, 14)]


BOX_W, BOX_H = 88, 36


def box_top(base):
    return base - BOX_H


def box_body(scr, cx, base):
    """The box's front wall (88 x 36)."""
    x, y = cx - BOX_W // 2, base - BOX_H
    scr.fill_rect(x, y, BOX_W, BOX_H, T.GOLD1)
    scr.fill_rect(x, y, BOX_W, 3, T.GOLD2)
    scr.fill_rect(x + BOX_W - 12, y + 3, 12, BOX_H - 3, T.GOLD0)
    scr.fill_rect(x, base - 3, BOX_W, 3, T.GOLD0)
    scr.rect(x, y, BOX_W, BOX_H, T.AMBER0)
    scr.fill_rect(x + 10, y + 12, 22, 3, T.GOLD2)        # packing label
    scr.fill_rect(x + 10, y + 18, 14, 3, T.GOLD2)


def box_closed(scr, cx, base):
    """Box with the lid taped shut: lid band on top, tape down the middle."""
    lid = base - BOX_H - 9
    scr.fill_rect(cx - 48, lid, 96, 9, T.GOLD2)
    scr.rect(cx - 48, lid, 96, 9, T.AMBER0)
    box_body(scr, cx, base)
    scr.fill_rect(cx - 5, lid, 10, 24, T.GOLD4)


def box_open_back(scr, cx, base):
    """Opened box, back half: the raised back flaps and the dark mouth."""
    top = base - BOX_H
    scr.fill_triangle(cx - 46, top, cx - 64, top - 26, cx - 30, top, T.GOLD2)
    scr.fill_triangle(cx + 46, top, cx + 64, top - 26, cx + 30, top, T.GOLD1)
    box_mouth(scr, cx, base)


def box_open_front(scr, cx, base):
    """Opened box, front half: the front wall and the folded-out front flaps."""
    top = base - BOX_H
    box_body(scr, cx, base)
    scr.fill_triangle(cx - 46, top + 1, cx - 60, top + 16, cx - 28, top + 1, T.GOLD2)
    scr.fill_triangle(cx + 46, top + 1, cx + 60, top + 16, cx + 28, top + 1, T.GOLD1)


def box_mouth(scr, cx, base):
    scr.fill_rect(cx - 44, base - BOX_H - 3, 88, 5, T.NIGHT0)


def crate(scr, ox, oy):
    """Zero's booth: a crate with slats and a sign on a stick."""
    scr.fill_rect(ox, oy + 30, 70, 38, T.GOLD1)
    scr.rect(ox, oy + 30, 70, 38, T.AMBER0)
    for k in (46, 58):
        scr.fill_rect(ox + 2, oy + k, 66, 2, T.GOLD0)
    scr.fill_rect(ox + 30, oy + 4, 3, 28, T.GOLD0)
    scr.fill_rect(ox + 12, oy, 40, 18, T.MOON)
    scr.rect(ox + 12, oy, 40, 18, T.GOLD2)
    scr.fill_rect(ox + 16, oy + 5, 32, 2, T.NIGHT3)
    scr.fill_rect(ox + 16, oy + 10, 22, 2, T.NIGHT3)


def yarn(scr, cx, cy, r):
    scr.fill_circle(cx, cy, r, T.RED)
    scr.circle(cx, cy, r, T.FIRE0)
    scr.line(cx - r + 3, cy - 3, cx + r - 5, cy + 5, T.FIRE0)
    scr.line(cx - r + 4, cy + 4, cx + r - 3, cy - 5, T.FIRE2)
    scr.line(cx - 3, cy - r + 3, cx + 5, cy + r - 4, T.FIRE0)
    scr.line(cx + r - 2, cy + r - 3, cx + r + 22, cy + r + 4, T.RED)
    scr.line(cx + r + 22, cy + r + 4, cx + r + 40, cy + r - 2, T.RED)


def catnip(scr, cx, base):
    scr.fill_rect(cx - 30, base - 3, 60, 4, T.NIGHT0)
    for dx, h, w in ((-14, 30, 8), (-4, 44, 10), (8, 36, 8), (18, 22, 6)):
        scr.fill_triangle(cx + dx - w, base - 2, cx + dx + w, base - 2, cx + dx, base - h, T.EARTH1)
        scr.fill_triangle(cx + dx, base - 2, cx + dx + w, base - 2, cx + dx, base - h, T.EARTH0)
    scr.fill_circle(cx - 4, base - 46, 3, T.PURPLE)
    scr.fill_circle(cx + 9, base - 38, 2, T.PURPLE)
    scr.fill_circle(cx - 15, base - 32, 2, T.PURPLE)


def page(scr, ox, oy):
    scr.fill_rect(ox, oy, 44, 58, T.GOLD4)
    scr.rect(ox, oy, 44, 58, T.GOLD2)
    scr.fill_rect(ox + 6, oy + 8, 32, 26, T.GOLD2)
    scr.fill_circle(ox + 22, oy + 21, 7, T.GOLD4)
    for k in (40, 46, 52):
        scr.fill_rect(ox + 6, oy + k, 32 - (k - 40), 2, T.GOLD1)
    scr.fill_triangle(ox + 44, oy, ox + 44, oy + 12, ox + 32, oy, T.GROUND)   # torn corner
