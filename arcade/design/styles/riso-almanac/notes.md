# Direction 04: Woodcut Riso Almanac

**Pitch.** *Nine Lives Arcana* as an 18th-century folk almanac printed on a risograph: warm newsprint, carbon-black ink, two spot inks (fluorescent vermilion and teal), a deliberate 1-px misregistration, halftone and woodcut hatching for shade. Every screen is a broadside page with hard rules, blackletter headlines, printed plates for cards and dotted leader lines like a table of contents.

## Art-direction brief

- **One idea:** the game is a printed object. Cards are almanac plates, the HUD is page furniture, damage is a woodcut starburst.
- **Ink logic (colour rules, so it never looks muddy):**
  - Black ink = all linework, text, hard shadow. Always on top.
  - **Vermilion = action and heat.** Cursor, FIGHT, the focused card, Power, damage, Fire, the playing side.
  - **Teal = information and cool.** Enemy plates, Water, Reversed cards, section tabs, Domino's halo.
  - Overprint (vermilion x teal) = plum, reserved for Rare rarity. Teal x straw = moss, reserved for Earth.
  - Warm = Domino and cards. Cool gray-green = rats and scraps (matches the design doc's §17 warm/cool rule).
- **Misregistration:** the spot-colour layer of headlines, pips, plates and sprite shadows is offset 1-3 px from the black layer. Used on large or iconic shapes only, never on body text.
- **Shade:** ordered Bayer dither (halftone) and 1-px diagonal hatching. No smooth gradients, no alpha.
- **Typography hierarchy:** blackletter for names and exclamations (Fire Claw, Gray Rat, Fight, Catwalk!), tiny letter-spaced capitals for section labels, a clean condensed pixel face for everything the player has to read.
- **Handheld habits:** one primary action per screen (FIGHT / A hint is always the loudest vermilion block), cursor = lifted card + 2-colour frame + paw print (three independent cues), button hints always in the black footer, body cap height 9 px, numerals 11 px.

## Palette (23 colours, all RGB565-exact; the PNGs contain 20 to 23 of them)

| name | hex | RGB565 | role |
|---|---|---|---|
| ink | #000000 | 0x0000 | carbon black, linework, text, big bars (fast fill) |
| paper | #F7DFB5 | 0xF6F6 | newsprint, dominant background (**fast fill, high byte = low byte**) |
| bone | #FFF3DE | 0xFF9B | highlights, white fur, panel fill |
| paper2 | #E7CB9C | 0xE653 | empty slots, floor |
| paper3 | #C6A673 | 0xC52E | foxing, plank seams |
| verm | #FF4929 | 0xFA45 | spot ink 1 |
| verm_d | #AD2021 | 0xA904 | misregistration shadow, counts |
| verm_t | #FFAE8C | 0xFD71 | Fire card base, sunburst |
| teal | #00868C | 0x0431 | spot ink 2 |
| teal_d | #00455A | 0x022B | tabs, card back, shadow of teal plates |
| teal_t | #94CFC6 | 0x9678 | Water card base, enemy plate |
| plum | #63244A | 0x6129 | overprint, Rare ring |
| straw | #FFE77B | 0xFF2F | sun, cheese, active-link text |
| straw_t | #FFEFAD | 0xFF75 | Air card base |
| gold | #DEA229 | 0xDD05 | Legendary ring, bell, coin |
| moss | #528E4A | 0x5469 | Earth ink, Catnip |
| moss_d | #295939 | 0x2AC7 | Earth shade |
| moss_t | #BDD38C | 0xBE91 | Earth card base |
| scrap | #94A68C | 0x9531 | rat scraps |
| scrap_d | #526952 | 0x534A | scrap shade |
| scrap_t | #C6CFAD | 0xC675 | scrap window |
| cool | #ADC3CE | 0xAE19 | Reversed card base |
| cool_t | #D6E3E7 | 0xD71C | Reversed window |

Fast (high byte = low byte) fills used for large areas: `0xF6F6` paper (about 60% of every screen) and `0x0000` ink (top/footer bars, reading strip, panels). 64-colour budget: 23 used.

## Fonts

| use | font | size | licence |
|---|---|---|---|
| display / names / exclamations | **Jacquard 24** (Sarah Cadigan-Fried) | 24 px (cap 15), also drawn 2x for the sheet masthead | SIL OFL 1.1 (`fonts/OFL-Jacquard24.txt`) |
| body, numbers, hints | **Jersey 10** (Soft Type Project) | 16 px (cap 9) body, 20 px (cap 11) numerals, 13 px (cap 7) for letter-spaced capital labels and card numbers on 40x54 cards | SIL OFL 1.1 (`fonts/OFL-Jersey10.txt`) |

Rendered with Pillow `fontmode = "1"` (no anti-aliasing). Note: in Jersey 10 at 13 px a "2" looks like a "Z", so every line containing digits that matter (`+2`, `x2`, `30/36`) is set at 16 px; 13 px is used only for capital labels and single card digits. All card text lines are well under 56 characters.

## Layout grid

480x320, 8 px baseline, 6-px outer margin. Hard rules (2 px ink) separate bands exactly like a page.

**Spread** (every element of §6.5 kept, one refinement: the PER ROUND row became a right-hand sidebar "forecast column", which frees a whole row for taller cards and a labelled Box)

| y | band |
|---|---|
| 0-58 | enemy band: portrait plate 56x52, blackletter name, HP tally bar (1 segment = 1 HP, tick every 5), 3 scrap cards 40x54, double rule |
| 61-79 | READING strip: vermilion tab + chain text separated by square dingbats |
| 82-165 | THE SPREAD: 6 slots x 56 px, cards 48x64, FIGHT block 64x64, focus card lifted 4 px, paw cursor below |
| 183-246 | THE BOX: 6 slots, cards 40x54, colophon (Night I / The Dusty Attic) |
| 249-293 | detail plate: blackletter card name, element roundel, `Wands 4 *1 Upright`, effect line, dotted leader to the POWER stamp |
| 296-320 | footer: vermilion rule, `Domino HP 30/36 Treats 14`, `A Pick up  B Menu  C Info` with round button glyphs |
| x 418-474 | PER ROUND sidebar: DMG (vermilion block) / SINGE / HEAL / CURL, 36 px rows with dotted separators |

**Battle**: top bar = boss name (blackletter) + HP bar with hatched "just lost" segment + statuses; enemy hand of 6 mini cards on a wooden shelf; diptych stage (Domino 64x64 on a teal disc, Chubbs 96x96 on a vermilion sunburst); central ribbon for the reading chain; damage starburst with the 2x numeral; player card row (active card lifted 4 px with a frame) and Domino panel; footer `A 2x  B Skip`.

## Animation language (all within the hardware limits: opaque blits, no alpha, no frame buffer)

- **Card play:** card lifts 4 px (erase = redraw 1 strip of slot background), 2 frames of paper-flash (swap the art window to `bone`), 4-6 element sparks as 2x2 / 3x3 vermilion rectangles. Cost: one 48x68 rectangle per frame.
- **Reading chain:** a vermilion 3x3 paw-print trail pops between the two cards (4 tiny rectangles), the Reading name floats above on an ink tag. The banner uses the colour ramp bone, straw, vermilion, gold; each link is set in a bigger face (Jersey 16, Jersey 16, Jacquard 24). The ribbon is 3 filled rectangles + 2 polygons, no bitmap.
- **Crit:** 2-px screen shake for 4 frames is done by redrawing the stage rectangle offset (paper bg is a fast fill), a `MEOW!` starburst bubble in the same style as the damage burst.
- **>= 30 damage:** the numeral is the 20-px glyph scaled 2x (pre-baked as one 40x30 bitmap), inside a 14-point starburst; blink 3 times by toggling the vermilion misregistration layer, hold 3 frames.
- **Hurt:** HP bar segments flash vermilion/bone (only the bar rectangle is redrawn), portrait jitters +/-2 px; the spot-colour shadow of a sprite is the cheap "hit" cue: shift it 2 px.
- **Scene transition:** a vertical "page turn": ink strip wipes across at fast-fill speed (`0x0000`), 6-8 steps of 60-80 px columns, then the next page is drawn behind it. The only slow operation is the 0.85 s backdrop bitmap, hidden under the wipe.
- **Idle cursor:** paw bobs 1 px every 250 ms (16x17 sprite, one small restore rectangle).

## Flash estimate (budget 600 KB)

Measured by `render.py` on the real pixels (byte-RLE, 1 count byte + 1 index byte per run, 4 bpp raw for comparison):

| asset | raw 4 bpp | byte-RLE |
|---|---|---|
| attic backdrop, 480x320 (planks, window, lamp, floor; no sprites, no UI) | 75 KB | **27 KB** |
| battle screen complete (dithered sprites + UI), only for reference | 75 KB | 66 KB |

Spread, Path, Shop, Result and Cat Bed screens need **no** illustrated bitmap: they are flat paper + ink rules + small plates, drawn with rectangles (fast fills). Estimated total for the demo: backdrops 3 x ~30 KB = 90 KB; four AI sprites (Domino, Zero, Gray Rat 64x64; Chubbs 96x96) about 4 KB each as 4 bpp = 14 KB plus a few animation frames (~30 KB); 48x64 card bitmaps at 4 bpp = 1.5 KB each, with the 4 element x 9 pip layouts built from 9x9 pips at runtime; icons 12 x 70 B; paw 100 B; fonts (Jersey 16/20/13 + Jacquard 24 subsets) about 25 KB. Total is roughly 200-250 KB, comfortably inside 600 KB. The paper backdrop (`0xF6F6`) and ink (`0x0000`) are both "fast" colours, so most pixels on screen are cheap.

## What is AI-generated, what is drawn in code

- **PixelLab (4 calls, `create-image-pixen`, see `gen_sprites.py`):** Domino 64x64, Chubbs 96x96, Gray Rat 64x64, Zero 64x64, prompted for "woodcut linocut, black ink, crosshatch". Post-processing in `render.py` (`sprite()`): luminance becomes a 2-ink Bayer dither (hard threshold for Domino so his coat is a bold two-tone silhouette; mid-grey halftone for rats; cheese and crown colours are remapped to straw and gold; Zero is printed in teal-only ink to read as pale and spectral without alpha). A spot-colour silhouette is printed 2-3 px offset behind each sprite (misregistration).
- **Code (Pillow, native resolution, pixel-exact):** all cards (frame, ring, window, pips, stars, gems, bites, back), the 12 icons, paw cursor, UI, bars, ribbons, starbursts, sunburst, attic backdrop, tiles, storyboard frames, style sheet.
- **Hand-fixable later:** pip glyphs and icons are 9x9 / 11x11 ASCII bitmaps at the top of `render.py` (`PIP`, `ICON_ASCII`), easy for a pixel artist to polish.

## Why it fits the game and the hardware

- A tarot deck-builder is *about* printed cards; the almanac frame makes every UI element a legitimate printed thing (rules, plates, tabs, folio lines) instead of a skinned web panel.
- Domino is already half black, half white: a woodcut silhouette is the natural way to draw him and he pops on teal.
- Everything is flat ink + dither: no alpha, no gradients, 23 colours, mostly rectangles in fast fills. Backgrounds compress to ~27 KB.
- The misregistration trick is free at runtime (just draw the spot layer 1 px off), and it is the signature of the style.

## Risks

- Dither on sprites over striped backdrops can shimmer; keep busy areas behind sprites to the flat teal / vermilion plates (as drawn).
- Blackletter caps (Jacquard) are hard to read as all-caps; the style only uses it in mixed case for names and short exclamations.
- Jersey 10 at 13 px confuses `2` and `Z`; keep digits at 16 px or larger.
- The warm paper (0xF6F6) tints all whites; true "white" is `bone` (0xFF9B) which is not a fast fill, so keep it to small areas.
- Cards are dense at 48x64; the Air pip is a sparkle and the Reversed state relies on the flip + cool inks + the small down-triangle.

## Credits

- Game design: the project's game design document (provided).
- Fonts: Jacquard 24 by Sarah Cadigan-Fried, Jersey 10 by the Soft Type Project, both SIL OFL 1.1 via Google Fonts.
- Sprites: PixelLab `create-image-pixen` (4 generations), recoloured and dithered by `render.py`.
- Everything else: `render.py` (Pillow).

## Reproduce

`python render.py` (downloads the two TTFs into `fonts/` if missing, reads `raw/*.png`, writes `spread.png`, `battle.png`, `spread@2x.png`, `battle@2x.png`, `sheet.png`, verifies RGB565-exactness and prints the flash estimate). `gen_sprites.py` regenerates `raw/` (needs `PIXELLAB_API_KEY`; not required for rendering).
