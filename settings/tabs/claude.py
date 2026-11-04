"""Claude tab: connection, model, personality, Try him, and the Voice (push-to-talk) section."""
from settings.tabs.common import *  # noqa: F401,F403


class ClaudeTab:
    def _claude_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        self.claude_on = QCheckBox("Let him answer with Claude")
        self.claude_on.toggled.connect(lambda on: self._queue(claude_enabled=on))
        outer.addWidget(self.claude_on)
        outer.addWidget(self._hint("When voice is built, he'll answer what you say out loud, in his own "
                                   "personality. Until then you can try him out below."))

        conn = QGroupBox("Connection")
        box = QVBoxLayout(conn)
        self.use_cli = QRadioButton("Claude Code (uses your Claude plan)")
        self.cli_status = self._hint("")
        self.use_api = QRadioButton("Anthropic API key")
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("Paste your API key")
        save = QPushButton("Save to KWallet")
        save.clicked.connect(self._save_key)
        remove = QPushButton("Remove")
        remove.clicked.connect(self._remove_key)
        row = QHBoxLayout()
        row.addWidget(self.key_edit, 1)
        row.addWidget(save)
        row.addWidget(remove)
        self.key_status = self._hint("")
        group = QButtonGroup(self)
        group.addButton(self.use_cli)
        group.addButton(self.use_api)
        self.use_cli.toggled.connect(lambda on: on and self._queue(claude_backend="claude-code"))
        self.use_api.toggled.connect(lambda on: on and self._queue(claude_backend="api"))
        for w in (self.use_cli, self.cli_status, self.use_api):
            box.addWidget(w)
        box.addLayout(row)
        box.addWidget(self.key_status)
        outer.addWidget(conn)

        form = QFormLayout()
        self.model_box = QComboBox()
        for model_id, label in client.MODELS:
            self.model_box.addItem(label, model_id)
        self.model_box.currentIndexChanged.connect(
            lambda _: self._queue(claude_model=self.model_box.currentData()))
        form.addRow("Model", self.model_box)
        files = QHBoxLayout()
        for label, name in (("Edit personality…", "personality.md"), ("Edit who I am…", "who-i-am.md")):
            b = QPushButton(label)
            b.clicked.connect(lambda _, n=name: QDesktopServices.openUrl(
                QUrl.fromLocalFile(os.path.join(ROOT, "brain", n))))
            files.addWidget(b)
        files.addStretch(1)
        form.addRow("Personality", files)
        outer.addLayout(form)

        test = QGroupBox("Try him")
        box = QVBoxLayout(test)
        row = QHBoxLayout()
        self.question = QLineEdit("What should I do with my afternoon?")
        self.question.returnPressed.connect(self._ask)
        self.ask_btn = QPushButton("Ask")
        self.ask_btn.clicked.connect(self._ask)
        row.addWidget(self.question, 1)
        row.addWidget(self.ask_btn)
        box.addLayout(row)
        self.answer = QLabel()
        self.answer.setWordWrap(True)
        self.answer.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.answer.setStyleSheet("background: #ffffff; color: #1e1628; border: 2px solid #1e1628;"
                                  "border-radius: 12px; padding: 8px;")
        self.answer.hide()
        self.answer_meta = self._hint("")
        box.addWidget(self.answer)
        box.addWidget(self.answer_meta)
        outer.addWidget(test)

        voice = QGroupBox("Voice")
        form = QFormLayout(voice)
        self.voice_on = QCheckBox("Push to talk: hold the key, talk, let go")
        self.voice_on.toggled.connect(lambda on: self._queue(voice_enabled=on))
        form.addRow("", self.voice_on)

        self.hotkey = QKeySequenceEdit()
        self.hotkey.setMaximumSequenceLength(1)
        use = QPushButton("Use this key")
        use.clicked.connect(self._set_hotkey)
        row = QHBoxLayout()
        row.addWidget(self.hotkey, 1)
        row.addWidget(use)
        self.hotkey_status = self._hint("A KDE global shortcut; it also shows up in System Settings > Shortcuts.")
        box = QVBoxLayout()
        box.addLayout(row)
        box.addWidget(self.hotkey_status)
        form.addRow("Key", box)

        self.screen_key = QKeySequenceEdit()
        self.screen_key.setMaximumSequenceLength(1)
        use = QPushButton("Use this key")
        use.clicked.connect(lambda: self._set_hotkey(screen=True))
        row = QHBoxLayout()
        row.addWidget(self.screen_key, 1)
        row.addWidget(use)
        self.screen_status = self._hint("Hold it and say \"roast my code\" or \"settle this argument\" (or anything "
                                        "about your screen). One screenshot goes to Claude, only then, and is deleted.")
        box = QVBoxLayout()
        box.addLayout(row)
        box.addWidget(self.screen_status)
        form.addRow("Look at my screen", box)

        self.mic = QComboBox()
        self.mic.currentIndexChanged.connect(lambda _: not self._syncing and self._queue(voice_mic=self.mic.currentData()))
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(lambda: self._fill_mics(self.mic.currentData()))
        row = QHBoxLayout()
        row.addWidget(self.mic, 1)
        row.addWidget(refresh)
        form.addRow("Microphone", row)

        self.stt_model = QComboBox()
        for name, label in stt.MODELS:
            self.stt_model.addItem(label, name)
        self.stt_model.currentIndexChanged.connect(self._model_changed)
        self.dl_btn = QPushButton("Download")
        self.dl_btn.clicked.connect(self._download_model)
        row = QHBoxLayout()
        row.addWidget(self.stt_model, 1)
        row.addWidget(self.dl_btn)
        self.dl_bar = QProgressBar()
        self.dl_bar.hide()
        self.stt_status = self._hint("")
        box = QVBoxLayout()
        box.addLayout(row)
        box.addWidget(self.dl_bar)
        box.addWidget(self.stt_status)
        form.addRow("Speech to text", box)

        self.test_btn = QPushButton("Hold to test")
        self.test_btn.pressed.connect(self._test_down)
        self.test_btn.released.connect(self._test_up)
        self.test_result = self._hint("Hold the button, say something, let go.")
        row = QHBoxLayout()
        row.addWidget(self.test_btn)
        row.addWidget(self.test_result, 1)
        form.addRow("Test", row)

        self.out_loud = QCheckBox("Answer out loud in my voice (needs the voice server: see voice-out/README.md)")
        self.out_loud.toggled.connect(lambda on: not self._syncing and self._queue(voice_out_loud=on))
        form.addRow("", self.out_loud)
        form.addRow("", self._hint("Your voice is turned into text on this computer by Whisper; only the "
                                   "text goes on to Claude. Recordings are deleted right after."))
        outer.addWidget(voice)
        self.net = QNetworkAccessManager(self)
        self.test_rec = recorder.Recorder(recorder.PATH.replace("ptt.wav", "settings-test.wav"))
        self._fill_mics(None)
        outer.addStretch(1)

        self._refresh_claude_status()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(tab)
        return scroll

    def _fill_mics(self, selected):
        self._syncing, was = True, self._syncing
        self.mic.clear()
        self.mic.addItem("System default", None)
        for name, desc in recorder.microphones():
            self.mic.addItem(desc, name)
        i = self.mic.findData(selected)
        if i < 0 and selected:
            self.mic.addItem(f"{selected} (not connected)", selected)
            i = self.mic.count() - 1
        self.mic.setCurrentIndex(max(0, i))
        self._syncing = was

    def _set_hotkey(self, screen=False):
        edit, status = (self.screen_key, self.screen_status) if screen else (self.hotkey, self.hotkey_status)
        seq = edit.keySequence()
        if seq.isEmpty():
            status.setText("Click the box, then press the key you want.")
            return
        kga = QDBusInterface("org.kde.kglobalaccel", "/kglobalaccel", "org.kde.KGlobalAccel",
                             QDBusConnection.sessionBus())
        key = seq[0].toCombined()
        hotkey = load("voice-in", "hotkey")
        mine = (hotkey.SCREEN_ACTION, hotkey.SCREEN_LABEL) if screen else (hotkey.ACTION, hotkey.LABEL)
        ours = kga.call("shortcut", hotkey._action_id(*mine)).arguments()
        free = kga.call("isGlobalShortcutAvailable", key, "desktop-buddy").arguments()
        if free and not free[0] and not (ours and isinstance(ours[0], list) and key in ours[0]):
            status.setText(f"{seq.toString()} is already used by another shortcut. Pick another.")
            return
        self._queue(**{"screen_hotkey" if screen else "voice_hotkey": seq.toString()})
        status.setText(f"{'Look at my screen' if screen else 'Push to talk'} is now {seq.toString()}.")

    def _model_changed(self, _=None):
        if not self._syncing:
            self._queue(whisper_model=self.stt_model.currentData())
        self._refresh_stt_status()

    def _refresh_stt_status(self):
        model = self.stt_model.currentData() or stt.DEFAULT_MODEL
        cli = stt.whisper_cli()
        have = stt.have_model(model)
        parts = [f"Whisper found at {cli}." if cli else
                 "Whisper isn't installed yet: run  sudo pacman -S whisper-cpp"]
        parts.append(f"The {model} model is downloaded ✓" if have else
                     f"The {model} model isn't downloaded yet.")
        self.stt_status.setText("\n".join(parts))
        downloading = getattr(self, "dl_reply", None) is not None
        self.dl_btn.setEnabled(not have and not downloading)
        self.dl_btn.setText("Downloaded" if have else "Download")

    def _download_model(self):
        model = self.stt_model.currentData()
        os.makedirs(stt.MODEL_DIR, exist_ok=True)
        self.dl_part = stt.model_path(model) + ".part"
        self.dl_file = open(self.dl_part, "wb")
        self.dl_model = model
        reply = self.net.get(QNetworkRequest(QUrl(stt.MODEL_URL.format(name=model))))
        reply.readyRead.connect(lambda: self.dl_file.write(bytes(reply.readAll())))
        reply.downloadProgress.connect(self._dl_progress)
        reply.finished.connect(self._dl_finished)
        self.dl_reply = reply
        self.dl_bar.setValue(0)
        self.dl_bar.show()
        self._refresh_stt_status()

    def _dl_progress(self, got, total):
        if total > 0:
            self.dl_bar.setMaximum(100)
            self.dl_bar.setValue(int(got * 100 / total))

    def _dl_finished(self):
        reply, self.dl_reply = self.dl_reply, None
        self.dl_file.write(bytes(reply.readAll()))
        self.dl_file.close()
        ok = reply.error() == QNetworkReply.NetworkError.NoError and os.path.getsize(self.dl_part) > 1_000_000
        if ok:
            os.replace(self.dl_part, stt.model_path(self.dl_model))
        else:
            os.remove(self.dl_part)
            self.stt_status.setText(f"Download failed: {reply.errorString()}")
        reply.deleteLater()
        self.dl_bar.hide()
        if ok:
            self._refresh_stt_status()

    def _test_down(self):
        self.test_rec.target = self.mic.currentData()
        self.test_rec.start()
        self.test_result.setText("recording… let go when you're done")

    def _test_up(self):
        secs = self.test_rec.stop()
        if self.test_rec.error:
            self.test_result.setText(self.test_rec.error)
            return
        if secs < 0.4:
            self.test_result.setText("Hold the button down while you talk.")
            self.test_rec.discard()
            return
        self.test_result.setText("transcribing…")
        self.test_worker = TranscribeWorker(self.test_rec.path, self.stt_model.currentData())
        self.test_worker.done.connect(lambda text, err: self.test_result.setText(
            err or (f"I heard: \"{text}\"" if text else "I didn't catch anything.")))
        self.test_worker.start()

    def _refresh_claude_status(self):
        exe = client.claude_cli()
        self.cli_status.setText(f"Found Claude Code at {exe}" if exe else
                                "Claude Code isn't installed (no `claude` command).")
        if not client.sdk_installed():
            self.key_status.setText("Needs the Anthropic SDK first: pip install --user --break-system-packages anthropic")
        elif not keychain.available():
            self.key_status.setText("No keyring tool found (secret-tool); ANTHROPIC_API_KEY still works.")
        else:
            self.key_status.setText("Key saved in KWallet ✓" if keychain.get() else
                                    "No key saved yet. It's stored in KWallet, never in a file.")

    def _save_key(self):
        value = self.key_edit.text().strip()
        self.key_edit.clear()
        if not value:
            return
        err = keychain.store(value)
        self._refresh_claude_status()
        if err:
            self.key_status.setText(err)

    def _remove_key(self):
        keychain.clear()
        self._refresh_claude_status()

    def _ask(self):
        question = self.question.text().strip()
        if not question or getattr(self, "worker", None) and self.worker.isRunning():
            return
        s = dict(self.settings.data)
        s.update(self.pending)
        self.ask_btn.setEnabled(False)
        self.answer.setText("thinking…")
        self.answer.show()
        self.answer_meta.setText("")
        self.worker = AskWorker(question, s["claude_backend"], s["claude_model"])
        self.worker.done.connect(self._answered)
        self.worker.start()

    def _answered(self, reply):
        self.ask_btn.setEnabled(True)
        how = "Claude Code" if reply.backend == "claude-code" else "API"
        name = dict(client.MODELS).get(reply.model, reply.model).split(" (")[0]
        if reply.error:
            self.answer.setText(reply.error)
            self.answer.setStyleSheet(self.answer.styleSheet().replace("color: #1e1628;", "color: #c0392b;"))
        else:
            self.answer.setText(reply.text)
            self.answer.setStyleSheet(self.answer.styleSheet().replace("color: #c0392b;", "color: #1e1628;"))
            short = reply.text if len(reply.text) <= 34 else reply.text[:31].rstrip() + "…"
            self.preview.buddy.say(short, life=3.5)
        self.answer_meta.setText(f"{how} · {name} · {reply.seconds:.1f}s")

    def _sync_claude(self, s):
        self.claude_on.setChecked(bool(s.get("claude_enabled")))
        (self.use_api if s.get("claude_backend") == "api" else self.use_cli).setChecked(True)
        self.model_box.setCurrentIndex(max(0, self.model_box.findData(s.get("claude_model"))))
        self.voice_on.setChecked(bool(s.get("voice_enabled", True)))
        self.hotkey.setKeySequence(QKeySequence(str(s.get("voice_hotkey") or "")))
        self.screen_key.setKeySequence(QKeySequence(str(s.get("screen_hotkey") or "")))
        if self.mic.currentData() != s.get("voice_mic"):
            self._fill_mics(s.get("voice_mic"))
        self.stt_model.setCurrentIndex(max(0, self.stt_model.findData(s.get("whisper_model", stt.DEFAULT_MODEL))))
        self._refresh_stt_status()
        self.out_loud.setChecked(bool(s.get("voice_out_loud")))
