"""Desktop overlay: transparent, click-through, always-on-top window that
hosts the buddy and repaints only the area around him.

On Wayland it's a layer-shell surface (via layer-shell-qt), so it can be pinned
to a chosen monitor and sits above normal windows without covering the panel.
Settings (size, monitor, activity, quiet, pause) come from
~/.config/desktop-buddy/settings.json and apply live; the tray icon and the
settings window both edit that file.

Run:   python3 overlay/main.py              (he lives his life)
       python3 overlay/main.py --demo       (cycles through every action)
       python3 overlay/main.py --action dance
       python3 overlay/main.py --screen DP-3 --scale 1.4   (one-off overrides)
Quit:  the tray icon's Quit, or Ctrl+C in the terminal.
"""
import argparse
import atexit
import os
import signal
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

LAYER_SHELL = (os.environ.get("XDG_SESSION_TYPE") == "wayland"
               and os.path.exists("/usr/lib/qt6/plugins/wayland-shell-integration/liblayer-shell.so"))
if LAYER_SHELL:
    os.environ.setdefault("QT_WAYLAND_SHELL_INTEGRATION", "layer-shell")

import json  # noqa: E402

from PyQt6.QtCore import QObject, QRectF, Qt, QTimer  # noqa: E402
from PyQt6.QtNetwork import QLocalServer  # noqa: E402
from PyQt6.QtGui import QPainter  # noqa: E402
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QWidget  # noqa: E402

import character.rig as rig  # noqa: E402
from character.adhd import TANGENTS  # noqa: E402
from character.behavior import ACTIONS, GREETINGS, QUIPS, Buddy  # noqa: E402
from character.scenes import SCENES  # noqa: E402
from core.bus import Bus  # noqa: E402
from core.load import load  # noqa: E402
from settings.store import PID_PATH, SOCKET, SettingsFile  # noqa: E402
from settings.tray import Tray, launch  # noqa: E402

# px above the bottom edge; a layer-shell surface already stops above the panel
FLOOR_MARGIN = 8 if LAYER_SHELL else 56


class Overlay(QWidget):
    def __init__(self, screen, buddy):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowTransparentForInput  # empty input region = click-through
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Desktop Buddy overlay")  # the KWin window reporter skips this one
        self.setScreen(screen)  # before the native window exists, so layer-shell picks it up
        self.setGeometry(screen.geometry())
        self.home = screen
        self.buddy = buddy
        self.paused = False
        self.dirty = QRectF()
        self.last = time.perf_counter()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def set_paused(self, on):
        if on == self.paused:
            return
        self.paused = on
        if on:
            self.timer.stop()
            self.update()  # clears him off the screen
        else:
            self.last = time.perf_counter()
            self.timer.start(16)

    def resizeEvent(self, e):
        # the compositor decides the final size (e.g. minus the panel)
        self.buddy.set_area(self.width(), self.height() - FLOOR_MARGIN)

    def tick(self):
        now = time.perf_counter()
        self.buddy.update(now - self.last)
        self.last = now
        box = self.buddy.bounds()
        self.update(self.dirty.united(box).toAlignedRect().adjusted(-4, -4, 4, 4))
        self.dirty = box

    def paintEvent(self, _):
        if self.paused:
            return
        p = QPainter(self)
        self.buddy.draw(p)


