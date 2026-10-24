"""Single source of truth for every non-character asset: name, size, frames, fps, meaning, frame-index formula.
build_ui.py renders each entry (real generator when one is registered, otherwise a sized placeholder) and
writes assets/ui.json plus docs/assets.md rows from this table."""
from dataclasses import dataclass

ELEMENTS = ["fire", "air", "water", "earth"]
MAJORS = ["The Fool", "The Magician", "The Empress", "The Emperor", "The Chariot", "Strength", "The Hanged Man",
          "The Sun"]
CHARMS = ["Catnip", "Fish Bone", "Paw Pad", "Yarn", "Bell", "Moonlight", "Nine Lives", "Rat Bite", "Fleas"]
SCRAPS = ["broken_sword", "gnaw", "burnt_wand", "cracked_coin", "leaky_cup", "bite_mark", "snatch", "burrow",
          "droppings", "fleas", "sleep_dust"]
STATUSES = ["singe", "puff", "drowsy", "curl", "leap"]
NODES = ["fight", "elite", "stall", "encounter", "cat_bed", "box", "boss"]
LINKS = ["nuzzle", "tail_tap", "hiss", "step", "mirror", "litter", "journey"]


@dataclass(frozen=True)
class Spec:
    name: str
    w: int
    h: int
    frames: int
    fps: int
    meaning: str
    index: str
    group: str


SPECS: list[Spec] = []


def add(name, w, h, frames, fps, meaning, index, group):
    SPECS.append(Spec(name, w, h, frames, fps, meaning, index, group))


DEF = "frame = CardDef.id (Minor = element*10 + number-1, Fire 0-9, Air 10-19, Water 20-29, Earth 30-39; Majors 40-47: " \
      "Fool, Magician, Empress, Emperor, Chariot, Strength, Hanged Man, Sun)"

# ---- cards -------------------------------------------------------------------------------------------------------
G = "Card faces"
add("card_u", 44, 60, 48, 0, "Upright card face, interior of the 2-px rim (field, filigree line, art plate, number or "
    "numeral, element icon). Four outermost corner pixels transparent. Draw rim, stars, charm separately.", DEF, G)
add("card_r", 44, 60, 48, 0, "Reversed card face (art flipped, cool palette, marker triangle at top). Same layout.", DEF, G)
add("card_s_u", 36, 50, 48, 0, "Small (Box / enemy row) upright face, interior of the 2-px rim of a 40x54 card.", DEF, G)
add("card_s_r", 36, 50, 48, 0, "Small reversed face.", DEF, G)
add("scrap", 44, 60, len(SCRAPS), 0, "Rat scrap card interior (gray-green, bite marks). Number X is not baked: draw it "
    "as text at interior (3, 11) baseline, color rat3 on rat1.", "frame = SCRAPS index: " + ", ".join(
    f"{i} {k}" for i, k in enumerate(SCRAPS)), G)
add("scrap_s", 36, 50, len(SCRAPS), 0, "Small scrap card interior. Number at interior (3, 10).", "same as scrap", G)
add("card_chewed_s", 36, 50, 3, 0, "Chewed Major in a rat spread (reversed face with bites), small interior.",
    "frame 0 Chariot, 1 Magician, 2 Strength", G)
add("card_droppings", 44, 60, 1, 0, "Droppings curse card interior (player Spread, red rim drawn by UI).", "single frame", G)
add("card_droppings_s", 36, 50, 1, 0, "Droppings curse card, small interior.", "single frame", G)
add("card_back", 48, 64, 1, 0, "Full card back, deep blue with gold cat-eye moon (rim included).", "single frame", G)
add("card_back_s", 40, 54, 1, 0, "Small full card back.", "single frame", G)

