# desktop-awareness notes

Reference for this folder: [README.md](README.md) — desktop icons (`icons.py`) and windows
(`windows.py` + `kwin_windows.js`).

## While working here

- **KWin scripts must be unloaded when done.** A script left loaded keeps running inside the user's window
  manager after the buddy is gone — a resource leak and a nasty surprise.
- **Don't change the user's KDE shortcuts.** The buddy gets the one push-to-talk binding he was invited to
  take, nothing more.
- Everything here is read **locally** — Plasma's config files and a KWin script. Nothing leaves the machine
  and nothing costs usage money. Keep new awareness features on that side of the line; a screenshot is only
  ever taken on the "Look at my screen" hotkey
  ([why](../docs/explanation/privacy-cost-and-licensing.md)).
- Publish findings on the bus (`desktop.icons`, `desktop.icon_added`, `desktop.windows`, `desktop.cursor`)
  rather than calling into `character/` or `attention/`. Add a row to
  [../core/README.md](../core/README.md) for any new topic.
