#!/bin/sh
# Installs what Desktop Buddy needs on a new computer (Arch/CachyOS, Debian/Ubuntu, Fedora).
#
#   sh tools/install-deps.sh              everything he needs: Python, PyQt6, layer-shell, git, the GitHub CLI (gh),
#                                         push-to-talk tools (pw-record, whisper.cpp where packaged), spectacle
#   sh tools/install-deps.sh --core       only Python, PyQt6 and layer-shell (he shows up on the desktop)
#   sh tools/install-deps.sh --claude     also install Claude Code (his answers), with Anthropic's own installer
#   sh tools/install-deps.sh --dry-run    show the commands without running them (can go with the others)
#   sh tools/install-deps.sh --yes        don't ask before installing
#
# From the one-file build:  ./desktop-buddy --deps [options]
# Uses sudo once for the package manager; nothing else on the system is changed. Safe to run again.
# Not installed here: the voice engine for speaking in your cloned voice (a 5 GB GPU setup, voice-out/README.md).
set -u
VOICE=1; SCREEN=1; EXTRA=1; CLAUDE=0; DRY=0; YES=0
for a in "$@"; do
  case "$a" in
    --core) VOICE=0; SCREEN=0; EXTRA=0;; --all|--voice|--screen) ;;   # (the last three: the default already)
    --claude) CLAUDE=1;;
    --dry-run) DRY=1;; --yes|-y) YES=1;;
    -h|--help) sed -n '2,12p' "$0"; exit 0;;
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
          [ $EXTRA = 1 ] && PKGS="$PKGS git github-cli curl"
          [ $VOICE = 1 ] && PKGS="$PKGS pipewire whisper-cpp"
          [ $SCREEN = 1 ] && PKGS="$PKGS spectacle";;
  apt)    PKGS="python3 python3-pyqt6 layer-shell-qt"
          [ $EXTRA = 1 ] && PKGS="$PKGS git gh curl"
          [ $VOICE = 1 ] && { PKGS="$PKGS pipewire-bin"; NOTES="$NOTES\n- whisper.cpp isn't packaged for Debian/Ubuntu: build it from github.com/ggml-org/whisper.cpp for speech to text."; }
          [ $SCREEN = 1 ] && PKGS="$PKGS spectacle";;
  dnf)    PKGS="python3 python3-pyqt6 layer-shell-qt"
          [ $EXTRA = 1 ] && PKGS="$PKGS git gh curl"
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

# Only Python and PyQt6 are required. If the one big command fails (a mirror serving a 404, a package the
# distro doesn't have), install the required ones first, then each extra on its own and list what didn't make it.
if ! sh -c "$CMD"; then
  echo "That failed; installing Python and PyQt6 first, then each extra on its own (he works without them)."
  case "$PM" in
    pacman) REQ="python python-pyqt6"; INST="$SUDO pacman -S --needed --noconfirm";;
    apt)    REQ="python3 python3-pyqt6"; INST="$SUDO apt-get install -y";;
    dnf)    REQ="python3 python3-pyqt6"; INST="$SUDO dnf install -y";;
  esac
  sh -c "$INST $REQ" || { echo "Install failed. Run it yourself: $INST $REQ" >&2; exit 1; }
  MISSED=""
  for p in $PKGS; do
    case " $REQ " in *" $p "*) continue;; esac
    sh -c "$INST $p" || MISSED="$MISSED $p"
  done
  [ -n "$MISSED" ] && echo "Couldn't install:$MISSED (his voice, screenshots or layer-shell may be missing). Try again later: sh tools/install-deps.sh"
fi

echo
python3 -c "import PyQt6.QtWidgets" 2>/dev/null && echo "PyQt6: ok" || { echo "PyQt6 still missing." >&2; exit 1; }
[ -e /usr/lib/qt6/plugins/wayland-shell-integration/liblayer-shell.so ] || [ -e /usr/lib64/qt6/plugins/wayland-shell-integration/liblayer-shell.so ] \
  && echo "layer-shell: ok" || echo "layer-shell: not found (fine: he runs as a normal window)"
[ $VOICE = 1 ] && { have pw-record && echo "pw-record: ok" || echo "pw-record: missing"; have whisper-cli && echo "whisper-cli: ok" || echo "whisper-cli: missing (speech to text needs it)"; }
[ $EXTRA = 1 ] && { have git && echo "git: ok"; have gh && echo "gh: ok" || echo "gh: missing"; }
[ -n "$NOTES" ] && printf "Notes:%b\n" "$NOTES"
if [ $CLAUDE = 0 ] && ! have claude && [ -t 0 ] && [ $YES = 0 ]; then
  printf "Install Claude Code too (it's what answers his questions)? [y/N] "; read -r ans
  case "$ans" in y|Y|yes|YES) CLAUDE=1;; esac
fi
if [ $CLAUDE = 1 ] && ! have claude; then
  echo "Installing Claude Code with Anthropic's installer (claude.ai/install.sh)..."
  curl -fsSL https://claude.ai/install.sh | bash || echo "Claude Code install failed; see https://claude.ai/code" >&2
  echo "Open a new terminal and run: claude   (it asks you to sign in once)"
elif have claude; then echo "claude: ok"
else echo "Claude Code not installed: he works without it, in text bubbles. Add it later with: sh tools/install-deps.sh --claude"; fi
echo "Done. Start him with ./desktop-buddy (or python3 overlay/main.py)."
