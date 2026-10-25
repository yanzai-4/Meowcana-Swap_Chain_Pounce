"""Meowcana (Swap. Chain. Pounce.) - every word the player reads that is not a card or rules text.

Pure data, stdlib only (Python 3.11+).  Owner: Writer.  See docs/story-and-tutorial.md for the
design rationale, the glossary and the full list of tutorial action keys and highlight regions.

Box limits (VT323, 8 px advance): a dialogue box holds at most 2 lines of 46 characters.  Every
``Line.text`` already contains its own "\\n" line break, so the UI never has to wrap it.  One idea
per box.  Characters are lightly anthropomorphic (costumes and props); descriptions say so.

Portraits: "domino", "zero", "spots", "sir_flea", "dog_ear", "chubbs", "oriel", "young_oriel",
or None (narration, no portrait).  Moods: "", "happy", "calm", "proud", "worried", "surprised",
"sly", "angry", "sad", "sleepy".
"""
from __future__ import annotations

from dataclasses import dataclass, field

LINE_CHARS = 46      # max characters per dialogue line
LINE_COUNT = 2       # max lines per dialogue box


@dataclass(frozen=True)
class Line:
    speaker: str                  # "" for narration
    text: str                     # 1-2 lines joined by "\n", each <= LINE_CHARS
    portrait: str | None = None
    mood: str = ""


@dataclass(frozen=True)
class Step:
    id: str
    lines: list[Line]             # shown first, A advances; the player acts afterwards
    wait_for: str                 # action key reported by a scene (see docs)
    highlight: str = ""           # UI region to spotlight ("" = none)
    allow: str = ""               # comma list of inputs that work: stick,a,b,c ("" = only what wait_for needs + stick)
    nudge: Line | None = None     # shown after ~8 s idle or a wrong move


@dataclass(frozen=True)
class NodeText:
    name: str                     # <= 20 chars
    desc: str                     # <= 2 lines of 46
    intro: str = ""               # one-line battle-start caption for enemies (<= 46)


@dataclass(frozen=True)
class EncounterText:
    key: str
    title: str                    # <= 24 chars
    prompt: str                   # <= 2 lines of 46
    options: tuple[str, str]      # button labels, <= 20 chars
    hints: tuple[str, str]        # one-line effect preview under each option, <= 46
    outcomes: dict[str, str]      # result text keyed as documented, <= 2 lines of 46


@dataclass(frozen=True)
class Page:
    title: str
    rows: list[str]               # <= 12 rows, <= 54 chars each


# ---------------------------------------------------------------------------------------------
# speaker shorthands
# ---------------------------------------------------------------------------------------------

def _n(text: str) -> Line:
    return Line("", text)


def _z(text: str, mood: str = "") -> Line:
    return Line("Zero", text, "zero", mood)


def _d(text: str, mood: str = "calm") -> Line:
    return Line("Domino", text, "domino", mood)


def _flea(text: str, mood: str = "angry") -> Line:
    return Line("Sir Flea", text, "sir_flea", mood)


def _ear(text: str, mood: str = "sly") -> Line:
    return Line("Dog-Ear", text, "dog_ear", mood)


def _chubbs(text: str, mood: str = "") -> Line:
    return Line("Chubbs", text, "chubbs", mood)


def _oriel(text: str, mood: str = "calm") -> Line:
    return Line("Young Oriel", text, "young_oriel", mood)


# ---------------------------------------------------------------------------------------------
# SCENES - story cutscenes
# ---------------------------------------------------------------------------------------------

