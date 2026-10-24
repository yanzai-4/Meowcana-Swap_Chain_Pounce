<!-- Game title: Meowcana. Tagline: Swap. Chain. Pounce. (Swap = arrange cards, Chain = readings, Pounce = the fight.) -->
# Story and Tutorial (Writer)

Source of truth for words: `python/nla/story.py`. This file explains the design and prints the full script.
All text is American English. Box limit: 2 lines x 46 characters (VT323, 8 px advance); each `Line.text`
already contains its own `\n`. Validated by script: every box fits (267 boxes checked, 0 over).

## Voice

- **Zero** (ghost kitten, the Fool, too-big scarf and bindle): playful, short words, forgetful, never lectures. Teaches by *show, then tell*: the highlight lights up first, the sentence names it, the player acts right after.
- **Domino** (tuxedo cat in apprentice-seer robe): calm, dry, nosy. Speaks rarely, one dry line per lesson at most.
- **Spots** (rat merchant, vest and monocle): smooth, a little sad underneath ("a rat has to eat").
- **Sir Flea** (tiny knight on a cockroach): pompous. **Dog-Ear** (scholar rat, robe and spectacles): bookish and smug. **Chubbs** (Pantry King in a crumb-stained velvet robe): greedy, afraid of hunger. **Granny Oriel**: asleep, only seen as Young Oriel in dreams.
- Glossary follows the GDD exactly: Spread, Box, Slot, Paw, Round, Power, Treats, Nuzzle, Tail Tap, Hiss, Step, Catwalk, Curl, Two-Tone, Reversed, Major Arcana. Zero says "Power", "Curl", "Hiss" etc. and explains each with one idea per box.

## Data format (`nla/story.py`)

| Name | Shape |
|---|---|
| `Line(speaker, text, portrait=None, mood="")` | speaker `""` = narration. Portraits: `domino zero spots sir_flea dog_ear chubbs oriel young_oriel` or None. Moods: `"" happy calm proud worried surprised sly angry sad sleepy` |
| `SCENES: dict[str, list[Line]]` | `opening enter_attic sir_flea_intro sir_flea_defeated dog_ear_intro dog_ear_defeated chubbs_intro chubbs_half chubbs_defeated ending first_death third_death_dream parlor_return demo_end` |
| `DEMO_END_SCREEN` | dict: `title subtitle body footer` for the big end card shown after `demo_end` |
| `PARLOR_QUIPS` | one-line ambient texts for the Parlor |
| `TIPS: dict[str, list[Line]]` | key = Rules flag, shown once: `first_stall first_major first_elite first_curse first_hiss first_levelup first_catbed first_box first_encounter first_merge first_box_full first_bite first_droppings boss_warning`. Unused keys are harmless. |
| `Step(id, lines, wait_for, highlight="", allow="", nudge=None)` | see below |
| `TUTORIAL: list[Step]` | 27 steps in order |
| `HOW_TO_PLAY: Page(title, rows)` | 12 rows of <= 54 chars (the skip-path recap, C reopens it) |
| `NODE_TEXT[kind]` | `NodeText(name, desc)` for kinds `rat_fight elite stall encounter cat_bed box boss` |
| `ENEMY_TEXT[enemy_key]` | `NodeText(name, desc, intro)` for all 11 enemies incl. 3 tutorial mice; `intro` = one-line battle start caption |
| `ENCOUNTERS[key]` | `EncounterText(key, title, prompt, options, hints, outcomes)` |
| `STALL_LINES[situation]` | lists of strings; pick one at random: `greeting buy broke reroll sell tuna service leave reason` |
| `RESULT_LINES` | `victory victory_close defeat boss_victory`: single-line quips (<= 40 chars) |
| `LOADING_QUIPS` | 12 captions (<= 40 chars) |

Encounter `outcomes` keys: `a` / `b` for the option chosen, plus `zero_booth`: `a_upright`, `a_reversed`; `ball_of_yarn`: `a_yarn`, `a_ouch`. `hints` mirror GDD numbers (Rules owns the numbers; if they change, update both).

## Tutorial mechanics

A `Step` shows its `lines` as dialogue boxes (A advances); when the last line is done the scene waits for `wait_for`.
`highlight` spotlights a region while the step is active. `allow` is a comma list of inputs that work
(`stick,a,b,c`); empty means only what `wait_for` needs, plus the stick. `nudge` is shown as a one-line box
after about 8 s of idle or after a wrong move. All gating is soft: a step may not trap the player (B always backs out of a held card).

