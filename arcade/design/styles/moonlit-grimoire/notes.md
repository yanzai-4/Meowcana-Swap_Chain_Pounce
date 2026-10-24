# Moonlit Grimoire — art direction for *Nine Lives Arcana*

**Pitch.** A luxurious occult tarot deck at midnight: deep indigo ground, antique-gold filigree, moonlight-silver highlights, and one candle-amber accent. Calm, ornate and premium. Gold marks focus and rarity only, never decoration everywhere.

Files: `spread.png`, `battle.png` (480x320), `spread@2x.png`, `battle@2x.png`, `sheet.png` (960x1504 style sheet), `render.py` (+ `pal.py`, `icons.py`, `ui.py`, `sheetgen.py` helpers), `gen_sprites.py` (the only network code, run once), `raw/` (4 PixelLab sprites), `fonts/`.

## Brief (to self)
- Mood: a fortune-teller's parlor and a dusty attic at night, lit by one candle and one window of moon. The cats are the warm, living thing in a cold blue room; the rats are cold gray-green.
- The deck is the hero: every card is a small tarot print with a gold inner line, plate and corner studs. UI chrome is quiet: 1-px gold-brown rules, a diamond in each divider, flourish corners only on panels that matter.
- One primary action per screen, shown by the only big plaque (FIGHT) or the only lifted/bracketed card (battle, spread cursor). The amber accent is reserved for: cursor, Power numbers, chain tier, candle, damage.
- Handheld rules: body text is VT323 16 px (cap height 9, 8 px advance), always silver on indigo (contrast > 7:1); button hints are always in the footer as lettered gems (`A Pick up  B Menu  C Info`, battle `A 2x  B Skip`); cursor = 4 amber corner brackets + paw, readable at arm's length; empty slots are dotted outlines.

## Why it fits the game
- Tarot is the subject: Rider-Waite-style plates, Roman numerals, a cat-eye moon back, element colors on card faces that stay distinguishable on indigo (orange-red / pale yellow / blue / green all sit well against it).
- Domino's black-and-white coat and Zero's pale spectral fur read strongly on indigo; the gray-green Rat scraps and Chubbs are clearly "other" (cold green vs. warm candle).
- Cards carry the visual weight, so backgrounds can stay flat. This is cheap on flash.

## Why it fits the hardware
- Dominant background is `night1 = #29244A = 0x2929` (a fast-fill color: high byte = low byte). `royal = 0x3131` (card back field) is also fast. Panels and the bottom half of the battle screen are solid fills of these. Texture is a sparse 32x32 star-dust tile (6 single pixels) over the fast fill, 0 alpha.
- No alpha anywhere. "Glow" is a dithered checker (candle halo), moonbeam is a flat polygon, shadows are flat ellipses.
- Every pixel is RGB565-exact (verified in `render.py`: it asserts `snap(c) == c` for every color of every output). Each 480x320 screen uses 39 (spread) / 41 (battle) colors; the sheet 48; the full palette 49.
- Sprites are opaque rectangles over flat floor/wall areas; busy areas (window, shelves, rafters) are away from where sprites stand. Domino stands on the floor strip (flat `night0` with 1-px plank lines) inside a flat `night2` moonbeam.

