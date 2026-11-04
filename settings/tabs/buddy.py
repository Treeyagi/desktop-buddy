"""Buddy tab: pause, size, monitor, activity, quiet, fullscreen, start at login."""
from settings.tabs.common import *  # noqa: F401,F403


class BuddyTab:
    def _buddy_tab(self):
        tab = QWidget()
        form = QFormLayout(tab)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.paused = QCheckBox("Hide him for now")
        self.paused.toggled.connect(lambda on: self._queue(paused=on))
        form.addRow("Pause", self.paused)

        self.size = QSlider(Qt.Orientation.Horizontal)
        self.size.setRange(50, 200)
        self.size_label = QLabel()
        self.size.valueChanged.connect(self._size_moved)
        row = QHBoxLayout()
        row.addWidget(self.size, 1)
        row.addWidget(self.size_label)
        form.addRow("Size", row)

        self.monitor = QComboBox()
        self.monitor.addItem("Auto (where your desktop icons are)", "auto")
        app = QApplication.instance()
        for i, scr in enumerate([app.primaryScreen()] +
                                [s for s in app.screens() if s != app.primaryScreen()]):
            g = scr.geometry()
            label = f"{scr.name()}  ({g.width()}×{g.height()}{', primary' if i == 0 else ''})"
            self.monitor.addItem(label, scr.name())
        self.monitor.currentIndexChanged.connect(
            lambda _: self._queue(monitor=self.monitor.currentData()))
        form.addRow("Monitor", self.monitor)

        self.activity = QSlider(Qt.Orientation.Horizontal)
        self.activity.setRange(0, 100)
        self.activity.valueChanged.connect(self._activity_moved)
        row = QHBoxLayout()
        row.addWidget(QLabel("chill"))
        row.addWidget(self.activity, 1)
        row.addWidget(QLabel("hyper"))
        form.addRow("Activity", row)

        self.quiet = QCheckBox("Quiet mode")
        self.quiet.toggled.connect(lambda on: self._queue(quiet=on))
        hint = QLabel("For calls and gaming: no speech bubbles or thought clouds, "
                      "no big scenes, mostly chill moves.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: gray")
        box = QVBoxLayout()
        box.addWidget(self.quiet)
        box.addWidget(hint)
        form.addRow("Quiet", box)

        self.fullscreen = QCheckBox("Hide while a fullscreen app is on his monitor")
        self.fullscreen.toggled.connect(lambda on: self._queue(fullscreen_hide=on))
        box = QVBoxLayout()
        box.addWidget(self.fullscreen)
        box.addWidget(self._hint("Games and fullscreen videos get the screen to themselves; "
                                 "he comes back when they're done."))
        form.addRow("Fullscreen", box)

        self.login = QCheckBox("Start him when I log in")
        self.login.setChecked(autostart.is_enabled())
        self.login.toggled.connect(self._login_toggled)
        self.login_hint = self._hint("")
        box = QVBoxLayout()
        box.addWidget(self.login)
        box.addWidget(self.login_hint)
        form.addRow("Startup", box)
        self._login_hint()
        return tab

    def _login_toggled(self, on):
        if on:
            autostart.enable(buddy_icon(128).pixmap(128, 128))
        else:
            autostart.disable()
        self._login_hint()

    def _login_hint(self):
        if autostart.is_enabled() and not autostart.points_here():
            self.login_hint.setText("The login entry points at an older copy of the project. "
                                    "Turn this off and on to point it here.")
        else:
            self.login_hint.setText("Adds Desktop Buddy to Plasma's autostart "
                                    "(~/.config/autostart). If you move the project folder, "
                                    "turn this off and on again.")

    def _size_moved(self, v):
        self.size_label.setText(f"{v / 100:.2f}×")
        self._queue(size=round(v / 100, 2))

    def _activity_moved(self, v):
        self._queue(activity=round(v / 100, 2))

    def _sync_buddy(self, s):
        self.paused.setChecked(bool(s["paused"]))
        self.size.setValue(int(round(float(s["size"]) * 100)))
        self.size_label.setText(f"{float(s['size']):.2f}×")
        i = self.monitor.findData(s.get("monitor", "auto"))
        self.monitor.setCurrentIndex(max(0, i))
        self.activity.setValue(int(round(float(s["activity"]) * 100)))
        self.quiet.setChecked(bool(s["quiet"]))
        self.fullscreen.setChecked(bool(s.get("fullscreen_hide", True)))
