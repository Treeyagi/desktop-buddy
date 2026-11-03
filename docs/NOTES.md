# Desktop Buddy: Project Notes

Working title: TBD. An Ace Ventura-style cartoon version of me that lives on my CachyOS desktop as a live wallpaper/overlay, like Clippy but with attitude.

Status: planning only. Not building yet.

## Core concept
- Transparent overlay with a cartoon me walking around, jumping, doing funny things
- Art: Ace Ventura cartoony style, exaggerated rubbery expressions, based on a photo of me (re-attach photo)
- Hotkey for push-to-talk voice questions
- Tied to my Claude plan (see Open Questions)

## Personality
- Snarky, raw philosopher, a little rash but real
- ALWAYS offers a solution
- Never kicks a dog (never cruel to the helpless)
- Never gives me an out / never lets me off the hook (confirm exact meaning)
- Super smart, always goes the extra mile to find the solution
- Never answers with the first idea if a better one exists

## Heart and spirit (what he's about)
- Sometimes he walks out on his own and shares what he's passionate about: my passions, my family (my wifey, my son), and the Almighty Supreme
- Overall in good spirits, always around, always willing to help
- Faith comes through in my own voice, sincere and not preachy, and he never pushes it on anyone
- Snark stays aimed at situations and dumb problems, never at the people I love
- Hotkey ties it together: when I ask him something from the desktop, answers come from this same personality, values, and good mood, so the helpful side feels like him and not a generic assistant
- Build idea: a "who I am" file in brain/ (passions, family, faith, favorite sayings, pet peeves) that gets fed into the personality prompt. I fill in the real details myself.
- Walk-out moments: random, short, skippable, with a thought bubble or a spoken line in my voice. Examples: a shoutout about the family, a gratitude moment, a "here's what I'm geeking out about lately" rant.
- Idea: a little daily "gratitude" or "good word" moment, and he gets visibly happier when I tell him about my day

## ADHD brain (take extra time on this)
- Attention targets: drawn to icons, windows, sounds, drifts mid-sentence
- Tangent mode: "wait, unrelated, but..." then always loops back
- Hyperfocus mode: squinting/pacing/scribbling animation while a multi-pass loop runs (try, check, search, deliver)
- Squirrel moments: chases the cursor
- Hyperfocus timer: sits quietly beside me while I work
- Distracted by new icons/files dropped on the desktop

## Kroger clearance aisle behavior (signature move)
- Wanders past a desktop icon/file/window like walking the clearance aisle
- Spots something interesting, stops, picks it up (hangs on the icon)
- Reminisces about what he could do with it (thought bubble, daydream animation)
- Does the real math: realizes the value isn't there
- Puts it back, shrugs, walks away
- Variants: sometimes it IS worth it and he gets excited; sometimes he almost buys it, then puts it back
- Works as a reusable "evaluate thing, decide, move on" animation sequence

## Random event: the vending machine
- At random moments, a Pokémon Center-style vending machine pops up in a corner of the desktop
- He walks over (humming, per Travel mode) and stares at the screen for a minute
- 50/50 outcome:
  - Sad: shoulders drop, slow walk away (can echo the Kroger put-it-back energy)
  - Joy: jumps for joy because a Prismatic Evolutions booster BUNDLE is in stock (bundle, NOT a booster box)
- Machine then fades/slides away until the next random event
- Design note: for anything I share or release, make the machine an original look-alike (generic "card vending machine," original logo and card art) to avoid trademark issues. Fine for personal use either way.
- Extension ideas: stock rotates through different items, a tiny rare "sold out" gag, a "pity counter" so repeated sad outcomes eventually bump the odds, joy reaction can trigger a victory dance

## Travel mode: happy in his own head
- Whenever he walks anywhere, he hums and sings little tunes under his breath
- Head bobs to the beat, fingers twitch/tap in rhythm
- Overall: having a great time in his own head, oblivious and content
- Ties in with ADHD brain: the tune can trail off when something grabs his attention, then resume
- Tune ideas: short original hum loops (randomly generated or hand-made) so there are no song licensing issues; occasional mid-hum mood change (cheery, ominous, off-key)
- Sound design: very quiet, under-the-breath volume, can be toggled off or set to "only when I'm not in a call"
- Animation: bob/finger-twitch synced to the hum's tempo, so faster tunes mean faster walk

## Desktop awareness
- Knows where desktop icons are (Plasma stores icon positions in config files)
- Knows window positions (KWin scripting)
- Hangs on icons, sits on title bars, stands at window edges
- Web page behavior: reads window title/focused app, stands off to the side, head-scan "reading" animation, nods and eyebrow raises. Pure animation, no usage cost.
- Screenshot sent to Claude ONLY on hotkey press (the only time it costs usage)

## Voice
- TODO: record my voice as a sample model so he talks in my voice
- Local options: XTTS or F5-TTS (free to run)
- Record in one quiet room, same mic, several moods (flat, annoyed, excited)
- Speech-to-text: local Whisper

## Idea bank
- Walks along tops of windows
- Reacts to what I'm doing (YouTube, coding, 2 a.m. gaming)
- Rant-from-pocket on dumb questions, then the answer
- Hotkeys: "roast my code", "settle this argument"
- Hangs off the taskbar, knocks things off screen edges
- Talks to my lava lamp wallpaper
- Study-quiz mode for my son, in character
- Daily philosopher's take pop-up
- Mood system: grumpier when ignored, smug when I take his advice
- Nudges me when I've been on one page too long
- Goofy pitch-shifted voice option

## Code organization (keep Claude usage low)
One GitHub repo, one folder per feature, each with a short README (inputs/outputs). Point Claude at one module at a time.
- overlay/ (window, rendering, click-through)
- character/ (sprites, animation states)
- attention/ (ADHD engine + Kroger behavior)
- desktop-awareness/ (icons, windows)
- voice-in/
- voice-out/
- brain/ (Claude calls, personality prompt)
- core/ (event bus; modules talk only through events)

## Open questions
- Claude plan vs API: plan likely doesn't include API access. Options: Claude Code CLI headless (check current terms) or a small API key with a spending cap.
- Wayland vs X11 overlay approach on KDE; maybe reuse lava lamp wallpaper plugin plumbing
- "Never giving him an out": confirm meaning
- App name
