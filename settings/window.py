"""Desktop Buddy settings window.

Runs as its own little program, because the overlay turns every window in its
process into a layer-shell surface. Open it from the tray icon, or run:

    python3 settings/window.py

Every change is written to ~/.config/desktop-buddy/settings.json right away,
and the running buddy picks it up live. The window also follows changes made
elsewhere (the tray's Pause and Quiet mode).
"""
import json
import os
import signal
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.pop("QT_WAYLAND_SHELL_INTEGRATION", None)  # a normal window, not a desktop layer

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QThread, QTimer, QUrl, pyqtSignal  # noqa: E402
from PyQt6.QtGui import (QColor, QDesktopServices, QFont, QIcon, QLinearGradient, QPainter,  # noqa: E402
                         QPainterPath, QPixmap)
from PyQt6.QtDBus import QDBusConnection, QDBusInterface  # noqa: E402
from PyQt6.QtGui import QKeySequence  # noqa: E402
from PyQt6.QtNetwork import QLocalSocket, QNetworkAccessManager, QNetworkReply, QNetworkRequest  # noqa: E402
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox,  # noqa: E402
                             QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QKeySequenceEdit, QLineEdit, QListWidget, QListWidgetItem,
                             QProgressBar, QPushButton, QRadioButton, QScrollArea, QSlider,
                             QTabWidget, QToolButton, QVBoxLayout, QWidget)

from brain import client, keychain  # noqa: E402
import character.rig as rig  # noqa: E402
from character.behavior import GREETINGS, QUIPS, Buddy  # noqa: E402
from core.load import load  # noqa: E402
from settings import autostart  # noqa: E402

stt = load("voice-in", "stt")
recorder = load("voice-in", "recorder")
from settings.store import DEFAULTS, PID_PATH, SOCKET, SettingsFile  # noqa: E402
from settings.tray import buddy_icon  # noqa: E402

PREVIEW_W, PREVIEW_H = 320, 240

# Behavior tab rows: (action or scene, label, what it is)
BEHAVIORS = [
    ("idle", "Hanging out", "Breathing, humming, scratching his beard, watching the bee."),
    ("quip", "Saying something", "A short line in a speech bubble."),
    ("wave", "Waving", "An open-hand wave, sometimes with a \"hey hey!\"."),
    ("jump", "Jumping", "Fists up in the air, sometimes a double hop."),
    ("dance", "Victory dance", "Fist pumps, hearts and notes, the bee loops around him."),
    ("spores", "Mushroom spores", "Shimmies until his hat puffs spores, stomps, toadstools pop up."),
    ("stretch", "Stretching", "Arms out wide and a big yawn."),
    ("meditate", "Meditating", "Floats cross-legged: ommm."),
    ("nap", "Napping", "Snoozes sitting down; the bee naps on his hat."),
    ("kroger", "Clearance aisle", "Finds something (often a real desktop icon), daydreams, does the math."),
    ("perch", "Sitting on windows", "Bees lift him onto a window's title bar; he rides along if you move it."),
    ("vending", "Card vending machine", "Rare. Sold out, or The Ultimate Pull."),
]


def shoe_swatch(style, w=170, h=104):
    """A picture of one pair of shoes in a colorway, for the Look tab."""
    old = rig.shoe_style
    rig.set_shoes(style)
    pm = QPixmap(w, h)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(w * 0.36, h * 0.72)
    p.scale(2.9, 2.9)
    rig._shoe(p, QPointF(0, 0), 0, False, "body")
    rig._shoe(p, QPointF(0, 0), 0, False, "tongue")
    p.end()
    rig.set_shoes(old)
    return QIcon(pm)


def often_from_slider(v):
    return round(2 ** ((v - 50) / 25), 3)  # 0 = 1/4 as often, 50 = normal, 100 = 4x


def slider_from_often(m):
    import math
    return int(round(50 + 25 * math.log2(max(0.25, min(4.0, float(m))))))


def buddy_pid():
    try:
        pid = int(open(PID_PATH).read().strip())
        os.kill(pid, 0)
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return pid if b"overlay/main.py" in f.read() else None
    except (OSError, ValueError):
        return None


