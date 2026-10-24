# Two-Tone Noir: art direction for *Nine Lives Arcana: The Cats and the Rat King*

**Pitch.** Domino's passive, *Two-Tone* ("half dark, half light, sees both sides of every fate"), becomes the whole art direction. The world is 1-bit ink and moonlight: black night, white paper, ordered dither for shadow and moonbeam. **Colour is rationed and means something.** It appears only on cards and on the numbers they make: vermilion for Fire, saffron for Air, cyan-blue for Water, moss for Earth, and one gold for rarity and the top of a reading chain. Rats were born from scraps that have no fate, so they never get a colour. A Reversed card is the same card with black and white swapped.

Files: `spread.png`, `battle.png` (480x320), `*@2x.png` (nearest-neighbour), `sheet.png` (960x1378), `render.py` (rebuilds everything), `gen_sprites.py` (the 4 PixelLab calls), `raw/` (PixelLab output), `fonts/` (OFL TTFs and licence texts).

## Brief (my own, before drawing)

| Question | Answer |
|---|---|
| Feeling | A candle-lit fortune teller's table seen through a cat's eye: quiet, graphic, a little sinister, never cute-by-default. |
| One memorable thing | The half-white/half-black coat. It is the logo, the medallion beside every HP bar, the Reversed-card rule, and the reason the screen is 1-bit. |
| Hierarchy rule | On every screen exactly one solid-white slab (FIGHT on Spread; the raised card + gold chain on Battle) and one saturated accent at a time. Everything else is thin white line on black. |
| What is *not* done | No gradients, no glow, no drop shadows, no rounded-corner panels, no emoji, no icon-in-a-rounded-square grids. Panels are rules and dotted lines; cards are the only boxes. |
| Hardware habit | Black is the ground, so a screen is mostly the fastest fill there is. Cursor and focus are shape (corner brackets + paw), never just colour. A footer with button hints is always on screen. |

## Why it fits the game

* **Readability at arm's length.** Contrast is maximal (white on black, black on accent). Element, orientation and rarity are encoded redundantly: accent colour + icon + pip shape; black vs white card face; 1/2 edge lines, studs, gold.
* **Reversed is visible from across the room.** Upright = white card, black ink, colour field. Reversed = black card, white edge, colour becomes the ink on a black field, art flipped. Domino's passive ("your Reversed cards gain +25%") is literally what the player sees.
* **Colour = meaning.** Damage numbers take the colour of the card that dealt them (the shipped Battle frame: saffron 12 from an Air card). Status icons borrow their element hue (Singe red, Drowsy blue, Curl green, Leap yellow, Puff white). Treats are gold. The gold chain link is the only gold in motion.
* **Lots of negative space.** Black is the margin, so the 480x320 screen can hold the full Spread layout (enemy, reading, 6 slots + FIGHT, per-round stats, box, detail, footer) without looking like a spreadsheet.
* **Rats and Zero get meaning from the limits.** Rats and scraps are dither only (fate-less, colour-less). Zero, the ghost, is a dithered/checkered pale sprite because the hardware has no alpha anyway.

## Palette (7 colours, all RGB565-exact, all "fast-fill" words)

Every colour below has equal high and low byte in RGB565 (or is 0x0000/0xFFFF), so every solid fill (panels, bars, chips, card faces and windows, FIGHT slab) is on the ~4x fast path.

| Name | Hex | RGB565 | Role |
|---|---|---|---|
| Ink / night | `#000000` | `0x0000` | ground, ink, Reversed card face |
| Paper / moon | `#FFFFFF` | `0xFFFF` | text, rules, card face, moonlight |
| Fire vermilion | `#E71C00` | `0xE0E0` | Fire cards, Singe, "Power 9" |
| Air saffron | `#E7DF31` | `0xE6E6` | Air cards, Leap, the Air damage number |
| Water cyan-blue | `#39A6EF` | `0x3D3D` | Water cards, Heal, Drowsy |
| Earth moss | `#42AA29` | `0x4545` | Earth cards, Curl |
| Gold | `#E79E21` | `0xE4E4` | rarity (Legendary edge, Nine Lives), top chain link, Catwalk, Treats |

`render.py` asserts on every output that all pixels are in this set and RGB565-exact; spread/battle/sheet each use exactly 7 colours. Sprites are strictly INK/PAPER.

## Typography

| Role | Font | Size | Licence |
|---|---|---|---|
| Display: FIGHT, names, big numbers | Jersey 25 / Jersey 20 (Sarah Cadigan-Fried) | 25 / 20 px (cap 16 / 12) | SIL OFL 1.1 |
| Card numbers, Roman numerals | Jersey 15 | 15 px (cap 8) | SIL OFL 1.1 |
| Section labels (READING, SPREAD, BOX...) | Jersey 10 at 2x | 20 px (cap 11) | SIL OFL 1.1 |
| Body, effect lines, stats | **DotGothic16** (Fontworks) | 16 px, **8 px advance** (cap 13) | SIL OFL 1.1 |
| Wordmark, boss and Major names | Jacquard 24 (Sarah Cadigan-Fried) | 24 px, 2x for the wordmark | SIL OFL 1.1 |

