# settings notes

Reference for this folder: [README.md](README.md) — every setting, tab by tab, plus start-at-login.
It is the user-facing documentation of each setting, so it has to stay in step with the code.

## A new setting touches four places

Miss one and it half-works:

1. `DEFAULTS` in `store.py`.
2. `Controller.apply` in `../overlay/main.py` — this is what makes it take effect **live**.
3. The widget in `tabs/<tab>.py`, plus a line in that tab's `_sync_<tab>()`.
4. A description in `README.md`.

Full recipe: [../docs/how-to/add-things.md](../docs/how-to/add-things.md).

## While working here

- One mixin per tab, each with `_<tab>_tab()` and `_sync_<tab>()`. Keep that shape.
- Check a tab with `python3 ../tools/render_tab.py <tab> out.png` — it runs against throwaway settings, so it
  won't touch the user's real ones.
- The settings file lives in `~/.config/desktop-buddy/` and the running buddy reloads it live.
- A new behaviour toggle also needs its row in `BEHAVIORS` in `tabs/common.py`.
