#!/usr/bin/env python3
"""Put Desktop Buddy in the start menu (KDE and other freedesktop desktops).

  python3 tools/install.py              add "Desktop Buddy" to the start menu, with a Stop action and an icon
  python3 tools/install.py --autostart  also start him when you log in
  python3 tools/install.py --uninstall  take the menu entry, icon and autostart back out

Nothing is copied: the menu entry points at this folder, so updating the repo updates him. Your
settings, recordings and the voice environment (~/.config and ~/.local/share/desktop-buddy) are never
touched, not even by --uninstall.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
APPS = os.path.join(HOME, ".local/share/applications")
ICONS = os.path.join(HOME, ".local/share/icons/hicolor")
AUTOSTART = os.path.join(HOME, ".config/autostart")
NAME = "desktop-buddy"
MENU = os.path.join(APPS, f"{NAME}.desktop")
AUTO = os.path.join(AUTOSTART, f"{NAME}.desktop")
SIZES = (48, 64, 128, 256)


def desktop_entry(autostart=False):
    py = shutil.which("python3") or "/usr/bin/python3"
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        "Name=Desktop Buddy",
        "GenericName=Desktop companion",
        "Comment=A cartoon of me that lives on the desktop",
        f"Exec={py} {ROOT}/overlay/main.py",
        f"Path={ROOT}",
        f"Icon={NAME}",
        "Terminal=false",
        "Categories=Utility;Amusement;",
        "Keywords=buddy;companion;pet;voice;",
        "StartupNotify=false",
    ]
    if autostart:
        lines.append("X-GNOME-Autostart-enabled=true")
        lines.append("X-KDE-autostart-after=panel")
    else:
        lines += ["Actions=stop;", "", "[Desktop Action stop]", "Name=Stop Desktop Buddy (and the voice)",
                  f"Exec={py} {ROOT}/tools/shutdown.py"]
    return "\n".join(lines) + "\n"


def make_icons():
    """Draw his face (the same one as the tray icon) at a few sizes."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, ROOT)
    from PyQt6.QtWidgets import QApplication
    from core.load import load
    app = QApplication.instance() or QApplication([])  # noqa: F841
    tray = load("settings", "tray")
    for size in SIZES:
        folder = os.path.join(ICONS, f"{size}x{size}", "apps")
        os.makedirs(folder, exist_ok=True)
        tray.buddy_icon(size).pixmap(size, size).save(os.path.join(folder, f"{NAME}.png"))


def refresh():
    for cmd in (["update-desktop-database", APPS], ["kbuildsycoca6", "--noincremental"],
                ["gtk-update-icon-cache", "-f", "-t", ICONS]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, capture_output=True)


def install(autostart):
    os.makedirs(APPS, exist_ok=True)
    make_icons()
    with open(MENU, "w", encoding="utf-8") as f:
        f.write(desktop_entry())
    os.chmod(MENU, 0o755)
    print(f"start menu entry: {MENU}")
    if autostart:
        os.makedirs(AUTOSTART, exist_ok=True)
        with open(AUTO, "w", encoding="utf-8") as f:
            f.write(desktop_entry(autostart=True))
        print(f"starts at login: {AUTO}")
    refresh()
    voice = os.path.join(HOME, ".local/share/desktop-buddy/tts/.venv/bin/python")
    if not os.path.exists(voice):
        print("note: voice out isn't set up yet (see voice-out/README.md); he works without it, in text.")
    print('done. Search "Desktop Buddy" in the start menu (it may take a few seconds to show up).')


def uninstall():
    for path in [MENU, AUTO] + [os.path.join(ICONS, f"{s}x{s}", "apps", f"{NAME}.png") for s in SIZES]:
        if os.path.exists(path):
            os.remove(path)
            print("removed", path)
    refresh()
    print("done. Your settings, recordings and voice environment were left alone.")


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install("--autostart" in sys.argv)
