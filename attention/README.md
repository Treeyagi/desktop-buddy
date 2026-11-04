# attention

The ADHD engine. Pure local logic, no Claude usage. It watches the desktop and the clock, decides when his attention wanders, and nudges him over the bus. The character decides how to act it out (`character/adhd.py`), and only takes the bait when he's free: walking, idling or chatting, never mid-scene or mid-conversation.

- **Inputs:** `desktop.windows`, `desktop.cursor` (KWin reports the pointer about 15 times a second while it moves), `voice.listening`, `buddy.interaction`, and playing audio streams (`pactl`, polled every 4 s)
- **Outputs:** the `attention.*` events below

| Event | When | What he does |
|---|---|---|
| `attention.squirrel` | the cursor moves, about 1 in 16 times, at most every 75 s | runs after the cursor, pounces when it stops near him ("gotcha!") |
| `attention.gaze` | you switch windows (30%, at most every 60 s), or new audio starts (50%, at most every 2 min) | stares, drifts toward it or bobs to the music, then "...anyway." |
| `attention.tangent` | every 6 to 15 minutes | "okay, the plan for today is—" then "wait, unrelated, but..." then a random thought, then "anyway." |
| `attention.nudge` | you've been on the same window longer than the nudge setting (default 60 min) | points and suggests a break (said later, if he's busy) |
| `attention.smug` | you switch windows within 3 minutes of a nudge | "told ya." |
| `attention.moment` | every 12 to 30 minutes (the first after 5 to 10) | stops and says something real from your story with a matching gesture; see `character/moments.py` |
| `attention.music` | audio is playing from a browser or a music player (`MUSIC_APPS` in `engine.py`) for two polls in a row (8 s); `False` when it stops | he says "ooh, a bop!" and dances, then dances again every 35 to 60 s while it plays (not in quiet mode) |
| `attention.react` | you switch to a video, code, game or chat window (50%, at most every 8 min), or use video/code/games between midnight and 4 a.m. (every 45 min) | a quip about it, picked from the lines in `ACTIVITIES` / `LATE` in `engine.py`; matched on app and window title, all local |
| `attention.mood` | always: settles toward cheerful; sinks when ignored over 25 min; rises when you interact | frowns when grumpy, extra cheery when happy; mood shifts which moves he picks |
| `attention.sulk` | he's grumpy (mood below -0.4), at most every 10 to 20 min | sits with arms crossed: "nobody talks to me anymore..." |
| `attention.focus` / `attention.focus_done` | you start a focus timer (tray menu or the Behavior tab: 25 or 50 min) | walks to the side of the screen and sits quietly with a countdown over his head; at the end, a dance and "break time! nice work." |

**What counts as attention to him:** push-to-talk, the settings window's buttons, and changing his settings.

**No distractions while:** a focus timer is running, or quiet mode is on.

## Settings (Behavior tab, "ADHD brain")
- `adhd_squirrel`, `adhd_distract`, `adhd_tangents`, `adhd_react`, `adhd_dance`, `adhd_moments`, `adhd_mood`: on/off switches, all on by default
- `nudge_minutes`: 0 means never, default 60
- `tangents`: his tangent lines, editable in the Sayings tab
- `moments`: his walk-out moment lines (`kind: text`), editable in the Sayings tab

## Still planned
- the hyperfocus thinking loop for Claude answers (try, check, search, deliver)
- react lines from Claude, and from the page title (what the video is) instead of fixed lines
