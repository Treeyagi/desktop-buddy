# Desktop Buddy: architecture and decisions

A cartoon of the user living on their KDE Plasma 6 desktop (Wayland, CachyOS): animated, desktop-aware, with
a Claude brain and push-to-talk. Python 3.14 + PyQt6, no other Python dependencies in the app itself.
Public repo, `Treeyagi/desktop-buddy`.

The per-folder `README.md` files are the reference for each module and are kept current — **read the README
of the folder you're working in**. This file covers what no single module's README can: how they fit together,
and why things are the way they are. The folder table is in [README.md](README.md).

## One rule holds the whole thing together

**Modules talk only through the event bus in `core/bus.py`.** Nothing imports another feature module and
reaches into it. Every topic is listed in [`core/README.md`](core/README.md).

That's why you can work on one folder without reading the others, and it's the main reason this project is
cheap to work on. When a module needs something from another, the answer is almost always **add a bus topic**,
not add an import.

## The paths through the app

**Push-to-talk, end to end:** `voice-in/hotkey.py` (KGlobalAccel) → `recorder.py` (`pw-record`) →
`stt.py` (whisper-cli) → `brain/` → `voice-out/speak.py` → the character animates while it speaks.
Along the way `voice.listening`, `voice.thinking` and `voice.reply` go out on the bus so the character and
overlay react. Measured: sound starts roughly 3–4 seconds after the key is released.

**Desktop awareness:** `desktop-awareness/icons.py` reads Plasma's icon config; `windows.py` plus
`kwin_windows.js` (a KWin script) reports windows and the cursor. These publish `desktop.icons`,
`desktop.icon_added`, `desktop.windows` and `desktop.cursor`, which the character uses to perch on title
bars, hang off icons and chase the pointer.

**Behaviour:** `attention/engine.py` decides when he's distracted, his mood and the focus timer.
`character/behavior.py` is the director: it picks the next action and returns a `Pose` each frame.

## Two looks, one character

This is the thing most likely to surprise you.

- **`rig.py`** draws him from code — body, face, hat, shoes — composed from shared poses in `moves.py`.
- **`sprite.py`** is the *alternative* look (Settings → Character): a sprite pack in
  `character/sprites/treeyagi/`, 29 animations in eight directions each, with timings and anchors in
  `anims.json`. `anim_for()` maps every Buddy state to an animation and viewing direction.

Both are driven by the same `Pose`/state machine. A change to how he behaves usually belongs in
`behavior.py`, not in either renderer, and a behaviour change may need both looks checked.

## Where the costs and the private things are

**The only thing that costs usage money is a Claude call**, and the only thing that sends a picture of the
screen is the "Look at my screen" hotkey. Everything else — walking, humming, perching, reacting to windows
— is local animation and costs nothing. Keep it that way.

**The API key lives in the system keyring** (KWallet via `secret-tool`), handled by `brain/keychain.py`.
Never in a file, never in the repo.

**The voice engine is a separate Python 3.11 virtual environment** at
`~/.local/share/desktop-buddy/tts/.venv`, holding Chatterbox TTS. It's deliberately outside the app's own
dependencies: the app stays "PyQt6 and nothing else", and a heavy ML stack can't break the buddy starting up.
It also unloads itself after 2 minutes idle and is tied to the buddy's process, so it can't outlive him.

Details and the rules that follow from this: [docs/explanation/privacy-cost-and-licensing.md](docs/explanation/privacy-cost-and-licensing.md).

## Decisions, with the reasoning

**Bus-only communication, one folder per feature, each with a README.** Chosen up front to keep the cost of
working with an AI assistant low: point it at one folder, and it needs nothing else in context. It has held
up — the modules really are independently workable.

**`brain/personality.md` and `who-i-am.md` are the user's own words.** The personality is the product here,
not a config file. Don't rewrite them, tidy them or "improve" the prose; only the user edits those.

**Claude Code is the default backend, with `--safe-mode`, no tools and no saved session**, running in
`~/.config/desktop-buddy`. It uses the user's existing plan rather than requiring an API key, and the
isolation means the buddy can never pick up the user's Claude Code plugins, hooks or CLAUDE.md files —
which would otherwise leak this project's instructions into his personality.

**A warm `claude` process** (`brain/session.py`) kept alive and answering in a stream, restarted after 10
questions, 20 idle minutes, or a personality/model change. Cold-starting a process per question was most of
the original ~10 second delay.

**Short answers by design** — two sentences, enforced in `personality.md`. It keeps him feeling snappy and
keeps the speech synthesis short, which is where the remaining delay lives.

**Hums are generated from scratch; the vending machine is an original look-alike.** Six two-bar melodies
built at runtime (124 BPM, A minor pentatonic) and cached, rather than real songs or samples. Both choices
exist so the project can be public and shared without a licensing problem. Keep that constraint for anything
new that plays or depicts something recognisable.

**Hum sound is off by default** (`hum_sound`): the synthesised tone sounded robotic, so he hums in a text
bubble instead. The code is kept for when it's worth bringing back.

**One-file executable for releases.** `tools/make-executable.sh` packs the whole app behind a shell stub that
unpacks to `~/.cache/desktop-buddy-app/<id>` on first run. Shipped as a `.tar.gz` because a plain download
loses the executable flag. See [docs/how-to/release.md](docs/how-to/release.md).

## Where to look next

- Each module's own `README.md` — the reference for that module
- [docs/how-to/check-your-work.md](docs/how-to/check-your-work.md) — the dev tools, and the shutdown you owe
- [docs/how-to/add-things.md](docs/how-to/add-things.md) — recipes for a new action, setting or bus topic
- [docs/how-to/release.md](docs/how-to/release.md) — building and publishing the one-file executable
- [docs/explanation/privacy-cost-and-licensing.md](docs/explanation/privacy-cost-and-licensing.md) — the mic, the screen, the key, the licensing lines
- [docs/NOTES.md](docs/NOTES.md) — the original vision document, kept as written
- [ROADMAP.md](ROADMAP.md) — what's next
