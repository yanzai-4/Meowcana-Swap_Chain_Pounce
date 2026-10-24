# Direction: Bell Tower Stained Glass

**Pitch.** Nine Lives Arcana as cathedral glass seen at midnight from inside Wickton's silent bell tower: saturated jewel cells (ruby / topaz / sapphire / emerald) held by bold black lead came, glowing against near-black violet stone. Cards are leaded glass panels, characters are saints in arched windows, text always sits on solid dark stone plates. The only things that glow are the things you can act on (cards, FIGHT, the cursor, the active chain).

## Art-direction brief
- **One idea, applied everywhere:** *glow = interactive.* Chrome (plates, rows, footer) is dark stone (`0x2929`, `0x0808`); colour is reserved for cards, gems, tabs and the primary button. Squint test: two masses (dark chrome, bright card row) plus one accent (FIGHT).
- **Lead is the style.** Every coloured thing has a 1 px black came outline; glass cells are diamond quarrels (diagonal lead lattice) picking one of three tones of a ramp. No gradients, no dithering, no alpha.
- **Wayfinding by jewel colour.** Section tabs (Reading ruby, Spread topaz, Per round amethyst, Box emerald, Scraps gray-green) and button chips (A ruby = Do, B sapphire = Back, C emerald = Info) keep the same colour language in every screen.
- **Warm vs cool (doc §17).** Warm: Domino, fire/topaz, candle-gold accents. Cool green-gray: rats, scraps. Moon silver/lilac for highlights and the night.
- **Handheld habits.** One primary action per screen (the ruby FIGHT lozenge, with an A chip), obvious focus (gold corner brackets + paw under the card, raised card in battle), footer always carries `A / B / C` hints with colour-coded chips, body text cap height 8 px, nothing relies on colour alone (Reversed = flipped art + ▼ mark + cool ramp; selected = brackets, not just a tint).

