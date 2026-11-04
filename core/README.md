# core

Event bus and shared config. Every other module talks only through this, so none of them needs to read the others.

- **Inputs:** events published by any module
- **Outputs:** events delivered to subscribers
- **Notes:** keep event names and payloads documented here as the project grows

## Built
- `bus.py`: `Bus.subscribe(topic, fn)` and `Bus.publish(topic, payload)`, in process.
- `load.py`: `load("desktop-awareness", "icons")` imports a module from a folder whose name has a dash.

## Events
| Topic | Payload | From | Used by |
|---|---|---|---|
| `desktop.icons` | `list[DesktopIcon]` for all screens, on start and on every change | desktop-awareness | character (picks Kroger finds) |
| `desktop.icon_added` | `DesktopIcon` for a file that just appeared | desktop-awareness | character (goes to check it out) |
| `voice.listening` | `True` on push-to-talk press, `False` on release | voice-in | character (listen / think), overlay (un-pause) |
| `voice.thinking` | the transcript, while Claude works | voice-in | character (thought cloud) |
| `voice.reply` | `{"text", "error", "heard"}` | voice-in | voice-out (speaks it, then re-publishes as `voice.say`) |
| `voice.reply_part` | `str`, one finished sentence while Claude is still writing | voice-in | voice-out (starts speaking early) |
| `voice.say` | the reply plus `"seconds"` (audio length, 0 if silent) | voice-out | character (answer: bubble and lips) |
| `buddy.hum` | `True` when a happy walk starts with a hum, `False` when it ends | character | voice-out (plays the hum) |
| `voice.mouth` | `float` 0..1 while audio plays, then `None` | voice-out | character (lip sync) |
| `voice.cancel` | `None`, for a tap too short to be speech | voice-in | character |
| `desktop.cursor` | `QPointF`, the mouse pointer in global coordinates | desktop-awareness | attention, character (chasing) |
| `buddy.interaction` | a short reason string, when you interact with him | overlay | attention (mood) |
| `attention.*` | see `attention/README.md` | attention | character |
| `desktop.windows` | `list[DesktopWindow]`, bottom to top, on every window change | desktop-awareness | character (hidden icons, perching), overlay (fullscreen hiding) |
