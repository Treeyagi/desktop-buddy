"""Push-to-talk, start to finish: hold the key and talk, let go, Whisper turns
it into text on this computer, Claude (brain/) answers in his personality, and
he says it in his bubble (out loud too, once voice-out exists).

Publishes on the bus (see core/README.md):
  voice.listening  True when the key goes down, False when it comes up
  voice.thinking   the transcript, while Claude works on an answer
  voice.reply      {"text", "error", "heard"}: his answer, or why there isn't one
  voice.cancel     a tap too short to be speech
"""
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from brain import client
from core.load import load

hotkey = load("voice-in", "hotkey")
recorder = load("voice-in", "recorder")
stt = load("voice-in", "stt")

MIN_SECONDS = 0.4
MAX_SECONDS = 45  # a stuck key (or a lost release) never leaves the mic on


class _Work(QThread):
    heard = pyqtSignal(str)
    done = pyqtSignal(object)

    def __init__(self, wav, settings):
        super().__init__()
        self.wav, self.s = wav, settings

    def run(self):
        text, err = stt.transcribe(self.wav, self.s.get("whisper_model") or stt.DEFAULT_MODEL)
        try:
            import os
            os.remove(self.wav)  # the recording is gone as soon as it's text
        except OSError:
            pass
        if err:
            self.done.emit({"error": err})
            return
        if not text:
            self.done.emit({"error": "Huh? I didn't catch that."})
            return
        self.heard.emit(text)
        if not self.s.get("claude_enabled"):
            self.done.emit({"heard": text, "error": "Turn on \"Let him answer with Claude\" in "
                                                    "Settings > Claude and I'll answer you."})
            return
        reply = client.ask(text, self.s.get("claude_backend", "claude-code"),
                           self.s.get("claude_model", client.DEFAULT_MODEL))
        self.done.emit({"heard": text, "text": reply.text, "error": reply.error})


class VoiceIn(QObject):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus
        self.settings = {}
        self.work = None
        self.rec = recorder.Recorder()
        self.rec.discard()  # a recording left behind if the buddy was ever killed hard
        self.ptt = hotkey.PushToTalk(self)
        self.ptt.pressed.connect(self._down)
        self.ptt.released.connect(self._up)
        self.limit = QTimer(self)
        self.limit.setSingleShot(True)
        self.limit.timeout.connect(self._timeout)

    def shutdown(self):
        """Quitting: stop any recording and throw it away."""
        self.limit.stop()
        self.rec.stop()
        self.rec.discard()

    def _timeout(self):
        self.ptt.down = False
        self._up()

    def apply(self, s):
        self.settings = dict(s)
        if s.get("voice_enabled", True):
            err = self.ptt.set_key(s.get("voice_hotkey") or "Meta+Space")
            if err:
                print("push-to-talk:", err)
        else:
            self.ptt.clear()
        self.rec.target = s.get("voice_mic") or None

    def busy(self):
        return self.work is not None and self.work.isRunning()

    def _down(self):
        if self.busy():
            return
        if not recorder.Recorder.available():
            self.bus.publish("voice.reply", {"error": "I can't record: pw-record (PipeWire) is missing."})
            return
        self.rec.start()
        self.limit.start(MAX_SECONDS * 1000)
        self.bus.publish("voice.listening", True)

    def _up(self):
        self.limit.stop()
        if self.rec.proc is None:
            return
        secs = self.rec.stop()
        self.bus.publish("voice.listening", False)
        if self.rec.error:
            self.bus.publish("voice.reply", {"error": self.rec.error})
            return
        if secs < MIN_SECONDS:
            self.rec.discard()
            self.bus.publish("voice.cancel", None)
            return
        self.work = _Work(self.rec.path, self.settings)
        self.work.heard.connect(lambda text: self.bus.publish("voice.thinking", text))
        self.work.done.connect(lambda r: self.bus.publish("voice.reply", r))
        self.work.start()
