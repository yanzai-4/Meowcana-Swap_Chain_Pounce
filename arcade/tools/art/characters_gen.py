"""PixelLab calls for the character roster. Outputs are cached in assets/raw/characters/_src/ (existing files are never
regenerated unless --force). Post-processing lives in characters.py. Token: user env var PIXELLAB_API_KEY (never written).
Usage:  python tools/art/characters_gen.py bases [name ...]        create-image-pixen / edit-image-pixen
        python tools/art/characters_gen.py anim <name> <idle|attack|cast|victory> [--frames N]
        python tools/art/characters_gen.py balance
Every run prints the balance delta (the real spend)."""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from pixellab import PixelLab  # noqa: E402

SRC = ROOT / "assets" / "raw" / "characters" / "_src"
LOOK = ("lightly anthropomorphic, upright on two legs, standing, full body, side view, muted gray-green fur and pink ears and tail like a "
        "storybook rat, cold silver moonlight rim light, dark indigo outline, midnight palette")
BASES = {
    "zero": ("ghost stray kitten standing upright on two legs, pale blue-white spectral fur, big hollow glowing eyes, oversized tattered "
             "Fool's scarf trailing, small bindle on a stick over the shoulder, wispy fading tail, pale silver glow, dark indigo outline",
             64, 64, "east", "single color outline"),
    "spots": ("fat rat merchant standing upright, brown and white spotted fur, striped waistcoat vest, gold monocle, jingling coin pouch "
              "in one hand, friendly shrewd smile, " + LOOK, 64, 64, "west", "single color outline"),
    "granny_oriel": ("old human grandmother asleep sitting in a rocking chair, wrapped in a big purple shawl, white bun hair, tiny round "
                     "glasses, closed eyes, peaceful, knitting in lap, warm candle light, dark indigo outline", 64, 64, "east",
                     "single color outline"),
    "gray_rat": ("scrappy street rat standing upright, patched brown tunic, rusty broken sword held in one hand, torn ear, scrappy grin, "
                 + LOOK, 64, 64, "west", "single color outline"),
    "pickpocket": ("sneaky rat thief standing upright in a dark hooded cloak, hood up, holding a lumpy burlap sack over the shoulder, "
                   "sly narrow eyes, " + LOOK, 64, 64, "west", "single color outline"),
    "paper_chewer": ("rat clerk standing upright wearing an apron made of torn book pages, holding a feather quill pen, inky paws, "
                     "chewed paper bits, " + LOOK, 64, 64, "west", "single color outline"),
    "stinker": ("grimy rat plumber standing upright in dirty patched overalls, holding a rubber toilet plunger like a weapon, green "
                "wavy stink lines around him, messy fur, " + LOOK, 64, 64, "west", "single color outline"),
    "rat_sergeant": ("rat sergeant standing upright, tin can helmet on head, red sash across chest, holding a long toothpick spear, "
                     "stern face, " + LOOK, 64, 64, "west", "single color outline"),
    "sir_flea": ("tiny rat knight in small silver armor with a plume helmet, riding a large brown cockroach like a horse, holding a "
                 "lance, side view, cold silver moonlight rim light, dark indigo outline", 80, 64, "west", "single color outline"),
    "dog_ear": ("bookworm scholar rat standing upright in a long burgundy robe, round spectacles, clutching a huge heavy book with "
                "dog-eared pages, wise stern look, " + LOOK, 64, 64, "west", "single color outline"),
    "tutorial_mouse": ("small young apprentice mouse standing upright wearing cardboard box armor and a cardboard helmet, holding a "
                       "tiny wooden stick, big round ears, nervous brave face, " + LOOK, 64, 64, "west", "single color outline"),
}
EDITS = {
    "chubbs_hungry": ("chubbs", "Keep the exact same character, pose and style but make him angrier and hungrier: furious glare, wide open "
                      "mouth with drool, bared buck teeth, glowing red eyes, crown slightly crooked, cloak flared.", 7),
}
ANIMS = {
    "idle": "idle breathing, subtle up and down bob, gentle sway",
    "attack": "attack, quick forward strike with the held weapon, then return to stance",
    "cast": "raise the tarot card high above the head with a magical flourish, then lower it",
    "victory": "victory stretch, arms up high and a happy stretch, then relax",
}


