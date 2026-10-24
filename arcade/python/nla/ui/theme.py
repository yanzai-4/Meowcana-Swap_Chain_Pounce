"""Moonlit Grimoire theme: palette, color roles, font roles, layout grid, spacing.

API (everything is a module-level constant or a tiny function):

    from nla.ui import theme as T

    T.NIGHT0 .. T.MOON, T.GOLD0 .. T.GOLD4, T.AMBER0 .. T.AMBER3   RGB565 ints (exact, from the style palette)
    T.GROUND            night1 (0x2929) - the fast-fill ground color of every screen
    T.PANEL, T.TEXT, T.MUTED, T.CAPTION, T.FOCUS, T.ACCENT          color roles (see below)
    T.DAMAGE, T.HEAL, T.CURSE                                       feedback roles
    T.elem_dark(e) / elem_mid(e) / elem_light(e) / elem_rev_mid(e)  element colors, e = 0 Fire, 1 Air, 2 Water, 3 Earth
    T.rarity_color(r)                                               card rim color; r = None/"none"/"common"/"rare"/"legendary"/"curse" or 0..4
    T.tier_color(tier)                                              chain tier ramp white -> yellow -> orange -> red -> gold
    T.dim(color)                                                    darkened color, same math as the engine's `dim=True`
    T.BODY, T.TITLE, T.NUM, T.TINY                                  font roles (engine font constants)
    T.text_h(font)                                                  cell height of a font in px
    T.S1 .. T.S5                                                    spacing scale 2, 4, 8, 12, 16
    T.SCREEN_W, T.SCREEN_H, T.MARGIN, T.INNER_L, T.INNER_R          screen box and 16 px safe margins
    T.SPREAD_*, T.BATTLE_*, T.FOOTER_*                              layout grid rows and zones (below)

Color roles: GROUND = night1 behind everything; PANEL = night0 fill of boxes; TEXT = silver2 body text on
night0/night1; MUTED = silver1 secondary text; CAPTION = night4 faint captions; FOCUS = gold4 focus text;
LABEL = gold3 titles and section labels (gold marks focus and rarity only); ACCENT = amber3 cursor, Power
numbers, chain, damage. Never put body text on anything lighter than night3.
"""

import engine

# --------------------------------------------------------------------------- palette


def _c(r, g, b):
    """8-bit RGB to the exact RGB565 code the style sheet uses (round to 5/6/5 bits)."""
    return (round(r * 31 / 255) << 11) | (round(g * 63 / 255) << 5) | round(b * 31 / 255)


NIGHT0 = _c(14, 10, 34)
NIGHT1 = _c(41, 36, 74)
NIGHT2 = _c(58, 52, 102)
NIGHT3 = _c(84, 78, 134)
NIGHT4 = _c(122, 116, 168)
SILVER1 = _c(160, 164, 194)
SILVER2 = _c(202, 208, 230)
MOON = _c(240, 242, 252)
GOLD0 = _c(88, 62, 32)
GOLD1 = _c(140, 100, 44)
GOLD2 = _c(196, 150, 60)
GOLD3 = _c(234, 194, 98)
GOLD4 = _c(252, 228, 152)
AMBER0 = _c(130, 56, 36)
AMBER1 = _c(206, 98, 40)
AMBER2 = _c(246, 152, 52)
AMBER3 = _c(255, 206, 114)
FIRE0, FIRE1, FIRE2 = _c(110, 34, 40), _c(196, 64, 48), _c(240, 122, 72)
AIR0, AIR1, AIR2 = _c(130, 116, 64), _c(222, 206, 130), _c(250, 240, 186)
WATER0, WATER1, WATER2 = _c(30, 54, 122), _c(60, 110, 196), _c(132, 178, 236)
EARTH0, EARTH1, EARTH2 = _c(30, 74, 58), _c(70, 136, 84), _c(140, 196, 120)
RFIRE0, RFIRE1 = _c(62, 40, 96), _c(112, 80, 150)
RAIR0, RAIR1 = _c(72, 84, 110), _c(150, 166, 196)
RWATER0, RWATER1 = _c(24, 38, 88), _c(66, 92, 156)
REARTH0, REARTH1 = _c(28, 62, 70), _c(64, 118, 116)
RAT0, RAT1, RAT2, RAT3 = _c(44, 56, 52), _c(86, 104, 90), _c(136, 156, 126), _c(180, 196, 160)
PINK = _c(206, 124, 132)
ROYAL, ROYAL1, ROYAL0 = _c(0x31, 0x24, 0x8C), _c(0x4A, 0x38, 0xAD), _c(0x18, 0x14, 0x5A)
BLUE, PURPLE, RED, HEAL_GREEN = _c(84, 120, 226), _c(160, 98, 214), _c(226, 58, 74), _c(112, 216, 134)