SCENES: dict[str, list[Line]] = {
    # After the tutorial (or Skip Tutorial / first Start Night): the story begins.
    "opening": [
        _n("Eclipse Night in Wickton. The moon goes\ndark. Something gnaws under the floor."),
        _n("Domino checks the reading table.\nThe Major Arcana are gone. All 22."),
        _n("Granny Oriel will not wake up.\nHer fate thread has been chewed through."),
        _z("They took the cards. Want to chase them?\nBetter hurry. Sunrise won't wait.", "worried"),
        _d("Granny would want them back.\nThe gnawing came from the attic."),
        _z("Follow me! I remember the way.\n...Mostly. Maybe. Follow me!", "happy"),
    ],
    "enter_attic": [
        _z("The Dusty Attic! Rats live up here.", "happy"),
        _z("Rat cards are just scraps. They can't read\nhow cards talk to each other. You can.", "sly"),
        _d("Then let's make the cards talk."),
    ],
    "sir_flea_intro": [
        _z("Ooh, a tiny knight! Riding a cockroach!", "surprised"),
        _flea("Halt, cat! This chariot is mine now!\nCharge, Roachie!"),
    ],
    "sir_flea_defeated": [
        _flea("My honor! My lance! ...My roach?", "sad"),
        _z("The Chariot is back. Roachie ran off.", "happy"),
    ],
    "dog_ear_intro": [
        _z("Shh. He's reading. Also, he is chewing.", "worried"),
        _ear("I've chewed a thousand books. Now I do\ntricks too: your tricks!"),
    ],
    "dog_ear_defeated": [
        _ear("Impossible. I read everything you did...", "sad"),
        _d("You read the moves. You missed the cat."),
    ],
    "chubbs_intro": [
        _z("Whoa. He's the size of a pantry.", "surprised"),
        _chubbs("Mmm. Fate smells delicious.\nStrength is in my belly now."),
        _chubbs("Finders keepers!"),
    ],
    "chubbs_half": [
        _chubbs("Not... enough... Still hungry...", "sad"),
        _z("Careful! He's getting hungrier!", "worried"),
    ],
    "chubbs_defeated": [
        _n("Chubbs coughs up Strength, then curls up\non a pile of crumbs."),
        _chubbs("I just... didn't want to be hungry\ntomorrow.", "sad"),
        _d("Everyone is afraid of tomorrow.\nI'll take Strength back, though."),
        _z("Strength is home! Domino, you did it!", "happy"),
    ],
    "ending": [
        _n("Behind the pantry, a hole leads down.\nFar below, water runs in the dark."),
        _z("The rest of the cards are deeper down.\nAnd they keep saying a name.", "worried"),
        _z("Thousandtail.", "worried"),
        _d("Then we keep going."),
    ],
    # First defeat of a save: shown in the Parlor after the Nine Bells go dark one step.
    "first_death": [
        _z("One life down. Eight to go.", "happy"),
        _z("Relax. The night is long.", "calm"),
    ],
    # Third defeat: Granny's Dream I.
    "third_death_dream": [
        _n("A dream. A younger Granny Oriel deals\ncards by candlelight."),
        _n("Under the table, a small mouse peeks at\nher cards. It does not dare to breathe."),
        _oriel("Well. Hello, little one."),
        _oriel("Sit, if you like. No one should be\nlocked out of their own fate."),
        _n("She lets it stay. The dream fades."),
    ],
    # Fate's Draft (Skip Tutorial path): three Pick 1 of 3 screens, then How to Play.
    "draft_intro": [
        _z("Welcome to Fate's Draft! Before the night\nbegins, you pick three cards.", "happy"),
        _z("I'll show you three. You take one.\nThen three more. Then once more!"),
        _d("Simple enough. I'll choose carefully."),
    ],
    "draft_pick2": [
        _z("Nice pick! Two more to go.", "happy"),
    ],
    "draft_pick3": [
        _z("Last one! Pick a card you'll love.", "happy"),
    ],
    "draft_done": [
        _z("Ready? The rats won't wait forever.\nLet's find those missing cards!", "happy"),
    ],
    # Any later defeat: a short welcome back (the first and third have their own scenes).
    "parlor_return": [
        _z("Back at the Parlor! A bell went dark.", "calm"),
        _z("The night rewinds to dusk. Try again!", "happy"),
    ],
    "demo_end": [
        _n("Night One is over.\nThe rest of the night is still being written."),
        _z("Thanks for reading cards with us!", "happy"),
        _z("Domino will be back at moonrise.", "calm"),
    ],
}