ATTACK_TEXT = {
    "domino": "throws a glowing tarot card forward with a flick of the wrist, then returns to stance",
    "gray_rat": "lunges and slashes with the rusty broken sword, then returns to stance",
    "pickpocket": "lunges forward grabbing and snatching with the free hand, sack swinging, then returns",
    "paper_chewer": "stabs forward with the quill pen like a dagger, paper bits flying, then returns",
    "stinker": "swings the plunger forward in a big overhead whack, then returns",
    "rat_sergeant": "thrusts the toothpick spear forward, then returns to stance",
    "sir_flea": "charges forward with the lance as the cockroach lunges, then returns",
    "dog_ear": "slams the heavy book forward in a big smash, then returns",
    "chubbs": "slams a fat fist forward with a heavy belly lunge, then returns",
    "chubbs_hungry": "furious lunge forward biting and clawing, then returns",
    "tutorial_mouse": "pokes forward with the tiny wooden stick, then returns",
}


POSES = {
    "domino_story_00": ("Same character, outfit and style, new pose: worried, both paws clasped holding the tarot card against his chest, "
                        "ears flattened back, big anxious eyes looking up. Facing right, feet on the ground.", 51),
    "domino_story_01": ("Same character, outfit and style, new pose: determined and brave, one paw raised pointing forward, cloak swaying "
                        "in the wind, confident stance, ready to go. Facing right, feet on the ground.", 52),
    "domino_story_02": ("Same character, outfit and style, new pose: relieved and proud, smiling, holding one golden tarot card up high "
                        "above his head in one paw, other paw on hip. Facing right, feet on the ground.", 53),
}


def client():
    tok = subprocess.check_output(["powershell", "-NoProfile", "-Command",
                                   "[Environment]::GetEnvironmentVariable('PIXELLAB_API_KEY','User')"], text=True).strip()
    return PixelLab(tok)


def balance(c):
    b = c.balance()
    return b["credits"]["usd"], b["subscription"].get("generations")


def retry(fn):
    for attempt in range(2):
        try:
            return fn()
        except RuntimeError as e:
            print(str(e)[:300])
            if "429" in str(e) and attempt == 0:
                time.sleep(15)
            else:
                raise


def main():
    mode = sys.argv[1]
    c = client()
    before = balance(c)
    print("balance before:", before)
    force = "--force" in sys.argv
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    SRC.mkdir(parents=True, exist_ok=True)
    if mode == "bases":
        for name in args or list(BASES) + list(EDITS):
            dst = SRC / f"{name}.png"
            if dst.exists() and not force:
                print("cached", name)
                continue
            if name in EDITS:
                base, desc, seed = EDITS[name]
                png = retry(lambda: c.edit_image_pixen((SRC / f"{base}.png").read_bytes(), desc, seed=seed))
            else:
                desc, w, h, direction, outline = BASES[name]
                png = retry(lambda: c.create_image_pixen(description=desc, image_size={"width": w, "height": h}, no_background=True,
                                                         view="side", direction=direction, outline=outline, detail="medium detail"))
            dst.write_bytes(png)
            print("saved", name)
    elif mode == "pose":
        name = args[0]
        desc, seed = POSES[name]
        src = (SRC / "domino_merge_b.png").read_bytes()
        (SRC / f"{name}.png").write_bytes(retry(lambda: c.edit_image_pixen(src, desc, seed=seed)))
        print("saved", name)
    elif mode == "anim":
        name, anim = args[0], args[1]
        n = int(sys.argv[sys.argv.index("--frames") + 1]) if "--frames" in sys.argv else 4
        src = (SRC / f"{name}.png").read_bytes()
        action = ATTACK_TEXT.get(name, ANIMS["attack"]) if anim == "attack" else ANIMS[anim]
        frames = retry(lambda: c.animate_with_text_v3(src, action, n, seed=3))
        for i, f in enumerate(frames):
            (SRC / f"{name}_{anim}_{i:02d}.png").write_bytes(f)
        print("saved", name, anim, len(frames), "frames")
    after = balance(c)
    print("balance after:", after, " spent usd:", round(before[0] - after[0], 4), " trial gens used:", (before[1] or 0) - (after[1] or 0))
    print("client.spent =", c.spent)


if __name__ == "__main__":
    main()
