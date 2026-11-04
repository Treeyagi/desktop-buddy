"""Says his answers out loud in the user's cloned voice.

Sits between voice-in and the character: it hears `voice.reply`, asks the local voice server
(server.py, Chatterbox) for audio, plays it, and publishes `voice.say` when the sound is ready so he
starts the answer (bubble and mouth) together with the audio. If voice is off, there's no server, or
you're on a call, `voice.say` goes out at once with no sound.

Publishes on the bus (see core/README.md):
  voice.say    {"text", "error", "heard", "seconds"}: show the answer now ("seconds" > 0 means audio plays)
  voice.mouth  float 0..1 about 30 times a second while it plays, then None
"""
import array
import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
import wave

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

ROOT = os.path.expanduser("~/.local/share/desktop-buddy/tts")
PYTHON = os.path.join(ROOT, ".venv", "bin", "python")
SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
URL = "http://127.0.0.1:8765"
OUT = os.path.expanduser("~/.cache/desktop-buddy/speech.wav")
FPS = 30
LOAD_SECONDS = 180   # waiting for the model to load into the GPU
SPEAK_SECONDS = 120


def installed():
    return os.path.exists(PYTHON)


def _get(path, timeout=2):
    try:
        with urllib.request.urlopen(URL + path, timeout=timeout) as r:
            return r.read().decode()
    except (OSError, urllib.error.URLError):
        return None


def server_state():
    """'ok' (ready), 'loading', or None (not running)."""
    return _get("/health")


def stop_server():
    try:
        urllib.request.urlopen(urllib.request.Request(URL + "/quit", data=b"", method="POST"), timeout=2)
    except (OSError, urllib.error.URLError):
        pass


def start_server():
    """Start the voice server tied to this process: if the buddy dies, so does it (frees the GPU)."""
    def tie():
        import ctypes
        ctypes.CDLL("libc.so.6").prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
    return subprocess.Popen([PYTHON, SERVER], preexec_fn=tie, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=False)


def on_a_call():
    """Another app is using the microphone right now (a call): stay quiet."""
    try:
        out = subprocess.run(["pactl", "-f", "json", "list", "source-outputs"], capture_output=True,
                             text=True, timeout=2)
        for s in json.loads(out.stdout):
            name = (s.get("properties") or {}).get("application.name", "")
            if not s.get("corked") and name not in ("pw-record", "ALSA plugin [pw-record]"):
                return True
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return False


def envelope(path):
    """Mouth opening, 0..1, per 1/FPS second of the recording."""
    with wave.open(path, "rb") as w:
        rate, frames = w.getframerate(), w.readframes(w.getnframes())
    samples = array.array("h", frames)
    step = max(1, rate // FPS)
    rms = []
    for i in range(0, len(samples), step):
        chunk = samples[i:i + step]
        rms.append((sum(x * x for x in chunk) / max(1, len(chunk))) ** 0.5)
    loud = sorted(rms)[int(len(rms) * 0.95)] if rms else 1.0
    return [min(1.0, (r / max(loud, 1.0)) ** 0.8) for r in rms], len(samples) / rate


class _Fetch(QThread):
    done = pyqtSignal(object)  # path of the wav, or an error string

    def __init__(self, text, mood):
        super().__init__()
        self.text, self.mood = text, mood

    def run(self):
        deadline = time.monotonic() + LOAD_SECONDS
        while server_state() != "ok":
            if time.monotonic() > deadline:
                self.done.emit("The voice server didn't start. Try `python3 tools/shutdown.py` and talk again.")
                return
            time.sleep(0.5)
        body = json.dumps({"text": self.text, "mood": self.mood}).encode()
        try:
            req = urllib.request.Request(URL + "/speak", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=SPEAK_SECONDS) as r:
                os.makedirs(os.path.dirname(OUT), exist_ok=True)
                with open(OUT, "wb") as f:
                    f.write(r.read())
        except urllib.error.HTTPError as e:
            self.done.emit(f"Voice error: {e.read().decode()[:200]}")
            return
        except (OSError, urllib.error.URLError) as e:
            self.done.emit(f"Voice error: {e}")
            return
        self.done.emit(OUT)


class Speaker(QObject):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus
        self.on = False
        self.mood = 0.2
        self.server = None   # the process we started
        self.fetch = None
        self.player = None
        self.levels, self.t0 = [], 0.0
        self.pending = None
        bus.subscribe("voice.reply", self._on_reply)
        bus.subscribe("voice.listening", lambda down: down and self._warm_up())
        bus.subscribe("attention.mood", lambda m: setattr(self, "mood", float(m)))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def apply(self, s):
        self.on = bool(s.get("voice_out_loud", True)) and bool(s.get("claude_enabled"))
        if not self.on:
            self.stop_playback()

    def shutdown(self):
        """Quitting: stop the sound and the voice server (frees the GPU)."""
        self.stop_playback()
        if self.server and self.server.poll() is None:
            stop_server()
            try:
                self.server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server.kill()

    def _warm_up(self):
        """Start loading the voice while you're still talking, so the answer isn't kept waiting."""
        if self.on and installed() and server_state() is None and not (self.server and self.server.poll() is None):
            self.server = start_server()

    def _mood_name(self, text):
        if self.mood < -0.3:
            return "annoyed"
        if self.mood > 0.6 or text.count("!") >= 2:
            return "excited"
        if self.mood > 0.35 and len(text) < 60:
            return "chill" if "..." in text else "normal"
        return "normal"

    def _on_reply(self, reply):
        reply = reply or {}
        text = reply.get("text")
        if not (self.on and text and not reply.get("error")) or not installed() or on_a_call():
            self.bus.publish("voice.say", reply)
            return
        self.stop_playback()
        self.pending = reply
        self._warm_up()   # from this (main) thread, so PDEATHSIG tracks the buddy
        self.fetch = _Fetch(text, self._mood_name(text))
        self.fetch.done.connect(self._ready)
        self.fetch.start()

    def _ready(self, result):
        reply, self.pending = self.pending, None
        if not reply:
            return
        if not os.path.exists(str(result)):  # an error string
            print("voice-out:", result)
            self.bus.publish("voice.say", reply)  # text only
            return
        try:
            self.levels, seconds = envelope(result)
        except (OSError, wave.Error, EOFError):
            self.bus.publish("voice.say", reply)
            return
        self.bus.publish("voice.say", dict(reply, seconds=seconds))
        self.player = subprocess.Popen(["pw-play", result], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.t0 = time.monotonic()
        self.timer.start(1000 // FPS)

    def _tick(self):
        i = int((time.monotonic() - self.t0) * FPS)
        if i >= len(self.levels) or (self.player and self.player.poll() is not None):
            self.stop_playback()
            return
        self.bus.publish("voice.mouth", self.levels[i])

    def stop_playback(self):
        self.timer.stop()
        if self.player and self.player.poll() is None:
            self.player.kill()
        self.player = None
        if self.levels:
            self.levels = []
            self.bus.publish("voice.mouth", None)
        try:
            os.remove(OUT)
        except OSError:
            pass