### Action keys (scenes report them to the tutorial driver)

| Key | Fired by | When |
|---|---|---|
| `press_a` | Flow | player presses A on the last line of a read-only step |
| `open_info` | Spread / Battle | Card Info overlay opened (optional, informational) |
| `close_info` | Spread | Card Info overlay closed after being opened in this step |
| `press_fight` | Spread | A on FIGHT (battle starts) |
| `battle_speed` | Battle | A pressed during playback (speed changes) |
| `battle_skip` | Battle | B pressed during playback (jump to result) |
| `battle_done` | Battle | playback finished or skipped; result is visible. If a pending battle step (`battle_speed`/`battle_skip`) is still waiting when this fires, the driver drops it and moves on |
| `pick_reward` | Reward | a card (or Skip) was chosen |
| `pick_up:slotN` | Spread | card in Spread slot N picked up (slots numbered from 1, left to right) |
| `drop:slotN` | Spread | held card dropped on slot N (optional, informational) |
| `hiss_fixed` | Spread | `analyze()` now reports zero `hiss` links (however the player got there) |
| `box_to_spread` | Spread | a card from the Box was dropped into a Spread slot |
| `catwalk_made` | Spread | `analyze()` readings now contain "Catwalk" |

### Highlight regions

`spread` (whole row), `slot:N` (1-based), `fight` (the FIGHT button), `box` (Box row), `enemy_row`, `reading_bar`, `footer` (A/B/C hints), `hp_bar`, `reward` (Pick 1 of 3 row), `reversed_card` (first Reversed card in the Spread; the scene resolves it and puts the cursor on it).

### Assumptions Rules must honor (sent to Rules)

- Lesson 1: Practice Mouse, fight lasts at least 3 beats (so speed/skip prompts appear); Spread has 4 slots, full, so the prize lands in the Box. Cursor starts on slot 1 for `l1_peek`.
- Lesson 2: Spread `[Fire][Fire][Water][Air reversed]`: exactly one Hiss (slot 2-3). Fix = pick up slot 3 (Water), drop on slot 4. The step keys `pick_up:slot3`, `slot:3`, `slot:4` assume this. Box holds the Lesson 1 prize.
- Lesson 3: cards that can form 3-4-5 (any elements) incl. a Reversed card; Coin Mouse has Cracked Coin; Domino has an Earth Curl card.

## Full script

### Scenes

**opening**

- **(narration)**: Eclipse Night in Wickton. The moon goes / dark. Something gnaws under the floor.
- **(narration)**: Domino leaps onto the reading table. / The Major Arcana are gone. All 22.
- **(narration)**: Granny Oriel will not wake up. / Her fate thread has been chewed through.
- **Zero** [worried]: They took the cards. Want to chase them? / Better hurry. Sunrise won't wait.
- **Domino** [calm]: Granny would want them back. / The gnawing came from the attic.
- **Zero** [happy]: Follow me! I remember the way. / ...Mostly. Maybe. Follow me!

**enter_attic**

- **Zero** [happy]: The Dusty Attic! Rats live up here.
- **Zero** [sly]: Rat cards are just scraps. They can't read / how cards talk to each other. You can.
- **Domino** [calm]: Then let's make the cards talk.

**sir_flea_intro**

- **Zero** [surprised]: Ooh, a tiny knight! Riding a cockroach!
- **Sir Flea** [angry]: Halt, cat! This chariot is mine now! / Charge, Roachie!

**sir_flea_defeated**

- **Sir Flea** [sad]: My honor! My lance! ...My roach?
- **Zero** [happy]: The Chariot is back. Roachie ran off.

**dog_ear_intro**

- **Zero** [worried]: Shh. He's reading. Also, he is chewing.
- **Dog-Ear** [sly]: I've chewed a thousand books. Now I do / tricks too: your tricks!

**dog_ear_defeated**

- **Dog-Ear** [sad]: Impossible. I read everything you did...
- **Domino** [calm]: You read the moves. You missed the cat.

**chubbs_intro**

- **Zero** [surprised]: Whoa. He's the size of a pantry.
- **Chubbs**: Mmm. Fate smells delicious. / Strength is in my belly now.
- **Chubbs**: Finders keepers!

**chubbs_half**

- **Chubbs** [sad]: Not... enough... Still hungry...
- **Zero** [worried]: Careful! He's getting hungrier!

