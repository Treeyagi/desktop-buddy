# overlay

Transparent, click-through window that draws the character over the desktop.

- **Inputs:** render commands and character position from `character/` via the event bus
- **Outputs:** window geometry events, click/hover events when interaction is enabled
- **Notes:** Wayland (KDE) is harder than X11. May reuse plumbing from the lava lamp wallpaper plugin.

## Spike findings (Wayland, KDE Plasma 6, PyQt6)
- The first spike (now replaced by `overlay/main.py`) showed that frameless + `WindowStaysOnTopHint` + `WindowTransparentForInput` + `WA_TranslucentBackground` gives a transparent always-on-top overlay with a placeholder character walking and bobbing.
- Wayland clients can't position their own windows, so the overlay is one screen-sized window and the character moves inside it (not a small moving window).
- KWin put it on the monitor with focus, not Qt's "primary" screen. Multi-monitor needs one overlay per screen, or a KWin script / layer-shell to pin it.
- Not yet verified: that mouse clicks truly pass through, and that it stays above fullscreen apps. `layer-shell-qt` is installed if we need a proper layer-shell surface.

## Running
- `python3 overlay/main.py` he lives his life (random actions)
- `python3 overlay/main.py --demo` cycles through every action
- `python3 overlay/main.py --action dance` repeats one action (any name in `character/behavior.py` ACTIONS, `walk`, or a scene: `kroger`, `vending`)
- `--screen DP-3` puts him on another monitor (default: the one with your desktop icons)
- `--scale 1.2` makes him bigger
- Quit from the tray icon (or Ctrl+C in the terminal); the overlay itself ignores the mouse.
- `--scale` and `--screen` are one-off overrides; normally size and monitor come from the settings (see `settings/README.md`).

Only the area around him is repainted each frame. About 20% of one CPU core at 60 fps.
For now the overlay imports `character.behavior.Buddy` directly; that moves onto the `core/` event bus once it exists.

## Layer-shell (Wayland)
On Wayland, `main.py` sets `QT_WAYLAND_SHELL_INTEGRATION=layer-shell` when layer-shell-qt's plugin is installed. That makes the overlay a proper desktop layer:
- it can be pinned to a chosen monitor
- it sits above normal windows
- the compositor sizes it to stop above the panel (1920x1050 here)

The window's origin is the screen's top-left, so desktop icon coordinates line up directly. I checked this by drawing boxes on every icon.
