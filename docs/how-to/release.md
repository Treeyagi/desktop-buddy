# How to release Desktop Buddy

**Ask the user before pushing or creating a release.** Local commits are fine without asking.

## Build

```
tools/make-executable.sh
```

This produces `dist/desktop-buddy` — one file: a small shell stub with the whole app packed behind it. On
first run it unpacks into `~/.cache/desktop-buddy-app/<id>` and starts from there; later runs start
immediately. Settings, recordings and the voice environment stay in `~/.config` and
`~/.local/share/desktop-buddy` as usual.

The build excludes `docs/`, the reference pictures in `character/`, and `dist/`. The version comes from
`git describe --tags`.

It still needs `python3`, PyQt6 and `layer-shell-qt` on the target PC.

## Ship the tar.gz, not the bare file

A plain download loses the executable flag; a `.tar.gz` keeps it. The release assets are:

- `desktop-buddy.tar.gz`
- `tools/install-deps.sh`

That's what v0.5.6 shipped.

## What the executable can do

| Flag | What |
|---|---|
| *(none)* | Start him |
| `--stop` | Stop him and the voice |
| `--deps` | Install what he needs (`--voice`, `--screen`, `--all` for more) |
| `--doctor` | Check this PC (python, PyQt6, layer-shell) |
| `--log` | Show the last run's output |
| `--install` / `--uninstall` | Start menu entry |

## Publish

Tag `vX.Y.Z` and `gh release create` with the two assets above.
