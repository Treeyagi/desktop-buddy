# voice-in

Push-to-talk: hold a key, talk, let go. He listens, Whisper turns it into text on this computer, Claude answers in his personality, and he says it in his bubble (out loud too once `voice-out/` exists).

- **Inputs:** a KDE global shortcut press and release, and microphone audio
- **Outputs:** `voice.listening`, `voice.thinking`, `voice.reply` and `voice.cancel` on the bus (see `core/README.md`)

## Files
- `hotkey.py`: registers "Desktop Buddy / Push to talk (hold)" with KGlobalAccel over D-Bus. It works in every app, shows up in System Settings > Shortcuts, and reports both press and release. The default is Meta+Space (it was free).
- `recorder.py`: `pw-record` (PipeWire) to 16 kHz mono WAV in `~/.cache/desktop-buddy/`. It uses the default mic or one picked in settings, and `microphones()` lists them. Safety:
  - The recorder process is tied to the buddy's process, so it stops even if he crashes or is killed.
  - Quitting stops and deletes any recording, and a leftover from a hard kill is deleted at the next start.
  - A recording stops by itself after 45 seconds.
- `stt.py`: speech to text with whisper.cpp's `whisper-cli` (`sudo pacman -S whisper-cpp`). The models are whisper.cpp's ggml files in `~/.local/share/desktop-buddy/whisper/`: tiny.en 75 MB, base.en 142 MB (the default), small.en 466 MB. Download them from Settings > Claude > Voice.
- `listen.py`: `VoiceIn` ties it together. Press starts recording. Release transcribes off the UI thread, deletes the recording, and asks Claude (if "Let him answer with Claude" is on), then publishes the reply. A tap under 0.4 s is ignored.

## Look at my screen (hotkey modes)
A second shortcut, "Look at my screen (hold)" (default Meta+Shift+Space), works like push-to-talk but also grabs one screenshot (`spectacle`) at the moment you press. This is the only time a screenshot exists or goes to Claude.
- The words you say pick the mode (`MODES` in `brain/client.py`): "roast my code" (snarky code review ending in the one fix that matters), "settle this argument" (who has the stronger point, how to end it), anything else is a plain question about what's on screen.
- The shot is shrunk to a 1568 px JPEG, sent, and deleted right after (also on a too-short tap or quit). With Claude Code he can read only that file's folder; with the API it goes as an image block.

## What he does
- **listen:** leans in with a hand cupped by his face, "I'm listening…".
- **think:** hyperfocus. He squints, paces a little and scratches his beard, with a thought cloud showing what he heard.
- **answer:** talks with hand gestures, his reply in a word-wrapped bubble (it shows even in quiet mode, since you asked).

If something's missing (no mic, Whisper not installed, no model, Claude switched off), he says so in his bubble instead.

Privacy: audio never leaves the computer; only the transcript goes to Claude.
