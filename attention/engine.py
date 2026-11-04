"""The ADHD engine: decides when his attention wanders. Pure local logic, no
Claude usage. It watches the desktop and the clock and nudges him through the
bus; the character decides how to act it out (and ignores it when he's busy).

Listens to (see core/README.md):
  desktop.windows, desktop.cursor, voice.listening, buddy.interaction
Publishes:
  attention.squirrel   QPointF (global): the cursor caught his eye, chase it
  attention.gaze       {"at": QPointF or None, "why": "window" | "sound"}
  attention.tangent    None: wander off mid-thought
  attention.nudge      str: you've been on one window a long time
  attention.smug       None: you took his advice ("told ya")
  attention.sulk       None: he's been ignored a while
  attention.music      bool: music is playing from a browser or a music player (True/False on change)
  attention.react      {"kind": str, "text": str}: a comment on what you're doing (video, code, game, late night)
  attention.mood       float, -1 grumpy .. 1 delighted
  attention.focus      {"until": monotonic seconds, "minutes": n} or None when stopped
  attention.focus_done None: the focus timer ran out, break time
"""
import json
import random
import re
import subprocess
import time

from PyQt6.QtCore import QObject, QTimer

NUDGES = [
    "still on this one? stand up, stretch, then come back swinging.",
    "you've been locked in a while. water break. I'll guard the desk.",
    "big stretch of focus. look at something far away for twenty seconds.",
    "hey. shoulders down, deep breath. then the next small step.",
]

# What you're doing, from the focused window's app and title (nothing leaves the machine).
# First match wins; each kind has lines he picks from.
ACTIVITIES = [
    ("video", r"youtube|twitch|netflix|vlc|mpv|plex|disney\+|prime video",
     ["ooh, what are we watching?", "is this a 'one more video' situation?",
      "I'll watch too. scoot over.", "snacks. we need snacks for this."]),
    ("game", r"steam_app|steam$|^steam|lutris|heroic|minecraft|gamescope|wine|proton|retroarch|yuzu|dolphin-emu",
     ["game time! go get 'em.", "is it a boss fight? it feels like a boss fight.",
      "don't rage. rage is bad for the controller.", "I'm cheering from the sidelines."]),
    ("code", r"code|kate|kdevelop|vim|nvim|emacs|pycharm|idea|konsole|alacritty|kitty|foot|terminal|github|stack overflow",
     ["ooh, coding. I'll be quiet. mostly.", "if it works, don't touch it.",
      "have you tried turning it off and on again?", "rubber duck reporting for duty."]),
    ("chat", r"discord|telegram|signal|whatsapp|slack|element|thunderbird|gmail|mail",
     ["messages! tell them I said hi.", "typing a big one? I'll wait.",
      "don't forget to answer the one from yesterday."]),
]
LATE = [
    "it's past midnight. sleep is a feature, not a bug.",
    "the late hours again? water, then bed. I mean it.",
    "even I'm sleepy. and I'm a drawing.",
]
# apps whose audio counts as music: browsers (YouTube, Spotify web...) and music players
MUSIC_APPS = re.compile(r"firefox|chrom|brave|vivaldi|opera|librewolf|zen|floorp|falkon|epiphany|spotify|vlc|mpv|"
                        r"strawberry|elisa|rhythmbox|amarok|audacious|clementine|lollypop|deadbeef|tidal|"
                        r"youtube|celluloid|haruna|amberol|supersonic|cider|plexamp", re.I)
REACT_COOLDOWN = 8 * 60   # seconds between comments on what you're doing
LATE_HOURS = (0, 4)       # midnight to 4 a.m.

MOOD_HOME = 0.2           # where his mood settles when things are normal
IGNORED_AFTER = 25 * 60   # seconds without contact before he starts getting grumpy


