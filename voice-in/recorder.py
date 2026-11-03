"""Records the microphone while push-to-talk is held, with PipeWire's
pw-record, as 16 kHz mono WAV (what Whisper wants). The file is overwritten
each time and only kept until it's been transcribed. Uses the system's default
mic unless a specific one is picked in settings."""
import ctypes
import json
import os
import shutil
import signal
import subprocess
import time

PATH = os.path.expanduser("~/.cache/desktop-buddy/ptt.wav")
PR_SET_PDEATHSIG = 1


def _die_with_parent():
    """Runs in the pw-record child: if the buddy goes away for any reason (quit,
    crash, kill), the kernel stops the recording too."""
    ctypes.CDLL("libc.so.6", use_errno=True).prctl(PR_SET_PDEATHSIG, signal.SIGINT)


class Recorder:
    def __init__(self, path=PATH):
        self.path = path
        self.proc = None
        self.started = 0.0
        self.target = None   # a PipeWire source name, or None for the default mic
        self.error = ""

    @staticmethod
    def available():
        return shutil.which("pw-record") is not None

    def start(self):
        self.stop()
        self.error = ""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        cmd = ["pw-record", "--rate", "16000", "--channels", "1", "--format", "s16"]
        if self.target:
            cmd += ["--target", self.target]
        self.proc = subprocess.Popen(cmd + [self.path], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, preexec_fn=_die_with_parent)
        self.started = time.monotonic()

    def stop(self):
        """Stop recording; returns how many seconds were recorded (0 if nothing was)."""
        if not self.proc:
            return 0.0
        secs = time.monotonic() - self.started
        if self.proc.poll() is not None and self.proc.returncode != 0:  # it never got going
            self.proc = None
            self.error = "I can't find your microphone. Is your headset on?"
            return 0.0
        self.proc.send_signal(signal.SIGINT)  # lets pw-record finish the WAV header
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None
        return secs

    def discard(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


def microphones():
    """[(source name, friendly description)] for the mics PipeWire knows about."""
    try:
        out = subprocess.run(["pactl", "-f", "json", "list", "sources"], capture_output=True,
                             text=True, timeout=5)
        sources = json.loads(out.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []
    return [(src.get("name", ""), src.get("description") or src.get("name", ""))
            for src in sources
            if not src.get("name", "").endswith(".monitor")]