# Big-letter screen after the demo_end lines. Title font is mixed case only.
DEMO_END_SCREEN: dict[str, object] = {
    "title": "Night One",
    "subtitle": "Swap. Chain. Pounce. Demo complete.",
    "body": [
        "Chubbs gave back Strength.",
        "Thousandtail still has the rest.",
    ],
    "footer": "A: Back to the Parlor",
}

# Short rotating Parlor lines (one per visit, picked by the Flow agent).
PARLOR_QUIPS: list[str] = [
    "Granny snores softly. The candle flickers.",
    "Zero is trying to catch his own tail.",
    "The reading table is waiting for you.",
    "Nine bells hang in the dark. Listen.",
    "Domino stretches. Time to chase some rats.",
]

# ---------------------------------------------------------------------------------------------
# TIPS - one-time contextual tips from Zero, keyed by run flag (Rules/Flow show each once)
# ---------------------------------------------------------------------------------------------

TIPS: dict[str, list[Line]] = {
    "first_stall": [
        _z("Spots sells cards! Spend Treats here.\nHe's a rat, but his prices are fair.", "sly"),
        _z("Leaving? Press B, then A. No take-backs!"),
    ],
    "first_major": [
        _z("A Major card! Big and strong. Each one\nis a cat with a special trick.", "surprised"),
        _z("Press C on it to read what it does."),
    ],
    "first_elite": [
        _z("Elite rats guard a stolen Major card.\nWin, and you get it back!", "worried"),
    ],
    "first_curse": [
        _z("Ew, a curse! It makes a card weaker.", "worried"),
        _z("A Cat Bed or Spots can wash it off."),
    ],
    "first_hiss": [
        _z("Fire next to Water? They'll hiss at\neach other.", "worried"),
        _z("Move one away and they'll stop."),
    ],
    "first_levelup": [
        _z("You leveled up! Pick one prize.", "happy"),
        _z("More Slots means a longer Spread.\nWider Cloth gives you one!"),
    ],
    "first_catbed": [
        _z("A Cat Bed! Nap to heal, sharpen a card,\nor groom away a curse. Pick one.", "happy"),
    ],
    "first_box": [
        _z("A Cardboard Box! If it fits, it sits.", "happy"),
        _z("Let's see what's inside..."),
    ],
    "first_encounter": [
        _z("Something is happening! Choose well.\nPress C if you want to know more.", "surprised"),
    ],
    "first_merge": [
        _z("Two of the same card! Merge them for\nmore stars, or keep both.", "surprised"),
        _z("Stars make a card hit harder."),
    ],
    "first_box_full": [
        _z("Your Box is full. Swap one out.\nYou get 1 Treat for the one you drop."),
    ],
    "first_bite": [
        _z("Bite Mark! The rat flips your card.\nUpside down or right side up.", "worried"),
    ],
    "first_droppings": [
        _z("Droppings! They take up a Slot and make\ntheir neighbors weaker. Ew.", "worried"),
    ],
    "boss_warning": [
        _z("That's Chubbs, the Pantry King.\nHe eats your strongest card.", "worried"),
        _z("Don't put all your power in one card.\nSpread it out, or leave a decoy!"),
        _d("Understood. Let's feed him a decoy."),
    ],
}

# ---------------------------------------------------------------------------------------------
# TUTORIAL - Prologue: The Reading Table
# ---------------------------------------------------------------------------------------------
# Action keys scenes report (see docs for exact semantics):
#   press_a  open_info  close_info  press_fight  battle_speed  battle_skip  battle_done
#   pick_up:slotN  drop:slotN  hiss_fixed  box_to_spread  catwalk_made  pick_reward
# Highlight regions:
#   spread  slot:N  fight  box  enemy_row  reading_bar  footer  hp_bar  reward  reversed_card

