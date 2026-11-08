# character

Sprites, rigs, and animation states for the cartoon me (Ace Ventura-style, rubbery and exaggerated).

- **Inputs:** state requests from `attention/` and `brain/` (walk, jump, talk, shrug, rant, hum-bob, victory dance, sad walk-off)
- **Outputs:** current frame and position for `overlay/`
- **Notes:** hum tempo drives walk speed and bob timing.

## The look
A vector puppet drawn with QPainter in the style of `reference-ultimate-pull.jpg`: chunky ink outlines, soft cel shading, big glossy eyes and chibi proportions.

- **Outfit:** a purple bucket hat with yellow stars and a red-and-white mushroom, a rainbow-striped hoodie with white drawstrings, and baggy jeans stacking over the shoes.
- **Shoes:** chunky 2000s D3-style skate shoes, about 1.5x a normal sneaker, modeled on the photos in `reference-shoes/`. They have a big padded tongue flopping forward, wavy molded lobes with oval lace loops, fat laces, a heel pull tab, a ribbed toe and a thick sole with air bubbles. There are three colorways: hot pink with black laces (the default), dusty pink with a speckled sole, and sky blue with a pink sole. The shape only, no logo. Switch with `rig.set_shoes("dusty pink")`; the settings window will use this. Close-ups are in `shoes-sheet.png`.
- **Face:** a ginger beard that goes grey-white at the chin, and a bushy mustache.
- **Expressions:** happy, closed and sparkly eyes, tears of joy, a wide-open laugh with teeth, a raised eyebrow, and blushing.
- **Arms:** both hands are free (fist, open or pointing). The arms stretch like rubber hoses for big gestures.
- **Bees:** bumblebee buddies fly around him.

`reference-tree-wizard.png` is the earlier look, kept for reference.

## Files
- `rig.py`: `Pose` (joint angles plus face settings) and `draw_buddy()`. Angles: 0 points down, positive swings forward. `reach_f`/`reach_b` stretch the arms, and `back_front` brings the far arm round in front (beard scratch, hugs).
- `behavior.py`: `Buddy` keeps:
  - position and the current action
  - pose blending, so moves never snap
  - a spring for the hat
  - blinking, tear drips and speech bubbles
  - the bees

  Each action is one `_<name>()` method that returns a Pose.
- `moves.py`: shared body moves. The walk cycle (moods: content, cheery, strut, sad), victory dance, fists up, hold, hug, beard scratch, shrug, palms up.
- `bees.py`: the bumblebees. Each one chases a moving target with a little wobble, flaps its wings, and buzzes off-screen when dismissed. One companion bee always hangs around him.
- `effects.py`: hummed music notes, sparkles, hearts, dust puffs, snore z's, tear drops, glowing spores, and flowers and toadstools that sprout from the floor.
- `scenes.py`: multi-step bits that queue a walk and then their own action, with thought clouds and props.
- `props.py`: clearance-aisle finds (gnome, lava lamp, cactus, rubber duck, mystery box, each with a yellow % tag), glowing copies of real desktop icons, the CARD-O-MATIC vending machine, the bundle and the holo "ULTRA RARE" card. All original art, no real logos or card art.
- `sprite.py`: the alternative look (settings: Character). Treeyagi from his character pack in `sprites/treeyagi/`: idle, walk, skip, charge, attack, hurt and faint in eight directions. Walking uses the walk cycle, jumps, dances and the sprint skip, spores and listening charge up the wand, a nap faints and holds, shadow boxing and "I choose you!" swing the wand. Everything else is the idle loop, with the pose's lift, squash and lean applied to the picture.
- `preview.py`: renders a contact sheet of actions to a PNG, no desktop needed:
  `python3 character/preview.py sheet.png`. The saved sheets are `action-sheet.png`, `scenes-kroger.png` and `scenes-vending.png`.

## Actions
- **walk:** sings or hums with notes, both arms swinging, head-bobbing to the beat. Sometimes he stops with "!", hands up, when something catches his eye.
- **idle:** one of twelve, each with breathing and blinking (he is content, not sleepy: the yawn is rare, sky-gazing and the owl are common, hyper ones the boxing; grumpy skips the happy ones):
  - watching the bee buzz around
  - hand on his belly
  - scratching his beard
  - humming
  - arms crossed, tapping his foot
  - **yawn and stretch** (eyes watering), **gazing at the sky** with hands behind his back, an **owl head-swivel** with huge eyes, a **neck and shoulder roll**
  - **shadow boxing**, **kicking a pebble** and watching it fly
  - the **Pokemon throw**: ball up, wind up, "I choose you!", and point
  - preview one with `python3 character/preview.py out.png --actions idle:owl`