* All text is drawn with `fontmode = "1"` (no anti-aliasing), glyph by glyph with integer advances, i.e. what a baked bitmap font does. DotGothic16 Latin is a true 8x16 cell, matching the 8x16 ASCII font in the design doc: 56 characters = 448 px, so every card-effect line fits.
* Why not one family: Jersey's tiny sizes drop the leg of "R" and lose "D/M" at 15 px, and VT323 at 6 px advance confuses c/e/o, so each face is used only at sizes where it is unambiguous. The wordmark/boss blackletter is the tarot-print "voice"; the sharp Jersey is the sports-scoreboard "rules of the game" voice.
* Licences: `fonts/OFL-*.txt` are the upstream texts, downloaded from `google/fonts` by `render.py`.

## Layout grid (480x320)

* Margins 16 px left/right (x = 16 and x = 464). Base unit 8 px. Only two text edges: x = 16 and the right margin.
* Card cell pitch **56 px** (card 48 + 4 + 4): cells at x = 20 + 56 i. Six slots end at x = 352; the **FIGHT slab** is x = 360-464 (104 px), same height as a card. Box cards (40x54) sit in the same cells (x = 24 + 56 i).
* Vertical stack (Spread): Enemy band 0-58 (rule at 59, sprite + name + HP + 3 scraps 32x44) / READING 64-77 / SPREAD label 84-95, cards 100-163 / PER ROUND 173-185 / BOX label 192-203, cards 206-260 (Treats wallet on the right) / detail line 1 (Jersey 20) and line 2 (8x16 body) / rule at 299 / footer 304-316.
* Section labels are always `LABEL ........` with a dotted rule to the next edge; the rule is the only divider besides the two solid rules (under the enemy band, above the footer).
* Cursor: **corner brackets** (2 px, 7 px arms) around the card + a **paw** with a black keyline on its lower edge. Brackets, not colour, mean focus. FIGHT is a white slab, so "focused" on it is the same bracket.
* Battle: top band = Chubbs (blackletter name, HP bar with a hatched "just lost" chunk, status icons) and his six scraps (32x44, active one bracketed); stage 58-198 (ceiling beam to floor edge); Domino's four cards at x = 20 + 56 i with the active one raised 8 px and bracketed; right panel = NOW PLAYING (name, tags, effect); footer with HP, Curl and `A 2x  B Skip`.
* I refined the doc's layout in four places (all elements kept): the paw overlaps the card edge instead of costing a row; the Treats counter moved from the footer to a gold wallet block beside the Box row (free space, and money deserves the gold); the Round counter lives in the NOW PLAYING header; the reading chain is a diagonal *staircase* (Number Path made visible) instead of a long strip.

## Cards and icons (all drawn in code, pixel-exact)

* Minor 48x64: number top-left (Jersey 15), stars top-right (7x7), 32x32 window with 1 px frame, element icon bottom-left, charm gem bottom-right. Pips follow classic layouts for 1-10 (24 px Ace, 12 px for 2 and 4, 8 px for 3, 5, 6, 6 px for 7-10).
* Rarity = number of edge lines: none = 1 line, Common = 2 lines, Rare = 2 lines + corner studs, Legendary = 2 px gold edge, Curse = 1 vermilion ring.
* Rat scrap 32x44: halftone paper (13/16 white), torn top/bottom, bite-mark circles, white keyline so it reads on black, no colour. Chewed Major: black card, element colour kept, bite marks.
* Card back: black, double white frame, a **gold cat-eye** (almond with slit pupil) in a dither halo with 8 rays and four corner diamonds.
* Icons: 4 elements 12x12, 5 statuses 12x12, 3 charms 8x8 (Nine Lives is gold), claw (damage) and the two-tone medallion, all hand-authored ASCII bitmaps in `render.py`.

## Animation language (within the hardware limits)

No alpha, no frame buffer, ~6 KB per card-rect redraw, full-screen ~0.85 s. Everything below is rectangle redraws, palette swaps, or solid fills.

