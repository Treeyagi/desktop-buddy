"""Walk-out moments: now and then he stops mid-whatever and says something from the heart
(gratitude, family, what he's geeking out about, dreams, good vibes, a calm breath), with a gesture to match.

The lines come from brain/who-i-am.md (you, your family, owls, Pokemon, falconry, the travel dreams).
Each line is "kind: text"; the kind picks the gesture. Edit them in the Sayings tab. No Claude calls,
so they cost nothing.
"""
import math
import random

from character.moves import hug, palms_up
from character.rig import Pose, ease, lerp

MOMENTS = [
    "gratitude: I appreciate you. Seriously. Yes, you.",
    "gratitude: quick gratitude check: you made it this far today. that counts.",
    "gratitude: thank you, brain, for running a million miles an hour. rude but impressive.",
    "family: go give wifey a hug. she's the rock, and rocks love hugs.",
    "family: your son is the greatest gift. go be ridiculous with him for ten minutes.",
    "family: Pokemon machine run with the little guy this weekend? I'm just saying.",
    "geek: owl fact: they fly almost silent because of fringed feathers. the dream is real.",
    "geek: falconry is just very patient friendship with a feathered missile.",
    "geek: okay, rabbit hole time. owls can turn their heads about 270 degrees. I'm jealous.",
    "geek: Pokemon pull rates are a whole math spiral and I'm already in it.",
    "dream: Machu Picchu. Spain. somewhere wild like Abu Dhabi. the plan is a plan.",
    "dream: future you is a falconer with a really good glove. keep going.",
    "vibes: time traveler update: future you says it all works out.",
    "vibes: good vibes only. mostly. I'm working on the mostly.",
    "vibes: breathe in the good stuff, breathe out the small stuff.",
    "calm: small thing, big feelings. that's the brain, not you. one breath, then one step.",
    "calm: frustrated? it's allowed. shrink it to the next tiny thing.",
]
KINDS = ("gratitude", "family", "geek", "dream", "vibes", "calm")


def parse(line):
    """'family: go hug wifey' -> ('family', 'go hug wifey'). A line with no known kind is a geek-out."""
    kind, sep, text = str(line).partition(":")
    if sep and kind.strip().lower() in KINDS:
        return kind.strip().lower(), text.strip()
    return "geek", str(line).strip()


class MomentsMixin:
    def _start_moment(self):
        kind, text = parse(self.data.get("text") or random.choice(self.moments or MOMENTS))
        self.data["kind"], self.data["line"] = kind, text
        self.dur = max(5.2, 2.6 + len(text) / 13)
        self.say(text, life=self.dur - 0.5)
        if kind == "family":
            self.fx.heart(*self._head_xy(0, -70))

    def _moment(self, dt):
        t, d = self.t, self.data
        kind = d["kind"]
        talk = min(self.dur - 1.0, 0.8 + len(d["line"]) / 14)
        talking = 0.3 < t < talk
        br = math.sin(t * 2.0)
        pose = Pose(bob=br * 1.0, look_x=0.4, smile=0.85)
        if kind != "calm":
            pose.mouth_open = (0.18 + 0.22 * abs(math.sin(t * 9))) if talking else 0.0
        getattr(self, "_moment_" + kind)(pose, t, br, talking)
        return pose

    def _moment_gratitude(self, pose, t, br, talking):
        """A hand on his heart, a small bow, eyes soft."""
        a = ease(min(1.0, t / 0.6))
        pose.sh_f, pose.el_f, pose.hand_f = lerp(8, 40, a), lerp(16, -122, a), "open"
        pose.sh_b, pose.el_b = -10, 14
        pose.lean, pose.head = 5 * a, 6 * a + 2 * math.sin(t * 1.4)
        pose.eyes, pose.blush, pose.smile, pose.look_x = "happy", 0.8, 1.0, 0.1
        self._every("heart", 1.3, lambda: self.fx.heart(*self._head_xy(random.uniform(-25, 25), -70)))

    def _moment_family(self, pose, t, br, talking):
        """Arms wrapped around someone who isn't there, swaying, hearts floating up."""
        a = ease(min(1.0, t / 0.7))
        hug(pose)
        pose.sh_f, pose.el_f = lerp(8, pose.sh_f, a), lerp(16, pose.el_f, a)
        sway = math.sin(t * 1.5)
        pose.lean, pose.head, pose.hat = 5 * sway, 8 * sway, -4 * sway
        pose.hip_f, pose.hip_b = 5 * sway, -5 * sway
        pose.eyes, pose.blush, pose.smile = "happy", 0.9, 1.0
        self._every("heart", 0.6, lambda: self.fx.heart(*self._head_xy(random.uniform(-35, 35), -70)))

    def _moment_geek(self, pose, t, br, talking):
        """Bouncing, hands going everywhere, eyes sparkling: the research-rabbit-hole face."""
        hop = abs(math.sin(t * 4.2))
        pose.bob = 3 * hop - 1
        pose.knee_f, pose.knee_b = 8 + 14 * hop, 8 + 14 * hop
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 70 + 40 * math.sin(t * 5.3), 40 + 30 * math.sin(t * 4.1), 1.3, "open"
        pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -70 - 40 * math.sin(t * 4.7), -40 - 30 * math.sin(t * 5.9), 1.3, "open"
        pose.brow, pose.sparkle, pose.blush, pose.look_x = 0.9, 0.7, 0.6, 0.7
        pose.head, pose.lean = 6 * math.sin(t * 3.3), 4 * math.sin(t * 2.1)
        self._every("spark", 0.22, lambda: self.fx.sparkle(*self._head_xy(random.uniform(-45, 45), -55), speed=60))

    def _moment_dream(self, pose, t, br, talking):
        """Staring off at the horizon, one arm out toward it, stars in his eyes."""
        a = ease(min(1.0, t / 0.8))
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = lerp(8, 125, a), lerp(16, 6, a), 1.0 + 0.35 * a, "point"
        pose.sh_b, pose.el_b = -20, 30
        pose.look_x, pose.look_y, pose.head, pose.lean = 1.0, -0.5, -5 * a, 3 * a
        pose.sparkle, pose.smile, pose.brow = 0.8, 0.9, 0.4
        self._every("note", 1.1, lambda: self.fx.sparkle(*self._xy(self._anchor("hand_f")), speed=45))

    def _moment_vibes(self, pose, t, br, talking):
        """Palms up, drifting an inch off the floor, spores floating from the mushroom."""
        a = ease(min(1.0, t / 0.8))
        palms_up(pose)
        pose.lift = (7 + 3 * math.sin(t * 1.5)) * a
        pose.eyes = "closed" if t > 1.0 and not talking else "happy"
        pose.smile, pose.blush, pose.head = 0.9, 0.5, 3 * math.sin(t * 0.9)
        m = self._anchor("mushroom")
        self._every("spore", 0.5, lambda: self.fx.spore(m.x(), m.y()))

    def _moment_calm(self, pose, t, br, talking):
        """One slow, deep breath: arms rise on the inhale and sink on the exhale."""
        breath = (1 - math.cos(min(1.0, t / 3.6) * math.tau)) / 2   # up and back down over ~3.6 s
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 10 + 95 * breath, 18 - 5 * breath, 1 + 0.2 * breath, "open"
        pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -12 - 95 * breath, -18 + 5 * breath, 1 + 0.2 * breath, "open"
        pose.sy, pose.lean, pose.head = 1 + 0.04 * breath, -4 * breath, -5 * breath
        pose.eyes = "closed" if 0.6 < t < 3.9 else "open"
        pose.smile, pose.blush, pose.mouth_open = 0.5, 0.4, 0.0