TUTORIAL: list[Step] = [
    # ----- Lesson 1: Cards go left to right (Practice Mouse) -----
    Step("l1_hello", [
        _z("Mew! I'm Zero, a ghost kitten.\nI'll teach you how to read cards!", "happy"),
        _d("Lead the way, little ghost."),
        _z("Oh! Before we start, press A to say hi.\nA is your Do button.", "happy"),
    ], "press_a"),
    Step("l1_peek", [
        _z("This is a card. It's one of your cat's\ntricks.", "happy"),
        _z("Press C to peek at it. Press C to close."),
    ], "close_info", highlight="slot:1", allow="c,stick",
        nudge=_z("C is Info. It never changes anything!")),
    Step("l1_order", [
        _z("Cards play left to right.\nThe Paw picks the next one.", "happy"),
    ], "press_a", highlight="spread"),
    Step("l1_enemy", [
        _z("The rat has cards too. Scraps!\nYou play one, then the rat plays one."),
    ], "press_a", highlight="enemy_row"),
    Step("l1_hp", [
        _z("This is HP. It's how brave you are.\nAt zero, it's nap time."),
    ], "press_a", highlight="hp_bar"),
    Step("l1_fight", [
        _z("Ready? Press A on FIGHT!", "happy"),
    ], "press_fight", highlight="fight", allow="a,stick",
        nudge=_z("Move to FIGHT and press A. Go go go!")),
    Step("l1_speed", [
        _z("Too slow? Press A to go faster!", "happy"),
    ], "battle_speed", highlight="footer", allow="a",
        nudge=_z("Press A. It makes the battle zoom.")),
    Step("l1_skip", [
        _z("Press B to skip to the end.", "happy"),
    ], "battle_skip", highlight="footer", allow="b",
        nudge=_z("B jumps straight to the result.")),
    Step("l1_prize", [
        _z("You won! Pick a card for a prize.\nMove left and right, then press A.", "happy"),
    ], "pick_reward", highlight="reward", allow="a,c,stick",
        nudge=_z("Press C to peek at a card first.")),

    # ----- Lesson 2: Neighbors matter (Dust Mouse, one planted Hiss) -----
    Step("l2_intro", [
        _z("Lesson two! Cards have neighbors.\nSome get along. Some don't.", "happy"),
    ], "press_a", highlight="spread"),
    Step("l2_chart", [
        _z("Same element? Nuzzle: +2 Power.\nFriends? Tail Tap: +1 Power."),
        _z("Opposites? Hiss: -1 Power. Fire and\nWater are opposites. Uh-oh!", "worried"),
    ], "press_a", highlight="reading_bar"),
    Step("l2_pickup", [
        _z("See the angry cat? Fire and Water are\nhissing at each other!", "worried"),
        _z("Pick up the Water card.\nMove onto it and press A."),
    ], "pick_up:slot3", highlight="slot:3", allow="a,stick",
        nudge=_z("Water is the blue card. Press A on it.")),
    Step("l2_drop", [
        _z("Now carry it to the end. When you press\nA, the two cards swap seats.", "happy"),
    ], "hiss_fixed", highlight="slot:4", allow="a,b,stick",
        nudge=_z("Move right to the last Slot, then A.")),
    Step("l2_fixed", [
        _z("No more hissing! See the numbers go up?", "happy"),
        _d("Neighbors matter. Noted."),
    ], "press_a", highlight="reading_bar"),
    Step("l2_box", [
        _z("Your prize is waiting in the Box.\nSpare cards sit there. They don't fight.", "happy"),
        _z("Press down to reach it. Pick it up\nwith A and drop it in the Spread."),
    ], "box_to_spread", highlight="box", allow="a,b,stick",
        nudge=_z("Down for the Box. A to pick up. Then up.")),
    Step("l2_fight", [
        _z("Perfect! Now FIGHT!", "happy"),
    ], "press_fight", highlight="fight", allow="a,stick"),
    Step("l2_prize", [
        _z("Another prize! You can skip it for\n+3 Treats. Treats buy things later.", "happy"),
    ], "pick_reward", highlight="reward", allow="a,b,c,stick"),

    # ----- Lesson 3: Count up + Reversed cards (Coin Mouse) -----
    Step("l3_intro", [
        _z("Big lesson! Numbers count up.\nA 3, then a 4: that's a Step!", "happy"),
        _z("Every Step gives +2 Power."),
    ], "press_a", highlight="spread"),
    Step("l3_catwalk", [
        _z("Three in a row is a Catwalk!\nThe last card plays twice!", "surprised"),
    ], "press_a", highlight="reading_bar"),
    Step("l3_reversed", [
        _z("See the upside-down card? Reversed cards\nplay mischief tricks.", "sly"),
        _d("Half dark, half light. I see both sides.\nMy Reversed cards get +25% Power."),
        _z("Press C on the upside-down card!"),
    ], "close_info", highlight="reversed_card", allow="c,stick",
        nudge=_z("Move to the upside-down card, then C.")),
    Step("l3_arrange", [
        _z("Now make 3, 4, 5 in a row!\nPick up cards and move them.", "happy"),
    ], "catwalk_made", highlight="spread", allow="a,b,stick",
        nudge=_z("Smallest number first. Bigger ones go right.")),
    Step("l3_catwalk_made", [
        _z("CATWALK! Look at those big numbers!", "happy"),
    ], "press_a", highlight="reading_bar"),
    Step("l3_curl", [
        _z("This rat has a Cracked Coin. It makes a\nshield called Curl. Hits chew it first.", "worried"),
        _z("Earth cards make Curl for you, too.\nWatch the little shield!"),
    ], "press_a", highlight="enemy_row"),
    Step("l3_fight", [
        _z("FIGHT! Show them your Catwalk!", "happy"),
    ], "press_fight", highlight="fight", allow="a,stick"),
    Step("l3_watch", [
        _z("See the shield soak up that hit?", "happy"),
    ], "battle_done", highlight="hp_bar", allow="a,b"),
    Step("l3_prize", [
        _z("Last prize! Take the one you like.", "happy"),
    ], "pick_reward", highlight="reward", allow="a,b,c,stick"),
    Step("l3_graduate", [
        _z("You did it! You read cards like a real\nseer, Domino!", "happy"),
        _z("A is Do. B is Back. C is Info.\nPress C any time you wonder."),
        _d("Granny taught me less than you did."),
        _z("Heehee! Now, about those missing cards...", "sly"),
    ], "press_a"),
]

