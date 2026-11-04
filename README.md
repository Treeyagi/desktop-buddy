# Desktop Buddy

An Ace Ventura-style cartoon version of me that lives on my CachyOS (KDE) desktop as a transparent overlay. He walks around, jumps, hums to himself, reacts to icons and windows, and answers voice questions on a hotkey, with a snarky raw-philosopher personality that always ends with a solution.

**Status:** v0.4.0. Everything in v0.1.0 (the animated character, bees, scenes, desktop awareness, tray and settings, Claude answers, push-to-talk with local Whisper) plus: the ADHD engine and focus timer; **voice out** (he answers in my cloned voice with Chatterbox, lips synced, sentence by sentence from a warm streaming Claude process, about 3 to 4 s to first sound); quiet original house-style humming on walks; reactions to what I'm doing (video, code, games, late nights); a second hotkey that shows Claude my screen for "roast my code" / "settle this argument"; and my personality and story in `brain/`. New in v0.3.0: a start menu installer (`tools/install.py`), dancing to music playing from a browser or player (dance routines of eight beat-driven moves), seven new idles and a cross-legged meditate, walk-out moments (gratitude, family, geeking out, dreams, good vibes, a calm breath), and the hum as a text bubble only. Stop everything with `python3 tools/shutdown.py`. New in v0.4.0: dance mode (nonstop dancing, in Settings) and quicker music reactions, four new dances (windshield wipers, chicken, T-rex, floss), fewer yawns, the booster pack rip in the vending scene (a rare hit, or a dud with a toss and "...anyway!"), voice engine start/stop and unload-when-idle in Settings, and an update button on the Buddy tab. What's next is in `ROADMAP.md`.

## Install in the start menu
```bash
python3 tools/install.py              # adds "Desktop Buddy" (with his face as the icon) to the start menu
python3 tools/install.py --autostart  # also starts him when you log in
python3 tools/install.py --uninstall  # removes the menu entry, icon and autostart
```
The entry points at this folder (nothing is copied), and right-clicking it in the menu offers "Stop Desktop Buddy (and the voice)". Uninstalling never touches your settings, recordings or the voice environment.

## Run him
```bash
python3 overlay/main.py
```
Then use the tray icon (his face with the mushroom hat) for Pause, Quiet mode, Settings and Quit. Settings can also be opened directly with `python3 settings/window.py`, and `--tab claude` (or `behavior`, `look`, `sayings`) opens a specific tab.

Requirements (CachyOS / Arch, KDE Plasma 6 on Wayland):
- `python-pyqt6` and `layer-shell-qt` (already on a Plasma install)
- for Claude: Claude Code (`claude` command) signed in, or an Anthropic API key plus `pip install --user --break-system-packages anthropic`
- for push-to-talk: `whisper-cpp` (`sudo pacman -S whisper-cpp`), a Whisper model (download it in Settings > Claude > Voice), and PipeWire's `pw-record`

Handy for development: `python3 overlay/main.py --demo` cycles through every action, `--action dance` repeats one, and `python3 character/preview.py sheet.png` renders contact sheets without touching the desktop.

Full brainstorm and idea list: [docs/NOTES.md](docs/NOTES.md)

Working on it with Claude Code? Start with `CLAUDE.md` (project map, recipes, test tools) and `ROADMAP.md`.

## How the code is organized
One folder per feature, each with its own short README (inputs and outputs). Modules talk only through events on the bus in `core/`, so you can work on one module without reading the others. This keeps Claude Code usage low: point it at a single folder.

| Folder | Job |
|---|---|
| `overlay/` | Transparent click-through window and rendering |
| `character/` | Sprites, rigs, animation states |
| `attention/` | ADHD engine (tangents, hyperfocus, squirrel moments) plus random events (Kroger aisle, vending machine, walk-out moments) |
| `desktop-awareness/` | Desktop icon positions, window positions, focused app |
| `voice-in/` | Hotkey push-to-talk and speech-to-text |
| `voice-out/` | Text-to-speech in my cloned voice, humming |
| `brain/` | Claude calls, personality prompt, "who I am" file |
| `core/` | Event bus and shared config |
| `tools/` | Dev helpers: soak test, render a settings tab, send commands to the running buddy |
| `settings/` | Tray icon, settings window, and the settings file the running buddy follows live |

## Decided
- Brain: both. Claude Code on your Claude plan (the default), or an API key kept in KWallet.
- Overlay: a Wayland layer-shell surface (layer-shell-qt), pinned to a monitor, click-through.

## Open questions
- App name
- "Never giving him an out": confirm the exact meaning (see docs/NOTES.md)
