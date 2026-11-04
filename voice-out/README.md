# voice-out

He speaks his answers in the user's cloned voice. Everything runs on this computer.

- **Inputs:** `voice.reply` (his answer), `voice.listening`, `attention.mood`
- **Outputs:** `voice.say` (the answer, sent once the audio is ready), `voice.mouth` (lip level, about 30 times a second)
- **Settings:** "Say answers out loud" (`voice_out_loud`) in the Claude tab; also needs "Let him answer with Claude"

## How it works
- `samples.py`: the four mood recordings from the My voice tab (`~/.local/share/desktop-buddy/voice/{normal,excited,annoyed,chill}.wav`).
- `server.py`: runs in its own Python 3.11 env, `~/.local/share/desktop-buddy/tts/.venv` (made with `uv`, about 8 GB with Chatterbox, PyTorch and the model). It keeps Chatterbox loaded on the GPU (about 5 GB) and answers `POST /speak` on 127.0.0.1:8765 with a WAV. It exits by itself after 30 idle minutes. Pacing: `cfg_weight` 0.3 (chosen by ear against 0.5 and 0.2; lower is slower and calmer), `temperature` 0.8, and `exaggeration` per mood in `MOODS`. A request can pass `"tune": {...}` to try other values.
- `speak.py`: the `Speaker` in the buddy. It starts the server when the buddy starts and when you press the talk key, splits the reply into sentences, generates the first, and publishes `voice.say` as soon as that one is ready so the bubble and the lips start together with the sound. The rest is generated while the first plays and played back to back (`voice.say` carries an estimate of the full length). If anything is missing it falls back to text only.
- **Mood:** the recording used depends on his mood and the text: annoyed when grumpy, excited when delighted or lots of "!", chill for short trailing lines, else normal.
- **Calls:** if another app is recording from the microphone (a call), he stays quiet and only shows the bubble.
- **Streaming from Claude:** `brain/session.py` keeps one Claude Code process warm (no 2.5 s startup per question) and hands each finished sentence to `voice.reply_part`; the Speaker starts the voice on the first one while Claude is still writing. The whole text arrives as `voice.reply`, and `voice.say` follows once the first sound is ready.
- **Speed (old, one sentence at a time):** with the voice loaded he starts talking about 5 s after Claude's reply arrives (one sentence at a time after that); the voice loads when the buddy starts, so the 15 to 20 s cold start only happens after it timed out or `tools/shutdown.py`. It keeps about 5 GB of GPU memory while loaded.

## Where the time goes (measured)
Speech to text 0.6 s, Claude's first sentence about 1.5 to 2.5 s (warm process), the voice about 1.5 to 2.5 s for that sentence: sound starts roughly 3 to 4 s after you let go of the key (it was about 10 s). He keeps answers to two short sentences (`brain/personality.md`), which is also what keeps the speech short.

## Shutting everything down
- Quitting the buddy (tray > Quit, Ctrl+C) also stops the voice server and any sound.
- `python3 tools/shutdown.py` stops the buddy, the voice server, any recording or playing speech, and deletes leftover audio and screenshots. Run it when you're done; it prints the GPU memory still in use.
- If the buddy is killed hard, the server dies with it (it is tied to the buddy's process).

## Setup (done once)
```
uv venv --python 3.11 ~/.local/share/desktop-buddy/tts/.venv
uv pip install --python ~/.local/share/desktop-buddy/tts/.venv/bin/python chatterbox-tts "setuptools<81"
```
The `setuptools<81` pin is needed because Chatterbox's watermark library imports `pkg_resources`. Chatterbox adds an inaudible watermark to its speech.

## Humming (`hum.py`)
On about half of his happy (content or cheery) walks he hums. The six two-bar melodies are made from scratch the first time (124 BPM, A minor pentatonic, off-beat notes, a soft vibrato "mm" tone) and kept in `~/.cache/desktop-buddy/hum*.wav`, so no real songs or samples are used. They play at 12% volume with `pw-play`, never during a call, and stop with the "Hum quietly" setting or quiet mode. His mouth makes a small "mm" while he does.
