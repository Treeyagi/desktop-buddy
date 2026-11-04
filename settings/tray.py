"""Tray icon in the panel: Pause, Quiet mode, Settings..., Quit.

Lives in the overlay process. On Plasma the menu is drawn by the panel (over
DBus), so it works even though the overlay uses layer-shell for its windows.
Clicking the icon opens the settings window.
"""
import os
import subprocess
import sys

from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from character.rig import Pose, draw_buddy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def buddy_icon(size=64):
    """A little portrait of him: hat, mushroom, happy face."""
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    k = size / 64
    draw_buddy(p, 29 * k, 96 * k, 1, 0.5 * k,
               Pose(eyes="happy", smile=1.0, mouth_open=0.35, blush=0.7, sh_f=8, sh_b=-8))
    p.end()
    return QIcon(pm)


def launch(script):
    """Start one of the project's windows as its own process (without layer-shell)."""
    env = dict(os.environ)
    env.pop("QT_WAYLAND_SHELL_INTEGRATION", None)
    return subprocess.Popen([sys.executable, os.path.join(ROOT, script)], env=env,
                            start_new_session=True)


class Tray(QSystemTrayIcon):
    def __init__(self, settings, quit_fn, parent=None, focus=None, unfocus=None):
        super().__init__(buddy_icon(), parent)
        self.settings = settings
        self.window = None
        self.setToolTip("Desktop Buddy")
        menu = QMenu()
        self.pause = QAction("Pause", menu)
        self.pause.setCheckable(True)
        self.pause.toggled.connect(lambda on: self._set("paused", on))
        self.quiet = QAction("Quiet mode", menu)
        self.quiet.setCheckable(True)
        self.quiet.toggled.connect(lambda on: self._set("quiet", on))
        menu.addAction(self.pause)
        menu.addAction(self.quiet)
        menu.addSeparator()
        if focus:  # the ADHD engine's focus timer: he sits quietly with you until break time
            timer = menu.addMenu("Focus timer")
            for minutes in (25, 50):
                timer.addAction(f"{minutes} minutes").triggered.connect(lambda _, m=minutes: focus(m))
            timer.addAction("Stop").triggered.connect(unfocus)
            menu.addSeparator()
        menu.addAction("Settings…").triggered.connect(self.open_settings)
        menu.addSeparator()
        menu.addAction("Quit").triggered.connect(quit_fn)
        self.menu = menu  # keep a reference; the tray doesn't own it
        self.setContextMenu(menu)
        self.activated.connect(self._clicked)
        settings.changed.connect(self.sync)
        self.sync(settings.data)

    def _set(self, key, value):
        if self.settings.data.get(key) != value:
            self.settings.set(**{key: value})

    def sync(self, data):
        for action, key in ((self.pause, "paused"), (self.quiet, "quiet")):
            action.blockSignals(True)
            action.setChecked(bool(data.get(key)))
            action.blockSignals(False)
        self.setToolTip("Desktop Buddy (paused)" if data.get("paused") else "Desktop Buddy")

    def _clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_settings()

    def open_settings(self):
        if self.window and self.window.poll() is None:
            return  # already open
        self.window = launch("settings/window.py")
