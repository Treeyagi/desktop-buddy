#!/bin/sh
# Installs what Desktop Buddy needs on a new computer (Arch/CachyOS, Debian/Ubuntu, Fedora).
#
#   sh tools/install-deps.sh              the basics: Python, PyQt6, layer-shell (he shows up on the desktop)
#   sh tools/install-deps.sh --voice      + push-to-talk: PipeWire's pw-record, and whisper.cpp where packaged
#   sh tools/install-deps.sh --screen     + a screenshot tool for "roast my code" (spectacle)
#   sh tools/install-deps.sh --all        everything above
#   sh tools/install-deps.sh --dry-run    show the commands without running them (can go with the others)
#   sh tools/install-deps.sh --yes        don't ask before installing
#
# From the one-file build:  ./desktop-buddy --deps [options]
# Uses sudo once for the package manager; nothing else on the system is changed. Safe to run again.
# Not installed here (optional, see the README): Claude Code (the `claude` command, for his answers),
# and the voice engine for speaking in your cloned voice (a 5 GB GPU setup, voice-out/README.md).
set -u
VOICE=0; SCREEN=0; DRY=0; YES=0
for a in "$@"; do
  case "$a" in
    --voice) VOICE=1;; --screen) SCREEN=1;; --all) VOICE=1; SCREEN=1;;
    --dry-run) DRY=1;; --yes|-y) YES=1;;
    -h|--help) sed -n '2,14p' "$0"; exit 0;;
    *) echo "Unknown option: $a (try --help)" >&2; exit 2;;
  esac
done

have() { command -v "$1" >/dev/null 2>&1; }
if have pacman; then PM=pacman
elif have apt-get; then PM=apt
elif have dnf; then PM=dnf
else echo "No pacman, apt or dnf found. Install Python 3, PyQt6 and layer-shell-qt by hand." >&2; exit 1; fi

NOTES=""
case "$PM" in
  pacman) PKGS="python python-pyqt6 layer-shell-qt"
          [ $VOICE = 1 ] && PKGS="$PKGS pipewire whisper-cpp"
          [ $SCREEN = 1 ] && PKGS="$PKGS spectacle";;
  apt)    PKGS="python3 python3-pyqt6 layer-shell-qt"
          [ $VOICE = 1 ] && { PKGS="$PKGS pipewire-bin"; NOTES="$NOTES\n- whisper.cpp isn't packaged for Debian/Ubuntu: build it from github.com/ggml-org/whisper.cpp for speech to text."; }
          [ $SCREEN = 1 ] && PKGS="$PKGS spectacle";;
  dnf)    PKGS="python3 python3-pyqt6 layer-shell-qt"
          [ $VOICE = 1 ] && { PKGS="$PKGS pipewire-utils"; NOTES="$NOTES\n- whisper.cpp isn't in Fedora's main repos: build it from github.com/ggml-org/whisper.cpp for speech to text."; }
          [ $SCREEN = 1 ] && PKGS="$PKGS spectacle";;
esac

SUDO=""
[ "$(id -u)" != 0 ] && SUDO="sudo"
case "$PM" in
  pacman) CMD="$SUDO pacman -S --needed --noconfirm $PKGS";;
  apt)    CMD="$SUDO apt-get install -y $PKGS";;
  dnf)    CMD="$SUDO dnf install -y $PKGS";;
esac

echo "Package manager: $PM"
echo "Will install:    $PKGS"
echo "Command:         $CMD"
if [ $DRY = 1 ]; then echo "(dry run: nothing was installed)"; exit 0; fi
if [ $YES = 0 ] && [ -t 0 ]; then
  printf "Go ahead? [Y/n] "; read -r ans
  case "$ans" in n|N|no|NO) echo "Cancelled."; exit 1;; esac
fi

# layer-shell-qt is optional (without it he's a normal window), so if the one command fails, retry without it
if ! sh -c "$CMD"; then
  echo "That failed; trying again without layer-shell-qt (he still works without it)."
  PKGS2="$(echo "$PKGS" | sed 's/ layer-shell-qt//')"
  CMD2="$(echo "$CMD" | sed 's/ layer-shell-qt//')"
  sh -c "$CMD2" || { echo "Install failed. Run it yourself: $CMD2" >&2; exit 1; }
fi

echo
python3 -c "import PyQt6.QtWidgets" 2>/dev/null && echo "PyQt6: ok" || { echo "PyQt6 still missing." >&2; exit 1; }
[ -e /usr/lib/qt6/plugins/wayland-shell-integration/liblayer-shell.so ] || [ -e /usr/lib64/qt6/plugins/wayland-shell-integration/liblayer-shell.so ] \
  && echo "layer-shell: ok" || echo "layer-shell: not found (fine: he runs as a normal window)"
[ $VOICE = 1 ] && { have pw-record && echo "pw-record: ok" || echo "pw-record: missing"; have whisper-cli && echo "whisper-cli: ok" || echo "whisper-cli: missing (speech to text needs it)"; }
[ -n "$NOTES" ] && printf "Notes:%b\n" "$NOTES"
echo "Done. Start him with ./desktop-buddy (or python3 overlay/main.py)."
