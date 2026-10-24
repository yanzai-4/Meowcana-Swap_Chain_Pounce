# Credits

Meowcana, its code, story, and rules are original hackathon work built on the UNO Q arcade starter in this repository (see [`README.md`](../README.md)). The controls and enclosure are based on the [Arduino UNO Q Arcade Bundle](https://projecthub.arduino.cc/Arduino_Genuino/uno-q-arcade-bundle-b272c5), with the [DIYables TFT shield](https://diyables.io/products/3.5-320x480-tft-lcd-color-touch-screen-shield-for-arduino-uno-mega) as the display.

## Fonts

All four fonts are licensed under the SIL Open Font License 1.1 and were taken from [Google Fonts](https://github.com/google/fonts). They live in `design/styles/moonlit-grimoire/fonts/` (a copy is in `tools/art/fonts/`) and are baked to 1-bit bitmaps by `tools/pack_assets.py`; no font file runs on the console.

| Font | Author | Used for |
| --- | --- | --- |
| VT323 | Peter Hull | Body text, stats, reading lines, footer (`BODY`, 16 px) |
| Jacquard 24 | Sarah Cadigan-Fried | Titles and names, mixed case only (`TITLE`, 24 px) |
| Jersey 10 | Sora Sagano | Damage and score numbers (`NUM`, 20 px) |
| Silkscreen | Jason Kottke | Button letters and small labels (`TINY`, 8 px) |

Source: `design/styles/moonlit-grimoire/notes.md` ("Credits").

## PixelLab-generated sprites

The characters were generated with [PixelLab](https://www.pixellab.ai) (`create-image-pixen` and `edit-image-pixen` for the base sprites, `animate-with-text-v3` for idle and attack animation), through `tools/pixellab.py` and `tools/art/characters_gen.py`: Domino, Zero, Spots, Granny Oriel, the rats and tutorial mice, Sir Flea, Dog-Ear, and Chubbs. Raw outputs are cached in `assets/raw/characters/_src/`. Every generated frame is post-processed by `tools/art/characters.py`: alpha cut to 1 bit, colors mapped (no dithering) to the Moonlit Grimoire palette, at most 15 colors per character, and portraits cropped from the base sprites. Domino's final look was chosen from several generated variants and retouched.

## Code-drawn art

Everything else is drawn in code with Pillow, pixel-exact and RGB565-exact, in the Moonlit Grimoire palette (`tools/art/pal.py`): card faces for all 48 cards (upright and reversed, two sizes), rat scrap cards, card back, icons, status and charm glyphs, VFX sprites (slash, spark, particles, MEOW bubble), panels and flourishes, and the five backdrops (attic, title, parlor, night path, end). Scripts: `tools/art/build_ui.py` with `gen_cards.py`, `gen_icons.py`, `gen_fx.py`, `gen_scenes.py`, `scraps.py`, and `majors.py`. The style study (`design/styles/moonlit-grimoire/`) was drawn the same way. The asset list is in [`assets.md`](assets.md).

## Tools and libraries

- **Arduino UNO Q** (Qualcomm QRB2210 on Debian Linux, STM32U585 on Zephyr), Arduino App Lab, Arduino App CLI, and the Arduino RouterBridge library for the Python-to-sketch RPC.
- **Modulino** Buttons, Joystick, and Movement with the Arduino Modulino library (pins and versions in `sketch/sketch.yaml`).
- **DIYables TFT Touch Shield** library for the TFT controller setup and the library bus path.
- **Python 3** with **Pillow** (art generation, font baking, simulator images); tkinter for the simulator window; **ziglang** (`pip install ziglang`) as the C++ compiler for the host parity test.
- **Android SDK Platform-Tools (`adb`)** for deploying to the board.
- Game design, story, rules, code, and art direction by the Meowcana team; implementation was assisted by AI coding agents.
