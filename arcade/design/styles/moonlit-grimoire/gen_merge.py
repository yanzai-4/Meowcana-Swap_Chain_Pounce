"""Domino merge: edit raw/domino_v5.png (Apprentice Seer outfit) to take the fur markings of raw/domino_v2.png.
Usage: python gen_merge.py a|b|c  (edit_image_pixen only, one call per candidate; writes raw/domino_merge_<x>.png)"""
import os, subprocess, sys, time
sys.path.insert(0, r"C:/Users/tygac/OneDrive/Documents/uno-q-hackout/arcade/tools")
from pixellab import PixelLab

HERE = os.path.dirname(os.path.abspath(__file__))
MARKINGS = ("Repaint only the fur markings; keep the starry purple robe, starry wizard hat, golden tarot deck, pose and style. "
            "Tuxedo cat: black upper face, forehead and ears (pink inner ears), clean white muzzle and chin, small black spot on pink nose, "
            "white chest bib, pure white gloves, black legs, black tail with white tip. Face right.")
# candidate a was generated with this longer first wording (still under the 500-char API limit)
A_PROMPT = ("Repaint only the cat's fur markings, keep the starry purple robe, pointed starry wizard hat, big golden tarot deck, pose and pixel style. "
            "Markings: tuxedo cat with solid black fur on the upper face, forehead and both ears (pink inner ears), a clean white muzzle and chin patch, "
            "small black spot on the pink nose, white chest bib at the collar, pure white gloves on both hands, black legs and body, "
            "long black tail with a white tip. Face turned to the right.")
JOBS = {
    "a": (A_PROMPT, 11),
    "b": (MARKINGS + " Give the eyes clear bright highlights and crisp amber irises.", 22),
    "c": (MARKINGS + " Give him a slightly more heroic, confident expression with a small smile and raised chin.", 33),
}
FINAL_AI = ("Change only the tarot card held in his hands: make it an ornate deep royal-blue tarot card back with a thin gold border, "
            "a diamond lattice pattern and a centered gold crescent-moon cat-eye emblem. Keep the pose, hands, outfit, fur, face and everything else identical.")
if __name__ == "__main__":
    k = sys.argv[1]
    if k == "final_ai":
        JOBS[k] = (FINAL_AI, 44)
    token = subprocess.check_output(["powershell", "-NoProfile", "-Command",
                                     "[Environment]::GetEnvironmentVariable('PIXELLAB_API_KEY','User')"], text=True).strip()
    client = PixelLab(token)
    desc, seed = JOBS[k]
    srcname = "domino_merge_b" if k == "final_ai" else "domino_v5"
    src = open(os.path.join(HERE, "raw", srcname + ".png"), "rb").read()
    for attempt in range(2):
        try:
            png = client.edit_image_pixen(src, desc, seed=seed)
            open(os.path.join(HERE, "raw", ("domino_final_ai.png" if k == "final_ai" else f"domino_merge_{k}.png")), "wb").write(png)
            print(k, "ok; client.spent =", client.spent)
            break
        except RuntimeError as e:
            print(str(e)[:300])
            if "429" in str(e) and attempt == 0:
                time.sleep(15)
            else:
                break
