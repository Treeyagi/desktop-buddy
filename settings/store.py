"""The buddy's settings: one JSON file both the overlay and the settings window
read and write. Whoever saves it, the others pick the change up live.

    ~/.config/desktop-buddy/settings.json

Unknown keys are kept, missing ones fall back to DEFAULTS, so older files keep
working as settings get added.
"""
import json
import os

from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal

DIR = os.path.expanduser("~/.config/desktop-buddy")
PATH = os.path.join(DIR, "settings.json")
PID_PATH = os.path.join(DIR, "buddy.pid")
SOCKET = f"desktop-buddy-{os.getuid()}"  # the settings window's "Do it now" line to the buddy

DEFAULTS = {
    "paused": False,      # hidden and frozen
    "size": 1.1,          # character scale
    "monitor": "auto",    # a screen name, or "auto" = the one with your desktop icons
    "activity": 0.5,      # 0 chill .. 1 hyper
    "quiet": False,       # calls / gaming: no bubbles, no big scenes, mostly chill
    # what he does (Behavior tab)
    "behaviors": {},      # action or scene name -> {"on": bool, "often": multiplier}; missing = on, 1x
    "vending_odds": 0.5,  # chance the bundle is in stock
    "pack_hit_odds": 0.25, # chance the pack he rips has a holo hit as its last card
    "vending_pity": 0.15, # added to the odds for each letdown in a row
    "icon_visits": True,  # clearance-aisle trips to your real desktop icons
    "new_file_reaction": True,
    "companion_bee": True,
    # ADHD brain (attention/)
    "adhd_squirrel": True,    # chases the mouse cursor now and then
    "adhd_distract": True,    # windows you switch to and new sounds catch his eye
    "adhd_tangents": True,    # "wait, unrelated, but..."
    "adhd_mood": True,        # grumpy when ignored, smug when right
    "adhd_react": True,       # comments on what you're doing (video, code, game, up late)
    "nudge_minutes": 60,      # nudge after this long on one window; 0 = never
    "moments": None,          # his walk-out moment lines ("kind: text"); None = the built-in ones
    "adhd_moments": True,     # walk-out moments: gratitude, family, geeking out, dreams, vibes
    "tangents": None,         # his tangent lines; None = the built-in ones
    "fullscreen_hide": True,  # hide while a fullscreen app (game, video) is on his monitor
    # look and sayings
    "character": "cartoon",  # cartoon (the vector rig) | sprite (character/sprite.py)
    "shoes": "hot pink",  # a style from character/rig.py SHOE_STYLES
    "quips": None,        # his random sayings; None = the built-in ones
    "greetings": None,    # what he says when he waves; None = the built-in ones
    # Claude (brain/): how he answers when you talk to him
    "claude_enabled": False,
    "claude_backend": "claude-code",   # claude-code (your Claude plan) | api (API key in KWallet)
    "claude_model": "claude-opus-5-5",
    # voice
    "voice_enabled": True,       # push-to-talk (voice-in/)
    "voice_hotkey": "Meta+Space",
    "screen_hotkey": "Meta+Shift+Space",  # hold, say "roast my code" / "settle this"; sends one screenshot
    "voice_mic": None,           # a PipeWire source name; None = the system default mic
    "whisper_model": "base.en",  # tiny.en | base.en | small.en
    "hum_enabled": True,         # hums on happy walks, as a text bubble
    "hum_sound": False,          # ...and as sound too (voice-out/hum.py; sounded robotic, so off)
    "dance_mode": False,         # dances nonstop, music or not
    "adhd_dance": True,          # dances when music plays from a browser or a music player
    "voice_engine_unload": False, # stop the voice engine after 2 idle minutes (frees ~5 GB of GPU); loads again on the next question
    "voice_out_loud": True,      # voice-out/: speak answers in his cloned voice
}


def load():
    data = dict(DEFAULTS)
    try:
        with open(PATH, encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            data.update(saved)
    except (OSError, ValueError):
        pass
    return data


def save(data):
    os.makedirs(DIR, exist_ok=True)
    tmp = PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, PATH)  # never leave a half-written file for the other side to read


def update(**changes):
    data = load()
    data.update(changes)
    save(data)
    return data


class SettingsFile(QObject):
    """Emits changed(dict) whenever the settings file's contents change."""
    changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        os.makedirs(DIR, exist_ok=True)
        if not os.path.exists(PATH):
            save(DEFAULTS)
        self.data = load()
        self.watch = QFileSystemWatcher([DIR, PATH], self)
        self.watch.directoryChanged.connect(self._poke)
        self.watch.fileChanged.connect(self._poke)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._reload)

    def _poke(self, *_):
        if PATH not in self.watch.files() and os.path.exists(PATH):
            self.watch.addPath(PATH)  # save() replaces the file, which drops the watch
        self.timer.start()

    def _reload(self):
        data = load()
        if data != self.data:
            self.data = data
            self.changed.emit(data)

    def set(self, **changes):
        self.data = update(**changes)
        self.changed.emit(self.data)
