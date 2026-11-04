"""Sayings tab: his sayings, greetings and tangents, Say it now; _send talks to the running buddy."""
from settings.tabs.common import *  # noqa: F401,F403


class SayingsTab:
    def _sayings_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.addWidget(self._hint("Double-click a line to edit it. Keep them short; long ones wrap "
                                   "onto a second line in his bubble."))
        self.say_lists = {}
        for key, title, defaults, action in (("quips", "Random sayings", QUIPS, "quip"),
                                             ("greetings", "When he waves", GREETINGS, "wave"),
                                             ("tangents", "Tangents (\"wait, unrelated, but...\")",
                                              TANGENTS, "tangent")):
            group = QGroupBox(title)
            box = QVBoxLayout(group)
            lst = QListWidget()
            lst.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                | QAbstractItemView.EditTrigger.EditKeyPressed)
            lst.itemChanged.connect(lambda _, k=key: self._sayings_changed(k))
            box.addWidget(lst)
            buttons = QHBoxLayout()
            for label, fn in (("Add", lambda _, k=key: self._add_saying(k)),
                              ("Remove", lambda _, k=key: self._remove_saying(k)),
                              ("Say it now", lambda _, k=key, a=action: self._say_now(k, a)),
                              ("Reset", lambda _, k=key: self._queue(**{k: None}) or self._flush())):
                b = QPushButton(label)
                b.clicked.connect(fn)
                buttons.addWidget(b)
            buttons.addStretch(1)
            box.addLayout(buttons)
            outer.addWidget(group)
            self.say_lists[key] = (lst, defaults)
        self.say_status = self._hint("")
        outer.addWidget(self.say_status)
        return tab

    def _lines(self, key):
        lst, _ = self.say_lists[key]
        return [lst.item(i).text() for i in range(lst.count())]

    def _fill(self, key, lines):
        lst, _ = self.say_lists[key]
        if self._lines(key) == lines:
            return
        lst.blockSignals(True)
        lst.clear()
        for line in lines:
            item = QListWidgetItem(line)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            lst.addItem(item)
        lst.blockSignals(False)

    def _sayings_changed(self, key):
        lines = [ln.strip()[:120] for ln in self._lines(key) if ln.strip()]
        self._queue(**{key: lines})

    def _add_saying(self, key):
        lst, _ = self.say_lists[key]
        item = QListWidgetItem("something new")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        lst.addItem(item)
        lst.setCurrentItem(item)
        lst.editItem(item)

    def _remove_saying(self, key):
        lst, _ = self.say_lists[key]
        row = lst.currentRow()
        if row >= 0 and lst.count() > 1:
            lst.takeItem(row)
            self._sayings_changed(key)

    def _say_now(self, key, action):
        lst, _ = self.say_lists[key]
        item = lst.currentItem() or lst.item(0)
        if item is None:
            return
        if not self._send(action, item.text()):
            self.preview.buddy.do_now(action, item.text())
            self.say_status.setText("The buddy isn't running, so the preview said it.")
        else:
            self.say_status.setText("")

    def _send(self, name, text=None):
        """Send a request to the running buddy; False if he isn't running."""
        sock = QLocalSocket()
        sock.connectToServer(SOCKET)
        if not sock.waitForConnected(300):
            return False
        msg = {"do": name}
        if text:
            msg["text"] = text
        sock.write((json.dumps(msg) + "\n").encode())
        sock.flush()
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True

    def _sync_sayings(self, s):
        for key, (lst, defaults) in self.say_lists.items():
            self._fill(key, list(s.get(key) or defaults))
