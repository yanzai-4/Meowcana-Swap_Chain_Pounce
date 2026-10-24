"""One-off PixelLab generation (<=5 calls). Output to raw/. Token read from user env, never printed."""
import subprocess, sys, time, os
sys.path.insert(0, r"C:/Users/tygac/OneDrive/Documents/uno-q-hackout/arcade/tools")
from pixellab import PixelLab
tok = subprocess.check_output(["powershell","-NoProfile","-Command","[Environment]::GetEnvironmentVariable('PIXELLAB_API_KEY','User')"]).decode().strip()
c = PixelLab(tok)
STYLE = ("stained glass window style pixel art, flat saturated jewel tone color cells, thick black lead lines between cells, "
         "no gradients, moonlit, medieval saint icon look")
JOBS = {
 "domino": (64, 64, "heroic tuxedo cat standing upright on four paws, left half of the face and body black, right half white, white gloves on paws and white chest, small black spot on the nose, " + STYLE),
 "chubbs": (96, 96, "huge gluttonous fat rat king sitting, round belly, tiny golden crown, gargoyle-like grin, gray-green fur, pink tail, holding a cheese wedge, " + STYLE),
 "grayrat": (64, 64, "small scrappy gray rat standing on hind legs, pink nose and tail, sharp teeth, " + STYLE),
 "zero": (64, 64, "ghost stray kitten spirit, pale blue white spectral glowing body, big sad eyes, wispy tail fading into mist, " + STYLE),
}
only = sys.argv[1:] or list(JOBS)
for k in only:
    if os.path.exists(f"raw/{k}.png"): continue
    w, h, d = JOBS[k]
    for attempt in range(8):
        try:
            png = c.create_image_pixen(description=d, image_size={"width": w, "height": h}, no_background=True,
                view="side", direction="east", outline="single color black outline", detail="medium detail")
            break
        except RuntimeError as e:
            if "429" in str(e) and attempt < 7: time.sleep(20); continue
            raise
    open(f"raw/{k}.png", "wb").write(png)
    print(k, "spent", c.spent)
