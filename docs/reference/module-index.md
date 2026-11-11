# Reference: where to find each module's reference

Every feature folder documents itself. **Read the README of the folder you're working in** — these are the
real reference pages, kept current with the code.

| Module | Its reference | Covers |
|---|---|---|
| `core/` | [core/README.md](../../core/README.md) | The event bus and **every bus topic**, with payloads and who uses them |
| `overlay/` | [overlay/README.md](../../overlay/README.md) | The transparent click-through window, Wayland layer-shell findings, running him |
| `character/` | [character/README.md](../../character/README.md) | The look, the files, every action and scene, and the sprite pack |
| `attention/` | [attention/README.md](../../attention/README.md) | The ADHD engine, its settings, what's still planned |
| `desktop-awareness/` | [desktop-awareness/README.md](../../desktop-awareness/README.md) | Desktop icon positions, windows, the KWin script |
| `brain/` | [brain/README.md](../../brain/README.md) | Claude backends, models, the personality files, the keyring |
| `voice-in/` | [voice-in/README.md](../../voice-in/README.md) | Push-to-talk, recording, speech to text |
| `voice-out/` | [voice-out/README.md](../../voice-out/README.md) | TTS, timings, start/stop/unload, setup, humming |
| `settings/` | [settings/README.md](../../settings/README.md) | Every setting, tab by tab, and start-at-login |

The folder-level job of each module is in the table in [README.md](../../README.md).

**The bus topic table in `core/README.md` is the contract between modules.** If you add or change a topic,
update that table in the same change.