## Screens
- `spread.png` / `spread@2x.png` — Spread screen per §6.5, all elements kept (enemy row with Gray Rat, HP, three scrap cards; READING line; Spread row `[Fire 3][Fire 4][Air 5 ▼][Water 3][--][--]` + FIGHT; paw cursor on Fire 4; per-round stats; Box row; Zero's tip; selected-card detail; footer). Label text is mixed-case in the gothic face ("Fight", "Reading", "Spread") because gothic capitals hurt legibility at 12–16 px.
- `battle.png` / `battle@2x.png` — Domino (64×64 window, lunging) vs Chubbs (96×96 window, hit by three Fire Claw slashes) in the pantry: Chubbs HP with white "ghost" of the last hit, six scrap cards, reading popup `Nuzzle +2 → Step +2 → Catwalk!` with escalating size/colour, `-9` damage number, Domino's row with the active card raised and bracketed, tail-line link between the chained cards, `A 2x  B Skip`.
- `sheet.png` — palette, type, card anatomy, icons, characters at 2×, background/tile samples, 4-frame storyboard.

## Palette (51 colours, all RGB565-exact, the screens use 39/41 of them)
Hex is the 888 expansion of the 565 value (bit replication); 565 word in brackets.

| Group | Colours |
|---|---|
| Ground (fast fills ★) | lead `#000000` (0x0000) ★ · night `#080042` (0x0808) ★ · stone `#29244A` (0x2929) ★ · stone2 `#524994` (0x5252) ★ · ink `#181031` · slate `#6B6D9C` |
| Light | silver `#B5BADE` · moon `#CEDBFF` · cream `#EFE7C6` · white `#EFF3FF` |
| Ruby | `#630C29` `#C61C39` `#FF717B` |
| Fire | `#731418` `#E74D18` `#FFA24A` |
| Topaz / gold | `#8C5D08` `#E7AA21` `#FFE784` |
| Air (pale yellow) | `#735918` `#F7DF6B` `#FFF7BD` |
| Sapphire / Water | `#10186B` `#295DDE` `#84C3FF` |
| Emerald / Earth | `#083C29` `#21964A` `#7BDF84` |
| Amethyst (rare) | `#421C7B` `#9455DE` `#CEA2FF` |
| Reversed ramps (cool) | fire `#29185A #6B4DB5 #AD96E7` · air `#18415A #4A96AD #9CE3E7` · water `#08284A #107194 #63C7DE` · earth `#182C39 #4A717B #94BEB5` |
| Rat scrap | `#293431 #6B7D63 #ADBA94` |
| Skin / wood | rose `#E78294` `#9C3863` · wood `#422831` `#7B5142` · tan `#CEA673` |

Rarity ring: none white · common sapphire-light · rare amethyst · legendary topaz-light · curse ruby. Element base: Fire orange-red, Air pale yellow, Water blue, Earth green (strips + side glass), art window = darkest tone so pips glow.

## Fonts (baked as pre-rendered 1-bit bitmaps, `ImageDraw.fontmode = "1"`)
| Use | Font | Sizes | License |
|---|---|---|---|
| Titles, names, tabs, FIGHT | **Jacquard 12** (Sarah Cadigan-Fried) | 16 / 24 / 48 px | SIL OFL 1.1 |
| Body, numbers, card numerals, damage | **Pixelify Sans** (Stefie Justprince) | 12 body (cap height 8), 16, 24, 32 | SIL OFL 1.1 |
| Sheet captions only (never in game) | **Silkscreen** (Jason Kottke) | 8 | SIL OFL 1.1 |

Rules: the gothic face is for words in mixed case only (its capitals and digits are decorative, not readable — digits are never set in Jacquard); everything numeric is Pixelify. Card effect lines ≤ 56 chars (the longest on the mock is 44). Text over glass is always lead-outlined and short (numbers, tab labels); sentences live on night plates.

## Layout grid (480×320)
Spread: enemy row y 0–66 (portrait window 64×64 at x 8) · READING plate y 67–86 · Spread tab + row y 87–167 (cards 48×64 at pitch 58 from x 14, FIGHT lozenge 100×64 at x 366) · paw y 169 · per-round plate y 183–199 · Box tab + row y 203–257 (40×54, pitch 44) with Zero's tip plate at x 326 · detail plate y 260–296 · footer y 298–320. Margins 8 (cards 14), gutters 8–10; text baselines on a 12 px rhythm; every plate = lead / stone highlight / night fill with gold corner studs.
Battle: Chubbs bar y 3–28 · enemy scraps (32×44) y 32–76 · popup y 82–134 · stage y 80–246 (shelves, windows on stone ledges, floor with colour-pool planks) · Domino cards y 255 (active at y 248) · status plate y 252–316.

## Animation language (within the hardware: only card rects ≈ 6 KB and a float-text rect are redrawn; no alpha, no full-screen redraw)
- **Cursor:** gold corner brackets + paw; 2-frame bob of the paw (±1 px). Pick-up: card lifts 4 px, original slot shows the empty dashed plate.
- **Card play:** lift 4 px → 2-frame white flash over the 32×32 art window (solid fill, no blending) → element sparks (1–3 px squares in fire/air/water/earth light tones, lead-outlined).
- **Reading chain:** gold tail-line with diamond node drawn between the two cards (re-blit of two card rects + a thin line), floating name in white; each extra link steps size and colour: white 12 px → yellow 16 px → orange Jacquard 24 px → red → gold, per §6.11.
- **Crit:** 2 px × 4-frame shake of the card rect/portrait windows (blit offsets) + "Meow!" plate; ≥30 dmg: number ×2 size, 3 flashes (white/orange alternate), 3-frame freeze.
- **Hurt:** HP bar white-flash one segment then drains; the 96×96 / 64×64 portrait windows jitter ±2 px; a ruby claw/bite overlay is a one-colour polygon.
- **Hiss:** two cards tilt back by 2 px alternating, a 12×12 arched-cat glyph appears on a night plate between them.
- **Scene transition:** a "lead wipe" — black came lines sweep over the screen as 8 px diagonal strips (fast-fill 0x0000 strips are the cheapest draw), then the new scene's static layer redraws once (≈0.85 s worst case, hidden under the wipe). Night-ends/Bells: 9 bell icons in the Parlor go out one by one.

## Why it fits the game
Tarot is already stained glass: arcana are icons, Majors are saints, the Fool's Journey is a procession of windows. The silent Wickton bell tower gives a diegetic reason for the leaded night. The cats-as-saints joke (Domino as a tuxedo saint, Chubbs the gluttonous gargoyle king, Zero a ghost in a rose window) matches the game's tone, and lead lines give strong silhouettes so a 48×64 card reads at arm's length.

## Why it fits the hardware
- **Fast fills:** the chrome is 0x2929 (stone), 0x0808 (plates), 0x0000 (lead) and 0x5252 — four of the 4×-fast colours; measured coverage is 82% of the Spread screen and 71% of the Battle screen (the rest is cards, sprites and the floor).
- **No alpha:** glow comes from flat bright cells next to black, never blending. Light pools on the floor are tinted plank cells; the white "flash" is a solid rect.
- **Sprites are opaque rectangles by design:** all four characters are *windows* (arched / round glass with their own lead frame), so blitting a 64×64 or 96×96 rect over the stone background is the artwork, not a compromise; the compositing background is flat stone.
- **Busy glass stays small:** diamond quarrels are only on cards (48×64 and 40×54, drawn once as sprites), tabs, the FIGHT lozenge and character windows. Large surfaces are flat.

## Flash cost (estimates; zlib on 6-bit indexed data as an LZ/RLE proxy — real packer will differ)
| Asset | Raw RGB565 | Indexed 16-colour, compressed |
|---|---|---|
| Spread screen as a full image (not needed; built from rects, tabs, tiles) | 307 KB | ~11 KB if it were baked |
| Battle background (stone + shelves + floor, **no** sprites/cards) | 307 KB | ~12 KB baked, or ≈ 3 KB as draw-command list |
| Domino / Zero / Gray Rat windows 64×64 | 8 KB each | ~1.0–1.2 KB each |
| Chubbs window 96×96 | 18 KB | ~2.1 KB |
| Card template + 10 pip layouts + elemental icons, scrap bases | — | < 8 KB (drawn from 1-bit masks + palette) |
| Rose-window medallion (title / transitions) | 5 KB | ~0.6 KB |
| Fonts (Jacquard 16/24/48 + Pixelify 12/16/24/32, ASCII) | — | ≈ 25 KB |

Total for the demo style layer ≈ 60–90 KB — far below the 600 KB budget even if 3–4 unique baked full-screen illustrated scenes (≈ 40–120 KB each at 64 colours, uncompressed) are added for chapter art. The mocks use **zero** unique full-screen bitmaps: the static layer can be drawn from rect fills + tiles + the sprite windows.

## AI-generated vs drawn in code
- **PixelLab `create-image-pixen` (4 calls, total printed spend 0.0 = trial credits):** Domino 64×64 (tuxedo cat + arch tracery), Chubbs 96×96, Gray Rat 64×64 (it returned a glass window), Zero 64×64 (rose window). All were post-processed in `render.py`: Domino/Chubbs get my own glass window behind them, every sprite is quantized to a 38-colour sub-palette of the palette above and snapped to RGB565, Zero is clipped to a circle. The prompts asked for "stained glass window style, thick black lead lines, jewel tones".
- **Drawn in code (Pillow, native resolution):** everything else — cards (frame, glass lattice, pips, stars, Reversed flip), Sun portrait, card back, scrap cards + icons, element/status/charm icons (ASCII masks with automatic lead outline and edge shading), HP bars, tabs, plates, FIGHT, paw/brackets, shelves/jars/cheese, floor, ledges, claw slashes, sparks, rose window, style sheet, storyboard.
- **Hand work still wanted for production:** a proper hand-pixelled Domino/Chubbs pass (clean up the tracery lines in the Domino arch, make Chubbs's window arch match Domino's), an 8×8 hand-drawn pip set (currently derived from the 12×12 masks), Majors' 32×32 portraits (only The Sun is mocked).

## Risks on this hardware
1. **Dense diamond lattice** on every card is ~60% non-fast pixels; at 6 cards + 6 box cards per screen that is fine because cards are pre-baked sprites, but animated redraws of many cards at once will cost. Fallback: flat M fill with 4 lead diagonals (already how the art window works).
2. **Dark chrome + saturated cards** needs a bright TFT; on a dim panel `night` (0x0808) and `stone` blur together. The gold stud/edge lines are the safety net.
3. **Gothic face** is slow to read at 12 px — hence the 16 px minimum and mixed case only; do not use it for numbers or sentences.

## Credits
Fonts: Jacquard 12, Pixelify Sans, Silkscreen — SIL Open Font License 1.1 (Google Fonts). Character art seeds: PixelLab `create-image-pixen`. Everything else: `render.py` (Pillow). Reproduce with `python render.py` (needs `raw/*.png` and `fonts/*.ttf`; `gen_sprites.py` is the one-off PixelLab script that produced `raw/`, it reads the token from the user environment and does not store it).
