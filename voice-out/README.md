# voice-out

He speaks his answers in the user's cloned voice. Everything runs on this computer.

- **Inputs:** `voice.reply` (his answer), `voice.listening`, `attention.mood`
- **Outputs:** `voice.say` (the answer, sent once the audio is ready), `voice.mouth` (lip level, about 30 times a second)
- **Settings:** "Say answers out loud" (`voice_out_loud`) in the Claude tab; also needs "Let him answer with Claude"

## How it works
- `samples.py`: the four mood recordings from the My voice tab (`~/.local/share/desktop-buddy/voice/{normal,excited,annoyed,chill}.wav`).
- `server.py`: runs in its own Python 3.11 env, `~/.local/share/desktop-buddy/tts/.venv` (made with `uv`, about 8 GB with Chatterbox, PyTorch and the model). It keeps Chatterbox loaded on the GPU (about 5 GB) and answers `POST /speak` on 127.0.0.1:8765 with a WAV. It exits by itself after 15 idle minutes.
- `speak.py`: the `Speaker` in the buddy. It starts the server when you press the talk key (so it loads while you talk), asks for audio when the reply comes, plays it with `pw-play`, and publishes `voice.say` when the sound is ready so the bubble and the lips start together with it. If anything is missing it falls back to text only.
- **Mood:** the recording used depends on his mood and the text: annoyed when grumpy, excited when delighted or lots of "!", chill for short trailing lines, else normal.
- **Calls:** if another app is recording from the microphone (a call), he stays quiet and only shows the bubble.
- **Speed:** about 5 s to start a sentence once loaded, 15 to 20 s for the first answer after the server was off.

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

Still planned: quiet humming while he walks.