# ---- glyphs ------------------------------------------------------------------------------------------------------
G = "Icons and glyphs"
add("ui_corner", 10, 10, 1, 0, "Flourish panel corner, top-left orientation (flip for the others).", "single", G)
add("ui_diamond", 5, 5, 2, 0, "Divider diamond.", "frame 0 gold3, 1 gold1", G)
add("ui_star", 5, 5, 2, 0, "Star pip. Frame 0 gold3 (filled), 1 night3 (empty).", "frame 0 filled, 1 empty", G)
add("ui_gem", 5, 5, 9, 0, "Charm gem for card corners, one color per charm.", "frame = Card.charm - 1 (Catnip, Fish Bone, "
    "Paw Pad, Yarn, Bell, Moonlight, Nine Lives, Rat Bite, Fleas)", G)
add("ui_charm", 8, 8, 9, 0, "Charm icon for panels and info.", "frame = Card.charm - 1", G)
add("ui_elem", 9, 9, 4, 0, "Element icon.", "frame = element (Fire 0, Air 1, Water 2, Earth 3)", G)
add("ui_elem_s", 7, 7, 4, 0, "Small element icon.", "frame = element", G)
add("ui_status", 12, 12, 5, 0, "Status icon (Singe, Puff, Drowsy, Curl, Leap).", "frame = singe 0, puff 1, drowsy 2, curl 3, leap 4", G)
add("ui_status_s", 9, 9, 5, 0, "Small status icon.", "same as ui_status", G)
add("ui_paw", 15, 11, 1, 0, "Paw cursor (amber).", "single", G)
add("ui_heart", 9, 9, 1, 0, "HP heart.", "single", G)
add("ui_treat", 9, 9, 1, 0, "Treats currency (amber fish treat).", "single", G)
add("ui_arrow", 7, 5, 2, 0, "Right arrow glyph.", "frame 0 silver2, 1 amber3", G)
add("ui_tri_down", 7, 4, 2, 0, "Down triangle (reversed marker).", "frame 0 silver2, 1 amber3", G)
add("ui_btn", 13, 13, 3, 0, "Button gem with letter.", "frame 0 A, 1 B, 2 C", G)
add("ui_bracket", 7, 7, 1, 0, "Amber cursor bracket, top-left; flip x/y for the other corners.", "single", G)
add("ui_moon_eye", 23, 23, 3, 0, "Cat-eye moon (loading cue, plaque). Frames: open, half, slit-closed.",
    "frame 0 open, 1 half, 2 closed (blink 0-1-2-1-0)", G)
add("ui_moon_eye_s", 15, 15, 1, 0, "Small cat-eye moon.", "single", G)
add("ui_candle", 5, 20, 2, 4, "Candle with flame, 2-frame flicker. Rows 0-6 flame, bottom stick.", "frame = tick % 2", G)
add("ui_sparkle", 5, 5, 2, 0, "Twinkle. Frame 0 moon cross, 1 dim cross.", "frame 0/1", G)
add("ui_plaque_fight", 92, 64, 2, 0, "FIGHT plaque with cat-eye moon and the word Fight.", "frame 0 idle, 1 focused (amber rim)", G)
add("ui_tut_arrow", 9, 9, 4, 0, "Tutorial pointing arrow (amber).", "frame 0 up, 1 down, 2 left, 3 right", G)
add("ui_node", 20, 20, len(NODES), 0, "Night Path node icon.", "frame = " + ", ".join(f"{i} {k}" for i, k in enumerate(NODES)), G)
add("ui_node_dim", 20, 20, len(NODES), 0, "Visited / unavailable node icon.", "same as ui_node", G)
add("ui_bell", 14, 16, 2, 0, "Nine Bells bell.", "frame 0 dark, 1 lit", G)
add("ui_link", 9, 9, len(LINKS), 0, "Reading link glyph drawn between two cards.", "frame = " + ", ".join(
    f"{i} {k}" for i, k in enumerate(LINKS)), G)
add("ui_star_dust", 32, 32, 1, 0, "Opaque star-dust background tile.", "single", G)

