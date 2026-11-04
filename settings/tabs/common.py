"""Imports and small helpers shared by the settings tabs."""
import json
import os
import signal
import subprocess
import sys
import time

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (QColor, QDesktopServices, QFont, QIcon, QLinearGradient, QPainter,
                         QPainterPath, QPixmap)
from PyQt6.QtDBus import QDBusConnection, QDBusInterface
from PyQt6.QtGui import QKeySequence
from PyQt6.QtNetwork import QLocalSocket, QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox,
                             QComboBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QKeySequenceEdit, QLineEdit, QListWidget, QListWidgetItem,
                             QProgressBar, QPushButton, QRadioButton, QScrollArea, QSlider, QSpinBox,
                             QTabWidget, QToolButton, QVBoxLayout, QWidget)

from brain import client, keychain
import character.rig as rig
from character.adhd import TANGENTS
from character.moments import MOMENTS
from character.behavior import GREETINGS, QUIPS, Buddy
from core.load import load
from settings import autostart

stt = load("voice-in", "stt")
samples = load("voice-out", "samples")
from settings.store import DEFAULTS, PID_PATH, SOCKET, SettingsFile
from settings.tray import buddy_icon

recorder = load("voice-in", "recorder")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
