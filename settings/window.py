"""Desktop Buddy settings window.

Runs as its own little program, because the overlay turns every window in its
process into a layer-shell surface. Open it from the tray icon, or run:

    python3 settings/window.py

Every change is written to ~/.config/desktop-buddy/settings.json right away,
and the running buddy picks it up live. The window also follows changes made
elsewhere (the tray's Pause and Quiet mode).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.pop("QT_WAYLAND_SHELL_INTEGRATION", None)  # a normal window, not a desktop layer

from settings.tabs.common import *  # noqa: E402,F401,F403  (Qt, helpers, shared modules)
from settings.tabs.behavior import BehaviorTab  # noqa: E402
from settings.tabs.buddy import BuddyTab  # noqa: E402
from settings.tabs.claude import ClaudeTab  # noqa: E402
from settings.tabs.look import LookTab  # noqa: E402
from settings.tabs.my_voice import MyVoiceTab  # noqa: E402
from settings.tabs.sayings import SayingsTab  # noqa: E402

PREVIEW_W, PREVIEW_H = 320, 240

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
        self.buddy.tangents = list(s.get("tangents") or TANGENTS)
        self.buddy.moments = list(s.get("moments") or []) or None
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


class SettingsWindow(BuddyTab, BehaviorTab, LookTab, SayingsTab, ClaudeTab, MyVoiceTab, QWidget):
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
        tabs.addTab(self._my_voice_tab(), "My voice")

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

    @staticmethod
    def _hint(text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: gray")
        return label


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
        for tab in ("buddy", "behavior", "look", "sayings", "claude"):
            getattr(self, "_sync_" + tab)(s)
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
        if self.recording_mood:  # never leave the mic on, or keep a half-finished take
            self.studio_timer.stop()
            self.studio_rec.stop()
            self.studio_rec.discard()
            self.recording_mood = None
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