- **jump:** crouch, then fists up in the air, then a squash landing. Sometimes a double hop.
- **wave:** an open-hand wave with "hey hey!".
- **dance:** a routine of 4 to 6 moves at 126 BPM, four beats each, crossfaded so nothing snaps. It always opens with the fist pump, then picks from: disco point, sprinkler, raise the roof, robot, running man (shuffle), headbang (EDM bounce, dust on the beat), hip circles, a twirl (he squeezes thin and turns), windshield wipers (both index fingers up, swinging to the beat), chicken (flapping elbows, pecking head), T-rex (tiny twitching arms, big stomps), and the floss. Hearts, notes and sparkles come with it, and the bee loops around him. The moves are `dance_*` in `moves.py` (`DANCE_MOVES`); preview one with `python3 character/preview.py out.png --actions dance:disco`.
- **moment:** a walk-out moment: he stops and says something real, with a gesture for the kind (`moments.py`): *gratitude* (hand on heart, a small bow, hearts), *family* (a hug, swaying, hearts), *geek* (bouncing, hands everywhere, sparkling eyes), *dream* (pointing at the horizon), *vibes* (palms up, floating a little, spores), *calm* (one slow deep breath). Preview: `--actions moment:family`. The lines come from `brain/who-i-am.md`; no Claude call, no cost.
- **turning:** whenever he turns around he does a quick squash and bounce instead of snapping.
- **spores:** he shimmies until the mushroom on his hat puffs glowing spores, then stomps, and toadstools and flowers pop up around him.
- **meditate:** sinks into a cross-legged sit with his hands on his knees, breathes slowly, floats a little in the middle with glowing sparkles and spores and says "ommm...", then settles back down.
- **nap:** sits back, hand on belly, snoring z's while the bee naps on his hat mushroom. Then he wakes with "?!" and stretches.
- **stretch:** arms out wide and a big yawn, with yawn tears.
- **quip:** a short line with an open-hand gesture.

## Scenes
**gamestop** (`gamestop.py`): mom says one console has to go. A CONSOLE ROLL slot machine rises and he pulls the lever; the console it lands on (NES, SNES, N64, GameCube, PS2, Dreamcast, Game Boy, Wii) is what he carries to the GAME STOP store on the far side of the screen. Halfway, a scalper pulls him aside and offers cash. He says no, the scalper whistles for goons, and the madness starts: goons chase him (he hops them), a midnight-release stampede and a racing rival kid overtake him, and rain may pour. At the door a manager offers a pittance and a coupon (most often), a surprise mint payday, or he keeps the console. Try it with `python3 tools/send.py gamestop`.

**kroger, using your real desktop icons** (about 3 in 4 times, when icons are known):
1. He spots an icon with "!", points, and walks under it.
2. Three bees dive in from the top of the screen, grab his hat brim and crown, and carry him up, legs kicking.
3. His companion bee flies up and brings him a glowing copy of the real icon.
4. He turns it over while scratching his beard, daydreams about it, then does the math on the file's real size and age.
5. The bee flies the copy back into its slot, and the bees set him down.

A brand-new file on the desktop gets checked out next, with "ooh, new!".

**kroger with a floor find:** he picks it up, scratches his beard, daydreams, does the math on the price. Then one of three endings:
- "nah." and a shrug (55%)
- a hug and "a steal!", then it goes into his hat (25%)
- "i'll take it!", he walks off, stops with "!", comes back and says "...nope." (20%)

**perch:** he picks a window with room above its title bar, as long as no other window is covering that spot. Bees lift him onto it ("nice view."), and he sits on the edge with his legs dangling, humming and watching the bee. If you drag the window, he rides along, with "wheee!" when it moves fast. If it closes or goes fullscreen, he yells "whoa!" and the bees carry him down. At the end the bees fly him back to the floor.

**vending:** the CARD-O-MATIC rises out of the floor. He hops with "!!", walks over, and stares at "CHECKING...", scratching his beard and tapping his foot. Two outcomes:
- **Sold out:** a blank stare, "...sold out.", a sad tear, his shoulders drop, and he walks away slowly.
- **In stock:** "IN STOCK?!" and he jumps for joy. He grabs the bundle and rips it open, then rummages through the pack, flicking nine cards over his shoulder ("nope.", "meh.") down to the tenth. If that last card is a hit (`pack_hit_odds`, 25%), **The Ultimate Pull** happens: a giant holo card rises up behind him while he cries tears of joy with both fists up, like the reference card. Two extra bees cheer, then the card goes into his hat for safekeeping and he dances.
- **A dud pack:** the last card turns out to be a common or an energy. He stares, tears build, then he throws the wrapper and all the cards in the air ("WHYYY"), they scatter, bounce and fade, and a beat later he shakes it off with "...anyway!" and is his goofy self again. The cards are `card_back`, `common_card` and `energy_card` in `props.py`; tossed items fly under gravity (`Item.free`).

The odds start at 50/50. Each letdown in a row adds 15% (the pity counter, capped at 90%) and a win resets it.

His sayings and greetings are editable in the settings window's Sayings tab; `QUIPS` and `GREETINGS` in `behavior.py` are just the defaults. Speech bubbles word-wrap long lines.
