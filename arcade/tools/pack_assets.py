"""Pack art and fonts for the console.

Inputs
  assets/*.json          one manifest per art owner (see "Manifest format")
  design/styles/moonlit-grimoire/fonts/*.ttf   baked as 1-bpp glyphs (BODY, TITLE, NUM, TINY)

Outputs
  sketch/assets.h        MCU flash: palette, frames, glyphs (shipped)
  python/assets.py       Asset constants by UPPER name (shipped)
  python/fontdata.py     glyph advances and font metrics for Screen.measure (shipped)
  build/sim_assets.bin   everything tools/sim.py needs (never shipped)
  build/asset_preview.png  review sheet of the first frames of every asset

Manifest format (paths are relative to the manifest's folder, then to its raw/ subfolder; PNG, RGBA)
  {"assets": [
     {"name": "card_back", "file": "raw/ui/card_back.png"},
     {"name": "domino_idle", "glob": "raw/domino/idle_*.png", "fps": 6},
     {"name": "domino_cast", "frames": ["raw/a.png", "raw/b.png"], "fps": 8},
     {"name": "cards_48x64", "sheet": "raw/cards.png", "cell": [48, 64], "count": 96}
  ]}
  - characters.json (schema owned by the character artist) is expanded to NAME, NAME_portrait and
    NAME_<animation> assets.
  - `file` = still, `glob` = sorted files (animation), `frames` = explicit list, `sheet` = grid of
    equally sized cells read left to right, top to bottom (a frame-set, e.g. every card face).
  - Alpha below 128 is transparent. Every opaque color must be RGB565-exact (bit replication).
  - All assets share one palette of at most 255 opaque colors.

Storage per asset (whichever is smaller): RLE6 (runs of 1-3 pixels in one byte, longer runs in two,
through a local palette of at most 63 colors) or, when the asset uses at most 15 colors, 4 bits per
pixel through a 16-entry local palette.

Usage (from arcade/):  python tools/pack_assets.py [--strict]
"""

import argparse
import json
import struct
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets"
FONT_DIR = ROOT / "design" / "styles" / "moonlit-grimoire" / "fonts"
HEADER = ROOT / "sketch" / "assets.h"
MODULE = ROOT / "python" / "assets.py"
FONT_MODULE = ROOT / "python" / "fontdata.py"
BUILD = ROOT / "build"
SIM_BIN = BUILD / "sim_assets.bin"
PREVIEW = BUILD / "asset_preview.png"

ALPHA_CUTOFF = 128
FLASH_BUDGET = 560 * 1024
MODE_RLE, MODE_P4 = 0, 1
FIRST_CHAR, LAST_CHAR = 32, 126
# (python name, ttf, pixel size): ids are the list positions.
FONTS = [("BODY", "VT323-Regular", 16), ("TITLE", "Jacquard24-Regular", 24),
         ("NUM", "Jersey10-Regular", 20), ("TINY", "Silkscreen-Regular", 8)]
# Extra glyphs after the ASCII range, same bitmaps in every font: (character, advance, top row relative to
# the baseline, bitmap rows). Screen.text sends them as bytes 127.. (index + FIRST_CHAR).
EXTRAS = [
    ("\u00b7", 6, -6, ["..##", "..##"]),                                                    # middle dot
    ("\u2192", 8, -8, ["...#...", "....#..", ".....#.", "#######", ".....#.", "....#..", "...#..."]),
    ("\u2605", 7, -8, ["..#..", ".###.", "#####", ".###.", ".#.#."]),                        # star
    ("\u25bc", 8, -7, ["#######", ".#####.", "..###..", "...#..."]),                       # down triangle
]
GLYPHS_PER_FONT = LAST_CHAR - FIRST_CHAR + 1 + len(EXTRAS)
GLYPH_COUNT = GLYPHS_PER_FONT * len(FONTS)


def snap565(rgb):
    r, g, b = rgb
    r5, g6, b5 = round(r * 31 / 255), round(g * 63 / 255), round(b * 31 / 255)
    return ((r5 << 3) | (r5 >> 2), (g6 << 2) | (g6 >> 4), (b5 << 3) | (b5 >> 2))


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def c_array(values, per_line=16):
    values = list(values)
    return ",\n".join("  " + ", ".join(values[i:i + per_line])
                      for i in range(0, len(values), per_line)) or "  0"


# ------------------------------------------------------------------ art

