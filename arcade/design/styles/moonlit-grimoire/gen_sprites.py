"""One-off PixelLab sprite generation for Moonlit Grimoire (create-image-pixen only, max 5 calls).
Usage: python gen_sprites.py domino|chubbs|grayrat|zero   (writes raw/<name>.png)"""
import os, subprocess, sys, time
sys.path.insert(0, r"C:/Users/tygac/OneDrive/Documents/uno-q-hackout/arcade/tools")
from pixellab import PixelLab

HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = {
    "domino": ("anthropomorphic tuxedo cat hero standing upright on two legs, confident heroic pose, face split half black half white, "
                "black spot on pink nose, white gloves, white chest, short midnight blue cloak with gold trim, small leather satchel, "
                "holding a tarot card in one hand, fortune-teller adventurer, silver moonlight rim light, dark indigo outline",
                64, 64, "east"),
    "domino_v1": ("anthropomorphic tuxedo cat standing upright on two legs, face split half black half white, black spot on pink nose, white gloves, white chest, gentleman magician, tiny black top hat, literal tuxedo with tails and bow tie, short cape, flicking a tarot card between two fingers, dark indigo outline, silver moonlight rim light, midnight indigo and antique gold palette", 64, 64, "east"),
    "domino_v2": ("anthropomorphic tuxedo cat standing upright on two legs, face split half black half white, black spot on pink nose, white gloves, white chest, hooded fortune-teller, deep midnight blue hood embroidered with gold crescent moons, long robe, holding a small glowing crystal ball, dark indigo outline, silver moonlight rim light, midnight indigo and antique gold palette", 64, 64, "east"),
    "domino_v3": ("anthropomorphic tuxedo cat standing upright on two legs, face split half black half white, black spot on pink nose, white gloves, white chest, night rogue, scarf, satchel of tarot cards, holding a card shaped like a dagger, nimble crouch-ready stance, dark leather clothes, dark indigo outline, silver moonlight rim light, midnight indigo and antique gold palette", 64, 64, "east"),
    "domino_v4": ("anthropomorphic tuxedo cat standing upright on two legs, face split half black half white, black spot on pink nose, white gloves, white chest, moon knight, light silver and gold armor, holding a round shield with a golden cat-eye moon emblem, small sword, heroic stance, dark indigo outline, silver moonlight rim light, midnight indigo and antique gold palette", 64, 64, "east"),
    "domino_v5": ("anthropomorphic tuxedo cat standing upright on two legs, face split half black half white, black spot on pink nose, white gloves, white chest, cute young apprentice seer, oversized starry midnight blue robe, tall pointed wizard hat with stars, clutching a big tarot deck with both hands, dark indigo outline, silver moonlight rim light, midnight indigo and antique gold palette", 64, 64, "east"),
    "domino_v6": ("anthropomorphic tuxedo cat standing upright on two legs, face split half black half white, black spot on pink nose, white gloves, white chest, plague doctor cartomancer, long dark coat, beaked bird mask pushed up on the head, holding a lantern, dark edgy gothic, dark indigo outline, silver moonlight rim light, midnight indigo and antique gold palette", 64, 64, "east"),
    "chubbs": ("huge fat gray rat king, round belly, tiny gold crown, sitting, sly grin with buck teeth, muted gray-green fur, ragged purple cloak, "
               "holding cheese wedge, cold moonlight rim light, dark indigo outline, spooky storybook",
               96, 96, "west"),
    "grayrat": ("small gray rat, side view, pink tail, beady eyes, sneaky pose, muted gray-green fur, silver moonlight rim light, dark indigo outline",
                64, 64, "west"),
    "zero": ("ghost kitten spirit, pale blue-white spectral small kitten, big hollow glowing eyes, wispy tail fading into mist, pale silver glow, "
             "dark indigo outline, mystical tarot Fool", 64, 64, "east"),
}

if __name__ == "__main__":
    name = sys.argv[1]
    token = subprocess.check_output(["powershell", "-NoProfile", "-Command",
                                     "[Environment]::GetEnvironmentVariable('PIXELLAB_API_KEY','User')"], text=True).strip()
    client = PixelLab(token)
    desc, w, h, direction = JOBS[name]
    for attempt in range(2):
        try:
            png = client.create_image_pixen(description=desc, image_size={"width": w, "height": h}, no_background=True, view="side",
                                            direction=direction, outline="single color outline", detail="medium detail")
            open(os.path.join(HERE, "raw", name + ".png"), "wb").write(png)
            print(name, "ok; client.spent =", client.spent)
            break
        except RuntimeError as e:
            print(str(e)[:200])
            if "429" in str(e) and attempt == 0:
                time.sleep(15)
            else:
                break