## Palette (RGB565-exact, bit-replication expansion)
| name | hex | RGB565 | use |
|---|---|---|---|
| night0 | #100821 | 0x1044 | ink, outlines, panel fill |
| night1 | #29244A | 0x2929 | **ground (fast fill)** |
| night2 | #393463 | 0x39AC | moonbeam, raised bits, buttons |
| night3 | #524D84 | 0x5270 | dotted empty slots, star dust |
| night4 | #7B75A5 | 0x7BB4 | muted captions |
| silver1 | #9CA6C6 | 0x9D38 | secondary text |
| silver2 | #CECFE7 | 0xCE7C | body text |
| moon | #EFF3FF | 0xEF9F | flash, highlights |
| gold0 | #5A3C21 | 0x59E4 | dividers, wood |
| gold1 | #8C6529 | 0x8B25 | panel rules |
| gold2 | #C69639 | 0xC4A7 | filigree, button rims |
| gold3 | #E7C363 | 0xE60C | titles, labels, rarity gold |
| gold4 | #FFE394 | 0xFF12 | focus text, damage |
| amber0 | #843821 | 0x81C4 | wood, shade |
| amber1 | #CE6129 | 0xCB05 | accent shade |
| amber2 | #F79A31 | 0xF4C6 | candle, paw, Singe |
| amber3 | #FFCF73 | 0xFE6E | cursor, Power, chain |
| fire0/1/2 | #6B2029 / #C64131 / #EF794A | 0x6905 / 0xC206 / 0xEBC9 | Fire card |
| air0/1/2 | #847542 / #DECF84 / #F7EFBD | 0x83A8 / 0xDE70 / 0xF777 | Air card |
| water0/1/2 | #21347B / #396DC6 / #84B2EF | 0x21AF / 0x3B78 / 0x859D | Water card |
| earth0/1/2 | #214939 / #4A8A52 / #8CC37B | 0x2247 / 0x4C4A / 0x8E0F | Earth card |
| rfire1, rair1, rwater1, rearth1 (+ dark) | #735194 / #94A6C6 / #425D9C / #427573 | see `pal.py` | Reversed (cool) |
| rat0-3 | #293831 / #52695A / #8C9E7B / #B5C39C | 0x29C6 / 0x534B / 0x8CEF / 0xB613 | Rat scraps, Rat |
| royal / royal1 / royal0 | #31248C / #4A38AD / #18145A | 0x3131 / 0x49D5 / 0x18AB | card back, window sky |
| blue / purple / red | #5279DE / #9C61D6 / #DE384A | 0x53DB / 0x9B1A / 0xD9C9 | rarity rims (Common / Rare / Curse) |
| heal / pink | #73D784 / #CE7D84 | 0x76B0 / 0xCBF0 | Domino HP bar, rat ears |

(Reversed palette exact values: `pal.py`, keys `r<element>0/1`.)

## Fonts and licenses (all SIL Open Font License 1.1, from github.com/google/fonts)
- **Jacquard 24** (24 px native, no AA): display names and titles in mixed case only (Fire Claw, Chubbs, Fight). Blackletter capitals are illegible in all-caps, so button labels are mixed case (`Fight`), not `FIGHT`.
- **VT323** (16 px native): all body text, stats, reading lines, footer. 8 px advance gives about 56 chars per 448 px.
- **Jersey 10** (20 px = 2x native, scaled 2x): damage numbers only (the old-style digits of Jacquard are hard to read).
- **Silkscreen** (8 px): the A/B/C letters on button gems and callout numbers on the sheet.
Rendered with `ImageDraw.fontmode = "1"` (1-bit, no anti-aliasing) at native sizes. Baked-bitmap cost is small: about 95 glyphs x 4 fonts.

## Layout grid
- 480x320, 16-px safe margin left/right, 4-px outer frame with flourish corners. Rows (y): enemy 6-62 / divider 66 / READING 68-84 / divider 88 / SPREAD header 90-101 + cards 106-170 / paw 173-184 / BOX 186-240 / divider 244 / detail panel 249-290 / footer 296-320. This keeps every element of §6.5 (enemy row, READING, spread + FIGHT, per-round stats, box row, selected-card detail, footer).
- Refinements: per-round stats moved onto the SPREAD header line (frees 18 px so the box row gets breathing room); FIGHT is a 92x64 plaque (vs 64) with a cat-eye moon; slots are 58 px pitch (6x58 + 8 + 92 = 448). The right side of the Box row holds a small candle-and-moon vignette (code-drawn) instead of dead space.
- Battle: top plate (enemy name, HP, statuses, threshold tick at 50% for *Still Hungry*) y0-29; enemy scrap row top right y34-88 (40x54 cards, 44 px pitch); stage y30-232 with Domino left / Chubbs right standing on a floor band (y196-232) with their feet at y222, 10 px above the tray (Chubbs about 90 px tall vs Domino about 48); chain popup upper-left (y96-142) so no face is covered; bottom band y232-296: Domino's row (40x54, active card lifted 4 px with a gold glow bracket) and a READING panel; footer with HP bar and `A 2x  B Skip`.
- Cards: 48x64 with 2-px rarity/ink rim, 1-px filigree line, 32x32 plate with gold edge. Box/scrap size 40x54 uses a 26x26 crop of the plate and 7x7 icons.

