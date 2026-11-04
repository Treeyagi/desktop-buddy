"""Quiet humming while he walks (sound is OFF by default: the `hum_sound` setting. The synth tone sounded
robotic, so for now he only hums in a text bubble). Original little house-style melodies (124 BPM, A minor pentatonic,
off-beat notes) made from scratch with a soft vibrato "mm" tone, so there are no real songs or
samples in here. Played very quietly, never during a call.

Listens to (see core/README.md):  buddy.hum  True when a happy walk starts, False when it ends
"""
import array
import math
import os
import random
import subprocess
import wave

from PyQt6.QtCore import QObject

RATE = 22050
BPM = 124
SCALE = [57, 60, 62, 64, 67, 69, 72]   # A minor pentatonic, MIDI numbers
DIR = os.path.expanduser("~/.cache/desktop-buddy")
PHRASES = 6
VOLUME = 0.12   # pw-play volume: a hum under his breath


def _tone(freq, seconds, rng):
    """One hummed note: a soft sine with a little 2nd and 3rd harmonic, vibrato, gentle attack and release."""
    n = int(RATE * seconds)
    out = array.array("f", [0.0] * n)
    phase = 0.0
    vib = rng.uniform(5.0, 6.0)
    for i in range(n):
        t = i / RATE
        f = freq * (1 + 0.004 * math.sin(2 * math.pi * vib * t) * min(1.0, t / 0.15))
        phase += 2 * math.pi * f / RATE
        env = min(1.0, t / 0.04) * min(1.0, (seconds - t) / 0.08) * (0.75 + 0.25 * math.exp(-t * 6))
        out[i] = env * (math.sin(phase) + 0.45 * math.sin(2 * phase) + 0.2 * math.sin(3 * phase))
    return out


def make_phrase(seed):
    """Two bars of eighth-note slots; about six of them hold a note, favoring the off-beats."""
    rng = random.Random(seed)
    eighth = 60.0 / BPM / 2
    slots = 16
    audio = array.array("f", [0.0] * int(RATE * eighth * slots))
    idx = rng.randrange(len(SCALE))
    pos = 0
    while pos < slots:
        length = rng.choice([1, 1, 2, 2, 3])
        rest = pos % 2 == 0 and rng.random() < 0.45   # the on-beats are often left empty: that's the groove
        if not rest:
            idx = max(0, min(len(SCALE) - 1, idx + rng.choice([-2, -1, -1, 0, 1, 1, 2])))
            note = _tone(440.0 * 2 ** ((SCALE[idx] - 69 - 12) / 12), eighth * length * 0.9, rng)
            start = int(RATE * eighth * pos)
            for i, v in enumerate(note):
                if start + i < len(audio):
                    audio[start + i] += v
        pos += length
    peak = max(max(audio), -min(audio)) or 1.0
    return array.array("h", [int(v / peak * 0.8 * 32767) for v in audio])


def path(i):
    return os.path.join(DIR, f"hum{i}.wav")


def ensure_phrases():
    os.makedirs(DIR, exist_ok=True)
    for i in range(PHRASES):
        if not os.path.exists(path(i)):
            with wave.open(path(i), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes(make_phrase(1990 + i).tobytes())


class Hummer(QObject):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.on = True
        self.player = None
        bus.subscribe("buddy.hum", self._hum)

    def apply(self, s):
        self.on = bool(s.get("hum_enabled", True)) and bool(s.get("hum_sound", False)) and not s.get("quiet")
        if not self.on:
            self.stop()

    def _hum(self, going):
        if not going or not self.on or (self.player and self.player.poll() is None):
            return   # a phrase already playing finishes by itself
        from core.load import load
        if load("voice-out", "speak").on_a_call():
            return
        ensure_phrases()
        self.player = subprocess.Popen(["pw-play", f"--volume={VOLUME}", path(random.randrange(PHRASES))],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        if self.player and self.player.poll() is None:
            self.player.kill()
        self.player = None