# PC wording: on the PC build (app.pc) any line below whose board text matches exactly is shown with the mouse
# wording instead. The board text above never changes. Same limits as every line: <= 46 chars, <= 2 lines.
PC_TEXT: dict[str, str] = {
    "Oh! Before we start, press A to say hi.\nA is your Do button.":
        "Oh! Before we start, click to say hi.\nClick is your Do button.",
    "Press C to peek at it. Press C to close.":
        "Press I (or middle-click) to peek at it.\nPress I again to close.",
    "Ready? Press A on FIGHT!": "Ready? Click FIGHT!",
    "Move to FIGHT and press A. Go go go!": "Click FIGHT! Go go go!",
    "Too slow? Press A to go faster!": "Too slow? Click to go faster!",
    "Press A. It makes the battle zoom.": "Click! It makes the battle zoom.",
    "Press B to skip to the end.": "Right-click (or Backspace) to skip to the end.",
    "B jumps straight to the result.": "Right-click jumps straight to the result.",
    "You won! Pick a card for a prize.\nMove left and right, then press A.":
        "You won! Pick a card for a prize.\nClick the card you like.",
    "Press C to peek at a card first.": "Hover a card and press I to peek first.",
    "Pick up the Water card.\nMove onto it and press A.": "Pick up the Water card.\nClick it.",
    "Water is the blue card. Press A on it.": "Water is the blue card. Click it.",
    "Now carry it to the end. When you press\nA, the two cards swap seats.":
        "Now carry it to the end. When you click\nthere, the two cards swap seats.",
    "Move right to the last Slot, then A.": "Move right to the last Slot and click it.",
    "Press down to reach it. Pick it up\nwith A and drop it in the Spread.":
        "Click a card in the Box to pick it up,\nthen click a Spread slot to drop it.",
    "Down for the Box. A to pick up. Then up.": "Click the Box card, then a Spread slot.",
    "Press C on the upside-down card!": "Point at the upside-down card, press I!",
    "Move to the upside-down card, then C.": "Hover the upside-down card, then press I.",
    "A is Do. B is Back. C is Info.\nPress C any time you wonder.":
        "Click is Do. Right-click is Back.\nI is Info. Esc opens the Menu.",
    "Leaving? Press B, then A. No take-backs!": "Leaving? Right-click, then confirm. No undo!",
    "Press C on it to read what it does.": "Point at it and press I to read it.",
    "C is Info. It never changes anything!": "I is Info. It never changes anything!",
    "Something is happening! Choose well.\nPress C if you want to know more.":
        "Something is happening! Choose well.\nPress I (or middle-click) to know more.",
}


