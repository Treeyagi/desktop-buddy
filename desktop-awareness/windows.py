"""Where the windows are, from KWin itself.

Wayland doesn't let apps see each other's windows, so this loads a tiny
read-only KWin script (kwin_windows.js) that sends us a snapshot over D-Bus
whenever a window opens, closes, moves, minimizes, goes fullscreen or the
virtual desktop changes. The script is unloaded again when the buddy quits.

Publishes on the bus (see core/README.md):
  desktop.windows   list[DesktopWindow], bottom of the stack first

Run it directly to print what KWin reports:  python3 desktop-awareness/windows.py
"""
import json
import os
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QRectF, pyqtClassInfo, pyqtSlot
from PyQt6.QtDBus import QDBusConnection, QDBusInterface

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "kwin_windows.js")
SCRIPT_NAME = "desktop-buddy-windows"
SERVICE = "org.desktopbuddy.Windows"
PATH = "/Windows"


@dataclass
class DesktopWindow:
    id: str
    title: str
    app: str
    rect: QRectF          # frame, in global (all-monitors) coordinates
    minimized: bool
    fullscreen: bool
    active: bool
    output: str           # monitor name, e.g. HDMI-A-3
    here: bool            # on the current virtual desktop
    z: int                # stacking position, higher is on top

    @property
    def showing(self):
        return self.here and not self.minimized


@pyqtClassInfo("D-Bus Interface", SERVICE)
class _Receiver(QObject):
    def __init__(self, on_update):
        super().__init__()
        self.on_update = on_update

    @pyqtSlot(str)
    def Update(self, data):
        self.on_update(data)


class WindowWatcher(QObject):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus
        self.windows = []
        self.receiver = _Receiver(self._update)
        session = QDBusConnection.sessionBus()
        if not session.registerService(SERVICE):
            print("desktop-awareness: another buddy already has the window service")
        session.registerObject(PATH, self.receiver, QDBusConnection.RegisterOption.ExportAllSlots)
        self.kwin = QDBusInterface("org.kde.KWin", "/Scripting", "org.kde.kwin.Scripting", session)
        if not self.kwin.isValid():
            print("desktop-awareness: KWin scripting isn't available; no window awareness")
            return
        self.kwin.call("unloadScript", SCRIPT_NAME)  # a leftover from a crash, if any
        self.kwin.call("loadScript", SCRIPT, SCRIPT_NAME)
        self.kwin.call("start")

    def stop(self):
        if self.kwin.isValid():
            self.kwin.call("unloadScript", SCRIPT_NAME)

    def _update(self, data):
        try:
            raw = json.loads(data)
        except ValueError:
            return
        self.windows = [DesktopWindow(
            id=w["id"], title=w["title"], app=w["app"],
            rect=QRectF(w["x"], w["y"], w["w"], w["h"]),
            minimized=w["minimized"], fullscreen=w["fullscreen"], active=w["active"],
            output=w["output"], here=w["here"], z=w["z"]) for w in raw]
        self.bus.publish("desktop.windows", self.windows)


if __name__ == "__main__":
    import signal
    import sys

    sys.path.insert(0, os.path.dirname(HERE))
    from PyQt6.QtCore import QCoreApplication, QTimer

    from core.bus import Bus

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QCoreApplication(sys.argv)
    bus = Bus()

    def show(windows):
        print(f"--- {len(windows)} windows (bottom to top)")
        for w in windows:
            r = w.rect
            flags = "".join(f for f, on in ((" min", w.minimized), (" FULL", w.fullscreen),
                                            (" active", w.active), (" other-desktop", not w.here)) if on)
            print(f"  {w.output:9} {r.x():5.0f},{r.y():5.0f} {r.width():5.0f}x{r.height():<5.0f} "
                  f"{w.app[:18]:18} {w.title[:40]!r}{flags}")

    bus.subscribe("desktop.windows", show)
    watcher = WindowWatcher(bus)
    QTimer.singleShot(int(sys.argv[1]) * 1000 if len(sys.argv) > 1 else 3000,
                      lambda: (watcher.stop(), app.quit()))
    app.exec()
