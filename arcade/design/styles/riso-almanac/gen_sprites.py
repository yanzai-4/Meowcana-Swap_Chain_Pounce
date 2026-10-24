"""One-off AI sprite generation (PixelLab create-image-pixen). Output -> raw/. Token never printed."""
import sys, time, subprocess, os
sys.path.insert(0, r"C:/Users/tygac/OneDrive/Documents/uno-q-hackout/arcade/tools")
from pixellab import PixelLab
tok = subprocess.check_output(["powershell","-NoProfile","-Command","[Environment]::GetEnvironmentVariable('PIXELLAB_API_KEY','User')"]).decode().strip()
c = PixelLab(tok)
STYLE = ("woodcut linocut print illustration, flat black ink and white paper only, bold thick black outline, "
         "crosshatch line shading, high contrast, no gradients, no color, no background, vintage almanac engraving")
JOBS = {
 "domino": (64, "tuxedo cat sitting upright proud, face half black half white split down the middle, white chest and white gloved front paws, black spot on white nose, long tail, " + STYLE, "east"),
 "chubbs": (96, "huge fat rat king wearing a tiny cracked paper crown and a tight buttoned vest, giant round belly, greedy grin with big front teeth, holding a cheese wedge, " + STYLE, "west"),
 "grayrat": (64, "scrappy small gray rat standing on hind legs, long thin tail, pointy snout, whiskers, holding a tiny rusty broken sword, " + STYLE, "west"),
 "zero": (64, "ghost kitten floating, small pale spectral kitten with big round eyes, tail fading into wisps of smoke, no feet, mostly white with hatching, " + STYLE, "east"),
}
only = sys.argv[1:] or list(JOBS)
for k in only:
    size, desc, d = JOBS[k]
    for attempt in range(2):
        try:
            png = c.create_image_pixen(description=desc, image_size={"width": size, "height": size}, no_background=True,
                                       view="side", direction=d, outline="single color black outline", detail="medium detail")
            open(f"raw/{k}.png", "wb").write(png); break
        except RuntimeError as e:
            print(str(e)[:120]); 
            if "429" in str(e) and attempt == 0: time.sleep(15); continue
            raise
    print(k, "spent", c.spent)
