# desktop-awareness

Knows what is on the desktop, with no screenshots.

- **Inputs:** Plasma desktop config (icon positions), KWin scripting (window positions, focused app, window title)
- **Outputs:** events like icon-found, window-moved, app-focused, page-title-changed
- **Notes:** "reading a web page" is animation only, driven by window title and focused app. A screenshot is sent to Claude only when the hotkey is pressed (the only point this costs usage).

## What's built: desktop icons (`icons.py`)
Reads where Plasma put every desktop icon from `~/.config/plasma-org.kde.plasma.desktop-appletsrc`, with no screenshots:
- the grid slot per file
- which screen it's on (the screen mapping)
- files Plasma hasn't saved a slot for yet go in the first free slots

It matches the list against what's really in `~/Desktop`, because Plasma keeps stale entries for deleted files.

- **Watching:** `IconWatcher` watches `~/Desktop` and that config file, then publishes `desktop.icons` and `desktop.icon_added` on the bus.
- **Per icon:** each `DesktopIcon` has its rect in screen pixels, `pixmap()` (the real themed icon, or a `.desktop` file's `Icon=`), `size_text()` and `age_text()`.
- **Grid geometry:** measured on this desktop at the default icon size. Slots are 112 px apart from x=56, rows 120 px apart from y=40, icons about 60 px. If you change the icon size, update `CELL_W`, `CELL_H`, `FIRST_X` and `FIRST_Y`.
- **Check it:** `python3 desktop-awareness/icons.py` prints what it sees.

## What's built: windows (`windows.py` + `kwin_windows.js`)
On Wayland, apps can't see each other's windows, but KWin can. `WindowWatcher` loads `kwin_windows.js` into KWin over D-Bus. That's a small read-only script: it never moves or changes a window. Whenever a window opens, closes, moves, minimizes, goes fullscreen, gets focus, or the virtual desktop changes, the script sends a JSON snapshot back to a D-Bus service the buddy registers (`org.desktopbuddy.Windows`).

- **What gets reported:** only normal windows and dialogs, bottom to top. Each has its title, app, frame, monitor, and whether it's minimized, fullscreen, active, or on the current desktop.
- **Filtered out:** the buddy's own see-through overlays. KWin lists them like windows, so they're recognized by their title "Desktop Buddy overlay" or by being a nameless python window.
- **Published:** the list goes on the bus as `desktop.windows`.
- **Clean exit:** the script is unloaded when the buddy quits, including on Ctrl+C. A leftover from a crash gets replaced on the next start.
- **Check it:** `python3 desktop-awareness/windows.py` prints what KWin reports.

What the buddy does with it:
- **Hidden icons:** icons behind a window don't count. He won't fly up to an icon you can't see, or notice a new file that landed behind a window.
- **Fullscreen:** a fullscreen app on his monitor hides him until it's gone (a setting).
- **Sitting on windows:** see the perch scene in `character/README.md`.

KWin 6.8 has no `workspace.stackingOrderChanged` signal, so the script only connects it when it exists. Activating a window already triggers a report.