**chubbs_defeated**

- **(narration)**: Chubbs coughs up Strength, then curls up / on a pile of crumbs.
- **Chubbs** [sad]: I just... didn't want to be hungry / tomorrow.
- **Domino** [calm]: Everyone is afraid of tomorrow. / I'll take Strength back, though.
- **Zero** [happy]: Strength is home! Domino, you did it!

**ending**

- **(narration)**: Behind the pantry, a hole leads down. / Far below, water runs in the dark.
- **Zero** [worried]: The rest of the cards are deeper down. / And they keep saying a name.
- **Zero** [worried]: Thousandtail.
- **Domino** [calm]: Then we keep going.

**first_death**

- **Zero** [happy]: One life down. Eight to go.
- **Zero** [calm]: Relax. The night is long.

**third_death_dream**

- **(narration)**: A dream. A younger Granny Oriel deals / cards by candlelight.
- **(narration)**: Under the table, a small mouse peeks at / her cards. It does not dare to breathe.
- **Young Oriel** [calm]: Well. Hello, little one.
- **Young Oriel** [calm]: Sit, if you like. No one should be / locked out of their own fate.
- **(narration)**: She lets it stay. The dream fades.

**parlor_return**

- **Zero** [calm]: Back at the Parlor! A bell went dark.
- **Zero** [happy]: The night rewinds to dusk. Try again!

**demo_end**

- **(narration)**: Night One is over. / The rest of the night is still being written.
- **Zero** [happy]: Thanks for reading cards with us!
- **Zero** [calm]: Domino will be back at moonrise.

### Tutorial

**l1_hello** — waits for `press_a`

- **Zero** [happy]: Mew! I'm Zero, a ghost kitten. / I'll teach you how to read cards!
- **Domino** [calm]: Lead the way, little ghost.
- **Zero** [happy]: Oh! Before we start, press A to say hi. / A is your Do button.

**l1_peek** — waits for `close_info`, highlight `slot:1`, allow `c,stick`

- **Zero** [happy]: This is a card. It's one of your cat's / tricks.
- **Zero**: Press C to peek at it. Press C to close.
- *nudge* **Zero**: C is Info. It never changes anything!

**l1_order** — waits for `press_a`, highlight `spread`

- **Zero** [happy]: Cards play left to right. / The Paw picks the next one.

**l1_enemy** — waits for `press_a`, highlight `enemy_row`

- **Zero**: The rat has cards too. Scraps! / You play one, then the rat plays one.

**l1_hp** — waits for `press_a`, highlight `hp_bar`

- **Zero**: This is HP. It's how brave you are. / At zero, it's nap time.

**l1_fight** — waits for `press_fight`, highlight `fight`, allow `a,stick`

- **Zero** [happy]: Ready? Press A on FIGHT!
- *nudge* **Zero**: Move to FIGHT and press A. Go go go!

**l1_speed** — waits for `battle_speed`, highlight `footer`, allow `a`

- **Zero** [happy]: Too slow? Press A to go faster!
- *nudge* **Zero**: Press A. It makes the battle zoom.

**l1_skip** — waits for `battle_skip`, highlight `footer`, allow `b`

- **Zero** [happy]: Press B to skip to the end.
- *nudge* **Zero**: B jumps straight to the result.

**l1_prize** — waits for `pick_reward`, highlight `reward`, allow `a,c,stick`

- **Zero** [happy]: You won! Pick a card for a prize. / Move left and right, then press A.
- *nudge* **Zero**: Press C to peek at a card first.

**l2_intro** — waits for `press_a`, highlight `spread`

- **Zero** [happy]: Lesson two! Cards have neighbors. / Some get along. Some don't.

**l2_chart** — waits for `press_a`, highlight `reading_bar`

- **Zero**: Same element? Nuzzle: +2 Power. / Friends? Tail Tap: +1 Power.
- **Zero** [worried]: Opposites? Hiss: -1 Power. Fire and / Water are opposites. Uh-oh!

**l2_pickup** — waits for `pick_up:slot3`, highlight `slot:3`, allow `a,stick`

- **Zero** [worried]: See the angry cat? Fire and Water are / hissing at each other!
- **Zero**: Pick up the Water card. / Move onto it and press A.
- *nudge* **Zero**: Water is the blue card. Press A on it.

**l2_drop** — waits for `hiss_fixed`, highlight `slot:4`, allow `a,b,stick`