class AttentionEngine(QObject):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus
        self.s = {}
        now = time.monotonic()
        self.mood = MOOD_HOME
        self.sent_mood = None
        self.last_contact = now
        self.active_id = None
        self.active_since = now
        self.nudged_this_stint = False
        self.nudge_at = None
        self.focus_until = None
        self.cursor = None
        self.cursor_at = 0.0
        self.cool = {"squirrel": 0.0, "gaze": 0.0, "tangent": now + random.uniform(240, 600),
                     "sulk": now + 600, "sound": 0.0}
        self.streams = None
        self.music = False
        self.music_votes = 0
        self.activity = None
        self.react_at = 0.0
        self.late_at = 0.0
        bus.subscribe("desktop.windows", self._on_windows)
        bus.subscribe("desktop.cursor", self._on_cursor)
        bus.subscribe("voice.listening", lambda down: down and self.contact())
        bus.subscribe("buddy.interaction", lambda _: self.contact())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        self.ticks = 0

    def apply(self, s):
        self.s = dict(s)

    def on(self, key):
        return bool(self.s.get(key, True))

    def calm(self):
        """No distractions while he's focusing with you or in quiet mode."""
        return self.focus_until is not None or self.s.get("quiet")

    # you paid attention to him ------------------------------------------------------
    def contact(self):
        self.last_contact = time.monotonic()
        self.mood = min(1.0, self.mood + 0.25)
        self._send_mood()

    def _send_mood(self):
        mood = self.mood if self.on("adhd_mood") else MOOD_HOME
        if self.sent_mood is None or abs(mood - self.sent_mood) > 0.04:
            self.sent_mood = mood
            self.bus.publish("attention.mood", mood)

    # focus timer (the tray starts it) ---------------------------------------------------
    def start_focus(self, minutes):
        self.focus_until = time.monotonic() + minutes * 60
        self.bus.publish("attention.focus", {"until": self.focus_until, "minutes": minutes})

    def stop_focus(self):
        if self.focus_until is not None:
            self.focus_until = None
            self.bus.publish("attention.focus", None)

    # what's happening on the desktop -------------------------------------------------
    def _on_windows(self, windows):
        active = next((w for w in windows if w.active and w.showing), None)
        new_id = active.id if active else None
        self._react(active)
        if new_id == self.active_id:
            return
        now = time.monotonic()
        self.active_id, self.active_since = new_id, now
        self.nudged_this_stint = False
        if self.nudge_at and now - self.nudge_at < 180:  # took his advice
            self.nudge_at = None
            self.mood = min(1.0, self.mood + 0.3)
            self._send_mood()
            self.bus.publish("attention.smug", None)
            return
        if (active and self.on("adhd_distract") and not self.calm() and now > self.cool["gaze"]
                and random.random() < 0.3):
            self.cool["gaze"] = now + 60
            r = active.rect
            self.bus.publish("attention.gaze", {"at": r.center(), "why": "window"})

    def _react(self, active):
        """Comment when you start something new (a video, code, a game), or when you're up past midnight."""
        kind, lines = None, None
        if active:
            hay = f"{active.app} {active.title}".lower()
            for k, pattern, texts in ACTIVITIES:
                if re.search(pattern, hay):
                    kind, lines = k, texts
                    break
        changed = kind != self.activity
        self.activity = kind
        now = time.monotonic()
        if not self.on("adhd_react") or self.calm():
            return
        hour = time.localtime().tm_hour
        if (active and LATE_HOURS[0] <= hour < LATE_HOURS[1] and now > self.late_at and kind in ("game", "video", "code")):
            self.late_at = self.react_at = now + 45 * 60
            self.bus.publish("attention.react", {"kind": "late", "text": random.choice(LATE)})
        elif changed and kind and now > self.react_at and random.random() < 0.5:
            self.react_at = now + REACT_COOLDOWN
            self.bus.publish("attention.react", {"kind": kind, "text": random.choice(lines)})

    def _on_cursor(self, pt):
        now = time.monotonic()
        moved = self.cursor is not None and (pt - self.cursor).manhattanLength() > 40
        self.cursor, self.cursor_at = pt, now
        if (moved and self.on("adhd_squirrel") and not self.calm() and now > self.cool["squirrel"]
                and random.random() < 0.06):
            self.cool["squirrel"] = now + 75
            self.bus.publish("attention.squirrel", pt)

    def _poll_sounds(self):
        """New audio starting to play catches his ear (pactl, every few seconds)."""
        try:
            out = subprocess.run(["pactl", "-f", "json", "list", "sink-inputs"], capture_output=True,
                                 text=True, timeout=2)
            live = [s for s in json.loads(out.stdout) if not s.get("corked")]
            playing = {s["index"] for s in live}
            music = any(MUSIC_APPS.search(" ".join((s.get("properties") or {}).get(k, "") for k in
                        ("application.name", "application.process.binary"))) for s in live)
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            return
        new = self.streams is not None and bool(playing - self.streams)
        self.streams = playing
        # music needs two polls in a row to start or stop, so a notification ping doesn't count
        self.music_votes = max(0, min(2, self.music_votes + (1 if music else -1)))
        want = self.on("adhd_dance") and (self.music_votes >= 2 or (self.music and self.music_votes > 0))
        if want != self.music:
            self.music = want
            self.bus.publish("attention.music", want)
        now = time.monotonic()
        if new and self.on("adhd_distract") and not self.calm() and now > self.cool["sound"] \
                and random.random() < 0.5:
            self.cool["sound"] = now + 120
            self.bus.publish("attention.gaze", {"at": None, "why": "sound"})

    def _tick(self):
        now = time.monotonic()
        self.ticks += 1
        if self.ticks % 4 == 0:
            self._poll_sounds()

        if self.focus_until is not None and now >= self.focus_until:
            self.focus_until = None
            self.mood = min(1.0, self.mood + 0.2)
            self.bus.publish("attention.focus", None)
            self.bus.publish("attention.focus_done", None)

        # mood: settles toward normal, sinks slowly when he's ignored
        idle = now - self.last_contact
        if idle > IGNORED_AFTER:
            self.mood = max(-0.8, self.mood - 0.0006)
        else:
            self.mood += (MOOD_HOME - self.mood) * 0.002
        self._send_mood()
        if (self.on("adhd_mood") and self.mood < -0.4 and not self.calm() and now > self.cool["sulk"]):
            self.cool["sulk"] = now + random.uniform(600, 1200)
            self.bus.publish("attention.sulk", None)

        if self.on("adhd_tangents") and not self.calm() and now > self.cool["tangent"]:
            self.cool["tangent"] = now + random.uniform(360, 900)
            self.bus.publish("attention.tangent", None)

        minutes = float(self.s.get("nudge_minutes", 60) or 0)
        if (minutes > 0 and self.active_id and not self.nudged_this_stint and not self.calm()
                and now - self.active_since > minutes * 60):
            self.nudged_this_stint = True
            self.nudge_at = now
            self.bus.publish("attention.nudge", random.choice(NUDGES))
