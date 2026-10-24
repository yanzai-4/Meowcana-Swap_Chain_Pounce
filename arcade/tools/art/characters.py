"""Character art post-processing (no network). Reads cached PixelLab outputs from assets/raw/characters/_src/,
maps them into the Moonlit Grimoire palette (RGB565-exact), 1-bit alpha, bottom-aligns every sprite on a common
baseline, flips to the contract facing, builds idle/attack frames (PixelLab frames when cached, otherwise a code
fallback), 48x48 portraits, a manifest (assets/characters.json) and the contact sheet build/art_characters_sheet.png.

Run: python tools/art/characters.py
Conventions
  size        canvas of every frame of that character (w, h)
  baseline    feet = last opaque row is h-1 (bottom row of the canvas); UIKit places the canvas bottom on the floor line
  facing      "right" for Domino/Zero/NPCs on the player side, "left" for all rats and Chubbs
  frames      <name>/base.png, idle_00..03.png, attack_00..03.png (+ cast_/victory_ for Domino when generated), portrait.png 48x48
Source cache naming in _src/: <name>.png (base), <name>_<anim>_<NN>.png (animation frames, same canvas as base source)
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
STYLE = ROOT / "design" / "styles" / "moonlit-grimoire"
sys.path.insert(0, str(STYLE))
sys.dont_write_bytecode = True
import pal  # noqa: E402

P = pal.P
OUT = ROOT / "assets" / "raw" / "characters"
SRC = OUT / "_src"
MANIFEST = ROOT / "assets" / "characters.json"
SHEET = ROOT / "build" / "art_characters_sheet.png"

COOL_DROP = {P[k] for k in ("rat0", "rat1", "earth0", "earth1", "air0")}
BASE_COLORS = sorted({v for k, v in P.items() if not (k.startswith("r") and not k.startswith("rat"))
                      and k not in ("blue", "purple")})
COOL_COLORS = [c for c in BASE_COLORS if c not in COOL_DROP]

# name: dict(src=file stem in _src, gen_facing=direction of the cached source, facing=contract facing, size, cool, role, anims)
SPEC = {
    "domino": dict(src="domino_merge_b", gen="right", facing="right", size=(64, 64), cool=True, role="hero",
                   anims={"idle": 4, "attack": 4, "cast": 4, "victory": 4}),
    "zero": dict(scale=0.68, src="zero_old", gen="right", facing="right", size=(64, 64), cool=True, role="guide", anims={"idle": 2}),
    "spots": dict(src="grayrat", gen="left", facing="left", size=(64, 64), cool=False, role="merchant", anims={"idle": 2}),
    "granny_oriel": dict(src="grayrat", gen="left", facing="right", size=(64, 64), cool=False, role="npc", anims={"idle": 2}),
    "gray_rat": dict(src="grayrat", gen="left", facing="left", size=(64, 64), cool=False, role="enemy", anims={"idle": 2, "attack": 3}),
    "pickpocket": dict(src="grayrat", gen="left", facing="left", size=(64, 64), cool=False, role="enemy", anims={"idle": 2, "attack": 3}),
    "paper_chewer": dict(src="grayrat", gen="left", facing="left", size=(64, 64), cool=False, role="enemy", anims={"idle": 2, "attack": 3}),
    "stinker": dict(src="grayrat", gen="left", facing="left", size=(64, 64), cool=False, role="enemy", anims={"idle": 2, "attack": 3}),
    "rat_sergeant": dict(src="grayrat", gen="left", facing="left", size=(64, 64), cool=False, role="enemy", anims={"idle": 2, "attack": 3}),
    "sir_flea": dict(src="grayrat", gen="left", facing="left", size=(80, 64), cool=False, role="elite", anims={"idle": 2, "attack": 3}),
    "dog_ear": dict(src="grayrat", gen="left", facing="left", size=(64, 64), cool=False, role="elite", anims={"idle": 2, "attack": 3}),
    "chubbs": dict(src="chubbs", gen="left", facing="left", size=(96, 96), cool=False, role="boss", anims={"idle": 4, "attack": 3}),
    "chubbs_hungry": dict(src="chubbs_hungry", gen="left", facing="left", size=(96, 96), cool=False, role="boss", anims={"idle": 2, "attack": 2}),
    "practice_mouse": dict(src="tutorial_mouse", gen="left", facing="left", size=(64, 64), cool=False, role="tutorial", anims={"idle": 2, "attack": 3}),
    "dust_mouse": dict(src="tutorial_mouse", gen="left", facing="left", size=(64, 64), cool=False, role="tutorial", anims={"idle": 2, "attack": 3}),
    "coin_mouse": dict(src="tutorial_mouse", gen="left", facing="left", size=(64, 64), cool=False, role="tutorial", anims={"idle": 2, "attack": 3}),
}
FPS = {"idle": 4, "attack": 8, "cast": 8, "victory": 6}
PORTRAIT = 48


def resolve(name, stem):
    """Prefer a character-specific cached source; fall back to the shared placeholder source."""
    own = SRC / f"{name}.png"
    return own if (stem is None and own.exists()) else SRC / f"{stem}.png"


def source_path(name, spec):
    own = SRC / f"{name}.png"
    return own if own.exists() else SRC / f"{spec['src']}.png"


def is_final(name, spec):
    return source_path(name, spec).stem not in ("grayrat", "zero_old") 


def clean(img, cool):
    """RGBA -> palette-mapped RGBA with 1-bit alpha."""
    img = img.convert("RGBA")
    rgb = Image.new("RGB", img.size, P["night0"])
    rgb.paste(img, mask=img.split()[3])
    q = pal.quantize_to(rgb, COOL_COLORS if cool else BASE_COLORS).convert("RGBA")
    q.putalpha(img.split()[3].point(lambda v: 255 if v >= 128 else 0))
    return q


def shrink(img, k):
    """Downscale an RGBA sprite by k (area filter on premultiplied color), then clean() re-snaps palette + 1-bit alpha."""
    w, h = max(1, round(img.width * k)), max(1, round(img.height * k))
    pm = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pm.paste(img.convert("RGBA"))
    return pm.resize((w, h), Image.BOX)


def place(img, size, anchor=None):
    """Bottom-align on the canvas and center horizontally. anchor=(cx, bottom) of the base bbox makes frames share the offset."""
    bb = img.getbbox()
    if bb is None:
        return Image.new("RGBA", size, (0, 0, 0, 0)), anchor
    if anchor is None:
        anchor = ((bb[0] + bb[2]) / 2.0, bb[3])
    w, h = size
    ox = int(round(w / 2.0 - anchor[0]))
    oy = h - int(anchor[1])
    if bb[2] - bb[0] > w or bb[3] - bb[1] > h:
        raise SystemExit("sprite larger than canvas %s: bbox %s" % (size, bb))
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(img, (ox, oy))
    return canvas, anchor


def shift_rows(img, y_split, dy):
    """Move everything above y_split down by dy (breathing squash), duplicating the seam row."""
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    top = img.crop((0, 0, img.width, y_split))
    out.alpha_composite(img.crop((0, y_split, img.width, img.height)), (0, y_split))
    out.alpha_composite(top, (0, dy))
    return out


def fallback_idle(base, n):
    bb = base.getbbox()
    split = bb[1] + int((bb[3] - bb[1]) * 0.55)
    seq = [base, shift_rows(base, split, 1), shift_rows(base, split, 1), base]
    return [base, seq[1]] if n == 2 else seq[:n]


def fallback_attack(base, facing, n):
    d = 1 if facing == "right" else -1
    frames = []
    for dx in {2: (6, 10), 3: (-3, 8, 2), 4: (-3, 5, 9, 2)}[n]:
        f = Image.new("RGBA", base.size, (0, 0, 0, 0))
        f.alpha_composite(base, (d * dx, 0))
        frames.append(f)
    return frames


MOUSE_RAMPS = {   # armor recolor by luminance (dark -> light); coin_mouse keeps the generated gold
    "practice_mouse": [P["gold0"], P["amber0"], P["gold1"], P["air0"]],
    "dust_mouse": [P["night2"], P["night3"], P["silver1"], P["silver2"]],
}


def recolor_armor(img, ramp):
    """Swap yellow/orange armor pixels (not the pink ears or tail) onto a 4-step ramp by luminance."""
    out = img.copy()
    px = out.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a and r > 120 and r - b > 70 and g > 70 and abs(r - g) < 110 and not (b > 100 and r - g > 50):
                lum = (r + g) / 2.0
                px[x, y] = ramp[min(3, max(0, int((lum - 90) / 45)))] + (255,)
    return out


def limit_colors(base, built, n):
    """Keep the n most used colors across base + every frame (4bpp storage); remap the rest to the nearest kept color."""
    from collections import Counter
    allf = [base] + [f for fr, _ in built.values() for f in fr]
    cnt = Counter()
    for f in allf:
        for r, g, b, a in f.getdata():
            if a:
                cnt[(r, g, b)] += 1
    keep = [c for c, _ in cnt.most_common(n)]
    lut = {}

    def remap(f):
        out = f.copy()
        px = out.load()
        for y in range(f.height):
            for x in range(f.width):
                r, g, b, a = px[x, y]
                if not a:
                    continue
                c = (r, g, b)
                if c not in keep:
                    if c not in lut:
                        lut[c] = min(keep, key=lambda k: (k[0] - r) ** 2 + (k[1] - g) ** 2 + (k[2] - b) ** 2)
                    px[x, y] = lut[c] + (255,)
        return out
    return remap(base), {k: ([remap(f) for f in fr], pl) for k, (fr, pl) in built.items()}


def portrait(base):
    bb = base.getbbox()
    cx = (bb[0] + bb[2]) // 2
    x0 = max(0, min(base.width - PORTRAIT, cx - PORTRAIT // 2))
    y0 = max(0, bb[1] - 2)
    crop = base.crop((x0, y0, x0 + PORTRAIT, y0 + PORTRAIT))
    bg = Image.new("RGBA", crop.size, P["night0"] + (255,))
    bg.alpha_composite(crop)
    return bg.convert("RGB")


def build():
    entries = []
    for name, spec in SPEC.items():
        folder = OUT / name
        folder.mkdir(parents=True, exist_ok=True)
        flip = spec["gen"] != spec["facing"]
        src = Image.open(source_path(name, spec))
        base_c = clean(src, spec["cool"])
        full_c = base_c          # unscaled copy: the dialogue portrait must not change
        if spec.get("scale"):
            base_c = clean(shrink(src, spec["scale"]), spec["cool"])
        if flip:
            base_c = ImageOps.mirror(base_c)
        if name in MOUSE_RAMPS:
            base_c = recolor_armor(base_c, MOUSE_RAMPS[name])
        base, anchor = place(base_c, spec["size"])
        counts = {}
        built = {}
        for anim, want in spec["anims"].items():
            frames = []
            files = sorted(SRC.glob(f"{source_path(name, spec).stem}_{anim}_[0-9][0-9].png"))
            for f in files:
                fr = clean(shrink(Image.open(f), spec["scale"]) if spec.get("scale") else Image.open(f), spec["cool"])
                if flip:
                    fr = ImageOps.mirror(fr)
                if name in MOUSE_RAMPS:
                    fr = recolor_armor(fr, MOUSE_RAMPS[name])
                frames.append(place(fr, spec["size"], anchor)[0])
            if len(frames) > 4:                    # v3 can return extra tail frames that drift off-pose
                frames = frames[:4]
            if frames and len(frames) > want:      # subsample evenly to the flash budget
                frames = [frames[round(i * (len(frames) - 1) / max(1, want - 1))] for i in range(want)]
            if not frames:
                frames = fallback_idle(base, want) if anim == "idle" else fallback_attack(base, spec["facing"], want)
            built[anim] = (frames, bool(files))
        base, built = limit_colors(base, built, 15 if True else 0)
        for anim, (frames, from_pl) in built.items():
            for old in folder.glob(f"{anim}_[0-9][0-9].png"):
                old.unlink()
            for i, fr in enumerate(frames):
                fr.save(folder / f"{anim}_{i:02d}.png")
            counts[anim] = {"frames": len(frames), "fps": FPS[anim], "source": "pixellab" if from_pl else "code"}
        base.save(folder / "base.png")
        portrait(place(ImageOps.mirror(full_c) if flip else full_c, spec["size"])[0] if spec.get("scale") else base).save(folder / "portrait.png")
        entries.append({"name": name, "role": spec["role"], "size": list(spec["size"]), "facing": spec["facing"],
                        "baseline": "bottom row of canvas", "base": f"characters/{name}/base.png",
                        "portrait": {"file": f"characters/{name}/portrait.png", "size": [PORTRAIT, PORTRAIT]},
                        "animations": counts, "final": is_final(name, spec)})
    MANIFEST.write_text(json.dumps({"palette": "design/styles/moonlit-grimoire/pal.py", "alpha": "1-bit",
                                    "characters": entries}, indent=2), encoding="utf-8")
    contact_sheet(entries)
    for e in entries:
        print(f"{e['name']:15s} {e['size']} {e['facing']:5s} " +
              " ".join(f"{k}x{v['frames']}({v['source']})" for k, v in e["animations"].items()) +
              ("" if e["final"] else "  [placeholder]"))


def backdrop_strip(w, h):
    strip = Image.new("RGB", (w, h), P["night1"])
    from PIL import ImageDraw
    d = ImageDraw.Draw(strip)
    d.rectangle([0, h - 26, w, h], fill=P["night0"])
    d.line([(0, h - 26), (w, h - 26)], fill=P["gold0"])
    for x in range(10, w, 36):
        d.line([(x, 0), (x, h - 27)], fill=P["night0"])
    return strip


def contact_sheet(entries):
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    k = 2
    pad = 10
    cols = 6
    cw = 100 * k // 1
    rows = (len(entries) + cols - 1) // cols
    cell_h = 104 * k + 20
    W = cols * (cw + pad) + pad
    H = rows * (cell_h + pad) + pad
    sheet = backdrop_strip(W, H)
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    d.fontmode = "1"
    for i, e in enumerate(entries):
        r, c = divmod(i, cols)
        x0 = pad + c * (cw + pad)
        y0 = pad + r * (cell_h + pad)
        d.rectangle([x0, y0, x0 + cw - 1, y0 + cell_h - 1], fill=P["night0"], outline=P["gold1"])
        im = Image.open(OUT / e["name"] / "base.png").convert("RGBA")
        im = im.resize((im.width * k, im.height * k), Image.NEAREST)
        sheet.paste(im, (x0 + (cw - im.width) // 2, y0 + cell_h - 20 - im.height), im)
        from PIL import ImageFont
        f = ImageFont.truetype(str(STYLE / "fonts" / "VT323-Regular.ttf"), 16)
        d.text((x0 + 4, y0 + 14), e["name"] + ("" if e["final"] else " *"), font=f, fill=P["gold3"], anchor="ls")
        n = sum(v["frames"] for v in e["animations"].values())
        d.text((x0 + 4, y0 + cell_h - 6), f"{e['size'][0]}x{e['size'][1]} {n}f", font=f, fill=P["silver1"], anchor="ls")
    sheet.save(SHEET)


def build_story_poses():
    """domino_story: 3 stills (worried / determined / relieved) from edits of domino_merge_b, same cool mapping and the
    same baseline anchor as domino. Written to assets/raw/characters/domino_story/pose_NN.png and added to the manifest."""
    folder = OUT / "domino_story"
    folder.mkdir(parents=True, exist_ok=True)
    spec = SPEC["domino"]
    anchor = place(clean(Image.open(SRC / "domino_merge_b.png"), True), spec["size"])[1]
    frames = []
    for i in range(3):
        fr = clean(Image.open(SRC / f"domino_story_{i:02d}.png"), True)
        frames.append(place(fr, spec["size"], anchor)[0])
    frames = limit_colors(frames[0], {"pose": (frames[1:], False)}, 15)
    allf = [frames[0]] + frames[1]["pose"][0]
    for i, fr in enumerate(allf):
        fr.save(folder / f"pose_{i:02d}.png")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["assets"] = [a for a in data.get("assets", []) if a["name"] != "domino_story"]
    data["assets"].append({"name": "domino_story", "glob": "characters/domino_story/pose_[0-9][0-9].png", "fps": 0,
                           "meaning": ["worried (clasped paws, card to chest)", "determined (paw pointing forward)",
                                       "relieved/proud (card held high)"]})
    MANIFEST.write_text(json.dumps(data, indent=2), encoding="utf-8")
    sheet = Image.new("RGB", (3 * 132, 132), P["night1"])
    for i, fr in enumerate(allf):
        big = fr.resize((128, 128), Image.NEAREST)
        sheet.paste(big, (i * 132 + 2, 2), big)
    sheet.save(ROOT / "build" / "domino_story_preview_2x.png")


def seed_sources():
    """Copy the cached design raws into _src (first run only)."""
    SRC.mkdir(parents=True, exist_ok=True)
    for stem, orig in (("domino", "domino_merge_b"), ("domino_merge_b", "domino_merge_b"), ("zero_old", "zero"), ("grayrat", "grayrat"), ("chubbs", "chubbs")):
        dst = SRC / f"{stem}.png"
        if not dst.exists():
            dst.write_bytes((STYLE / "raw" / f"{orig}.png").read_bytes())


if __name__ == "__main__":
    seed_sources()
    build()
    if (SRC / "domino_story_02.png").exists():
        build_story_poses()
