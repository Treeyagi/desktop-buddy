# settings

The tray icon, the settings window, and the settings file they share with the running buddy.

- **Inputs:** clicks in the tray menu and the settings window
- **Outputs:** `~/.config/desktop-buddy/settings.json`; the overlay watches it and applies changes live
- **Notes:** the settings window runs as its own process. The overlay sets `QT_WAYLAND_SHELL_INTEGRATION=layer-shell`, which would turn any window in its process into a borderless desktop layer.

## Files
- `store.py`: `DEFAULTS`, `load()`, `save()`, `update(**changes)`, and `SettingsFile`, which emits `changed(dict)` when the file changes on disk. Saving swaps in a complete new file in one step, so nobody reads a half-written one. Unknown keys are kept and missing ones fall back to defaults.
- `tray.py`: the panel icon (a little portrait of him). The menu has Pause, Quiet mode, Settings… and Quit, and clicking the icon opens settings. It lives in the overlay process; Plasma draws the menu.
- `window.py`: the settings window. A live mini buddy at the top reacts as you move the sliders. Next to it: whether the buddy is running, with a Start/Quit button. Run it directly with `python3 settings/window.py`.

## Settings (Buddy tab)
| Key | What it does |
|---|---|
| `paused` | Hides and freezes him (the overlay stops redrawing) |
| `size` | Character scale, 0.5 to 2.0 in the window (default 1.1) |
| `monitor` | A screen name, or `auto` for the screen with your desktop icons. Switching makes a new overlay window on that screen |
| `activity` | 0 chill to 1 hyper. Shifts how often he picks calm moves (idle, meditate, nap, stretch) versus lively ones and scenes; also sets walking speed and how long he idles |
| `quiet` | For calls and gaming: no speech bubbles or thought clouds, no big scenes, calm moves only |
| `fullscreen_hide` | Hide while a fullscreen app (game, video) is on his monitor; he comes back after (default on) |

## Settings (Behavior tab)
| Key | What it does |
|---|---|
| `behaviors` | Per action or scene: `{"on": bool, "often": multiplier}`. The slider runs from 1/4 as often to 4x; a missing entry means on, normal. Walking is always on (the Activity slider sets how much) |
| `vending_odds` | Chance the bundle is in stock (default 50%) |
| `vending_pity` | Added to the odds for each sold-out in a row (default +15%, capped at 95% total); a win resets it |
| `icon_visits` | Clearance-aisle trips to your real desktop icons. Off means floor finds only |
| `new_file_reaction` | A new file on the desktop gets checked out next ("ooh, new!") |
| `adhd_squirrel`, `adhd_distract`, `adhd_tangents`, `adhd_mood` | ADHD brain switches (see `attention/README.md`) |
| `nudge_minutes` | Nudge after this long on one window; 0 means never (default 60) |
| `companion_bee` | The bee that hangs around him. Off means it buzzes away; helper bees still fly in for icon errands and lifts |

**Do it now:** each row has a button that makes the running buddy drop what he's doing and do that move right away. He tidies up first: anything he's holding sparkles away, errands get called off, and if he's in the air he floats down first. The window sends `{"do": "<name>"}` over a local socket (`desktop-buddy-<uid>`) that the overlay listens on. A request while he's paused un-pauses him. If he isn't running, the window's preview does basic moves instead.

## Settings (Look and Sayings tabs)
| Key | What it does |
|---|---|
| `shoes` | `hot pink` (default), `dusty pink` or `sky blue`; picked from rendered swatches and applied live |
| `quips` | His random sayings, as a list. `null` uses the built-in ones in `character/behavior.py` |
| `greetings` | What he says when he waves. `null` uses the built-ins |

The Sayings tab edits both lists. Double-click a line to edit it; there are Add, Remove and Reset buttons. "Say it now" makes the running buddy say the selected line right away (or the preview, if he isn't running). Long lines wrap onto more lines in his bubble.

## Start at login (Buddy tab)
`autostart.py` adds or removes `~/.config/autostart/desktop-buddy.desktop`, which Plasma runs at login. It points at this copy of the project, so after moving the folder, turn the switch off and on again (the tab warns you if it points somewhere else). This isn't a setting in `settings.json`; the file itself is the switch.

## Settings (Claude tab)
| Key | What it does |
|---|---|
| `claude_enabled` | Lets him answer with Claude (used once voice is built) |
| `claude_backend` | `claude-code` (your Claude plan) or `api` (API key in KWallet). See `brain/README.md` |
| `claude_model` | `claude-opus-5-5` (default), `claude-sonnet-5-5` or `claude-haiku-5-5` |
| `voice_enabled` | Push to talk on or off (default on) |
| `voice_hotkey` | The push-to-talk key (default Meta+Space). The window checks it against your other KDE shortcuts |
| `voice_mic` | A PipeWire source name, or `null` for the system default mic |
| `whisper_model` | `tiny.en`, `base.en` (default) or `small.en`; the Voice section downloads them, with a progress bar |
| `voice_out_loud` | Greyed out until voice out exists |

The Voice section also has "Hold to test": it records and transcribes right in the window.

The tab also has buttons that open `brain/personality.md` and `brain/who-i-am.md`, and a "Try him" box that asks Claude for real and shows his answer. The mini buddy says the start of it too. The API key itself never goes in `settings.json`; it's saved to KWallet.

## Running buddy
The overlay writes its process ID to `~/.config/desktop-buddy/buddy.pid`. A second `python3 overlay/main.py` sees the buddy is already running and opens the settings window instead. The window's Quit button stops the buddy through that file.