- **Zero** [happy]: Now carry it to the end. When you press / A, the two cards swap seats.
- *nudge* **Zero**: Move right to the last Slot, then A.

**l2_fixed** — waits for `press_a`, highlight `reading_bar`

- **Zero** [happy]: No more hissing! See the numbers go up?
- **Domino** [calm]: Neighbors matter. Noted.

**l2_box** — waits for `box_to_spread`, highlight `box`, allow `a,b,stick`

- **Zero** [happy]: Your prize is waiting in the Box. / Spare cards sit there. They don't fight.
- **Zero**: Press down to reach it. Pick it up / with A and drop it in the Spread.
- *nudge* **Zero**: Down for the Box. A to pick up. Then up.

**l2_fight** — waits for `press_fight`, highlight `fight`, allow `a,stick`

- **Zero** [happy]: Perfect! Now FIGHT!

**l2_prize** — waits for `pick_reward`, highlight `reward`, allow `a,b,c,stick`

- **Zero** [happy]: Another prize! You can skip it for / +3 Treats. Treats buy things later.

**l3_intro** — waits for `press_a`, highlight `spread`

- **Zero** [happy]: Big lesson! Numbers count up. / A 3, then a 4: that's a Step!
- **Zero**: Every Step gives +2 Power.

**l3_catwalk** — waits for `press_a`, highlight `reading_bar`

- **Zero** [surprised]: Three in a row is a Catwalk! / The last card plays twice!

**l3_reversed** — waits for `close_info`, highlight `reversed_card`, allow `c,stick`

- **Zero** [sly]: See the upside-down card? Reversed cards / play mischief tricks.
- **Domino** [calm]: Half dark, half light. I see both sides. / My Reversed cards get +25% Power.
- **Zero**: Press C on the upside-down card!
- *nudge* **Zero**: Move to the upside-down card, then C.

**l3_arrange** — waits for `catwalk_made`, highlight `spread`, allow `a,b,stick`

- **Zero** [happy]: Now make 3, 4, 5 in a row! / Pick up cards and move them.
- *nudge* **Zero**: Smallest number first. Bigger ones go right.

**l3_catwalk_made** — waits for `press_a`, highlight `reading_bar`

- **Zero** [happy]: CATWALK! Look at those big numbers!

**l3_curl** — waits for `press_a`, highlight `enemy_row`

- **Zero** [worried]: This rat has a Cracked Coin. It makes a / shield called Curl. Hits chew it first.
- **Zero**: Earth cards make Curl for you, too. / Watch the little shield!

**l3_fight** — waits for `press_fight`, highlight `fight`, allow `a,stick`

- **Zero** [happy]: FIGHT! Show them your Catwalk!

**l3_watch** — waits for `battle_done`, highlight `hp_bar`, allow `a,b`

- **Zero** [happy]: See the shield soak up that hit?

**l3_prize** — waits for `pick_reward`, highlight `reward`, allow `a,b,c,stick`

- **Zero** [happy]: Last prize! Take the one you like.

**l3_graduate** — waits for `press_a`

- **Zero** [happy]: You did it! You read cards like a real / seer, Domino!
- **Zero**: A is Do. B is Back. C is Info. / Press C any time you wonder.
- **Domino** [calm]: Granny taught me less than you did.
- **Zero** [sly]: Heehee! Now, about those missing cards...

### Tips

**first_stall**

- **Zero** [sly]: Spots sells cards! Spend Treats here. / He's a rat, but his prices are fair.
- **Zero**: Leaving? Press B, then A. No take-backs!

**first_major**

- **Zero** [surprised]: A Major card! Big and strong. Each one / is a cat with a special trick.
- **Zero**: Press C on it to read what it does.

**first_elite**

- **Zero** [worried]: Elite rats guard a stolen Major card. / Win, and you get it back!

**first_curse**

- **Zero** [worried]: Ew, a curse! It makes a card weaker.
- **Zero**: A Cat Bed or Spots can wash it off.

**first_hiss**

- **Zero** [worried]: Fire next to Water? They'll hiss at / each other.
- **Zero**: Move one away and they'll stop.

**first_levelup**

- **Zero** [happy]: You leveled up! Pick one prize.
- **Zero**: More Slots means a longer Spread. / Wider Cloth gives you one!

**first_catbed**

- **Zero** [happy]: A Cat Bed! Nap to heal, sharpen a card, / or groom away a curse. Pick one.

**first_box**

