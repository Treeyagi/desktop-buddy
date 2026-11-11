# How to check your work on Desktop Buddy

Use these tools rather than writing new throwaway test scripts.

## The dev tools

| Command | What it does |
|---|---|
| `python3 tools/soak.py [minutes]` | Every move plus random life, headless. **Must print `ok`.** |
| `python3 character/preview.py out.png --actions dance,jump` | Contact sheet of moves, without touching the desktop |
| `python3 tools/render_tab.py behavior out.png` | Render one settings tab against throwaway settings |
| `python3 tools/send.py dance` / `--focus 25` | Drive an already-running buddy |
| `python3 tools/install.py` / `--uninstall` | The start menu entry |
| `python3 tools/shutdown.py` | **Stop everything.** See below. |

## Running him live

```
python3 overlay/main.py
```

Handy flags: `--demo` cycles through every action, `--action dance` repeats one.
Settings directly: `python3 settings/window.py`, with `--tab claude` (or `behavior`, `look`, `sayings`).

Screenshot a live run with:

```
spectacle -b -n -f -o shot.png
```

One screenshot before a visual change and one after — not repeatedly to double-check.

## If you changed his behaviour, check both looks

He has two renderers: the drawn rig and the sprite pack (Settings → Character). A behaviour change can look
right in one and wrong in the other. `preview.py` is the cheap way to see it.

## Always shut down when you're done

```
python3 tools/shutdown.py
```

This stops the buddy, the voice server, any recording or playing speech, **and deletes leftover audio and
screenshots**. It also prints the GPU memory still in use.

This isn't housekeeping — leftover recordings and screenshots of the user's desktop are exactly what
shouldn't be lying around. Run it at the end of any session where you started him.

Quitting normally (tray → Quit, Ctrl+C) also stops the voice server, and the server dies with the buddy if
he's killed hard.