def pc_lines(lines):
    """`lines` with the PC mouse wording swapped in where PC_TEXT has a variant (Line or str entries)."""
    out = []
    for line in lines:
        text = line if isinstance(line, str) else line.text
        pc = PC_TEXT.get(text)
        if pc is None:
            out.append(line)
        elif isinstance(line, str):
            out.append(pc)
        else:
            out.append(Line(line.speaker, pc, line.portrait, line.mood))
    return out

# Shown on the one-screen recap (Skip Tutorial path, reopen with C on the draft screens).
HOW_TO_PLAY = Page("How to Play", [
    "SWAP: arrange your cards. Left to right!",
    "CHAIN: neighbors make readings. Same Nuzzle",
    "+2, friends Tail Tap +1, opposites Hiss -1.",
    "Counting up (3-4-5): Step +2, then Catwalk!",
    "POUNCE: press FIGHT and watch your cat play.",
    "",
    "A  Do: pick up, put down, FIGHT",
    "B  Back: cancel, skip the battle",
    "C  Info: what does this do?",
    "",
    "Upside-down cards get +25% from Two-Tone.",
    "Win fights, pick cards, beat Chubbs by sunrise.",
])

# The same page with the PC controls (app.pc): mouse first, keys second.
HOW_TO_PLAY_PC = Page(HOW_TO_PLAY.title, HOW_TO_PLAY.rows[:6] + [
    "Click  Do: pick up, put down, FIGHT",
    "Right-click  Back: cancel, skip the battle",
    "I (or middle-click)  Info: what is this?",
    "Esc  Menu.  Enter = Click, Backspace = Back.",
] + HOW_TO_PLAY.rows[10:])

# ---------------------------------------------------------------------------------------------
# NODE_TEXT - Night Path nodes (C on a node shows desc). Keyed by Node.kind.
# ---------------------------------------------------------------------------------------------

NODE_TEXT: dict[str, NodeText] = {
    "rat_fight": NodeText("Rat Fight", "A rat blocks the way.\nWin to pick a card and earn Treats."),
    "elite": NodeText("Elite Rat", "A rat guarding a stolen Major card.\nHard fight. Great prize."),
    "stall": NodeText("Spots' Stall", "A merchant rat with a monocle.\nSpend Treats on cards and more."),
    "encounter": NodeText("Strange Spot", "Something is happening up here.\nYou choose what to do."),
    "cat_bed": NodeText("Cat Bed", "A warm, soft bed. Rest or train:\nnap, sharpen, or groom."),
    "box": NodeText("Cardboard Box", "A box. Of course you're going in.\nThere might be a card inside."),
    "boss": NodeText("Chubbs", "The Pantry King sits on the loot.\nHe's hiding Strength."),
}

