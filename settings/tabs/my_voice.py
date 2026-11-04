"""My voice tab: record the mood samples his voice gets cloned from."""
from settings.tabs.common import *  # noqa: F401,F403


class MyVoiceTab:
    def _my_voice_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.addWidget(self._hint(
            "He'll talk in your voice. Read each script out loud in that mood, the way you'd really "
            "say it: one quiet room, the same mic every time, 10 to 20 seconds each. The recordings "
            "stay on this computer (~/.local/share/desktop-buddy/voice). Uses the microphone picked "
            "in Claude > Voice."))
        self.studio = {}
        self.studio_rec = recorder.Recorder(rate=samples.RATE)
        self.recording_mood = None
        self.studio_timer = QTimer(self)
        self.studio_timer.timeout.connect(self._studio_tick)
        for mood, label, script in samples.MOODS:
            group = QGroupBox(label)
            box = QVBoxLayout(group)
            text = QLabel(f"\u201c{script}\u201d")
            text.setWordWrap(True)
            text.setStyleSheet("font-size: 15px; padding: 4px;")
            box.addWidget(text)
            row = QHBoxLayout()
            rec = QPushButton("\u25cf Record")
            play = QPushButton("\u25b6 Play")
            status = self._hint("")
            rec.clicked.connect(lambda _, m=mood: self._toggle_record(m))
            play.clicked.connect(lambda _, m=mood: subprocess.Popen(["pw-play", samples.path(m)]))
            row.addWidget(rec)
            row.addWidget(play)
            row.addWidget(status, 1)
            box.addLayout(row)
            outer.addWidget(group)
            self.studio[mood] = (rec, play, status)
        outer.addStretch(1)
        self._refresh_studio()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        return scroll

    def _refresh_studio(self):
        for mood, (rec, play, status) in self.studio.items():
            secs = samples.seconds(mood)
            busy = self.recording_mood is not None
            rec.setEnabled(not busy or self.recording_mood == mood)
            play.setEnabled(secs > 0 and not busy)
            if self.recording_mood != mood:
                rec.setText("\u25cf Record again" if secs else "\u25cf Record")
                status.setText(f"\u2713 {secs:.1f} s recorded" if secs >= 3 else "not recorded yet")

    def _toggle_record(self, mood):
        rec, _, status = self.studio[mood]
        if self.recording_mood == mood:  # stop
            self.studio_timer.stop()
            secs = self.studio_rec.stop()
            self.recording_mood = None
            tmp = self.studio_rec.path
            if self.studio_rec.error:
                self._refresh_studio()
                status.setText(self.studio_rec.error)
            elif secs < 3:
                os.remove(tmp) if os.path.exists(tmp) else None
                self._refresh_studio()
                status.setText("That was too short; read the whole script.")
            else:
                os.replace(tmp, samples.path(mood))
                self._refresh_studio()
            return
        os.makedirs(samples.DIR, exist_ok=True)
        self.studio_rec.path = samples.path(mood) + ".tmp.wav"
        self.studio_rec.target = self.mic.currentData()
        self.studio_rec.start()
        self.recording_mood = mood
        self.studio_started = time.monotonic()
        self._refresh_studio()
        rec.setText("\u25a0 Stop")
        self.studio_timer.start(200)

    def _studio_tick(self):
        mood = self.recording_mood
        if mood is None:
            return
        secs = time.monotonic() - self.studio_started
        self.studio[mood][2].setText(f"recording\u2026 {secs:.0f} s (press Stop when you're done)")
        if secs > 40:  # nobody needs more than this; don't leave the mic on
            self._toggle_record(mood)