def expand_characters(data):
    """characters.json (one record per character) as plain asset items: NAME (base still),
    NAME_portrait, and NAME_<animation> from <folder of base>/<animation>_NN.png."""
    items = []
    for ch in data.get("characters", []):
        name, folder = ch["name"], ch["base"].rsplit("/", 1)[0]
        items.append({"name": name, "file": ch["base"]})
        if "portrait" in ch:
            items.append({"name": f"{name}_portrait", "file": ch["portrait"]["file"]})
        for anim, info in ch.get("animations", {}).items():
            items.append({"name": f"{name}_{anim}", "glob": f"{folder}/{anim}_[0-9][0-9].png",
                          "fps": info.get("fps", 0)})
    return items


def load_manifest(path, strict):
    """[(name, [RGBA frames], fps, source manifest name)] for one manifest."""
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    for item in data.get("assets", []) + expand_characters(data):
        name = item["name"]
        try:
            frames = load_frames(path.parent, item)
        except FileNotFoundError as error:
            if strict:
                raise SystemExit(f"{path.name}: {name}: missing {error.filename}")
            print(f"warning: skip {name} ({path.name}): missing {Path(error.filename).name}")
            continue
        entries.append((name, frames, int(item.get("fps", 0)), path.stem))
    return entries


def load_frames(folder, item):
    def resolve(file):
        for base in (folder, folder / "raw"):
            if (base / file).exists():
                return base / file
        raise FileNotFoundError(0, "missing", str(folder / file))

    def open_image(file):
        return Image.open(resolve(file)).convert("RGBA")

    def find(pattern):
        for base in (folder, folder / "raw"):
            files = sorted(p.relative_to(base).as_posix() for p in base.glob(pattern))
            if files:
                return [Image.open(base / f).convert("RGBA") for f in files]
        raise FileNotFoundError(0, "no match", str(folder / pattern))

    if "file" in item:
        return [open_image(item["file"])]
    if "frames" in item:
        return [open_image(f) for f in item["frames"]]
    if "glob" in item:
        return find(item["glob"])
    if "sheet" in item:
        sheet = open_image(item["sheet"])
        cw, ch = item["cell"]
        cols, rows = sheet.width // cw, sheet.height // ch
        count = item.get("count", cols * rows)
        if count > cols * rows:
            raise SystemExit(f"{item['name']}: sheet holds {cols * rows} cells, manifest wants {count}")
        return [sheet.crop((i % cols * cw, i // cols * ch, (i % cols + 1) * cw, (i // cols + 1) * ch))
                for i in range(count)]
    raise SystemExit(f"{item['name']}: needs one of file / glob / frames / sheet")


def pixels(image):
    data = image.tobytes()
    return [(data[i], data[i + 1], data[i + 2]) if data[i + 3] >= ALPHA_CUTOFF else None
            for i in range(0, len(data), 4)]


def build_palette(entries):
    colors = {}
    for name, frames, _, _ in entries:
        for frame in frames:
            for px in set(pixels(frame)):
                if px is not None and px not in colors:
                    if snap565(px) != px:
                        raise SystemExit(f"{name}: color {px} is not RGB565-exact "
                                         f"(nearest exact is {snap565(px)}); fix it in the art script")
                    colors[px] = None
    if len(colors) > 255:
        raise SystemExit(f"{len(colors)} colors across all assets; the shared palette holds 255")
    palette = sorted(colors, key=lambda c: rgb565(*c))
    return palette, {c: i + 1 for i, c in enumerate(palette)}  # 0 = transparent


def rle6(indices, local):
    """Runs of local palette indices (<= 63): 1-3 pixels in one byte (length << 6 | index),
    longer runs as (index, length) with length 4-255."""
    out = bytearray()
    i, n = 0, len(indices)
    while i < n:
        j = i
        while j < n and indices[j] == indices[i]:
            j += 1
        idx, length = local[indices[i]], j - i
        while length:
            take = min(length, 255)
            if take <= 3:
                out.append(take << 6 | idx)
            else:
                out += bytes((idx, take))
            length -= take
        i = j
    return bytes(out)


def pack4(indices, local):
    padded = [local[i] for i in indices]
    if len(padded) % 2:
        padded.append(0)
    return bytes((padded[i] << 4) | padded[i + 1] for i in range(0, len(padded), 2))


def encode_asset(name, frames, lookup):
    """-> (mode, [frame bytes], local palette bytes: local index -> shared palette index)."""
    indexed = [[lookup[p] if p is not None else 0 for p in pixels(f)] for f in frames]
    used = sorted({i for f in indexed for i in f} - {0})
    if len(used) > 63:
        raise SystemExit(f"{name}: {len(used)} colors in one asset; the limit is 63")
    local = {0: 0, **{g: n + 1 for n, g in enumerate(used)}}
    run_frames = [rle6(f, local) for f in indexed]
    if len(used) <= 15:
        p4_frames = [pack4(f, local) for f in indexed]
        if sum(map(len, p4_frames)) < sum(map(len, run_frames)):
            return MODE_P4, p4_frames, bytes([0] + used + [0] * (15 - len(used)))
    return MODE_RLE, run_frames, bytes([0] + used)


# ------------------------------------------------------------------ fonts

def bake_font(ttf, size):
    """Glyphs rendered like design/styles/moonlit-grimoire/ui.py (fontmode '1', baseline anchor 'ls').
    Pillow places a lone glyph up to a pixel off from the same glyph inside a string, so every glyph
    is rendered after an "H" and measured against that H's baseline.
    Returns dict(height, ascent, glyphs=[(advance, width, bits)]); bits = height rows of ceil(width/8) bytes."""
    font = ImageFont.truetype(str(FONT_DIR / (ttf + ".ttf")), size)
    ref_adv = int(font.getlength("H"))
    width = ref_adv + size * 2 + 8

    def render(text):
        canvas = Image.new("1", (width, size * 3), 0)
        draw = ImageDraw.Draw(canvas)
        draw.fontmode = "1"
        draw.text((0, size * 2), text, font=font, fill=1, anchor="ls")
        return canvas

    h_ink = render("H")
    h_top = h_ink.getbbox()[1]
    not_h = ImageChops.invert(h_ink)
    raw = []
    for code in range(FIRST_CHAR, LAST_CHAR + 1):
        ch = chr(code)
        pair = render("H" + ch)
        # Pillow may move the whole string by a pixel; the H tells us where the baseline went.
        baseline = pair.crop((0, 0, ref_adv, size * 3)).getbbox()[1] + size * 2 - h_top
        ink = ImageChops.logical_and(pair, not_h)               # the glyph without the H's own ink
        raw.append((int(font.getlength(ch)), ink.crop((ref_adv, 0, width, size * 3)), baseline))
    boxes = [(c.getbbox(), base) for _, c, base in raw if c.getbbox()]
    top = min(b[1] - base for b, base in boxes)          # relative to baseline (negative = above)
    bottom = max(b[3] - base for b, base in boxes)
    height, ascent = bottom - top, -top
    glyphs = []
    for adv, canvas, base in raw:
        box = canvas.getbbox()
        if box and box[0] < 0:
            raise SystemExit(f"{ttf}: glyph with negative left bearing")
        width = box[2] if box else 0
        crop = canvas.crop((0, base + top, width, base + bottom))
        data = crop.tobytes()
        stride = (width + 7) // 8
        rows = [data[r * stride:(r + 1) * stride] for r in range(height)] if width else []
        glyphs.append((adv, width, b"".join(rows)))
    for _, adv, top_rel, bitmap in EXTRAS:
        width = max(len(r) for r in bitmap)
        stride = (width + 7) // 8
        rows = []
        for r in range(height):
            line = bitmap[r - (ascent + top_rel)] if 0 <= r - (ascent + top_rel) < len(bitmap) else ""
            bits = int(line.ljust(stride * 8, ".").replace("#", "1").replace(".", "0"), 2)
            rows.append(bits.to_bytes(stride, "big"))
        glyphs.append((adv, width, b"".join(rows)))
    return {"height": height, "ascent": ascent, "glyphs": glyphs}


def bake_fonts():
    return [(name, bake_font(ttf, size)) for name, ttf, size in FONTS]


# ------------------------------------------------------------------ output

def write_outputs(entries, palette, encoded, fonts):
    data = bytearray()
    frame_offsets, table, py_lines, sim_assets, stats = [], [], [], [], []
    max_w = 1
    for asset_id, ((name, frames, fps, source), (mode, blobs, local)) in enumerate(zip(entries, encoded)):
        w, h = frames[0].size
        if any(f.size != (w, h) for f in frames) or w > 65535 or h > 65535:
            raise SystemExit(f"{name}: frames must share one size")
        max_w = max(max_w, w)
        before = len(data)
        pal_off = len(data)
        data += local
        first = len(frame_offsets)
        for blob in blobs:
            frame_offsets.append(len(data))
            data += blob
        table.append(f"  {{{w}, {h}, {first}, {len(frames)}, {mode}, {pal_off}}},  // {asset_id} {name}")
        py_lines.append(f"{name.upper()} = Asset({asset_id}, {w}, {h}, {len(frames)}, {fps or 1})")
        sim_assets.append({"name": name, "w": w, "h": h, "first": first, "frames": len(frames),
                           "mode": mode, "pal": pal_off})
        stats.append((name, source, w, h, len(frames), "p4" if mode else "rle6", len(data) - before))
    frame_offsets.append(len(data))

    font_data = bytearray()
    font_table, font_glyphs, font_py, sim_fonts = [], [], [], []
    for font_id, (name, font) in enumerate(fonts):
        first = len(font_glyphs)
        offsets = []
        for adv, width, bits in font["glyphs"]:
            offsets.append(len(font_data))
            font_glyphs.append(f"{{{adv}, {width}, {len(font_data)}}}")
            font_data += bits
        font_table.append(f"  {{{font['height']}, {font['ascent']}, {first}}},  // {font_id} {name}")
        font_py.append((name, font_id, font["height"], font["ascent"],
                        tuple(g[0] for g in font["glyphs"]), tuple(g[1] for g in font["glyphs"])))
        sim_fonts.append({"name": name, "height": font["height"], "ascent": font["ascent"],
                          "glyphs": [(g[0], g[1], o) for g, o in zip(font["glyphs"], offsets)],
                          "first": first})

    HEADER.write_text(f"""// Generated by tools/pack_assets.py from assets/*.json and the baked fonts. Do not edit.
#pragma once
#include <stdint.h>

namespace ArcadeAssets {{
// mode 0 = RLE6 (byte: length 1-3 << 6 | local index, or local index then length 4-255);
// mode 1 = 4 bpp. Both map local indices to PALETTE through the bytes at palOffset (local 0 = transparent).
struct Asset {{ uint16_t w, h; uint16_t firstFrame; uint16_t frames; uint8_t mode; uint32_t palOffset; }};
struct Font {{ uint8_t height, ascent; uint16_t firstGlyph; }};
struct Glyph {{ uint8_t advance, width; uint16_t offset; }};  // 1-bpp rows, MSB first, width rounded up to bytes
constexpr int ASSET_COUNT = {len(entries)};
constexpr int MAX_ASSET_WIDTH = {max_w};
constexpr int FONT_COUNT = {len(fonts)};
constexpr int FIRST_CHAR = {FIRST_CHAR};
constexpr int GLYPHS_PER_FONT = {GLYPHS_PER_FONT};
// RGB565; index 0 is transparent and never read.
static const uint16_t PALETTE[] = {{
{c_array(["0x0000"] + [f"0x{rgb565(*c):04X}" for c in palette])}
}};
constexpr int PALETTE_COUNT = sizeof(PALETTE) / sizeof(PALETTE[0]);
static const Asset ASSETS[] = {{
{chr(10).join(table) or "  {1, 1, 0, 0, 0, 0},"}
}};
static const uint32_t FRAME_OFFSETS[] = {{
{c_array(str(o) for o in frame_offsets)}
}};
static const uint8_t DATA[] = {{
{c_array(f"0x{b:02X}" for b in data) if data else "  0"}
}};
static const Font FONTS[] = {{
{chr(10).join(font_table)}
}};
static const Glyph GLYPHS[] = {{
{c_array(font_glyphs, 6)}
}};
static const uint8_t FONT_DATA[] = {{
{c_array(f"0x{b:02X}" for b in font_data)}
}};
}}  // namespace ArcadeAssets
""", encoding="utf-8", newline="\n")

    MODULE.write_text('"""Generated by tools/pack_assets.py from assets/*.json. Do not edit."""\n\n'
                      "from engine import Asset\n\n" + "\n".join(py_lines)
                      + ("\n\n" if py_lines else "") + "ALL = [" + ", ".join(n for n, *_ in
                      ((e[0].upper(),) for e in entries)) + "]\n", encoding="utf-8", newline="\n")

    lines = ['"""Generated by tools/pack_assets.py: baked font advances and metrics. Do not edit."""', ""]
    for name, font_id, *_ in font_py:
        lines.append(f"{name} = {font_id}")
    lines += ["", "FIRST_CHAR = %d" % FIRST_CHAR, "# Per font id: (height, ascent) of the text cell in pixels.",
              "METRICS = (" + ", ".join(f"({h}, {a})" for _, _, h, a, *_ in font_py) + ",)",
              "EXTRA_CHARS = " + repr("".join(e[0] for e in EXTRAS)) + "  # glyph indices after the ASCII range",
              "# Per font id: advance of each glyph (ASCII from FIRST_CHAR, then EXTRA_CHARS).",
              "ADVANCES = ("]
    lines += [f"    {adv!r}," for _, _, _, _, adv, _ in font_py]
    lines += [")", "# Per font id: ink width of each glyph (can exceed its advance by a pixel).", "WIDTHS = ("]
    lines += [f"    {wid!r}," for *_, wid in font_py]
    lines += [")", ""]
    FONT_MODULE.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    BUILD.mkdir(exist_ok=True)
    header = json.dumps({"palette": [rgb565(*c) for c in palette], "assets": sim_assets,
                         "frame_offsets": frame_offsets, "fonts": sim_fonts,
                         "first_char": FIRST_CHAR, "glyph_count": GLYPHS_PER_FONT, "data_len": len(data),
                         "font_data_len": len(font_data)}).encode()
    SIM_BIN.write_bytes(b"NLA1" + struct.pack("<I", len(header)) + header + bytes(data) + bytes(font_data))
    return len(data), len(frame_offsets) * 4, len(palette) * 2, len(font_data), stats


def write_preview(entries):
    """Review sheet: first 12 frames of each asset at 2x on a checkerboard, one row per asset."""
    if not entries:
        PREVIEW.unlink(missing_ok=True)
        return
    scale, gap, per_row = 2, 4, 12
    shown = [(n, f[:per_row]) for n, f, *_ in entries]
    cell_w = max(f[0].width for _, f in shown) * scale + gap
    cell_h = [max(i.height for i in f) * scale + gap for _, f in shown]
    sheet = Image.new("RGBA", (cell_w * per_row, sum(cell_h)), (20, 20, 20, 255))
    y = 0
    for (_, frames), ch in zip(shown, cell_h):
        for col, frame in enumerate(frames):
            tile = Image.new("RGBA", frame.size, (60, 60, 60, 255))
            tile.alpha_composite(frame)
            sheet.paste(tile.resize((frame.width * scale, frame.height * scale), Image.NEAREST),
                        (col * cell_w, y))
        y += ch
    BUILD.mkdir(exist_ok=True)
    sheet.save(PREVIEW)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--strict", action="store_true", help="fail on a missing source image")
    args = parser.parse_args()

    entries, names = [], {}
    for manifest in sorted(ASSET_DIR.glob("*.json")):
        for entry in load_manifest(manifest, args.strict):
            if entry[0] in names:
                raise SystemExit(f"duplicate asset name {entry[0]!r} ({names[entry[0]]} and {entry[3]})")
            if not entry[0].replace("_", "").isalnum() or not entry[0].isascii():
                raise SystemExit(f"bad asset name {entry[0]!r}; use letters, digits and underscores")
            names[entry[0]] = entry[3]
            entries.append(entry)
    if len(entries) > 255:
        raise SystemExit(f"{len(entries)} assets; ids are one byte")
    palette, lookup = build_palette(entries)
    encoded = [encode_asset(name, frames, lookup) for name, frames, _, _ in entries]
    art, offsets, pal, font_bytes, stats = write_outputs(entries, palette, encoded, bake_fonts())
    write_preview(entries)

    print(f"{'asset':<24}{'manifest':<12}{'size':>9}{'frames':>7}{'enc':>5}{'bytes':>9}")
    for name, source, w, h, frames, mode, size in sorted(stats, key=lambda s: -s[6])[:40]:
        print(f"{name:<24}{source:<12}{f'{w}x{h}':>9}{frames:>7}{mode:>5}{size:>9}")
    if len(stats) > 40:
        print(f"  ... {len(stats) - 40} smaller assets not listed")
    by_source = {}
    for _, source, *_, size in stats:
        by_source[source] = by_source.get(source, 0) + size
    for source, size in sorted(by_source.items()):
        print(f"  art from {source}.json: {size:,} B")
    total = art + offsets + pal + font_bytes + 4 * GLYPH_COUNT
    print(f"{len(entries)} assets, {sum(len(f) for _, f, *_ in entries)} frames, {len(palette)}/255 colors")
    print(f"flash: art {art:,} + frame table {offsets:,} + palette {pal:,} + fonts {font_bytes:,}"
          f" = {total:,} B of {FLASH_BUDGET:,} ({100 * total / FLASH_BUDGET:.1f}%)")
    if total > FLASH_BUDGET:
        sys.exit(f"error: over the {FLASH_BUDGET // 1024} KB asset flash budget")


if __name__ == "__main__":
    main()