class Controller(QObject):
    """Owns the buddy and his overlay window, and applies settings changes."""

    def __init__(self, app, args):
        super().__init__()
        self.app, self.args = app, args
        # Plasma numbers screens with the primary as 0, then the rest in order
        self.screens = [app.primaryScreen()] + [s for s in app.screens() if s != app.primaryScreen()]
        self.bus = Bus()
        self.settings_seen = None
        self.settings = SettingsFile(self)
        s = self.settings.data
        screen = self.pick_screen(s)
        geo = screen.geometry()
        self.buddy = Buddy(geo.width(), geo.height() - FLOOR_MARGIN, scale=args.scale or float(s["size"]),
                           demo=args.demo, bus=self.bus, screen_id=self.screens.index(screen))
        self.overlay = Overlay(screen, self.buddy)
        self.overlay.show()
        self.watcher = load("desktop-awareness", "icons").IconWatcher(self.bus, parent=self)
        self.fullscreen_here = False
        self.bus.subscribe("desktop.windows", self._on_windows)
        self.windows = load("desktop-awareness", "windows").WindowWatcher(self.bus, parent=self)
        app.aboutToQuit.connect(self.windows.stop)  # take the KWin script back out
        self.voice = load("voice-in", "listen").VoiceIn(self.bus, parent=self)
        app.aboutToQuit.connect(self.voice.shutdown)  # never leave the mic recording
        self.voice.apply(self.settings.data)
        self.speaker = load("voice-out", "speak").Speaker(self.bus, parent=self)
        app.aboutToQuit.connect(self.speaker.shutdown)  # stops the sound and the voice server
        self.speaker.apply(self.settings.data)
        self.hummer = load("voice-out", "hum").Hummer(self.bus, parent=self)
        app.aboutToQuit.connect(self.hummer.stop)
        self.hummer.apply(self.settings.data)
        self.bus.subscribe("voice.listening", self._on_listening)
        self.attention = load("attention", "engine").AttentionEngine(self.bus, parent=self)
        self.attention.apply(self.settings.data)
        self.buddy.set_screen(screen.name(), screen.geometry().topLeft())
        if args.action:  # after the watchers, so he already knows the icons and windows
            QTimer.singleShot(400, lambda: self.buddy.force(args.action))
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = Tray(self.settings, app.quit, parent=self,
                             focus=self.attention.start_focus, unfocus=self.attention.stop_focus)
            self.tray.show()
        else:
            print("no system tray found; open settings with: python3 settings/window.py")
        self.settings.changed.connect(self.apply)
        self.apply(s)
        # "Do it now" requests from the settings window: one JSON line per connection
        QLocalServer.removeServer(SOCKET)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._connection)
        if not self.server.listen(SOCKET):
            print("couldn't open the Do-it-now socket:", self.server.errorString())

    def _connection(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: self._read(s))
            sock.disconnected.connect(sock.deleteLater)

    def _read(self, sock):
        while sock.canReadLine():
            try:
                msg = json.loads(bytes(sock.readLine()).decode())
            except ValueError:
                continue
            if isinstance(msg, dict) and "focus" in msg:  # the settings window's focus timer buttons
                minutes = int(msg["focus"] or 0)
                self.attention.start_focus(minutes) if minutes > 0 else self.attention.stop_focus()
                self.bus.publish("buddy.interaction", "focus")
                continue
            if isinstance(msg, dict) and "voice_engine" in msg:  # the settings window's start/stop buttons
                (self.speaker.engine_start if msg["voice_engine"] == "start" else self.speaker.engine_stop)()
                continue
            if isinstance(msg, dict) and msg.get("do"):
                if self.overlay.paused:
                    self.settings.set(paused=False)  # asking for a move means you want to see it
                text = msg.get("text")
                self.buddy.do_now(str(msg["do"]), str(text)[:200] if text else None)
                self.bus.publish("buddy.interaction", "do-now")

    def _on_listening(self, down):
        if down and self.settings.data.get("paused"):
            self.settings.set(paused=False)  # you're talking to him, so he comes back

    def _on_windows(self, windows):
        here = self.overlay.home.name()
        full = any(w.fullscreen and w.showing and w.output == here for w in windows)
        if full != self.fullscreen_here:
            self.fullscreen_here = full
            self.apply(self.settings.data)

    def pick_screen(self, s):
        name = self.args.screen or s.get("monitor", "auto")
        for scr in self.screens:
            if scr.name() == name:
                return scr
        if name not in ("auto", None):
            print(f"no screen named {name}; have: {', '.join(x.name() for x in self.screens)}")
        return self.screens[0]

    def apply(self, s):
        b = self.buddy
        if not self.args.scale:
            size = max(0.5, min(2.5, float(s.get("size", 1.1))))
            if abs(size - b.scale) > 1e-3:
                b.set_scale(size)
        b.activity = max(0.0, min(1.0, float(s.get("activity", 0.5))))
        b.quiet = bool(s.get("quiet", False))
        dance_mode = bool(s.get("dance_mode", False))
        if dance_mode and not b.dance_mode and b._free():   # switched on: starts right away
            b.enter("dance")
        b.dance_mode = dance_mode
        b.hums = bool(s.get("hum_enabled", True))
        b.behaviors = s.get("behaviors") or {}
        b.vend_odds = max(0.0, min(1.0, float(s.get("vending_odds", 0.5))))
        b.pack_odds = max(0.0, min(1.0, float(s.get("pack_hit_odds", 0.25))))
        b.vend_pity = max(0.0, min(1.0, float(s.get("vending_pity", 0.15))))
        b.icon_visits = bool(s.get("icon_visits", True))
        b.new_file_reaction = bool(s.get("new_file_reaction", True))
        b.set_companion(bool(s.get("companion_bee", True)))
        rig.set_shoes(str(s.get("shoes", "hot pink")))
        b.sprite_mode = s.get("character") == "sprite"
        b.quips = [q for q in (s.get("quips") or QUIPS) if str(q).strip()] or list(QUIPS)
        b.greetings = [q for q in (s.get("greetings") or GREETINGS) if str(q).strip()] or list(GREETINGS)
        b.tangents = [q for q in (s.get("tangents") or TANGENTS) if str(q).strip()] or list(TANGENTS)
        b.moments = [q for q in (s.get("moments") or []) if str(q).strip()] or None
        if hasattr(self, "attention"):
            if self.settings_seen is not None and s != self.settings_seen:
                self.bus.publish("buddy.interaction", "settings")  # fiddling with his settings counts
            self.attention.apply(s)
        self.settings_seen = dict(s)
        screen = self.pick_screen(s)
        if screen is not self.overlay.home:  # layer-shell windows can't move: make a new one there
            old = self.overlay
            b.set_screen_id(self.screens.index(screen))
            b.set_screen(screen.name(), screen.geometry().topLeft())
            self.overlay = Overlay(screen, b)
            self.overlay.show()
            old.close()
            old.deleteLater()
        if hasattr(self, "voice"):
            self.voice.apply(s)
        if hasattr(self, "speaker"):
            self.speaker.apply(s)
        if hasattr(self, "hummer"):
            self.hummer.apply(s)
        hide_for_fullscreen = self.fullscreen_here and bool(s.get("fullscreen_hide", True))
        self.overlay.set_paused(bool(s.get("paused", False)) or hide_for_fullscreen)


