"""Push-to-talk, start to finish: hold the key and talk, let go, Whisper turns
it into text on this computer, Claude (brain/) answers in his personality, and
he says it in his bubble (out loud too, once voice-out exists).

Publishes on the bus (see core/README.md):
  voice.listening  True when the key goes down, False when it comes up
  voice.thinking   the transcript, while Claude works on an answer
  voice.reply_part one finished sentence of the answer while Claude is still writing it (str)
  voice.reply      {"text", "error", "heard"}: his answer, or why there isn't one
  voice.cancel     a tap too short to be speech
"""
import os
import shutil
import subprocess

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QImage

from brain import client
from brain.session import session
from core.load import load

hotkey = load("voice-in", "hotkey")
recorder = load("voice-in", "recorder")
stt = load("voice-in", "stt")

SHOT_DIR = os.path.expanduser("~/.cache/desktop-buddy")
SHOT_EDGE = 1568  # longest side sent to Claude
MIN_SECONDS = 0.4
MAX_SECONDS = 45  # a stuck key (or a lost release) never leaves the mic on


def _remove(path):
    if path:
        try:
            os.remove(path)
        except OSError:
            pass


class _Work(QThread):
    heard = pyqtSignal(str)
    part = pyqtSignal(str)   # one finished sentence of the answer, while Claude is still writing
    done = pyqtSignal(object)

    def __init__(self, wav, settings, shot=None):
        super().__init__()
        self.wav, self.s, self.shot = wav, settings, shot  # shot: (spectacle process, png path) or None

    def _prepare_shot(self):
        """Wait for the screenshot, shrink it to a JPEG, delete the original. Returns the path or None."""
        proc, png = self.shot
        jpg = png[:-4] + ".jpg"
        try:
            proc.wait(timeout=10)
            img = QImage(png)
            if img.isNull():
                return None
            if max(img.width(), img.height()) > SHOT_EDGE:
                img = img.scaled(SHOT_EDGE, SHOT_EDGE, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
            return jpg if img.save(jpg, "JPG", 85) else None
        except (OSError, subprocess.TimeoutExpired):
            return None
        finally:
            _remove(png)

    def run(self):
        text, err = stt.transcribe(self.wav, self.s.get("whisper_model") or stt.DEFAULT_MODEL)
        _remove(self.wav)  # the recording is gone as soon as it's text
        if err:
            self.done.emit({"error": err})
            return
        if not text:
            self.done.emit({"error": "Huh? I didn't catch that."})
            return
        self.heard.emit(text)
        image = self._prepare_shot() if self.shot else None
        if self.shot and not image and self.s.get("claude_enabled"):
            self.done.emit({"heard": text, "error": "I couldn't grab a screenshot (is spectacle installed?)."})
            return
        if not self.s.get("claude_enabled"):
            self.done.emit({"heard": text, "error": "Turn on \"Let him answer with Claude\" in "
                                                    "Settings > Claude and I'll answer you."})
            return
        try:
            reply = None
            if not image and self.s.get("claude_backend", "claude-code") == "claude-code":
                reply = session.ask(text, self.part.emit)   # the warm process, answering in a stream
            if reply is None:   # no warm process (or a screenshot, or the API): the one-shot way
                reply = client.ask(text, self.s.get("claude_backend", "claude-code"),
                                   self.s.get("claude_model", client.DEFAULT_MODEL), image=image)
        finally:
            _remove(image)  # the screenshot is gone as soon as he's looked at it
        self.done.emit({"heard": text, "text": reply.text, "error": reply.error})


class VoiceIn(QObject):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus
        self.settings = {}
        self.work = None
        self.rec = recorder.Recorder()
        self.rec.discard()  # a recording left behind if the buddy was ever killed hard
        self.shot = None      # (spectacle process, png path) while a screen hotkey press is in flight
        self.ptt = hotkey.PushToTalk(self)
        self.ptt.pressed.connect(self._down)
        self.ptt.released.connect(self._up)
        self.screen = hotkey.PushToTalk(self, hotkey.SCREEN_ACTION, hotkey.SCREEN_LABEL)
        self.screen.pressed.connect(lambda: self._down(screen=True))
        self.screen.released.connect(self._up)
        self.limit = QTimer(self)
        self.limit.setSingleShot(True)
        self.limit.timeout.connect(self._timeout)

    def shutdown(self):
        """Quitting: stop any recording and throw it away."""
        self.limit.stop()
        self.rec.stop()
        self.rec.discard()
        self._drop_shot()
        session.stop()

    def _warm_claude(self):
        """Keep a Claude process ready so the answer doesn't wait for it to start (main thread)."""
        s = self.settings
        if s.get("claude_enabled") and s.get("claude_backend", "claude-code") == "claude-code":
            session.warm(s.get("claude_model", client.DEFAULT_MODEL))

    def _timeout(self):
        self.ptt.down = self.screen.down = False
        self._up()

    def apply(self, s):
        self.settings = dict(s)
        if s.get("voice_enabled", True):
            err = self.ptt.set_key(s.get("voice_hotkey") or "Meta+Space")
            if err:
                print("push-to-talk:", err)
            err = self.screen.set_key(s.get("screen_hotkey") or "")
            if err:
                print("look-at-screen:", err)
        else:
            self.ptt.clear()
            self.screen.clear()
        self.rec.target = s.get("voice_mic") or None
        self._warm_claude()

    def busy(self):
        return self.work is not None and self.work.isRunning()

    def _down(self, screen=False):
        if self.busy() or self.rec.proc is not None:
            return
        if not recorder.Recorder.available():
            self.bus.publish("voice.reply", {"error": "I can't record: pw-record (PipeWire) is missing."})
            return
        self.shot = self._grab() if screen else None
        self._warm_claude()
        self.rec.start()
        self.limit.start(MAX_SECONDS * 1000)
        self.bus.publish("voice.listening", True)

    def _grab(self):
        """Screenshot at the moment of the press (only here and only for the screen hotkey)."""
        if not shutil.which("spectacle"):
            return None
        os.makedirs(SHOT_DIR, exist_ok=True)
        png = os.path.join(SHOT_DIR, "screen.png")
        _remove(png)
        proc = subprocess.Popen(["spectacle", "-b", "-n", "-f", "-o", png],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return proc, png

    def _drop_shot(self):
        if self.shot:
            self.shot[0].kill()
            _remove(self.shot[1])
            self.shot = None

    def _up(self):
        self.limit.stop()
        if self.rec.proc is None:
            return
        secs = self.rec.stop()
        self.bus.publish("voice.listening", False)
        if self.rec.error:
            self._drop_shot()
            self.bus.publish("voice.reply", {"error": self.rec.error})
            return
        if secs < MIN_SECONDS:
            self._drop_shot()
            self.rec.discard()
            self.bus.publish("voice.cancel", None)
            return
        self.work = _Work(self.rec.path, self.settings, self.shot)
        self.shot = None
        self.work.heard.connect(lambda text: self.bus.publish("voice.thinking", text))
        self.work.part.connect(lambda text: self.bus.publish("voice.reply_part", text))
        self.work.done.connect(lambda r: self.bus.publish("voice.reply", r))
        self.work.start()
