"""Domino concept sheet: domino-variants.png (+ @2x). Run: python variants.py (needs raw/domino.png and raw/domino_v1..v6.png)."""
import os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)
from PIL import Image, ImageDraw
import render as R
import ui
from pal import P, is565
from ui import text, text_w, rect, frame, paste, TITLE

NAMES = [("domino", "0  Current: Cloaked Adventurer"), ("domino_v1", "1  Gentleman Magician"),
         ("domino_v2", "2  Hooded Fortune-Teller"), ("domino_v3", "3  Night Rogue"), ("domino_v4", "4  Moon Knight"),
         ("domino_v5", "5  Apprentice Seer"), ("domino_v6", "6  Plague-Doctor Cartomancer")]
CW, CH = 400, 196        # cell
COLS = 2


def main():
    rows = (len(NAMES) + COLS - 1) // COLS
    SW, SH = 24 + COLS * (CW + 16), 64 + rows * (CH + 12) + 12
    im = Image.new("RGB", (SW, SH), P["night1"])
    ui.tile_fill(im, ui.star_tile(48, 48, 11, 7))
    ui.moon_eye(im, 36, 32, 18)
    text(im, 66, 40, "Domino concepts", P["gold3"], TITLE())
    text(im, 66, 56, "Moonlit Grimoire direction. Each shown at 2x, then in a 240x160 crop of the battle scene.", P["silver2"])
    for i, (key, label) in enumerate(NAMES):
        cx = 16 + (i % COLS) * (CW + 16)
        cy = 68 + (i // COLS) * (CH + 12)
        ui.panel(im, cx, cy, cx + CW - 1, cy + CH - 1, fill="night0", orn=False)
        sp = R.sprite(key)
        bb = sp.getbbox()
        big = sp.resize((128, 128), Image.NEAREST)
        paste(im, big, cx + 6, cy + 24)
        text(im, cx + 8, cy + 17, label, P["gold3"])
        crop = R.battle(popup=False, dmg=0, slash=False, particles=False, hero=key, hero_cool=False).crop((0, 160, 240, 320))
        im.paste(crop, (cx + 152, cy + 28))
        frame(im, cx + 151, cy + 27, cx + 392, cy + 188, P["gold1"])
        text(im, cx + 8, cy + 176, "64x64, east", P["night4"])
    cols = set(im.getdata())
    assert all(is565(c) for c in cols)
    im.save("domino-variants.png")
    im.resize((im.width * 2, im.height * 2), Image.NEAREST).save("domino-variants@2x.png")
    print("domino-variants.png", im.size, len(cols), "colors")


FINAL = [("domino_merge_b", "Ref: B Brighter eyes (card is a gold slab)"), ("domino_final_hand", "V1  Hand-pixeled card back (code)"),
         ("domino_final_ai", "V2  AI edit: card back")]


def final():
    CWF, CHF = 580, 196
    SW, SH = 32 + CWF, 68 + len(FINAL) * (CHF + 10) + 8
    im = Image.new("RGB", (SW, SH), P["night1"])
    ui.tile_fill(im, ui.star_tile(48, 48, 11, 7))
    ui.moon_eye(im, 36, 32, 18)
    text(im, 66, 40, "Domino final: the held card as a card back", P["gold3"], TITLE())
    text(im, 66, 56, "2x sprite, 4x hands + card, battle crop. V1 code-painted, V2 AI edit of B.", P["silver2"])
    for i, (key, label) in enumerate(FINAL):
        cx, cy = 16, 68 + i * (CHF + 10)
        ui.panel(im, cx, cy, cx + CWF - 1, cy + CHF - 1, fill="night0", orn=False)
        text(im, cx + 8, cy + 17, label, P["gold3"])
        sp = R.sprite(key, False, cool=True)
        paste(im, sp.resize((128, 128), Image.NEAREST), cx + 6, cy + 26)
        text(im, cx + 6, cy + 175, "2x sprite", P["night4"])
        det = sp.crop((24, 20, 56, 52)).resize((128, 128), Image.NEAREST)
        paste(im, det, cx + 144, cy + 26)
        text(im, cx + 144, cy + 175, "4x hands + card", P["night4"])
        crop = R.battle(popup=False, dmg=0, slash=False, particles=False, hero=key, hero_cool=True).crop((0, 160, 240, 320))
        im.paste(crop, (cx + 330, cy + 26))
        frame(im, cx + 329, cy + 25, cx + 570, cy + 186, P["gold1"])
        text(im, cx + 330, cy + 195 - 2, "battle crop 240x160", P["night4"]) if False else None
    cols = set(im.getdata())
    assert all(is565(c) for c in cols)
    im.save("domino-final.png")
    im.resize((im.width * 2, im.height * 2), Image.NEAREST).save("domino-final@2x.png")
    print("domino-final.png", im.size, len(cols), "colors")


MERGE = [("domino_v5", "Ref: v5 Apprentice Seer (outfit)", False), ("domino_v2", "Ref: v2 Hooded Fortune-Teller (fur)", False),
         ("domino_merge_a", "A  Exact marking description", False), ("domino_merge_b", "B  + brighter eyes", False),
         ("domino_merge_c", "C  + heroic expression", False)]


def merge():
    rows = (len(MERGE) + COLS - 1) // COLS
    SW, SH = 24 + COLS * (CW + 16), 64 + rows * (CH + 12) + 12
    im = Image.new("RGB", (SW, SH), P["night1"])
    ui.tile_fill(im, ui.star_tile(48, 48, 11, 7))
    ui.moon_eye(im, 36, 32, 18)
    text(im, 66, 40, "Domino merge: Seer outfit + Fortune-Teller fur", P["gold3"], TITLE())
    text(im, 66, 56, "Candidates A-C edited from v5 with PixelLab edit-image-pixen. 2x sprite + 240x160 battle crop.", P["silver2"])
    for i, (key, label, flip) in enumerate(MERGE):
        cx = 16 + (i % COLS) * (CW + 16)
        cy = 68 + (i // COLS) * (CH + 12)
        ui.panel(im, cx, cy, cx + CW - 1, cy + CH - 1, fill="night0", orn=False)
        sp = R.sprite(key, flip, cool=True)
        paste(im, sp.resize((128, 128), Image.NEAREST), cx + 6, cy + 24)
        text(im, cx + 8, cy + 17, label, P["gold3"])
        crop = R.battle(popup=False, dmg=0, slash=False, particles=False, hero=key, hero_cool=True).crop((0, 160, 240, 320))
        im.paste(crop, (cx + 152, cy + 28))
        frame(im, cx + 151, cy + 27, cx + 392, cy + 188, P["gold1"])
        text(im, cx + 8, cy + 176, "64x64, east", P["night4"])
    cols = set(im.getdata())
    assert all(is565(c) for c in cols)
    im.save("domino-merge.png")
    im.resize((im.width * 2, im.height * 2), Image.NEAREST).save("domino-merge@2x.png")
    print("domino-merge.png", im.size, len(cols), "colors")


if __name__ == "__main__":
    main()
    merge()
    final()
