# Desktop Buddy: notes for Claude

A cartoon of the user living on their KDE Plasma 6 desktop (Wayland, CachyOS): animated, desktop-aware,
Claude brain, push-to-talk. Python 3.14 + PyQt6, no other Python deps in the app.
GitHub: `Treeyagi/desktop-buddy` — **public**, so nothing secret may ever land in a file here.

General working rules (plain English, plan first, git and secrets) are in `~/.claude/CLAUDE.md`.
Live plan: `ROADMAP.md`. Original vision: `docs/NOTES.md`.

## Read these before you touch anything

| Before you... | Read first |
|---|---|
| work in **any** feature folder | **that folder's `README.md`** — they're the reference and they're kept current |
| work in `character/`, `brain/`, `voice-in/`, `voice-out/`, `desktop-awareness/` or `settings/` | the nested `CLAUDE.md` there; it loads automatically |
| have a module talk to another module | [core/README.md](core/README.md) — the bus topic table is the contract |
| add an action, a setting or a bus topic | [docs/how-to/add-things.md](docs/how-to/add-things.md) |
| check a change, or finish a session | [docs/how-to/check-your-work.md](docs/how-to/check-your-work.md) |
| touch the mic, the screen, the API key, or anything that plays music | [docs/explanation/privacy-cost-and-licensing.md](docs/explanation/privacy-cost-and-licensing.md) |
| build or publish a release | [docs/how-to/release.md](docs/how-to/release.md) |
| make a structural or design decision | [ARCHITECTURE.md](ARCHITECTURE.md) |

Add new knowledge to the quadrant that fits ([docs/README.md](docs/README.md)), not to this file.

## Non-negotiables

- **Modules talk only through the bus** (`core/bus.py`). Add a topic rather than an import, and add its row
  to the table in `core/README.md` in the same change.
- **Never leave the mic recording.** Recordings are deleted after use.
- **A screenshot happens only on the "Look at my screen" hotkey** — the one path that sends a picture of the
  user's desktop, and the main thing that costs usage money.
- **The API key lives in the system keyring only** (`brain/keychain.py`, KWallet), never in a file.
  This repo is public.
- **KWin scripts must be unloaded when done**, and don't change the user's KDE shortcuts beyond push-to-talk.
- **Don't edit `brain/personality.md` or `brain/who-i-am.md`.** They're the user's own words — his product,
  not config.
- **Run `python3 tools/shutdown.py` when you're done.** It stops the buddy and voice server and deletes
  leftover audio and screenshots.
- `python3 tools/soak.py` must print `ok`. Verify with the tools in `tools/`, not new throwaway scripts.
- **Don't read `character/rig.py` or `character/scenes.py`** unless the task is about them.
- No real songs, samples or recognisable depictions — generated melodies and original look-alikes only.
