"""The sprite character: Treeyagi, from his character pack (character/sprites/treeyagi/).

An alternative to the vector rig (settings: "character"). The pack has seven actions in eight directions
(idle, walk, skip, charge, attack, hurt, faint; frames and timings in anims.json, ground baseline y=150,
anchor at half the frame width). The Buddy's states map onto them in `anim_for`; the pose's lift, bob,
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
BASELINE = _meta["baseline"]
ANIMS = _meta["anims"]
SIDE = {"walk", "skip", "attack"}   # these play in profile; the rest in front three-quarter view
SIZE = 190.0 / 128.0                # the character is 128 px tall inside its frame; draw him ~190 px tall at scale 1
_frames = {}


def frame(action, direction, n):
    key = (action, direction, n)
    if key not in _frames:
        _frames[key] = QPixmap(os.path.join(DIR, action, direction, f"{n:02d}.png"))
    return _frames[key]


def anim_for(buddy):
    """(action, seconds into it, walk phase or None) for what the Buddy is doing now."""
    st = buddy.state
    if st == "walk":
        return "walk", buddy.t, buddy.data.get("phase", 0.0)
    if st in ("gs_madness", "dance", "jump"):
        return "skip", buddy.t, None
    if st in ("spores", "listen", "think"):
        return "charge", buddy.t, None
    if st == "nap":
        return "faint", buddy.t, None
    if st == "idle" and buddy.data.get("kind") in ("choose", "box"):
        return "attack", buddy.t, None
    return "idle", buddy.t, None


def pick(action, t, phase):
    a = ANIMS[action]
    count = len(a["ms"])
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


def draw_sprite(p, x, floor, facing, scale, pose, buddy):
    action, t, phase = anim_for(buddy)
    side = "E" if facing > 0 else "W"
    direction = side if action in SIDE else ("SE" if facing > 0 else "SW")
    pm = frame(action, direction, pick(action, t, phase))
    if pm.isNull():
        return
    k = scale * SIZE
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(x, floor - (pose.lift - pose.bob) * scale)
    p.rotate(pose.lean * 0.5 * facing)
    p.scale(pose.sx * k, pose.sy * k)
    p.drawPixmap(QPointF(-pm.width() / 2, -BASELINE), pm)
    p.restore()


def thumbnail():
    """A standing frame for the settings picker."""
    return frame("idle", "SE", 0)