def already_running():
    try:
        pid = int(open(PID_PATH).read().strip())
        os.kill(pid, 0)
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return pid if b"overlay/main.py" in f.read() else None
    except (OSError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser(description="Desktop Buddy overlay")
    ap.add_argument("--scale", type=float, help="character size for this run (default: from settings)")
    ap.add_argument("--demo", action="store_true", help="cycle through every action")
    ap.add_argument("--action", choices=sorted(list(ACTIONS) + list(SCENES) + ["walk"]),
                    help="repeat one action or scene forever")
    ap.add_argument("--screen", help="monitor name for this run, e.g. HDMI-A-3 (default: from settings)")
    args = ap.parse_args()

    pid = already_running()
    if pid:
        print(f"Desktop Buddy is already running (pid {pid}); opening settings instead.")
        launch("settings/window.py")
        return
    os.makedirs(os.path.dirname(PID_PATH), exist_ok=True)
    with open(PID_PATH, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(lambda: os.path.exists(PID_PATH) and already_running() == os.getpid()
                    and os.remove(PID_PATH))

    app = QApplication(sys.argv)
    # Ctrl+C or a kill: quit properly, so the KWin window script gets unloaded
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    keepalive = QTimer()  # lets Python notice those signals even while he's paused
    keepalive.start(300)
    app.setQuitOnLastWindowClosed(False)  # switching monitors closes the old window
    app.setApplicationName("Desktop Buddy")
    ctl = Controller(app, args)  # noqa: F841
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
