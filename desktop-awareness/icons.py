"""Where Plasma put the desktop icons, read from its config (no screenshots).

Plasma's folder view saves each file's grid slot, per screen, in
~/.config/plasma-org.kde.plasma.desktop-appletsrc:

  [Containments][N]           plugin=org.kde.plasma.folder, lastScreen=<Plasma screen id>
  [Containments][N][General]  positions={"WxH": ["1", "<slots per row>", url, row, col, ...]}
                              changedPositions={url: ["WxH", row, col], ...}
  [ScreenMapping]             screenMapping=url,screen,activity,url,screen,activity,...

Those lists keep stale entries for deleted files, so only files that exist in
~/Desktop count, and the screen mapping decides which screen a file is on
(files missing from the mapping aren't shown by Plasma, so they're skipped).
Files Plasma hasn't saved a slot for yet go in the first free slots.

Publishes on the bus (see core/README.md):
  desktop.icons       list[DesktopIcon], on start and whenever the desktop changes
  desktop.icon_added  DesktopIcon, for each file that newly shows up

Run it directly to print what it sees:  python3 desktop-awareness/icons.py
"""
import itertools
import json
import os
import re
import time
from configparser import RawConfigParser
from dataclasses import dataclass
from urllib.parse import unquote

from PyQt6.QtCore import QFileSystemWatcher, QMimeDatabase, QObject, QPointF, QRectF, QTimer
from PyQt6.QtGui import QIcon

CONFIG = os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc")
DESKTOP = os.path.expanduser("~/Desktop")

# Grid geometry, measured on this desktop at the default icon size: slots are
# 112 px apart starting at x=56, rows 120 px apart starting at y=40 (checked
# against an icon in row 7), icons ~60 px.
CELL_W, CELL_H = 112, 120
FIRST_X, FIRST_Y = 56, 40
ICON = 60

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_mime = None