- **Zero** [happy]: A Cardboard Box! If it fits, it sits.
- **Zero**: Let's see what's inside...

**first_encounter**

- **Zero** [surprised]: Something is happening! Choose well. / Press C if you want to know more.

**first_merge**

- **Zero** [surprised]: Two of the same card! Merge them for / more stars, or keep both.
- **Zero**: Stars make a card hit harder.

**first_box_full**

- **Zero**: Your Box is full. Swap one out. / You get 1 Treat for the one you drop.

**first_bite**

- **Zero** [worried]: Bite Mark! The rat flips your card. / Upside down or right side up.

**first_droppings**

- **Zero** [worried]: Droppings! They take up a Slot and make / their neighbors weaker. Ew.

**boss_warning**

- **Zero** [worried]: That's Chubbs, the Pantry King. / He eats your strongest card.
- **Zero**: Don't put all your power in one card. / Spread it out, or leave a decoy!
- **Domino** [calm]: Understood. Let's feed him a decoy.

### How to Play

```
How to Play
SWAP: arrange your cards. Left to right!
CHAIN: neighbors make readings. Same Nuzzle
+2, friends Tail Tap +1, opposites Hiss -1.
Counting up (3-4-5): Step +2, then Catwalk!
POUNCE: press FIGHT and watch your cat play.

A  Do: pick up, put down, FIGHT
B  Back: cancel, skip the battle
C  Info: what does this do?

Upside-down cards get +25% from Two-Tone.
Win fights, pick cards, beat Chubbs by sunrise.
```

### Nodes and enemies

- **rat_fight** — Rat Fight: A rat blocks the way. Win to pick a card and earn Treats.
- **elite** — Elite Rat: A rat guarding a stolen Major card. Hard fight. Great prize.
- **stall** — Spots' Stall: A merchant rat with a monocle. Spend Treats on cards and more.
- **encounter** — Strange Spot: Something is happening up here. You choose what to do.
- **cat_bed** — Cat Bed: A warm, soft bed. Rest or train: nap, sharpen, or groom.
- **box** — Cardboard Box: A box. Of course you're going in. There might be a card inside.
- **boss** — Chubbs: The Pantry King sits on the loot. He's hiding Strength.
- **practice_mouse** — Practice Mouse: A small apprentice rat in cardboard armor. Very polite. Caption: "The Practice Mouse bows. Then it swings."
- **dust_mouse** — Dust Mouse: An apprentice rat covered in dust. It sneezes a lot. Caption: "The Dust Mouse sneezes. A cloud rolls in."
- **coin_mouse** — Coin Mouse: An apprentice rat hugging a cracked coin like a shield. Caption: "The Coin Mouse hugs its coin tight."
- **gray_rat** — Gray Rat: A plain gray rat with a broken sword. Not a deep thinker. Caption: "Gray Rat waves a broken sword."
- **pickpocket** — Pickpocket: A rat in a thief hood with a big sack. Strikes first. Hard to hit. Caption: "The Pickpocket slips out of the shadows."
- **paper_chewer** — Paper Chewer: A rat in a torn-page apron, quill behind its ear. Flips your cards. Caption: "The Paper Chewer licks its quill."
- **stinker** — Stinker: A rat in grimy overalls with a plunger. Leaves messes in your Spread. Caption: "The Stinker lifts its plunger. Phew."
- **rat_sergeant** — Rat Sergeant: A rat in a tin-can helmet with a toothpick spear. Tough. Caption: "The Rat Sergeant shouts: Squeak to attention!"
- **sir_flea** — Sir Flea: A tiny knight in tiny armor, riding a cockroach. Guards The Chariot. Caption: "Sir Flea charges on his cockroach!"
- **dog_ear** — Dog-Ear: A scholar rat in robe and spectacles, hugging a chewed book. Caption: "Dog-Ear adjusts his spectacles."
- **chubbs** — Chubbs: The Pantry King, in a crumb-stained velvet robe. Always hungry. Caption: "Chubbs licks his lips. Dinner is served."

### Encounters

**Lost Mouse** (lost_mouse): A tiny mouse in a paper hat shivers under a teacup. It looks very lost.
- [Let it go] Next fight: it chews the rat's first card.
- [Eat it] Heal 12 HP. Gain +2 max HP.
- outcome `a`: The mouse squeaks thanks and scurries off. You feel it will remember you.
- outcome `b`: Crunch. Domino feels strong. Zero looks very much in the other direction.

