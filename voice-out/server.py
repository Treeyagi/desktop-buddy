"""The voice server: keeps Chatterbox loaded and turns text into speech in the user's cloned voice.

Runs in its own Python 3.11 env (~/.local/share/desktop-buddy/tts/.venv), started by speak.py when he
first needs to talk, and exits by itself after IDLE_MINUTES of silence (that frees the GPU).
Local only (127.0.0.1), nothing is sent anywhere once the model is downloaded.

  GET  /health            -> "ok" once the model is loaded, "loading" before
  POST /speak  {"text", "mood"} -> a 16-bit mono WAV
  POST /quit              -> exits
"""
import io
import json
import os
import re
import sys
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8765
IDLE_MINUTES = 30
SAMPLES = os.path.expanduser("~/.local/share/desktop-buddy/voice")
# mood -> (his recording of that mood, Chatterbox "exaggeration": how emotional it sounds)
MOODS = {"normal": 0.5, "excited": 0.8, "annoyed": 0.65, "chill": 0.3}
MAX_CHARS = 280  # Chatterbox is happiest with sentence-sized chunks

model = None
last_used = time.monotonic()
lock = threading.Lock()


def load_model():
    global model
    import torch
    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")


def chunks(text):
    """Split into sentence-sized pieces so long answers keep their quality."""
    parts, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        if cur and len(cur) + len(sentence) > MAX_CHARS:
            parts.append(cur)
            cur = ""
        cur = f"{cur} {sentence}".strip()
    if cur:
        parts.append(cur)
    return parts


def speak(text, mood, tune=None):
    import numpy as np
    sample = os.path.join(SAMPLES, f"{mood}.wav")
    if not os.path.exists(sample):
        sample = os.path.join(SAMPLES, "normal.wav")
    pieces = []
    with lock:
        for part in chunks(text):
            args = dict(exaggeration=MOODS.get(mood, 0.5), cfg_weight=0.3, temperature=0.8)  # 0.3: slower, more natural pacing than 0.5
            args.update({k: float(v) for k, v in (tune or {}).items() if k in args})
            wav = model.generate(part, audio_prompt_path=sample, **args)
            pieces.append(wav.squeeze().cpu().numpy())
            pieces.append(np.zeros(int(model.sr * 0.18), dtype="float32"))  # a breath between sentences
    audio = np.concatenate(pieces) if pieces else np.zeros(1, dtype="float32")
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(model.sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, kind="text/plain"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, "ok" if model else "loading")

    def do_POST(self):
        global last_used
        last_used = time.monotonic()
        if self.path == "/quit":
            self._send(200, "bye")
            threading.Thread(target=lambda: (time.sleep(0.2), os._exit(0))).start()
            return
        if model is None:
            self._send(503, "loading")
            return
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            audio = speak(str(req.get("text", "")), str(req.get("mood", "normal")), req.get("tune"))
        except Exception as e:  # report instead of dying: the buddy shows the error in his bubble
            self._send(500, f"{type(e).__name__}: {e}")
            return
        last_used = time.monotonic()
        self._send(200, audio, "audio/wav")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    load_model()
    print("voice server ready", flush=True)
    while time.monotonic() - last_used < IDLE_MINUTES * 60:
        time.sleep(5)
    print("idle, shutting down", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
