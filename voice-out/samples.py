"""Your voice samples: short recordings in a few moods that the voice-cloning
engine learns your voice from. Recorded in Settings > My voice; they stay on
this computer in ~/.local/share/desktop-buddy/voice/.

Read each script the way you'd really say it in that mood. One quiet room,
the same mic every time, about 10 to 20 seconds each.
"""
import os
import wave

DIR = os.path.expanduser("~/.local/share/desktop-buddy/voice")
RATE = 24000  # better than Whisper's 16 kHz; voice cloning likes clean, full audio

# (mood, label, what to read)
MOODS = [
    ("normal", "Normal",
     "Hey, it's me. I'm just talking the way I normally talk, about nothing in particular. "
     "The coffee's warm, the bees are busy, and I've got a whole list of stuff to get done "
     "today. Let's see how much of it actually happens."),
    ("excited", "Excited",
     "No way. No way! It's in stock? Are you kidding me right now? This is the best day ever. "
     "I've been waiting forever for this one. Let's go, let's go, let's go!"),
    ("annoyed", "Annoyed",
     "Seriously? We're doing this again? I said it yesterday, and the day before that. Fine. "
     "Here's what we're gonna do, and this time we're actually doing it."),
    ("chill", "Chill",
     "Alright, take a breath. There's no rush. The work will still be there in five minutes. "
     "Sit back, let it settle, and then we'll figure out the next step together."),
]


def path(mood):
    return os.path.join(DIR, f"{mood}.wav")


def seconds(mood):
    """Length of a recorded sample, or 0 if there isn't one."""
    try:
        with wave.open(path(mood)) as w:
            return w.getnframes() / float(w.getframerate())
    except (OSError, wave.Error, EOFError):
        return 0.0


def recorded():
    return [m for m, _, _ in MOODS if seconds(m) >= 3]