**Catnip Patch** (catnip_patch): A patch of catnip glows by the window. It smells like the best idea ever.
- [Sniff] A random card gets Catnip (+2 Power).
- [Roll around] Heal 20 HP. Start the next fight Drowsy.
- outcome `a`: One card feels extra lively. Catnip!
- outcome `b`: So soft! Domino feels great, and a little sleepy. Zzz.

**Zero's Reading Booth** (zero_booth): Zero built a booth from a crate. The sign says: FREE READINGS (I THINK).
- [Draw a card] Get a random Major. Reversed? A curse bites.
- [Walk away] Nothing happens. Zero waves.
- outcome `a_upright`: Zero flips a card. A Major! It's yours.
- outcome `a_reversed`: Upside down! The Major joins you, but a rat curse nibbles another card.
- outcome `b`: Zero waves. Come back any time! He will forget he said that.

**Granny's Dream** (grannys_dream): Domino curls up. In his dream, Granny's hands shuffle the moonlight.
- [Rework a card] Pick a card: flip it for good, +1 Star.
- [Rest in the dream] Heal 30% of your max HP.
- outcome `a`: The card turns over and glows brighter.
- outcome `b`: Granny hums. Domino wakes up well rested.

**Loose Page** (loose_page): A torn tarot page flutters in the dust. The edges are chewed. The ink is warm.
- [Pick it up] Gain a 2-Star Minor card, upside down.
- [Burn it] A card gets Moonlight.
- outcome `a`: The page folds itself into a bold new card. It's upside down, of course.
- outcome `b`: The page burns bright. One card glows with moonlight.

**Ball of Yarn** (ball_of_yarn): A red ball of yarn rolls past. It wiggles. It begs to be chased.
- [Chase it!] Coin flip: a card gets Yarn, or lose 5 HP.
- [Ignore it] Nothing happens. Great self-control.
- outcome `a_yarn`: Got it! Yarn tangles around one of your cards. It'll boost its neighbor.
- outcome `a_ouch`: Oops! You trip over it. Ow. Lose 5 HP. Zero pretends not to laugh.
- outcome `b`: Domino watches it roll away. So. Much. Self-control.

### Spots, results, loading

- **greeting**: Squeak. You get what you pay for. | Welcome, welcome! Everything has a price. | A cat? In my shop? ...Cash is cash. | Look all you like. Touching costs extra.
- **buy**: Pleasure doing business! | A fine choice. No refunds. Squeak. | Sold! Your Treats are in good paws.
- **broke**: Not enough Treats. Come back richer. | Squeak! That's more than you have.
- **reroll**: New stock! Fresh from the cracks. | Shuffle, shuffle. Anything catch your eye?
- **sell**: Hmm. Half price. Take it or leave it. | I'll take that off your paws.
- **tuna**: Tuna! The good kind. Eat up.
- **service**: Special service today. Ask nicely. | I do repairs too. For a fee.
- **leave**: Come back soon! Bring friends. Treats. | Rats need to eat too, you know. | Safe travels. Mind the dark.
- **reason**: You wonder why a rat sells to a cat? A rat has to eat. A rat has to plan.
- **result victory**: Purr-fect reading! | The rat is out of cards. | That went smoothly. Mostly. | Nine lives, zero worries. | The cards approve.
- **result victory_close**: A cat always has one more life. | Close one! Whiskers singed.
- **result defeat**: Domino is napping. Rats are rude. | The cards slipped away. | Not tonight. The bell rings. | Even a seer drops a card.
- **result boss_victory**: The Pantry King has been dethroned.
- **loading**: Shuffling the Great Deck... | Waking Domino from a nap... | Dusting off the cards... | Zero is looking for his tail... | Counting nine lives... | Knocking a cup off the table... | Chasing a moonbeam... | Sharpening claws on the sofa... | Listening for gnawing... | Tidying the Spread... | Cleaning the crystal ball... | Chewing on a plan...
- **parlor**: Granny snores softly. The candle flickers. | Zero is trying to catch his own tail. | The reading table is waiting for you. | Nine bells hang in the dark. Listen. | Domino stretches. Time to chase some rats.

### Demo end card

{'title': 'Night One', 'subtitle': 'Swap. Chain. Pounce. Demo complete.', 'body': ['Chubbs gave back Strength.', 'Thousandtail still has the rest.'], 'footer': 'A: Back to the Parlor'}
