"""The sprite character: Treeyagi, from his character pack (character/sprites/treeyagi/).

An alternative to the vector rig (settings: "character"). The pack has seven actions in eight directions
(idle, walk, skip, charge, attack, hurt, faint; frames and timings in anims.json). Walk, idle, skip, charge,
hurt and faint are cut from the pack's high-resolution source sheets (about 216 px tall); attack only exists
in the pack at 128 px, so it is drawn bigger and softer. Each action has its own anchor (ax, ay) and size. The Buddy's states map onto them in `anim_for`; the pose's lift, bob,
squash and lean still move the whole picture, so jumps and squashes work. Walking is driven by the walk
phase so his feet plant; the rest play on their own clocks.
"""
import json
import math
import os

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QPixmap

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites", "treeyagi")
with open(os.path.join(DIR, "anims.json")) as _f:
    _meta = json.load(_f)
ANIMS = _meta["anims"]
_frames = {}


def frame(action, direction, n):
    key = (action, direction, n)
    if key not in _frames:
        _frames[key] = QPixmap(os.path.join(DIR, action, direction, f"{n:02d}.png"))
    return _frames[key]


class Anim:
    """What to draw this frame: an action, a view (side | three | front | back), a time or walk phase or a
    fixed frame, and extra wobble (degrees of tilt, pixels up) for things the pack has no art for."""
    def __init__(self, action, view="three", t=0.0, phase=None, frame=None, speed=1.0, tilt=0.0, up=0.0):
        self.action, self.view, self.t, self.phase, self.frame = action, view, t, phase, frame
        self.speed, self.tilt, self.up = speed, tilt, up


def anim_for(b):
    """Maps the Buddy's current state onto the pack's animations (b is the Buddy)."""
    st, t, d = b.state, b.t, b.data
    sin = math.sin
    if st == "walk":
        sad = d.get("mood") == "sad"
        return Anim("walk", "side", phase=d.get("phase", 0.0), tilt=5 if sad else 0, up=-2 if sad else 0)
    if st in ("chase", "pounce"):
        return Anim("skip" if st == "pounce" else "walk", "side", t=t, phase=d.get("phase") if st == "chase" else None)
    if st == "gs_madness":
        if d.get("hop", 1.0) < 1.0:   # dodging: a hop
            return Anim("skip", "side", frame=1)
        return Anim("walk", "side", phase=d.get("phase", 0.0), tilt=8)
    if st == "dance":
        return Anim("skip", "three", t=t, speed=0.4 * 126 / 60,   # one skip cycle (0.4 s) per beat (60/126 s)
                     tilt=4 * sin(t * math.tau * 126 / 120))
    if st == "jump":
        return Anim("skip", "side", frame=0 if t < 0.25 else 1 if t < 0.9 else 2)
    if st == "wave":   # the wand raised above his hat, wiggling
        return Anim("attack", "side", frame=2, tilt=7 * sin(t * 14))
    if st in ("listen", "think", "spores", "focus_sit"):
        return Anim("charge", "front" if st != "spores" else "three", t=t)
    if st in ("answer", "quip", "moment", "nudge"):   # talking to you: front on, bobbing along
        return Anim("idle", "front", t=t, up=2 * abs(sin(t * 7)))
    if st == "nap":
        return Anim("faint", "side", t=t)
    if st == "sulk":
        return Anim("idle", "three", t=t, tilt=7, up=-4)   # slumped; he only has grins to work with
    if st in ("notice", "spot_icon", "spot_machine", "tangent"):   # caught his eye: a little start
        return Anim("skip", "three", frame=1 if t < 0.4 else None, t=t)
    if st == "perch":   # sitting on a window with his back to you, watching the desktop
        return Anim("idle", "back", t=t)
    if st == "fly":     # dangling from the bees
        return Anim("idle", "front", t=t, tilt=6 * sin(b.clock * 3.2))
    if st == "gs_roll":
        m = b.gs.get("machine")
        if m is not None and m.lever > 0:   # pulling the lever
            return Anim("attack", "side", frame=0 if m.lever < 0.3 else 3)
        return Anim("idle", "side", t=t)
    if st == "gs_scalper":
        return Anim("idle", "side", t=t, tilt=6 * sin(t * 16) if 8.2 < t < 10.4 else 0)
    if st == "gs_door":
        end, sold = d.get("end"), d.get("sold")
        if sold and end == "pittance":
            return Anim("hurt", "three", frame=1)
        if sold and end == "bonus":
            return Anim("skip", "three", t=t)
        return Anim("idle", "side", t=t)
    if st == "idle" and d.get("kind") in ("choose", "box"):
        return Anim("attack", "side", t=t)
    return Anim("idle", "three", t=t)


def pick(action, t, phase, frame=None):
    a = ANIMS[action]
    count = len(a["ms"])
    if frame is not None:
        return min(frame, count - 1)
    if phase is not None:
        return int(phase / (2 * math.pi) * count) % count
    total = sum(a["ms"])
    ms = t * 1000.0
    if a["loop"]:
        ms %= total
    elif ms >= total:
        return count - 1
    for i, d in enumerate(a["ms"]):
        if ms < d:
            return i
        ms -= d
    return count - 1


VIEWS = {"side": ("E", "W"), "three": ("SE", "SW"), "front": ("S", "S"), "back": ("N", "N")}


def draw_sprite(p, x, floor, facing, scale, pose, buddy):
    an = anim_for(buddy)
    direction = VIEWS[an.view][0 if facing > 0 else 1]
    pm = frame(an.action, direction, pick(an.action, an.t * an.speed, an.phase, an.frame))
    if pm.isNull():
        return
    a = ANIMS[an.action]
    k = scale * a["size"]
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(x, floor - (pose.lift - pose.bob + an.up) * scale)
    p.rotate((pose.lean * 0.5 + pose.head * 0.4) * facing + an.tilt * facing)
    p.scale(pose.sx * k, pose.sy * k)
    p.drawPixmap(QPointF(-a["ax"], -a["ay"]), pm)
    p.restore()


def thumbnail():
    """A standing frame for the settings picker."""
    return frame("idle", "SE", 0)
