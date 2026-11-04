# Desktop Buddy

An Ace Ventura-style cartoon version of me that lives on my CachyOS (KDE) desktop as a transparent overlay. He walks around, jumps, hums to himself, reacts to icons and windows, and answers voice questions on a hotkey, with a snarky raw-philosopher personality that always ends with a solution.

**Status:** v0.1.0. He lives on the desktop: a full animated character with bee buddies, scenes (clearance aisle, card vending machine, sitting on windows), awareness of your real desktop icons and windows, a tray icon and settings window, Claude answers in his personality, and push-to-talk with local Whisper. Since v0.1.0: the ADHD engine (squirrel moments, distractions, tangents, nudges, moods, a focus timer) and the My voice recording tab. Not built yet: voice out (his cloned voice).

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
| `settings/` | Tray icon, settings window, and the settings file the running buddy follows live |

## Decided
- Brain: both. Claude Code on your Claude plan (the default), or an API key kept in KWallet.
- Overlay: a Wayland layer-shell surface (layer-shell-qt), pinned to a monitor, click-through.

## Open questions
- App name
- "Never giving him an out": confirm the exact meaning (see docs/NOTES.md)