# ---- vfx ---------------------------------------------------------------------------------------------------------
G = "VFX sprites"
add("fx_slash", 40, 40, 4, 16, "Triple claw slash over the target, grows then fades.", "frame = progress 0-3", G)
add("fx_spark", 12, 12, 4, 16, "Hit spark burst.", "frame = progress 0-3", G)
add("fx_part", 8, 8, 12, 12, "Element particles, 3 frames each.", "frame = element*3 + step (Fire embers, Air wisps, "
    "Water drops, Earth chips)", G)
add("fx_heal", 8, 8, 3, 12, "Heal plus-sparkle.", "frame = step 0-2", G)
add("fx_curl", 16, 16, 3, 12, "Curl shield swirl.", "frame = step 0-2", G)
add("fx_meow", 72, 30, 2, 0, "MEOW! speech bubble for crits.", "frame 0 small pop, 1 full", G)
add("fx_hiss", 24, 24, 2, 8, "Arched hissing cat icon shown between two cards on a Hiss.", "frame = tick % 2", G)
add("fx_bite", 14, 14, 1, 0, "Bite mark stamped on a card corner.", "single", G)

# ---- backdrops ---------------------------------------------------------------------------------------------------
G = "Backdrops"
add("bg_attic", 480, 232, 1, 0, "Dusty Attic battle stage, y 0-231. Flat floor strip y 196-231 (night0 planks).",
    "single; hero feet at y222, floor fill color night0", G)
add("bg_title", 480, 320, 1, 0, "Title screen: moonlit parlor window, cat-eye moon, Meowcana wordmark and "
    "the subtitle Swap. Chain. Pounce. Menu band y 232-320 is flat night1.", "single", G)
add("bg_parlor", 480, 320, 1, 0, "Moonnap Parlor: reading table, sleeping Granny Oriel, empty bell wall.",
    "single; bells drawn on top with ui_bell at PARLOR_BELLS positions", G)
add("bg_path", 480, 320, 1, 0, "Night Path map: attic road with 7 step sockets and fork links.",
    "single; sockets at x = 44 + 62*step (step 0-5), boss x = 428; y = 168, forks at y = 124 / 212", G)
add("bg_end", 480, 320, 1, 0, "Demo end art: closed grimoire under the window moon. Text band y 236-320 flat night1.", "single", G)

NOTES = [
    "- Card faces are the interior of the card inside the 2-px rim: blit at (card_x + 2, card_y + 2); card sizes are 48x64 "
    "and 40x54. The UI draws the 2-px rim (ink edge ring + rarity color), stars (`ui_star`, top-right, first star at "
    "card (W-8, 5), 6 px pitch) and the charm gem (`ui_gem`, bottom-right at card (W-12, H-12)).",
    "- Baked in a face: number or numeral (top-left, card baseline (5, 13) big / (5, 12) small; Ace shows A), 1-px "
    "filigree line with corner studs, art plate (32x32 big, 26x26 small, gold edge), element icon bottom-left, and for "
    "Reversed cards a small down triangle at bottom center. Majors show the Roman numeral instead of a number.",
    "- Scrap faces carry no number: draw it as text, color rat3 on the rat1 field, at card (5, 12) big / (5, 11) small "
    "(baseline). Bite dents are baked into the right edge; the UI draws a rat2 rim (ink edge rat0).",
    "- Transparent pixels (alpha 0) exist in card interiors (four corners), icons, fx_*, ui_btn, ui_moon_eye, ui_node; "
    "bg_*, ui_plaque_fight, ui_star_dust and card_back* (except corners) are fully opaque.",
    "- Python constants are the upper-cased names (`assets.CARD_U`, `assets.UI_ELEM`, ...), frame = index formula above.",
]

GROUPS = [G for G in dict.fromkeys(s.group for s in SPECS)]

if __name__ == "__main__":
    print(len(SPECS), "assets,", sum(s.frames for s in SPECS), "frames")
