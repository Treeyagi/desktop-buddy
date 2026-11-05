# Roadmap

What's done is described in each folder's README (current release: v0.5.3). This is what's next; the full
brainstorm is in `docs/NOTES.md`.

## Next up
1. **Study-quiz mode** for the user's son, in character. Ideas to settle first: how it starts (tray menu, a
   hotkey, or "quiz me"), subject and age level, questions from Claude (the warm session in
   `brain/session.py` keeps it fast) or a list the user types in, spoken in the cloned voice, a mouth-synced
   "nice!" and a dance on a streak. Keep answers short, and keep it kind: he never shames a wrong answer.

## Polish
- Roam across both monitors (walk from one to the other).
- More outfits on the Look tab (hat colors, hoodies, seasonal).
- Hyperfocus thinking loop for Claude answers (try, check, search, deliver).

## Ideas, not started
- **Hum with sound** (off for now: the synthesized tone sounded robotic). Needs a better source than the
  built-in synth; the switch is `hum_sound`.
- **Speak the walk-out moments** in the cloned voice (they are bubble-only now; it would use the GPU voice
  more often).
- **Smarter reactions:** use the page title (what the video actually is) or a Claude line instead of the
  fixed lines in `attention/engine.py`; only count browser audio as music when it looks like music.
- **Reply even faster:** a smaller first sentence, or a faster voice model.

## Notes for the next session
- Start him: `python3 overlay/main.py`, or "Desktop Buddy" in the start menu (`python3 tools/install.py`).
- Stop everything (buddy, voice server, warm Claude process, audio): `python3 tools/shutdown.py`.
- Voice out needs the one-time Python 3.11 env in `~/.local/share/desktop-buddy/tts/` (see
  `voice-out/README.md`); it holds about 5 GB of GPU memory while loaded.
- Check work with `python3 tools/soak.py`, `character/preview.py` (`--actions dance:disco`, `idle:owl`,
  `moment:family`) and `tools/render_tab.py`.
- `brain/who-i-am.md` is filled in; still blank: name, wife's and son's names, favorite sayings.
- Careful with `pkill -f` and `pgrep -f` here: a pattern that appears in your own shell command matches and
  kills that shell. `tools/shutdown.py` anchors its patterns for this reason.

## Open questions
- App name.
- "Never giving him an out": confirm the exact meaning.
