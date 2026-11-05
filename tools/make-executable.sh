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
case "\${1:-}" in
  --help|-h) echo "desktop-buddy [--stop | --install [--autostart] | --uninstall | --version]"; exit 0;;
  --version) cat "\$CACHE/VERSION"; exit 0;;
  --stop) exec python3 "\$CACHE/tools/shutdown.py";;
  --install) shift; exec python3 "\$CACHE/tools/install.py" "\$@";;
  --uninstall) exec python3 "\$CACHE/tools/install.py" --uninstall;;
esac
python3 -c "import PyQt6" 2>/dev/null || { echo "Desktop Buddy needs PyQt6: sudo pacman -S python-pyqt6 layer-shell-qt" >&2; exit 1; }
cd "\$CACHE" && exec python3 overlay/main.py "\$@"
exit 0
__PAYLOAD__
STUB
cat dist/payload.tgz
} > dist/desktop-buddy
chmod +x dist/desktop-buddy
tar -czf dist/desktop-buddy.tar.gz -C dist desktop-buddy
echo "Built dist/desktop-buddy ($(du -h dist/desktop-buddy | cut -f1)) and dist/desktop-buddy.tar.gz"
