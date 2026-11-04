# Desktop Buddy: notes for Claude

A cartoon of the user living on their KDE Plasma 6 (Wayland, CachyOS) desktop. Python 3.14 + PyQt6, no
other Python deps. GitHub: Treeyagi/desktop-buddy (private). Plans and ideas: `ROADMAP.md`.

## Keep token use low
- Read the README of the one folder you're working in, then only the files you need. Don't read
  `character/rig.py` (drawing) or `character/scenes.py` unless the task is about them.
- Modules talk only through the bus (`core/bus.py`); every topic is in `core/README.md`. Prefer adding
  a topic over reaching into another module.
- Verify with the tools below instead of writing new test scripts.

## Map
| Where | What |
|---|---|
| `overlay/main.py` | Entry point. `Controller` wires everything, applies settings live, listens on the local socket |
| `character/behavior.py` | `Buddy`: director (`pick_next`), basic actions as `_<name>()` returning a `Pose`, voice moves |
| `character/scenes.py` / `adhd.py` | Mixins: multi-step scenes (kroger, vending, perch, flying) / ADHD moves |
| `character/rig.py` | `Pose` fields and all drawing (body, face, hat, shoes). `moves.py` = shared poses |
| `character/bees.py`, `effects.py`, `props.py` | Bees, particles, props (items, vending machine, card) |
| `attention/engine.py` | ADHD engine: decides when he's distracted, nudges, mood, focus timer |
| `desktop-awareness/` | `icons.py` (Plasma config), `windows.py` + `kwin_windows.js` (KWin script: windows, cursor) |
| `brain/` | `client.ask()` to Claude (Claude Code CLI or API), `personality.md`, `who-i-am.md` |
| `voice-in/` | push-to-talk: `hotkey.py` (KGlobalAccel), `recorder.py` (pw-record), `stt.py` (whisper-cli), `listen.py` |
| `voice-out/` | `samples.py` (mood scripts). TTS not built yet |
| `settings/store.py` | `DEFAULTS` + the JSON file in `~/.config/desktop-buddy/`; overlay reloads it live |
| `settings/window.py` + `settings/tabs/*.py` | Settings window; one mixin per tab, each with `_<tab>_tab()` and `_sync_<tab>()` |
| `settings/tray.py` | Tray icon menu |

## Recipes
- **New action:** add `"name": (weight, (min_s, max_s))` to `ACTIONS` in `behavior.py` and a `_name(self, dt)`
  method returning a `Pose` (optional `_start_name`). Add a row to `BEHAVIORS` in `settings/tabs/common.py`.
- **New setting:** add to `DEFAULTS` in `settings/store.py`, apply it in `Controller.apply` (`overlay/main.py`),
  add the widget in its tab file plus a line in that tab's `_sync_<tab>()`, and document it in `settings/README.md`.
- **New bus topic:** publish/subscribe with `bus.publish(topic, payload)`, add a row to `core/README.md`.

## Check your work
- `python3 tools/soak.py [minutes]`: every move + random life, headless; must print "ok".
- `python3 character/preview.py out.png --actions dance,jump`: contact sheet of moves.
- `python3 tools/render_tab.py behavior out.png`: render a settings tab (throwaway settings).
- `python3 tools/install.py` / `--uninstall`: the start menu entry. `python3 tools/shutdown.py`: stop everything.
- `python3 tools/send.py dance` / `--focus 25`: drive a running buddy.
- Live: `python3 overlay/main.py`, screenshot with `spectacle -b -n -f -o shot.png`.

## Rules
- Never leave the mic recording; recordings get deleted after use. Never commit secrets (API key lives in KWallet).
- KWin scripts must be unloaded when done. Don't change the user's KDE shortcuts beyond push-to-talk.
- Commits end with the Co-Authored-By line; the repo uses the GitHub noreply email.
