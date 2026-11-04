#!/usr/bin/env python3
"""Stop everything Desktop Buddy runs: the buddy, the voice server (frees the GPU), any recording
and playing speech, and the KWin script.  Run it when you're done:  python3 tools/shutdown.py"""
import glob
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from core.load import load  # noqa: E402

ME = os.getpid()


def pids(pattern):
    out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True).stdout.split()
    return [int(p) for p in out if int(p) != ME]


def main():
    speak = load("voice-out", "speak")
    speak.stop_server()                       # asks the voice server to exit cleanly
    # anchored to the start of the command line, so a shell that merely mentions these names is left alone
    found = {"the buddy": pids(r"^(\S*/)?python[0-9.]* (\S*/)?overlay/main\.py"),
             "the voice server": pids(r"^(\S*/)?python[0-9.]* (\S*/)?voice-out/server\.py"),
             "a recording": pids(r"^(\S*/)?pw-record .*desktop-buddy"),
             "speech playback": pids(r"^(\S*/)?pw-play .*desktop-buddy/speech\.wav")}
    for what, ps in found.items():
        for pid in ps:
            try:
                os.kill(pid, signal.SIGTERM)  # the buddy unloads its KWin script and deletes recordings on SIGTERM
                print(f"stopped {what} ({pid})")
            except ProcessLookupError:
                pass
    time.sleep(1.5)
    for ps in found.values():
        for pid in ps:
            try:
                os.kill(pid, signal.SIGKILL)
                print(f"force-stopped {pid}")
            except ProcessLookupError:
                pass
    for path in glob.glob(os.path.expanduser("~/.cache/desktop-buddy/*.wav")) + \
            glob.glob(os.path.expanduser("~/.cache/desktop-buddy/screen.*")):
        os.remove(path)                       # no leftover recordings, speech or screenshots
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    print("all stopped." + (f" GPU memory in use: {gpu}" if gpu else ""))


main()
