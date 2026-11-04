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
            if self.isInterruptionRequested():
                return
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
        self.fetches = set()   # running fetch threads: Qt aborts if one is garbage-collected mid-run
        self.player = None
        self.levels, self.t0 = [], 0.0
        self.gen = 0         # which answer this is; results of an older one are dropped
        self._reset()
        bus.subscribe("voice.reply_part", self._on_part)
        bus.subscribe("voice.reply", self._on_reply)
        bus.subscribe("voice.listening", self._on_listening)
        bus.subscribe("attention.mood", lambda m: setattr(self, "mood", float(m)))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def _reset(self):
        self.streaming = False   # an answer is being spoken (sentences may still be arriving)
        self.complete = False    # all of its sentences are here
        self.reply = None        # the final voice.reply, once it arrives
        self.parts, self.buf = [], ""   # sentences to speak, and a short one waiting for company
        self.idx = 0             # how many parts have been requested
        self.in_flight = False
        self.ready = []          # generated (wav path, characters) waiting to be played
        self.rate = None         # seconds of audio per character, from the first sentence
        self.said = False        # voice.say already published
        self.speaking = False
        self.skip = False        # this answer isn't spoken (call, off): leave it to voice.reply
        self.mood_name = "normal"

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
        for fetch in list(self.fetches):   # let them end before Qt tears down
            fetch.requestInterruption()
            fetch.wait(3000)
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

    def _on_listening(self, down):
        if down:
            self.stop_playback()   # you started talking: he stops
            self._warm_up()

    def _can_speak(self):
        return self.on and installed() and not on_a_call()

    # the answer arrives: sentence by sentence, then whole --------------------------------
    def _begin(self, first_text):
        self.stop_playback()
        self._reset()
        self.streaming = True
        self.mood_name = self._mood_name(first_text)
        self._warm_up()

    def _on_part(self, text):
        if self.skip:
            return
        if self.streaming and self.complete:   # a new answer while the old one is still playing
            self.stop_playback()
        if not self.streaming:
            if not self._can_speak():
                self.skip = True
                return
            self._begin(text)
        self.buf = f"{self.buf} {text}".strip()
        if len(self.buf) >= MIN_CHUNK // 2:   # a very short sentence waits for the next one
            self.parts.append(self.buf)
            self.buf = ""
            self._kick()

    def _on_reply(self, reply):
        reply = reply or {}
        text = reply.get("text")
        skipped, self.skip = self.skip, False
        if self.streaming and self.complete:   # not the end of the answer being spoken: a new one
            self.stop_playback()
        if not self.streaming and (skipped or not (self._can_speak() and text and not reply.get("error"))):
            self.bus.publish("voice.say", reply)   # nothing to speak: show it now
            return
        if not self.streaming:   # a whole answer with no parts before it (the API, or a screenshot)
            self._begin(text)
            self.parts = split_sentences(text)
        if reply.get("error") or not text:
            self.stop_playback()
            self.bus.publish("voice.say", reply)
            return
        if self.buf:
            self.parts.append(self.buf)
            self.buf = ""
        self.reply, self.complete = reply, True
        self._kick()
        self._maybe_say()
        if not (self.speaking or self.ready or self.in_flight) and self.idx >= len(self.parts):
            if not self.said:
                self.bus.publish("voice.say", reply)
            self.stop_playback()   # everything was already spoken before the final text arrived

    def _kick(self):
        """Ask the voice server for the next sentence, one at a time, while the last one plays."""
        if self.in_flight or self.idx >= len(self.parts):
            return
        self.in_flight = True
        part = self.parts[self.idx]
        fetch = _Fetch(part, self.mood_name, OUT.format(f"{self.gen}_{self.idx}"), self.gen)
        self.idx += 1
        fetch.done.connect(lambda result, gen, n=len(part): self._fetched(result, gen, n))
        self.fetches.add(fetch)
        fetch.finished.connect(lambda f=fetch: self.fetches.discard(f))
        fetch.start()

    def _fetched(self, result, gen, chars):
        if gen != self.gen or not self.streaming:
            return   # an answer that was cancelled
        self.in_flight = False
        if not os.path.exists(str(result)):   # an error string
            print("voice-out:", result)
            if not self.said and self.reply:
                self.bus.publish("voice.say", self.reply)   # text only
            self.stop_playback()
            return
        self.ready.append((result, chars))
        self._kick()   # keep generating while this plays
        if not self.speaking:
            self._play_next()

    def _maybe_say(self):
        """Show the answer once there's sound for it and we know the whole text."""
        if self.said or not self.reply or self.rate is None:
            return
        self.said = True
        self.bus.publish("voice.say", dict(self.reply, seconds=self.rate * len(self.reply["text"]) + 0.5))

    def _play_next(self):
        if not self.ready:
            return
        path, chars = self.ready.pop(0)
        try:
            self.levels, seconds = envelope(path)
        except (OSError, wave.Error, EOFError):
            self.levels, seconds = [], 0.0
        if self.rate is None and chars:
            self.rate = seconds / chars
            self._maybe_say()
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
        elif self.complete and self.idx >= len(self.parts) and not self.in_flight:   # that was the last one
            self.stop_playback()
        else:
            self.speaking = False   # the next sentence isn't ready yet; _fetched will start it
            self.timer.stop()

    def stop_playback(self):
        self.gen += 1   # anything still being generated is dropped
        self.timer.stop()
        if self.player and self.player.poll() is None:
            self.player.kill()
        self.player = None
        was_speaking = self.speaking or bool(self.levels)
        self._reset()
        self.levels = []
        if was_speaking:
            self.bus.publish("voice.mouth", None)
        for path in glob.glob(OUT.format("*")):
            try:
                os.remove(path)
            except OSError:
                pass