# Enemy blurbs shown on the Spread screen (name + C text) and the battle start caption.
ENEMY_TEXT: dict[str, NodeText] = {
    "practice_mouse": NodeText("Practice Mouse", "A small apprentice rat in cardboard\narmor. Very polite.", "The Practice Mouse bows. Then it swings."),
    "dust_mouse": NodeText("Dust Mouse", "An apprentice rat covered in dust.\nIt sneezes a lot.", "The Dust Mouse sneezes. A cloud rolls in."),
    "coin_mouse": NodeText("Coin Mouse", "An apprentice rat hugging a cracked\ncoin like a shield.", "The Coin Mouse hugs its coin tight."),
    "gray_rat": NodeText("Gray Rat", "A plain gray rat with a broken sword.\nNot a deep thinker.", "Gray Rat waves a broken sword."),
    "pickpocket": NodeText("Pickpocket", "A rat in a thief hood with a big sack.\nStrikes first. Hard to hit.", "The Pickpocket slips out of the shadows."),
    "paper_chewer": NodeText("Paper Chewer", "A rat in a torn-page apron, quill\nbehind its ear. Flips your cards.", "The Paper Chewer licks its quill."),
    "stinker": NodeText("Stinker", "A rat in grimy overalls with a plunger.\nLeaves messes in your Spread.", "The Stinker lifts its plunger. Phew."),
    "rat_sergeant": NodeText("Rat Sergeant", "A rat in a tin-can helmet with a\ntoothpick spear. Tough.", "The Rat Sergeant shouts: Squeak to attention!"),
    "sir_flea": NodeText("Sir Flea", "A tiny knight in tiny armor, riding a\ncockroach. Guards The Chariot.", "Sir Flea charges on his cockroach!"),
    "dog_ear": NodeText("Dog-Ear", "A scholar rat in robe and spectacles,\nhugging a chewed book.", "Dog-Ear adjusts his spectacles."),
    "chubbs": NodeText("Chubbs", "The Pantry King, in a crumb-stained\nvelvet robe. Always hungry.", "Chubbs licks his lips. Dinner is served."),
}

# ---------------------------------------------------------------------------------------------
# ENCOUNTERS
# ---------------------------------------------------------------------------------------------
# outcomes keys: "a", "b" = the option chosen; extra keys where a roll or a sub-choice changes the
# result (see docs): zero_booth: "a_upright" "a_reversed"; ball_of_yarn: "a_yarn" "a_ouch".

ENCOUNTERS: dict[str, EncounterText] = {
    "lost_mouse": EncounterText(
        "lost_mouse", "Lost Mouse",
        "A tiny mouse in a paper hat shivers under\na teacup. It looks very lost.",
        ("Let it go", "Eat it"),
        ("Next fight: it chews the rat's first card.", "Heal 12 HP. Gain +2 max HP."),
        {
            "a": "The mouse squeaks thanks and scurries off.\nYou feel it will remember you.",
            "b": "Crunch. Domino feels strong. Zero looks\nvery much in the other direction.",
        },
    ),
    "catnip_patch": EncounterText(
        "catnip_patch", "Catnip Patch",
        "A patch of catnip glows by the window.\nIt smells like the best idea ever.",
        ("Sniff", "Roll around"),
        ("A random card gets Catnip (+2 Power).", "Heal 20 HP. Start the next fight Drowsy."),
        {
            "a": "One card feels extra lively. Catnip!",
            "b": "So soft! Domino feels great, and a little\nsleepy. Zzz.",
        },
    ),
    "zero_booth": EncounterText(
        "zero_booth", "Zero's Reading Booth",
        "Zero built a booth from a crate. The sign\nsays: FREE READINGS (I THINK).",
        ("Draw a card", "Walk away"),
        ("Get a random Major. Reversed? A curse bites.", "Nothing happens. Zero waves."),
        {
            "a_upright": "Zero flips a card. A Major! It's yours.",
            "a_reversed": "Upside down! The Major joins you, but a\nrat curse nibbles another card.",
            "b": "Zero waves. Come back any time!\nHe will forget he said that.",
        },
    ),
    "grannys_dream": EncounterText(
        "grannys_dream", "Granny's Dream",
        "Domino curls up. In his dream, Granny's\nhands shuffle the moonlight.",
        ("Rework a card", "Rest in the dream"),
        ("Pick a card: flip it for good, +1 Star.", "Heal 30% of your max HP."),
        {
            "a": "The card turns over and glows brighter.",
            "b": "Granny hums. Domino wakes up well rested.",
        },
    ),
    "loose_page": EncounterText(
        "loose_page", "Loose Page",
        "A torn tarot page flutters in the dust.\nThe edges are chewed. The ink is warm.",
        ("Pick it up", "Burn it"),
        ("Gain a 2-Star Minor card, upside down.", "A card gets Moonlight."),
        {
            "a": "The page folds itself into a bold new card.\nIt's upside down, of course.",
            "b": "The page burns bright. One card glows\nwith moonlight.",
        },
    ),
    "ball_of_yarn": EncounterText(
        "ball_of_yarn", "Ball of Yarn",
        "A red ball of yarn rolls past.\nIt wiggles. It begs to be chased.",
        ("Chase it!", "Ignore it"),
        ("Coin flip: a card gets Yarn, or lose 5 HP.", "Nothing happens. Great self-control."),
        {
            "a_yarn": "Got it! Yarn tangles around one of your\ncards. It'll boost its neighbor.",
            "a_ouch": "Oops! You trip over it. Ow. Lose 5 HP.\nZero pretends not to laugh.",
            "b": "Domino watches it roll away.\nSo. Much. Self-control.",
        },
    ),
}

