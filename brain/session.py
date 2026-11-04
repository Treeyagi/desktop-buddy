"""A Claude Code process kept warm between questions, answering in a stream.

`claude -p` costs about 2.5 s to start every time. Here one process stays alive (`--input-format
stream-json`), so a question goes straight to the model, and each sentence of the answer is handed
out the moment it's written, so the voice can start before the answer is finished.

- warm() must be called from the main thread (the process is tied to the buddy with PDEATHSIG, which
  follows the thread that started it). ask() runs on any thread and falls back to the caller doing a
  one-shot client.ask() when there is no live process.
- The process remembers the last few questions (so follow-ups work), then restarts after MAX_TURNS.
- It restarts by itself when the personality or the model changes.
"""
import json
import os
import re
import signal
import subprocess
import threading
import time

from brain import client

MAX_TURNS = 10
IDLE_SECONDS = 20 * 60   # an unused process is let go (and restarted on the next press)


def _tie_to_parent():
    import ctypes
    ctypes.CDLL("libc.so.6").prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG


class Session:
    def __init__(self):
        self.proc = None
        self.key = None
        self.turns = 0
        self.used = time.monotonic()
        self.lock = threading.Lock()

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def warm(self, model):
        """Start (or restart) the process if needed. Main thread only."""
        if self.lock.locked():   # mid-answer: leave it alone
            return
        key = (model, client.system_prompt())
        stale = self.turns >= MAX_TURNS or time.monotonic() - self.used > IDLE_SECONDS
        if self.alive() and key == self.key and not stale:
            return
        self.stop()
        exe = client.claude_cli()
        if not exe:
            return
        os.makedirs(client.WORKDIR, exist_ok=True)
        cmd = [exe, "-p", "--system-prompt", key[1], "--model", model, "--effort", "low", "--tools", "",
               "--safe-mode", "--no-session-persistence", "--strict-mcp-config",
               "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
               "--include-partial-messages"]
        self.proc = subprocess.Popen(cmd, cwd=client.WORKDIR, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, preexec_fn=_tie_to_parent)
        self.key, self.turns, self.used = key, 0, time.monotonic()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None

    def ask(self, question, on_sentence, timeout=60):
        """Returns a client.Reply, calling on_sentence(text) for each finished sentence on the way."""
        start = time.monotonic()
        with self.lock:
            if not self.alive():
                return None   # caller falls back to a one-shot ask
            watchdog = threading.Timer(timeout, self.stop)
            watchdog.start()
            try:
                return self._ask(question, on_sentence, start)
            finally:
                watchdog.cancel()
                self.used = time.monotonic()

    def _ask(self, question, on_sentence, start):
        try:
            self.proc.stdin.write(json.dumps({"type": "user", "message": {"role": "user", "content": question}}) + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError):
            self.stop()
            return None
        buf, text = "", ""
        for line in self.proc.stdout:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            kind = d.get("type")
            if kind == "stream_event":
                delta = (d.get("event") or {}).get("delta") or {}
                if delta.get("type") == "text_delta":
                    buf += delta.get("text", "")
                    *done, buf = re.split(r"(?<=[.!?])\s+", buf)
                    for sentence in done:
                        text += sentence + " "
                        on_sentence(sentence)
            elif kind == "result":
                self.turns += 1
                if d.get("is_error"):
                    return client.Reply(error=str(d.get("result") or "Claude Code reported an error."),
                                        seconds=time.monotonic() - start)
                if buf.strip():
                    on_sentence(buf.strip())
                final = str(d.get("result") or (text + buf)).strip()
                return client.Reply(text=final, seconds=time.monotonic() - start, backend="claude-code")
        self.stop()   # the process ended without answering
        return client.Reply(error="Claude Code stopped before answering. Try again.", seconds=time.monotonic() - start)


session = Session()