| Beat | Treatment | Cost |
|---|---|---|
| Card play | Card lifts 4 px (redraw 48x64 rect twice), 2 frames of **white flash** (fill the card rect `0xFFFF`), then 3 element particles (1 px lines/dots in the element colour: ember, wind streak, drop, crumb). | 2-3 card rects + a few 1-px fills |
| Reading chain | Links appear one by one as chips along a diagonal staircase; each link is **one font size bigger** (8x16 body, Jersey 20, Jersey 25) and the colour steps white, then gold on the last. Chips are solid fills + text, so each is ~1-2 KB of draw. Stars pop beside the gold chip. | tiny |
| Reading line (Spread) | The chain names appear in the READING row; `Catwalk` and its star are gold. No animation needed. | none |
| Crit / big hit | Impact burst (white jagged star, black keyline) with the damage number at **2x** (pre-scaled glyphs) in the element colour; 3 claw wedges over the target; manga speed lines behind the sprites. Shake = move the *sprite rects* 2 px for 4 frames (not the screen). >=30 damage: number blinks 3x by swapping INK/PAPER halo, 3-frame hit-stop. | 2 sprite rects + burst rect |
| Hurt | Target sprite **inverts** for 2 frames (palette LUT swap INK/PAPER in the blit), +2-4 px shake, HP bar's lost chunk is hatched (Bayer 6/16) then eaten. | 1 sprite rect + 1 bar |
| Hiss / Bite Mark | Card tilts back one frame (redraw offset); bite: 8-frame flip where the card squeezes horizontally (1-bit scaling = skip columns) and a bite circle is knocked out of the corner. | card rect |
| Victory / death | Domino stretch = 2 pre-drawn frames; death = ink wipe. | sprite rect |
| Scene transition | **Ink wipe**: 16 px black/white bars sweep the screen in alternating directions (all solid fills, ~30 ms per bar), new scene drawn behind. Moonlight fade-in on the Parlor uses 4 Bayer levels of the 1-bit scene. | fast fills |
| Idle | Cursor paw bobs 1 px every 8 frames; the moon in the attic window doesn't animate (static background, redraw-free). | 12x12 rect |

## Flash and speed budget

* Backgrounds are 1-bit. A full 480x320 scene is **19.2 KB raw**; the attic backdrop in this board measures **5,454 row runs, about 5.5 KB with 1-byte RLE** (it can also be drawn directly as fills). That is 4-8x cheaper than the 40-120 KB of a 64-colour illustration, so the demo can afford ~20 unique full screens (Parlor, Night Path, Stall, Cat Bed, Attic, Pantry, dream rooms, result screens) inside ~120 KB, or fewer screens plus more tiles.
* Sprites (1 bpp + 1 bpp mask): Chubbs 96x96 = 2.3 KB, Domino/Zero/Rat 64x64 = 1 KB each; the doc's 7 rats + 4 NPCs + Chubbs is about 14 KB. Card templates, 12 icons, 12 charm/scrap glyphs: under 10 KB. Fonts (DotGothic16 95 glyphs x 16 B plus 3 Jersey sizes plus Jacquard): about 15 KB. Whole art set well under 120 KB of the 600 KB budget.
* Speed: black ground, white rules, bars, chips, card faces and the colour windows are all hi==lo-byte fills (4x path). Only dithered scenes and sprites are slow, and they only redraw on scene change or as small rects. This is the fastest of the four directions on this hardware.
* Compositing under sprites: the backdrop is 1-bit, so the MCU can store it once (19 KB) and re-blit a stage slice behind a moving sprite; busy dither is confined to the moonbeam, ceiling shade and floor, away from sprite paths.

## What is AI-generated vs drawn in code

* **AI (PixelLab `create-image-pixen`, 4 calls, trial credit, `client.spent` printed 0.0):** Domino 64x64, Chubbs 96x96, Gray Rat 64x64, Zero 64x64. Prompts (see `gen_sprites.py`) asked for "pure 1-bit black and white ink illustration, ordered dithering, Return of the Obra Dinn look". Post-processing in `render.py`: contrast curve then 4x4 Bayer threshold to strict INK/PAPER; 1 px white rim-light added only beside black outline pixels so black fur reads on the black stage; rat flipped to face the player; Zero's linework turned into a dotted checker (ghost, no alpha); sprite inversion for hurt frames.
* **Code (Pillow, pixel-exact):** everything else: all cards, pips, icons, statuses, charms, medallions, scraps, card back, the Sun portrait, attic backdrop, tiles, UI chrome, bars, cursor, chips, bursts, speed lines, claw marks, text, sheet and storyboard.
* One PixelLab call remains unused.

## Risks

1. Pure black ground plus white text on a TFT can bloom or smear at small sizes; 1 px dotted rules are the first thing to blur. Keep dotted rules optional.
2. DotGothic16 is thin (1 px strokes). If a unit's panel is dim, switch body text to Jersey 20 and shorten lines (loses the 56-char guarantee).
3. 1-bit sprites need good source art: PixelLab output is usable only after dithering, and Domino (44x60 inside 64x64) is small against Chubbs. A hand-cleaned pass on the four sprites is the biggest quality upgrade available.
4. Colour scarcity is the idea, but if elements need more than 4 hues later (Court cards, Chapter 2-3), add tints by dithering the accent with paper, not new palette entries.

## Credits

* Sprites: PixelLab (create-image-pixen). Fonts: Jersey 10/15/20/25, Jacquard 24 (Sarah Cadigan-Fried), DotGothic16 (Fontworks), all SIL OFL 1.1 via the `google/fonts` repository.
* Inspiration, not assets: Return of the Obra Dinn, Playdate, ink manga, tarot woodcuts. Design checklists from taste-skill (`critique.md`, `tells.md`, `colour.md`, `type.md`, `layout.md`) and ui-ux-pro-max applied to a 480x320 handheld: one primary action per screen, visible focus, always-on button hints, contrast first.