# Elements are indexed like rules.cards: 0 Fire, 1 Air, 2 Water, 3 Earth.
FIRE, AIR, WATER, EARTH = 0, 1, 2, 3
_ELEM_DARK = (FIRE0, AIR0, WATER0, EARTH0)
_ELEM_MID = (FIRE1, AIR1, WATER1, EARTH1)
_ELEM_LIGHT = (FIRE2, AIR2, WATER2, EARTH2)
_ELEM_REV_MID = (RFIRE1, RAIR1, RWATER1, REARTH1)


def elem_dark(e):
    return _ELEM_DARK[e]


def elem_mid(e):
    return _ELEM_MID[e]


def elem_light(e):
    return _ELEM_LIGHT[e]


def elem_rev_mid(e):
    return _ELEM_REV_MID[e]


def elem_body(e, reversed_=False):
    """Field color of a card face (what shows around the art plate)."""
    return _ELEM_REV_MID[e] if reversed_ else _ELEM_MID[e]


# --------------------------------------------------------------------------- color roles
GROUND = NIGHT1          # fast fill (hi byte == lo byte)
PANEL = NIGHT0
RAISED = NIGHT2
TEXT = SILVER2
MUTED = SILVER1
CAPTION = NIGHT4
LABEL = GOLD3
FOCUS = GOLD4
ACCENT = AMBER3
RULE = GOLD1             # 1 px panel rules
RULE_DIM = GOLD0         # dividers
RULE_BRIGHT = GOLD2      # filigree, button rims
DAMAGE = GOLD4
HEAL = HEAL_GREEN
CURSE = RED
SINGE = AMBER2
DISABLED = NIGHT3
BAR_HP_ENEMY = FIRE1
BAR_HP_ENEMY_HI = FIRE2
BAR_HP_HERO = HEAL_GREEN
BAR_HP_HERO_HI = MOON

_RARITY = {
    None: SILVER2, "none": SILVER2, 0: SILVER2,
    "common": BLUE, 1: BLUE,
    "rare": PURPLE, 2: PURPLE,
    "legendary": GOLD3, 3: GOLD3,
    "curse": RED, 4: RED,
}


def rarity_color(r):
    return _RARITY[r]


TIER_COLORS = (MOON, GOLD4, AMBER2, RED, GOLD3)   # chain tier 0..4: white, yellow, orange, red, gold


def tier_color(tier):
    return TIER_COLORS[max(0, min(len(TIER_COLORS) - 1, tier))]


def dim(color):
    """Darkened color; identical to the engine's `dim=True` on assets: (c >> 1) & 0x7BEF."""
    return (color >> 1) & 0x7BEF


def is_fast(color):
    """True when the TFT can fill this color at the fast rate (high byte equals low byte)."""
    return (color >> 8) == (color & 0xFF)


# --------------------------------------------------------------------------- fonts
BODY = engine.BODY      # VT323 16 px: all body text, stats, footer
TITLE = engine.TITLE    # Jacquard 24: names and titles, mixed case only
NUM = engine.NUM        # Jersey 10 at 20 px: damage numbers, digits and +-x%!/
TINY = engine.TINY      # Silkscreen 8: tiny callouts