class Preview(QWidget):
    """A tiny live buddy that reacts to the size and activity sliders."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(PREVIEW_W, PREVIEW_H)
        self.buddy = Buddy(PREVIEW_W, PREVIEW_H - 22, scale=0.8)
        self.buddy.scenes_enabled = False
        self.buddy.x = PREVIEW_W / 2
        self.paused = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def apply(self, s):
        # the preview box is small, so show the size relative to the default
        self.buddy.set_scale(0.8 * float(s["size"]) / DEFAULTS["size"])
        self.buddy.activity = float(s["activity"])
        self.buddy.quiet = bool(s["quiet"])
        self.buddy.behaviors = s.get("behaviors") or {}
        rig.set_shoes(str(s.get("shoes", "hot pink")))
        self.buddy.quips = list(s.get("quips") or QUIPS)
        self.buddy.greetings = list(s.get("greetings") or GREETINGS)
        self.buddy.set_companion(bool(s.get("companion_bee", True)))
        self.paused = bool(s["paused"])

    def tick(self):
        if not self.paused:
            self.buddy.update(1 / 60)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame = QPainterPath()
        frame.addRoundedRect(QRectF(0, 0, PREVIEW_W, PREVIEW_H), 16, 16)
        p.setClipPath(frame)
        sky = QLinearGradient(0, 0, 0, PREVIEW_H)
        sky.setColorAt(0, QColor(70, 60, 140))
        sky.setColorAt(1, QColor(40, 110, 140))
        p.fillRect(self.rect(), sky)
        p.fillRect(QRectF(0, PREVIEW_H - 22, PREVIEW_W, 22), QColor(48, 120, 80))
        self.buddy.draw(p)
        if self.paused:
            p.fillRect(self.rect(), QColor(20, 16, 40, 150))
            p.setPen(QColor(255, 255, 255))
            f = QFont()
            f.setPixelSize(18)
            f.setBold(True)
            p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "paused")


class AskWorker(QThread):
    """Asks Claude off the UI thread."""
    done = pyqtSignal(object)

    def __init__(self, question, backend, model):
        super().__init__()
        self.question, self.backend, self.model = question, backend, model

    def run(self):
        self.done.emit(client.ask(self.question, self.backend, self.model))


class TranscribeWorker(QThread):
    """Runs Whisper on the test recording off the UI thread."""
    done = pyqtSignal(str, str)

    def __init__(self, wav, model):
        super().__init__()
        self.wav, self.model = wav, model

    def run(self):
        text, err = stt.transcribe(self.wav, self.model)
        try:
            os.remove(self.wav)
        except OSError:
            pass
        self.done.emit(text, err)


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Desktop Buddy")
        self.settings = SettingsFile(self)
        self.pending = {}
        self.write_timer = QTimer(self)
        self.write_timer.setSingleShot(True)
        self.write_timer.setInterval(150)
        self.write_timer.timeout.connect(self._flush)

        self.preview = Preview()
        title = QLabel("<b style='font-size:18px'>Desktop Buddy</b><br>"
                       "<span style='color:gray'>Changes apply right away.</span>")
        self.status = QLabel()
        self.run_btn = QPushButton()
        self.run_btn.clicked.connect(self._start_or_quit)
        side = QVBoxLayout()
        side.addWidget(title)
        side.addStretch(1)
        side.addWidget(self.status)
        side.addWidget(self.run_btn)
        header = QHBoxLayout()
        header.addWidget(self.preview)
        header.addLayout(side, 1)

        tabs = QTabWidget()
        self.tabs = tabs
        tabs.addTab(self._buddy_tab(), "Buddy")
        tabs.addTab(self._behavior_tab(), "Behavior")
        tabs.addTab(self._look_tab(), "Look")
        tabs.addTab(self._sayings_tab(), "Sayings")
        tabs.addTab(self._claude_tab(), "Claude")

        reset = QPushButton("Reset to defaults")
        reset.clicked.connect(lambda: self.settings.set(**DEFAULTS))
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(reset)

        root = QVBoxLayout(self)
        root.addLayout(header)
        root.addWidget(tabs)
        root.addLayout(footer)

        self.settings.changed.connect(self.sync)
        self.sync(self.settings.data)
        self.poll = QTimer(self)
        self.poll.timeout.connect(self._update_status)
        self.poll.start(1000)
        self._update_status()

    # the Buddy tab -------------------------------------------------------------
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

    # the Behavior tab ---------------------------------------------------------
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

    def _do_now(self, name):
        if self._send(name):
            self.do_status.setText("")
        elif name not in ("kroger", "vending", "perch"):
            self.preview.buddy.do_now(name)
            self.do_status.setText("The buddy isn't running, so the preview did it.")
        else:
            self.do_status.setText("Start the buddy to see that one; it needs the whole screen.")

    # the Look tab -------------------------------------------------------------
    def _look_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        shoes = QGroupBox("Shoes")
        row = QHBoxLayout(shoes)
        self.shoe_buttons = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for style in rig.SHOE_STYLES:
            b = QToolButton()
            b.setCheckable(True)
            b.setIcon(shoe_swatch(style))
            b.setIconSize(QSize(170, 104))
            b.setText(style)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.clicked.connect(lambda _, st=style: self._queue(shoes=st))
            group.addButton(b)
            row.addWidget(b)
            self.shoe_buttons[style] = b
        row.addStretch(1)
        outer.addWidget(shoes)
        outer.addWidget(self._hint("Chunky 2000s D3-style skate shoes. Hat, hoodie and other outfit "
                                   "options can be added here later."))
        outer.addStretch(1)
        return tab

    # the Sayings tab ----------------------------------------------------------
    def _sayings_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.addWidget(self._hint("Double-click a line to edit it. Keep them short; long ones wrap "
                                   "onto a second line in his bubble."))
        self.say_lists = {}
        for key, title, defaults, action in (("quips", "Random sayings", QUIPS, "quip"),
                                             ("greetings", "When he waves", GREETINGS, "wave")):
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

    # the Claude tab -----------------------------------------------------------
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

        self.out_loud = QCheckBox("Answer out loud in my voice (comes with voice out)")
        self.out_loud.setEnabled(False)
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

    # voice ------------------------------------------------------------------------
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

    def _set_hotkey(self):
        seq = self.hotkey.keySequence()
        if seq.isEmpty():
            self.hotkey_status.setText("Click the box, then press the key you want.")
            return
        kga = QDBusInterface("org.kde.kglobalaccel", "/kglobalaccel", "org.kde.KGlobalAccel",
                             QDBusConnection.sessionBus())
        key = seq[0].toCombined()
        hotkey = load("voice-in", "hotkey")
        ours = kga.call("shortcut", hotkey._action_id()).arguments()
        free = kga.call("isGlobalShortcutAvailable", key, "desktop-buddy").arguments()
        if free and not free[0] and not (ours and isinstance(ours[0], list) and key in ours[0]):
            self.hotkey_status.setText(f"{seq.toString()} is already used by another shortcut. Pick another.")
            return
        self._queue(voice_hotkey=seq.toString())
        self.hotkey_status.setText(f"Push to talk is now {seq.toString()}.")

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

    @staticmethod
    def _hint(text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: gray")
        return label

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

    def _size_moved(self, v):
        self.size_label.setText(f"{v / 100:.2f}×")
        self._queue(size=round(v / 100, 2))

    def _activity_moved(self, v):
        self._queue(activity=round(v / 100, 2))

    # saving and syncing ---------------------------------------------------------
    def _queue(self, **changes):
        if self._syncing:
            return
        self.pending.update(changes)
        preview = dict(self.settings.data)
        preview.update(self.pending)
        self.preview.apply(preview)
        self.write_timer.start()

    def _flush(self):
        if self.pending:
            changes, self.pending = self.pending, {}
            self.settings.set(**changes)

    _syncing = False

    def sync(self, s):
        self._syncing = True
        self.paused.setChecked(bool(s["paused"]))
        self.size.setValue(int(round(float(s["size"]) * 100)))
        self.size_label.setText(f"{float(s['size']):.2f}×")
        i = self.monitor.findData(s.get("monitor", "auto"))
        self.monitor.setCurrentIndex(max(0, i))
        self.activity.setValue(int(round(float(s["activity"]) * 100)))
        self.quiet.setChecked(bool(s["quiet"]))
        self.fullscreen.setChecked(bool(s.get("fullscreen_hide", True)))
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
        shoe = self.shoe_buttons.get(s.get("shoes", "hot pink"))
        if shoe:
            shoe.setChecked(True)
        for key, (lst, defaults) in self.say_lists.items():
            self._fill(key, list(s.get(key) or defaults))
        self.claude_on.setChecked(bool(s.get("claude_enabled")))
        (self.use_api if s.get("claude_backend") == "api" else self.use_cli).setChecked(True)
        self.model_box.setCurrentIndex(max(0, self.model_box.findData(s.get("claude_model"))))
        self.voice_on.setChecked(bool(s.get("voice_enabled", True)))
        self.hotkey.setKeySequence(QKeySequence(str(s.get("voice_hotkey") or "")))
        if self.mic.currentData() != s.get("voice_mic"):
            self._fill_mics(s.get("voice_mic"))
        self.stt_model.setCurrentIndex(max(0, self.stt_model.findData(s.get("whisper_model", stt.DEFAULT_MODEL))))
        self._refresh_stt_status()
        self.out_loud.setChecked(bool(s.get("voice_out_loud")))
        self._syncing = False
        self.preview.apply(s)

    # running or not -----------------------------------------------------------
    def _update_status(self):
        pid = buddy_pid()
        self.status.setText("● Buddy is running" if pid else "○ Buddy isn't running")
        self.status.setStyleSheet("color: #3fbf6f" if pid else "color: gray")
        self.run_btn.setText("Quit buddy" if pid else "Start buddy")

    def _start_or_quit(self):
        pid = buddy_pid()
        if pid:
            os.kill(pid, signal.SIGTERM)
        else:
            subprocess.Popen([sys.executable, os.path.join(ROOT, "overlay", "main.py")],
                             start_new_session=True)
        QTimer.singleShot(1200, self._update_status)

    def closeEvent(self, e):
        self._flush()
        super().closeEvent(e)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    app.setApplicationName("Desktop Buddy")
    app.setDesktopFileName("desktop-buddy")
    w = SettingsWindow()
    w.setWindowIcon(buddy_icon(128))
    w.resize(700, 700)
    if "--tab" in sys.argv[1:-1]:  # e.g. --tab claude
        want = sys.argv[sys.argv.index("--tab") + 1].lower()
        for i in range(w.tabs.count()):
            if w.tabs.tabText(i).lower() == want:
                w.tabs.setCurrentIndex(i)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