@dataclass
class DesktopIcon:
    path: str
    name: str
    screen: int       # Plasma screen id (0 = primary)
    row: int
    col: int
    rect: QRectF      # the icon image, in that screen's coordinates

    @property
    def center(self):
        return self.rect.center()

    def size_text(self):
        try:
            if os.path.isdir(self.path):
                return f"{len(os.listdir(self.path))} files"
            n = os.path.getsize(self.path)
        except OSError:
            return "???"
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024

    def age_text(self):
        try:
            days = (time.time() - os.path.getmtime(self.path)) / 86400
        except OSError:
            return "old"
        if days < 1:
            return "fresh today"
        if days < 60:
            return f"{days:.0f}d old"
        return f"{days / 30:.0f}mo old"

    def pixmap(self, size=64):
        """The icon Plasma shows for this file, from the current icon theme."""
        global _mime
        name = None
        if self.path.endswith(".desktop"):
            try:
                with open(self.path, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if line.startswith("Icon="):
                            name = line[5:].strip()
                            break
            except OSError:
                pass
        icon = QIcon()
        if name:
            icon = QIcon(name) if os.path.isabs(name) else QIcon.fromTheme(name)
        if icon.isNull():
            _mime = _mime or QMimeDatabase()
            m = _mime.mimeTypeForFile(self.path)
            icon = QIcon.fromTheme(m.iconName(), QIcon.fromTheme(m.genericIconName()))
            if icon.isNull() and os.path.isdir(self.path):
                icon = QIcon.fromTheme("folder")
        return None if icon.isNull() else icon.pixmap(size, size)


def _name(url):
    return unquote(url[len("desktop:/"):]) if url.startswith("desktop:/") else None


def _screen_mapping(raw):
    """Parse url,screen,activity triples; file names can contain commas."""
    parts = raw.split(",") if raw else []
    out, activity, i = {}, None, 0
    while i < len(parts):
        j = i + 1
        while j + 1 < len(parts) and not (parts[j].isdigit() and _UUID.match(parts[j + 1])):
            j += 1
        if j + 1 >= len(parts):
            break
        name = _name(",".join(parts[i:j]))
        if name is not None:
            out[name] = int(parts[j])
        activity = parts[j + 1]
        i = j + 2
    return out, activity


def read_icons(config=CONFIG, desktop=DESKTOP):
    cp = RawConfigParser(strict=False, interpolation=None, delimiters=("=",), allow_no_value=True)
    cp.optionxform = str
    cp.read(config, encoding="utf-8")
    files = sorted(f for f in os.listdir(desktop) if not f.startswith("."))
    mapping, activity = _screen_mapping(cp.get("ScreenMapping", "screenMapping", fallback=""))

    folders = {}
    for sec in cp.sections():
        if sec.count("][") != 1 or cp.get(sec, "plugin", fallback="") != "org.kde.plasma.folder":
            continue
        if activity and cp.get(sec, "activityId", fallback="") not in ("", activity):
            continue
        folders[int(cp.get(sec, "lastScreen", fallback="0") or 0)] = sec

    icons = []
    for screen, sec in sorted(folders.items()):
        general = sec + "][General"
        raw = cp.get(general, "positions", fallback="") if cp.has_section(general) else ""
        positions = json.loads(raw) if raw else {}
        res = cp.get(general, "lastResolution", fallback=None) if cp.has_section(general) else None
        res = res or next(iter(positions), None)
        lst = positions.get(res, [])
        per_row = int(lst[1]) if len(lst) > 1 else 17
        slots = {}
        for k in range(2, len(lst) - 2, 3):
            slots[_name(lst[k])] = (int(lst[k + 1]), int(lst[k + 2]))
        raw = cp.get(general, "changedPositions", fallback="") if cp.has_section(general) else ""
        for url, v in (json.loads(raw) if raw else {}).items():
            if v and v[0] == res:
                slots[_name(url)] = (int(v[1]), int(v[2]))

        # Plasma only shows files it has mapped to a screen (a fresh config may have no mapping yet)
        mine = [f for f in files if (f in mapping or not mapping) and mapping.get(f, 0) == screen]
        placed, taken = {}, set()
        for f in mine:
            if f in slots and slots[f] not in taken:
                placed[f] = slots[f]
                taken.add(slots[f])
        free = (divmod(i, per_row) for i in itertools.count() if divmod(i, per_row) not in taken)
        for f in mine:
            if f not in placed:
                placed[f] = next(free)
        for f, (row, col) in placed.items():
            c = QPointF(FIRST_X + col * CELL_W, FIRST_Y + row * CELL_H)
            rect = QRectF(c.x() - ICON / 2, c.y() - ICON / 2, ICON, ICON)
            icons.append(DesktopIcon(os.path.join(desktop, f), f, screen, row, col, rect))
    return icons


class IconWatcher(QObject):
    """Re-reads the icons when ~/Desktop or Plasma's config changes."""

    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus
        self.known = None
        self.watch = QFileSystemWatcher([p for p in (DESKTOP, CONFIG) if os.path.exists(p)], self)
        self.watch.directoryChanged.connect(self._poke)
        self.watch.fileChanged.connect(self._poke)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(800)
        self.timer.timeout.connect(self.refresh)
        self.refresh()

    def _poke(self, *_):
        if CONFIG not in self.watch.files() and os.path.exists(CONFIG):
            self.watch.addPath(CONFIG)  # Plasma replaces the file when it saves
        self.timer.start()

    def refresh(self):
        try:
            icons = read_icons()
        except Exception as e:  # a half-written config shouldn't kill the buddy
            print("desktop-awareness: couldn't read icons:", e)
            return
        paths = {i.path for i in icons}
        if self.known is not None:
            for icon in icons:
                if icon.path not in self.known:
                    self.bus.publish("desktop.icon_added", icon)
        self.known = paths
        self.bus.publish("desktop.icons", icons)


if __name__ == "__main__":
    for i in read_icons():
        print(f"screen {i.screen}  row {i.row} col {i.col:2d}  "
              f"center ({i.center.x():.0f}, {i.center.y():.0f})  {i.name!r}")
