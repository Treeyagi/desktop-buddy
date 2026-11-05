#!/bin/sh
# Builds Desktop Buddy as ONE executable file (dist/desktop-buddy) and a tar.gz of it for releases.
#
#   tools/make-executable.sh
#
# The file is a small shell stub with the whole app packed after it. The first run unpacks it into
# ~/.cache/desktop-buddy-app/<id> and starts him from there; the next runs start at once. Your settings,
# recordings and voice environment live in ~/.config and ~/.local/share/desktop-buddy, as always.
# It still needs python3, PyQt6 and layer-shell-qt on the PC (see the README).
#
#   ./desktop-buddy              start him             ./desktop-buddy --stop     stop him and the voice
#   ./desktop-buddy --deps       installs what he needs (Python, PyQt6, layer-shell; --voice, --screen, --all)
#   ./desktop-buddy --doctor     checks this PC (python, PyQt6, layer-shell)    --log   shows the last run's output
#   ./desktop-buddy --install    start menu entry      ./desktop-buddy --uninstall   take it back out
# Ship the .tar.gz: a plain download loses the executable flag, a tar.gz keeps it.
set -eu
cd "$(dirname "$0")/.."
mkdir -p dist
VERSION="$(git describe --tags --always 2>/dev/null || echo dev)"
printf '%s\n' "$VERSION" > dist/VERSION
# everything the app runs, without the dev pictures and notes
git ls-files -z | grep -zvE '^(docs/|character/(reference-|.*\.(png|jpg))|dist/)' > dist/files.lst
tar -czf dist/payload.tgz --null -T dist/files.lst -C dist VERSION
ID="$(sha256sum dist/payload.tgz | cut -c1-12)"
{
cat <<STUB
#!/bin/sh
# Desktop Buddy $VERSION, one file. Run it; --help lists the options.
SELF="\$(readlink -f "\$0")"
CACHE="\${XDG_CACHE_HOME:-\$HOME/.cache}/desktop-buddy-app/$ID"
if [ ! -f "\$CACHE/overlay/main.py" ]; then
  mkdir -p "\$CACHE.tmp" || exit 1
  N=\$(awk '/^__PAYLOAD__\$/{print NR+1; exit}' "\$SELF")
  tail -n +"\$N" "\$SELF" | tar xz -C "\$CACHE.tmp" || { echo "Couldn't unpack Desktop Buddy." >&2; exit 1; }
  mv "\$CACHE.tmp" "\$CACHE" 2>/dev/null || true
fi
export DESKTOP_BUDDY_EXE="\$SELF"
LOG="\$(dirname "\$CACHE")/last-run.log"
say() {   # to the terminal, and as a dialog when there is no terminal (a start menu click)
  echo "\$1" >&2
  [ -t 2 ] && return 0
  [ -n "\${DISPLAY:-}\${WAYLAND_DISPLAY:-}" ] || return 0
  if command -v kdialog >/dev/null 2>&1; then kdialog --title "Desktop Buddy" --error "\$1" &
  elif command -v zenity >/dev/null 2>&1; then zenity --error --title "Desktop Buddy" --text "\$1" &
  elif command -v notify-send >/dev/null 2>&1; then notify-send "Desktop Buddy" "\$1" &
  fi
  return 0
}
hint() {
  if command -v pacman >/dev/null 2>&1; then echo "sudo pacman -S --needed python python-pyqt6 layer-shell-qt"
  elif command -v apt >/dev/null 2>&1; then echo "sudo apt install python3 python3-pyqt6"
  elif command -v dnf >/dev/null 2>&1; then echo "sudo dnf install python3 python3-pyqt6"
  else echo "install python3 and PyQt6 with your package manager"; fi
}
case "\${1:-}" in
  --help|-h) echo "desktop-buddy [--stop | --install [--autostart] | --uninstall | --version | --doctor | --log | --deps [--yes]]"; exit 0;;
  --version) cat "\$CACHE/VERSION"; exit 0;;
  --log) cat "\$LOG" 2>/dev/null || echo "No log yet."; exit 0;;
  --doctor)
    echo "Desktop Buddy \$(cat "\$CACHE/VERSION")"
    echo "python3:  \$(command -v python3 || echo MISSING) \$(python3 --version 2>&1)"
    python3 -c "import PyQt6.QtWidgets" 2>/dev/null && echo "PyQt6:    ok" || echo "PyQt6:    MISSING (\$(hint))"
    echo "session:  \${XDG_SESSION_TYPE:-unknown}, display \${WAYLAND_DISPLAY:-\${DISPLAY:-none}}"
    [ -e /usr/lib/qt6/plugins/wayland-shell-integration/liblayer-shell.so ] && echo "layer-shell: ok (pinned to the desktop)" || echo "layer-shell: missing (he works as a normal window; optional)"
    echo "unpacked: \$CACHE"; echo "log:      \$LOG"; exit 0;;
  --deps) shift; exec sh "\$CACHE/tools/install-deps.sh" "\$@";;
  --stop) exec python3 "\$CACHE/tools/shutdown.py";;
  --install) shift; exec python3 "\$CACHE/tools/install.py" "\$@";;
  --uninstall) exec python3 "\$CACHE/tools/install.py" --uninstall;;
esac
command -v python3 >/dev/null 2>&1 || { say "Desktop Buddy needs Python 3. Install it with: \$(hint)"; exit 1; }
python3 -c "import PyQt6.QtWidgets" 2>/dev/null || { say "Desktop Buddy needs PyQt6. Install it with: \$(hint)   (run ./desktop-buddy --doctor for details)"; exit 1; }
cd "\$CACHE" || exit 1
python3 overlay/main.py "\$@" >"\$LOG" 2>&1
rc=\$?
case \$rc in 0|130|143|15) exit 0;; esac
say "Desktop Buddy stopped (error \$rc). The last lines: \$(tail -n 6 "\$LOG" | tr '\\n' ' ')   Full log: \$LOG"
exit \$rc
__PAYLOAD__
STUB
cat dist/payload.tgz
} > dist/desktop-buddy
chmod +x dist/desktop-buddy
tar -czf dist/desktop-buddy.tar.gz -C dist desktop-buddy
echo "Built dist/desktop-buddy ($(du -h dist/desktop-buddy | cut -f1)) and dist/desktop-buddy.tar.gz"