## Animation language (all within the hardware budget: dirty-rect redraws of card-sized rectangles, no full-screen redraw)
- **Card play:** active card jumps up 4 px (redraw 40x58 rect + gold bracket), 2 frames of full moon-white flash, then 4-6 element particles (2x2 px amber / fire / silver sparks) rising 12-24 px and dying in 6 frames. A diamond gem slides along the gold link between consecutive cards.
- **Reading chain:** a gold tab above the popup (`CHAIN x3`) climbs the tier colors white -> yellow -> orange -> red -> gold; floating name text scales 1x -> 2x (VT323 16 -> 32 are both baked) per link; the popup is one 188x52 panel redrawn only when the text changes.
- **Crit / big hit (>=30):** screen shake 2 px x 4 frames (shift only the stage rect, not the footer); the damage number is Jersey 20 at 2x (pre-baked "0-9" bitmaps), three flashes between gold4 and moon, 3-frame hit-stop; three diagonal moon-white slash lines over the target; `MEOW!` bubble reuses the popup panel.
- **Hurt:** HP bar flashes `red` for 2 frames, the sprite shifts +-2 px for 4 frames (blit the sprite at an offset over the flat floor; the stage strip behind it is flat so no background restore is needed above the floor line).
- **Scene transition:** card-flip wipe from the center out to both sides, 8 columns of 60 px, each column filled with `night1` (0x2929 fast fill) before the new scene's first blit; the cat-eye moon blinks once (open -> slit -> open) as a loading cue. Victory: Domino stretches (2-frame sprite swap) while a crescent-and-stars strip slides under the title.
- Calm default: nothing moves while the player is choosing except a 1-frame twinkle on one star-dust pixel every ~2 s and the candle flame (2 frames).

## Flash estimate (backgrounds and sprites; from the actual renders)
- Spread screen: no illustrated background. Fast solid fills + the 32x32 star-dust tile (2 KB as RGB565, or 1 KB at 4 bpp) + hand-drawn flourish glyphs (~10 x 10 px each, < 0.5 KB total).
- Battle attic scene (480x232, 23 colors): ~13 KB as byte-RLE with a 32-entry palette, ~55 KB at plain 4 bpp (if reduced to 16 colors). One scene for the whole demo, plus a cheaper reuse (window, shelf, floor crops) for the Dusty Attic path screens.
- Sprites at 4 bpp, uncompressed: Domino 2 KB, Zero 2 KB, Gray Rat 2 KB, Chubbs 4.5 KB (plus a 16-color palette each, 32 B). With a few extra frames (idle/hurt/attack) per character: roughly 40 KB.
- Cards are drawn at runtime from the 4 element icons (9x9 and 7x7), 5 statuses, 3 charms, the paw, flourish corner and 8 art plates; icons total < 1 KB. Full demo estimate for this direction: well under 150 KB of art, leaving room for 3-4 more illustrated full screens (Moonnap Parlor, Night Path map, Title, Result) at ~15-60 KB each.

## AI-generated vs drawn in code
- **AI (PixelLab `create-image-pixen`, 5 sprites generated in total, 4 used: the first quadruped Domino was replaced and is kept only as `raw/domino_quadruped_unused.png`):** Domino 64x64, Zero 64x64, Gray Rat 64x64, Chubbs 96x96. Post-processed in `render.py`: alpha thresholded to 1 bit, colors mapped (no dithering) to the Moonlit palette, Domino is the chosen Apprentice Seer (starry robe and hat, black/white tuxedo fur from the Fortune-Teller concept; PixelLab edit pass `raw/domino_merge_b.png`), facing right. The tarot card he holds is repainted in code (`finalhand.py`) as a miniature card back (royal field, gold border, cat-eye moon) into `raw/domino_final_hand.png`; fingers and gloves stay in front. An AI alternative is `raw/domino_final_ai.png`.
- **Drawn in code (Pillow, pixel-exact):** all frames, panels, flourishes, dividers, cards (pips, Major portrait of the Sun with the sunbathing cat, scrap arts, bite marks, card back), all icons, the paw cursor, bars, button gems, the attic scene (window, rafters, shelves, candle), star-dust tile, popups, sparkles, and the storyboard. Nothing in the 480x320 images is a raster from a generator except the four sprites.

## Risks on this hardware
- Blackletter caps are not readable: titles must stay mixed case and ≥ 24 px; never use Jacquard for stats or all-caps.
- 40x54 cards are dense (7x7 pips, 1-px filigree). The 1-px inner line and corner studs may shimmer on a cheap TFT at an angle; the 2-px rim and the big number carry readability.
- Over-using gold would flatten the hierarchy; keep amber for cursor/Power/damage and gold for rarity and focus.
- The dithered candle halo and moonbeam polygon cost redraws if animated; keep them static in the scene bitmap.

## Credits
- Sprites: PixelLab `create-image-pixen` (generated for this project, trial credits, no spend reported by the client).
- Fonts: Jacquard 24 (Sarah Cadigan-Fried), VT323 (Peter Hull), Jersey 10 (Sora Sagano), Silkscreen (Jason Kottke), all OFL 1.1 via Google Fonts.
- Everything else: code-drawn in this folder by `render.py`.
