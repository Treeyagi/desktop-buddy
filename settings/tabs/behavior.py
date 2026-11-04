"""Behavior tab: what he does and how often, Do it now, vending odds, icons and bees, ADHD brain."""
from settings.tabs.common import *  # noqa: F401,F403


class BehaviorTab:
    def _behavior_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)

        what = QGroupBox("What he does")
        grid = QGridLayout(what)
        grid.setColumnStretch(2, 1)
        for col, text in ((1, "rarely"), (3, "a lot")):
            grid.addWidget(self._hint(text), 0, col)
        self.behavior_rows = {}
        for r, (name, label, about) in enumerate(BEHAVIORS, start=1):
            on = QCheckBox(label)
            on.setToolTip(about)
            often = QSlider(Qt.Orientation.Horizontal)
            often.setRange(0, 100)
            often.setToolTip("How often, compared to normal")
            now = QPushButton("Do it now")
            on.toggled.connect(lambda _, n=name: self._behavior_changed(n))
            often.valueChanged.connect(lambda _, n=name: self._behavior_changed(n))
            now.clicked.connect(lambda _, n=name: self._do_now(n))
            on.toggled.connect(often.setEnabled)
            grid.addWidget(on, r, 0)
            grid.addWidget(often, r, 1, 1, 3)
            grid.addWidget(now, r, 4)
            self.behavior_rows[name] = (on, often)
        walk = QPushButton("Do it now")
        walk.clicked.connect(lambda: self._do_now("walk"))
        grid.addWidget(QLabel("Walking somewhere"), len(BEHAVIORS) + 1, 0)
        grid.addWidget(self._hint("always on; the Activity slider sets how much"), len(BEHAVIORS) + 1, 1, 1, 3)
        grid.addWidget(walk, len(BEHAVIORS) + 1, 4)
        self.do_status = self._hint("")
        grid.addWidget(self.do_status, len(BEHAVIORS) + 2, 0, 1, 5)
        outer.addWidget(what)

        vend = QGroupBox("Card vending machine")
        form = QFormLayout(vend)
        self.vend_odds = QSlider(Qt.Orientation.Horizontal)
        self.vend_odds.setRange(0, 100)
        self.vend_odds_label = QLabel()
        self.vend_odds.valueChanged.connect(self._vend_changed)
        row = QHBoxLayout()
        row.addWidget(self.vend_odds, 1)
        row.addWidget(self.vend_odds_label)
        form.addRow("Bundle in stock", row)
        self.vend_pity = QSlider(Qt.Orientation.Horizontal)
        self.vend_pity.setRange(0, 50)
        self.vend_pity_label = QLabel()
        self.vend_pity.valueChanged.connect(self._vend_changed)
        row = QHBoxLayout()
        row.addWidget(self.vend_pity, 1)
        row.addWidget(self.vend_pity_label)
        form.addRow("Pity per letdown", row)
        form.addRow("", self._hint("Each sold-out in a row adds the pity to the odds (up to 95%); "
                                   "a win resets it."))
        outer.addWidget(vend)

        icons = QGroupBox("Desktop icons and bees")
        box = QVBoxLayout(icons)
        self.icon_visits = QCheckBox("Visit my real desktop icons (the bees carry him up to them)")
        self.icon_visits.toggled.connect(lambda on: self._queue(icon_visits=on))
        self.new_files = QCheckBox("Check out new files when they land on the desktop (\"ooh, new!\")")
        self.new_files.toggled.connect(lambda on: self._queue(new_file_reaction=on))
        self.icon_visits.toggled.connect(self.new_files.setEnabled)
        self.companion = QCheckBox("Companion bee (hangs around him; helper bees still show up for errands)")
        self.companion.toggled.connect(lambda on: self._queue(companion_bee=on))
        for w in (self.icon_visits, self.new_files, self.companion):
            box.addWidget(w)
        outer.addWidget(icons)

        self.dance_mode = QCheckBox("Dance mode: he dances nonstop, music or not")
        self.dance_mode.toggled.connect(lambda on: self._queue(dance_mode=on))
        outer.addWidget(self.dance_mode)

        adhd = QGroupBox("ADHD brain")
        box = QVBoxLayout(adhd)
        self.adhd_boxes = {}
        for key, label in (("adhd_squirrel", "Squirrel moments: now and then he chases your mouse cursor"),
                           ("adhd_distract", "Gets distracted by windows you switch to and sounds that start"),
                           ("adhd_tangents", "Tangents: \"wait, unrelated, but...\""),
                           ("adhd_react", "Reacts to what you're doing: videos, coding, games, being up past midnight"),
                           ("adhd_moments", "Walk-out moments: now and then he stops to say something real (gratitude, family, what he's geeking out about)"),
                           ("adhd_dance", "Dances when music plays from your browser or a music player"),
                           ("adhd_mood", "Moods: grumpy when ignored for a while, smug when you take his advice")):
            cb = QCheckBox(label)
            cb.toggled.connect(lambda on, k=key: self._queue(**{k: on}))
            box.addWidget(cb)
            self.adhd_boxes[key] = cb
        row = QHBoxLayout()
        row.addWidget(QLabel("Nudge me after"))
        self.nudge = QSpinBox()
        self.nudge.setRange(0, 180)
        self.nudge.setSingleStep(15)
        self.nudge.setSuffix(" min on one window")
        self.nudge.setSpecialValueText("never")
        self.nudge.valueChanged.connect(lambda v: self._queue(nudge_minutes=v))
        row.addWidget(self.nudge)
        row.addStretch(1)
        box.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel("Focus timer:"))
        for label, minutes in (("25 min", 25), ("50 min", 50), ("Stop", 0)):
            b = QPushButton(label)
            b.clicked.connect(lambda _, m=minutes: self._focus(m))
            row.addWidget(b)
        row.addStretch(1)
        for label, name in (("Tangent now", "tangent"), ("Sulk now", "sulk")):
            b = QPushButton(label)
            b.clicked.connect(lambda _, n=name: self._do_now(n))
            row.addWidget(b)
        box.addLayout(row)
        box.addWidget(self._hint("The focus timer is also in the tray menu. He sits quietly beside you "
                                 "with a countdown, then celebrates at break time."))
        outer.addWidget(adhd)
        outer.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        return scroll

    def _behavior_changed(self, name):
        if self._syncing:
            return
        current = dict(self.pending.get("behaviors", self.settings.data.get("behaviors") or {}))
        on, often = self.behavior_rows[name]
        current[name] = {"on": on.isChecked(), "often": often_from_slider(often.value())}
        self._queue(behaviors=current)

    def _vend_changed(self, _=None):
        self.vend_odds_label.setText(f"{self.vend_odds.value()}%")
        self.vend_pity_label.setText(f"+{self.vend_pity.value()}%")
        self._queue(vending_odds=self.vend_odds.value() / 100, vending_pity=self.vend_pity.value() / 100)

    def _focus(self, minutes):
        sock = QLocalSocket()
        sock.connectToServer(SOCKET)
        if not sock.waitForConnected(300):
            self.do_status.setText("Start the buddy to use the focus timer.")
            return
        sock.write((json.dumps({"focus": minutes}) + "\n").encode())
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()

    def _do_now(self, name):
        if self._send(name):
            self.do_status.setText("")
        elif name not in ("kroger", "vending", "perch"):
            self.preview.buddy.do_now(name)
            self.do_status.setText("The buddy isn't running, so the preview did it.")
        else:
            self.do_status.setText("Start the buddy to see that one; it needs the whole screen.")

    def _sync_behavior(self, s):
        behaviors = s.get("behaviors") or {}
        for name, (on, often) in self.behavior_rows.items():
            b = behaviors.get(name, {})
            on.setChecked(bool(b.get("on", True)))
            often.setValue(slider_from_often(b.get("often", 1.0)))
            often.setEnabled(on.isChecked())
        self.vend_odds.setValue(int(round(float(s.get("vending_odds", 0.5)) * 100)))
        self.vend_pity.setValue(int(round(float(s.get("vending_pity", 0.15)) * 100)))
        self.vend_odds_label.setText(f"{self.vend_odds.value()}%")
        self.vend_pity_label.setText(f"+{self.vend_pity.value()}%")
        self.icon_visits.setChecked(bool(s.get("icon_visits", True)))
        self.new_files.setChecked(bool(s.get("new_file_reaction", True)))
        self.new_files.setEnabled(self.icon_visits.isChecked())
        self.companion.setChecked(bool(s.get("companion_bee", True)))
        self.dance_mode.setChecked(bool(s.get("dance_mode", False)))
        for key, cb in self.adhd_boxes.items():
            cb.setChecked(bool(s.get(key, True)))
        self.nudge.setValue(int(s.get("nudge_minutes", 60) or 0))
