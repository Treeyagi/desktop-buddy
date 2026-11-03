"""Start at login: a standard XDG autostart entry that Plasma runs when you log in.

    ~/.config/autostart/desktop-buddy.desktop

The entry points at this copy of the project, so if you move the folder, turn
the switch off and on again in settings to point it at the new place.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.expanduser("~/.config/autostart/desktop-buddy.desktop")
ICON = os.path.expanduser("~/.config/desktop-buddy/icon.png")


def is_enabled():
    return os.path.exists(PATH)


def points_here():
    try:
        with open(PATH, encoding="utf-8") as f:
            return os.path.join(ROOT, "overlay", "main.py") in f.read()
    except OSError:
        return False


def enable(icon_pixmap=None):
    if icon_pixmap is not None:
        os.makedirs(os.path.dirname(ICON), exist_ok=True)
        icon_pixmap.save(ICON, "PNG")
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    main = os.path.join(ROOT, "overlay", "main.py")
    with open(PATH, "w", encoding="utf-8") as f:
        f.write("[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Desktop Buddy\n"
                "Comment=Cartoon me living on the desktop\n"
                f'Exec="{sys.executable}" "{main}"\n'
                f"Icon={ICON}\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n")


def disable():
    try:
        os.remove(PATH)
    except FileNotFoundError:
        pass
