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
import glob
import json
import os
import re
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
OUT = os.path.expanduser("~/.cache/desktop-buddy/speech{}.wav")
FPS = 30
LOAD_SECONDS = 180   # waiting for the model to load into the GPU
SPEAK_SECONDS = 120


MIN_CHUNK = 45   # sentences shorter than this are joined, so the voice doesn't sound choppy


def split_sentences(text):
    parts, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        cur = f"{cur} {sentence}".strip()
        if len(cur) >= MIN_CHUNK:
            parts.append(cur)
            cur = ""
    if cur:
        if parts and len(cur) < 20:
            parts[-1] += " " + cur
        else:
            parts.append(cur)
    return parts


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
    done = pyqtSignal(object, int)  # path of the wav (or an error string), and which request this was

    def __init__(self, text, mood, path, gen):
        super().__init__()
        self.text, self.mood, self.path, self.gen = text, mood, path, gen

    def run(self):
        deadline = time.monotonic() + LOAD_SECONDS
        while server_state() != "ok":
            if time.monotonic() > deadline:
                self.done.emit("The voice server didn't start. Try `python3 tools/shutdown.py` and talk again.", self.gen)
                return
            time.sleep(0.5)
        body = json.dumps({"text": self.text, "mood": self.mood}).encode()
        try:
            req = urllib.request.Request(URL + "/speak", data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=SPEAK_SECONDS) as r:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, "wb") as f:
                    f.write(r.read())
        except urllib.error.HTTPError as e:
            self.done.emit(f"Voice error: {e.read().decode()[:200]}", self.gen)
            return
        except (OSError, urllib.error.URLError) as e:
            self.done.emit(f"Voice error: {e}", self.gen)
            return
        self.done.emit(self.path, self.gen)


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
        self.reply = None    # the answer being spoken
        self.parts, self.idx, self.gen = [], 0, 0   # its sentences, how many are generated, request number
        self.ready = []      # generated wavs waiting to be played
        self.said = False    # voice.say already published for this answer
        self.speaking = False
        self.mood_name = "normal"
        bus.subscribe("voice.reply", self._on_reply)
        bus.subscribe("voice.listening", lambda down: down and self._warm_up())
        bus.subscribe("attention.mood", lambda m: setattr(self, "mood", float(m)))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def apply(self, s):
        was = self.on
        self.on = bool(s.get("voice_out_loud", True)) and bool(s.get("claude_enabled"))
        if not self.on:
            self.stop_playback()
        elif not was:
            self._warm_up()   # load the voice now so the first answer isn't kept waiting

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
        """Start loading the voice ahead of time (at start, and when you press the talk key)."""
        if self.on and installed() and server_state() is None and not (self.server and self.server.poll() is None):
            self.server = start_server()   # from the main thread, so PDEATHSIG tracks the buddy

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
        self.reply, self.parts, self.idx, self.said = reply, split_sentences(text), 0, False
        self.mood_name = self._mood_name(text)
        self._warm_up()
        self._fetch_next()

    def _fetch_next(self):
        if self.idx >= len(self.parts):
            return
        self.fetch = _Fetch(self.parts[self.idx], self.mood_name, OUT.format(self.idx), self.gen)
        self.fetch.done.connect(self._fetched)
        self.fetch.start()

    def _fetched(self, result, gen):
        if gen != self.gen or not self.reply:
            return   # an answer that was cancelled
        if not os.path.exists(str(result)):   # an error string
            print("voice-out:", result)
            if not self.said:
                self.bus.publish("voice.say", self.reply)   # text only
            self.reply = None
            return
        self.idx += 1
        self.ready.append(result)
        self._fetch_next()   # keep generating while this plays
        if not self.speaking:
            self._play_next()

    def _play_next(self):
        if not self.ready:
            return
        path = self.ready.pop(0)
        try:
            self.levels, seconds = envelope(path)
        except (OSError, wave.Error, EOFError):
            self.levels, seconds = [], 0.0
        if not self.said:   # the first sentence is ready: show the answer, with a guess at the full length
            self.said = True
            share = max(1, len(self.parts[0])) / max(1, sum(len(p) for p in self.parts))
            self.bus.publish("voice.say", dict(self.reply, seconds=seconds / share + 0.5))
        self.speaking = True
        self.player = subprocess.Popen(["pw-play", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.t0 = time.monotonic()
        self.timer.start(1000 // FPS)

    def _tick(self):
        i = int((time.monotonic() - self.t0) * FPS)
        if self.player and self.player.poll() is None and i < len(self.levels):
            self.bus.publish("voice.mouth", self.levels[i])
            return
        self.player, self.levels = None, []
        self.bus.publish("voice.mouth", 0.0)
        if self.ready:
            self._play_next()
        elif self.idx >= len(self.parts):   # that was the last sentence
            self.stop_playback()
        else:
            self.speaking = False   # the next sentence isn't ready yet; _fetched will start it

    def stop_playback(self):
        self.gen += 1   # anything still being generated is dropped
        self.timer.stop()
        if self.player and self.player.poll() is None:
            self.player.kill()
        self.player = None
        was_speaking = self.speaking or bool(self.levels)
        self.speaking, self.levels, self.ready, self.reply = False, [], [], None
        if was_speaking:
            self.bus.publish("voice.mouth", None)
        for path in glob.glob(OUT.format("*")):
            try:
                os.remove(path)
            except OSError:
                pass
