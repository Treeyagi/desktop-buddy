# voice-out notes

Reference for this folder: [README.md](README.md) — how it works, measured timings, start/stop/unload, setup,
and humming.

## While working here

- **The TTS engine lives in its own Python 3.11 virtual environment** at
  `~/.local/share/desktop-buddy/tts/.venv` (Chatterbox, with a `setuptools<81` pin). It is deliberately
  **not** an app dependency: the buddy stays "PyQt6 and nothing else" and a heavy ML stack can't stop him
  starting. Don't add it to the app's requirements.
- The voice server runs on `127.0.0.1:8765`, is owned by the running buddy, unloads after 2 minutes idle,
  and dies with him. Keep that: it must never outlive the buddy.
- `python3 ../tools/shutdown.py` stops the server and any playing speech and deletes leftover audio.
  Run it when you're done.
- **Hum sound is off by default** (`hum_sound`) because the synthesised tone sounded robotic; he hums in a
  text bubble instead. The code stays for when it's worth revisiting.
- Melodies are **generated from scratch at runtime** and cached — no real songs or samples, ever. This repo
  is public ([why](../docs/explanation/privacy-cost-and-licensing.md)).
- Never play sound during a call, and respect quiet mode and the "Hum quietly" setting.