_text_h = {}


def text_h(font):
    h = _text_h.get(font)
    if h is None:
        h = _text_h[font] = engine.font_metrics(font)[0]
    return h


def text_ascent(font):
    return engine.font_metrics(font)[1]


# --------------------------------------------------------------------------- spacing
S1, S2, S3, S4, S5 = 2, 4, 8, 12, 16
SCREEN_W, SCREEN_H = 480, 320
MARGIN = 16
INNER_L, INNER_R = MARGIN, SCREEN_W - MARGIN - 1     # 16 .. 463 inclusive (448 px)
INNER_W = INNER_R - INNER_L + 1

# --------------------------------------------------------------------------- card geometry
CARD_W, CARD_H = 48, 64          # big card (spread row)
CARD_SW, CARD_SH = 40, 54        # small card (box, scraps, battle)
CARD_LIFT = 4                    # px a played/raised card jumps

# --------------------------------------------------------------------------- layout grid: Spread screen
SPREAD_ENEMY_Y0, SPREAD_ENEMY_Y1 = 6, 62
SPREAD_DIV1_Y = 66
SPREAD_READING_Y0, SPREAD_READING_Y1 = 68, 84
SPREAD_DIV2_Y = 88
SPREAD_HEADER_Y0, SPREAD_HEADER_Y1 = 90, 101
SPREAD_CARD_Y = 106                                   # top of the 48x64 cards (to y 169)
SPREAD_SLOT_X0, SPREAD_SLOT_PITCH = 18, 58            # 6 slots: 18, 76, 134, ...
SPREAD_FIGHT = (372, 106, 92, 64)                     # x, y, w, h of the Fight plaque
SPREAD_PAW_Y = 173
SPREAD_BOX_Y = 186                                    # top of the 40x54 box cards (to y 239)
SPREAD_BOX_X0, SPREAD_BOX_PITCH = 90, 46
SPREAD_DIV3_Y = 244
SPREAD_DETAIL = (16, 249, 448, 42)                    # selected-card panel
ENEMY_PORTRAIT = (16, 9, 59, 53)                      # framed enemy portrait box
ENEMY_SCRAP_X0, ENEMY_SCRAP_PITCH, ENEMY_SCRAP_Y = 328, 48, 6

# --------------------------------------------------------------------------- layout grid: Battle screen
BATTLE_PLATE = (0, 0, 480, 30)                        # top plate: name, HP, statuses
BATTLE_STAGE = (0, 30, 480, 202)                      # stage y 30..231
BATTLE_FLOOR_Y = 196                                  # floor band y196..232
BATTLE_FEET_Y = 222
BATTLE_SCRAP_X0, BATTLE_SCRAP_PITCH, BATTLE_SCRAP_Y = 204, 44, 34
BATTLE_BAND_Y = 232                                   # bottom band y232..295
BATTLE_HAND_X0, BATTLE_HAND_PITCH, BATTLE_HAND_Y = 16, 46, 238
BATTLE_READING = (212, 240, 252, 51)                  # reading panel
BATTLE_POPUP = (100, 98, 187, 45)                     # chain popup panel
BATTLE_HERO_X, BATTLE_ENEMY_X = 64, 396               # sprite center x

# --------------------------------------------------------------------------- footer
FOOTER_DIV_Y = 296
FOOTER_Y = 298                                        # top of the footer text row (to 319)
FOOTER_H = 22


# --------------------------------------------------------------------------- assets
_asset_cache = {}


def asset(name):
    """Packed asset by its manifest name, e.g. asset("ui_btn") -> assets.UI_BTN (cached)."""
    a = _asset_cache.get(name)
    if a is None:
        import assets
        a = _asset_cache[name] = getattr(assets, name.upper())
    return a
