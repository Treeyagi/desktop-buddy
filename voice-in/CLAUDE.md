# voice-in notes

Reference for this folder: [README.md](README.md) — the files and what he does.

## The rule that matters most

**Never leave the mic recording.** He records only while the talk key is held, and recordings are deleted
after use. `python3 ../tools/shutdown.py` deletes any that are left over — run it when you're done.

Push-to-talk is a deliberate limit, not a stopgap. Don't widen it into always-listening or a wake word:
that's a different app with different consent ([why](../docs/explanation/privacy-cost-and-licensing.md)).

## While working here

- The chain is `hotkey.py` (KGlobalAccel) → `recorder.py` (`pw-record`) → `stt.py` (whisper-cli) →
  `listen.py`, which publishes `voice.listening`, `voice.thinking`, `voice.reply` and `voice.cancel`
  on the bus. The character and overlay react to those — don't call into them directly.
- A tap too short to be speech must publish `voice.cancel`, not an empty transcript.
- Don't change the user's KDE shortcuts beyond the one push-to-talk binding.