# ---------------------------------------------------------------------------------------------
# STALL_LINES - Spots the merchant (one is picked at random from each list)
# ---------------------------------------------------------------------------------------------

STALL_LINES: dict[str, list[str]] = {
    "greeting": [
        "Squeak. You get what you pay for.",
        "Welcome, welcome! Everything has a price.",
        "A cat? In my shop? ...Cash is cash.",
        "Look all you like. Touching costs extra.",
    ],
    "buy": [
        "Pleasure doing business!",
        "A fine choice. No refunds. Squeak.",
        "Sold! Your Treats are in good paws.",
    ],
    "broke": [
        "Not enough Treats. Come back richer.",
        "Squeak! That's more than you have.",
    ],
    "reroll": [
        "New stock! Fresh from the cracks.",
        "Shuffle, shuffle. Anything catch your eye?",
    ],
    "sell": [
        "Hmm. Half price. Take it or leave it.",
        "I'll take that off your paws.",
    ],
    "tuna": [
        "Tuna! The good kind. Eat up.",
    ],
    "service": [
        "Special service today. Ask nicely.",
        "I do repairs too. For a fee.",
    ],
    "leave": [
        "Come back soon! Bring friends. Treats.",
        "Rats need to eat too, you know.",
        "Safe travels. Mind the dark.",
    ],
    "reason": [   # one-time flavor the Stall may show on a later visit
        "You wonder why a rat sells to a cat?\nA rat has to eat. A rat has to plan.",
    ],
}

# ---------------------------------------------------------------------------------------------
# RESULT_LINES - quips on the Result screen
# ---------------------------------------------------------------------------------------------

RESULT_LINES: dict[str, list[str]] = {
    "victory": [
        "Purr-fect reading!",
        "The rat is out of cards.",
        "That went smoothly. Mostly.",
        "Nine lives, zero worries.",
        "The cards approve.",
    ],
    "victory_close": [   # won with under 25% HP left
        "A cat always has one more life.",
        "Close one! Whiskers singed.",
    ],
    "defeat": [
        "Domino is napping. Rats are rude.",
        "The cards slipped away.",
        "Not tonight. The bell rings.",
        "Even a seer drops a card.",
    ],
    "boss_victory": [
        "The Pantry King has been dethroned.",
    ],
}

# ---------------------------------------------------------------------------------------------
# LOADING_QUIPS - transition captions, <= 40 chars
# ---------------------------------------------------------------------------------------------

LOADING_QUIPS: list[str] = [
    "Shuffling the Great Deck...",
    "Waking Domino from a nap...",
    "Dusting off the cards...",
    "Zero is looking for his tail...",
    "Counting nine lives...",
    "Knocking a cup off the table...",
    "Chasing a moonbeam...",
    "Sharpening claws on the sofa...",
    "Listening for gnawing...",
    "Tidying the Spread...",
    "Cleaning the crystal ball...",
    "Chewing on a plan...",
]
