"""One-off PixelLab generation (4 calls, create-image-pixen only). Output -> raw/. Token from user env var, never stored."""
import subprocess, sys, time, os
sys.path.insert(0, r"C:/Users/tygac/OneDrive/Documents/uno-q-hackout/arcade/tools")
from pixellab import PixelLab
tok = subprocess.run(["powershell", "-NoProfile", "-Command",
    "[Environment]::GetEnvironmentVariable('PIXELLAB_API_KEY','User')"], capture_output=True, text=True).stdout.strip()
c = PixelLab(tok)
STYLE = ("pure 1-bit black and white ink illustration, only black and white, no color, no gray gradients, "
         "high contrast, hard-edged ordered dithering for shadow, woodcut manga ink, Return of the Obra Dinn look")
JOBS = {
 "domino": ("tuxedo cat standing upright on all fours, face split half black half white, white gloves on paws, "
            "white chest bib, small black spot on the nose, long tail raised, calm confident pose, " + STYLE, 64, "east"),
 "chubbs": ("enormous fat rat king, huge round belly, tiny crown, small beady eyes, whiskers, bib with crumbs, "
            "hunched menacing pose, " + STYLE, 96, "west"),
 "rat":    ("small scrawny gray rat, hunched, long thin tail, sharp teeth, scruffy fur, " + STYLE, 64, "west"),
 "zero":   ("ghost kitten spirit, small pale spectral kitten, wispy tail dissolving into smoke, big hollow eyes, "
            "mostly white with dotted outline, floating, " + STYLE, 64, "south-east"),
}
for name, (desc, size, d) in JOBS.items():
    out = f"raw/{name}.png"
    if os.path.exists(out): continue
    for attempt in range(2):
        try:
            png = c.create_image_pixen(description=desc, image_size={"width": size, "height": size},
                no_background=True, view="side", direction=d, outline="single color black outline", detail="medium detail")
            open(out, "wb").write(png); break
        except RuntimeError as e:
            if "429" in str(e) and attempt == 0: time.sleep(15); continue
            print("ERR", name, str(e)[:200]); break
    print(name, "spent", c.spent, flush=True)
