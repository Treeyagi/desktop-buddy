"""The sprite character: Treeyagi, from his character pack v2.9 (character/sprites/treeyagi/).

An alternative to the vector rig (settings: "character"). 29 animations in eight directions (frames and
timings in anims.json): empty-handed everyday ones plus the wand ones (draw, holster, charge, attack). Most
are cut from the pack's high-resolution source sheets; charge and attack only exist at 128 px in the pack, so
they are drawn bigger and a little softer. Each action has its own anchor (ax, ay), feet line and draw size.

`anim_for()` maps every Buddy state onto an animation and a view. The wand only ever appears around the
wand states: when a state wants it and he doesn't have it out, he plays draw_wand first, and when he is
done with it, holster_wand. Only air (carried, perched) lifts him; the sprites hop and lean in their own art, and animation changes crossfade.
"""
import json
import math
import os

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QPixmap

from character.gamestop import CONSOLES

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites", "treeyagi")
with open(os.path.join(DIR, "anims.json")) as _f:
    ANIMS = json.load(_f)["anims"]
_frames = {}

VIEWS = {"side": ("E", "W"), "three": ("SE", "SW"), "front": ("S", "S"), "back": ("N", "N")}
DANCES = ["dance_groove", "dance_shuffle", "dance_disco"]   # one move cycle per beat, a new style every four beats
BEAT = 60.0 / 126.0
ARMED = {"charge", "attack"}


def frame(action, direction, n):
    key = (action, direction, n)
    if key not in _frames:
        _frames[key] = QPixmap(os.path.join(DIR, action, direction, f"{n:02d}.png"))
    return _frames[key]


class Anim:
    """What to draw: an action, a view, and how to pick the frame: a walk phase, a fixed frame, a progress
    (0..1 through the state, mapped over the frames) or plain time. Plus a little extra tilt/lift."""
    def __init__(self, action, view="three", t=0.0, phase=None, frame=None, prog=None, speed=1.0, tilt=0.0, up=0.0):
        self.action, self.view, self.t, self.phase, self.frame, self.prog = action, view, t, phase, frame, prog
        self.speed, self.tilt, self.up = speed, tilt, up


def _prog(t, dur):
    return max(0.0, min(0.999, t / dur)) if dur else 0.0


def anim_for(b):
    """Maps the Buddy's current state onto the pack's animations (b is the Buddy)."""
    st, t, d = b.state, b.t, b.data
    sin = math.sin
    dur = getattr(b, "dur", 0) or 0
    if st == "walk":
        cycle = 125.0 if d.get("mood") == "sad" else 140.0   # ground covered by one full walk cycle, so his feet don't slide
        phase = getattr(b, "_spr_dist", 0.0) / (cycle * b.scale) * math.tau
        return Anim("sad_walk" if d.get("mood") == "sad" else "walk", "side", phase=phase)
    if st == "chase":
        return Anim("sprint", "side", t=t)
    if st == "pounce":
        return Anim("dodge", "side", prog=_prog(t, dur))
    if st == "gs_madness":
        if d.get("hop", 1.0) < 1.0:   # dodging whatever closes in
            return Anim("dodge", "side", prog=d["hop"])
        return Anim("sprint", "side", t=t)
    if st == "dance":
        clip = DANCES[int(t / (4 * BEAT)) % 3]
        return Anim(clip, "front", t=t, speed=sum(ANIMS[clip]["ms"]) / 1000.0 / BEAT)
    if st == "jump":
        return Anim("dodge", "three", prog=_prog(t, 1.25))
    if st == "wave":
        return Anim("wave", "three", t=t)
    if st in ("quip", "answer", "moment", "nudge"):
        return Anim("talk", "front", t=t)
    if st in ("listen", "think", "focus_sit"):
        return Anim("think", "front", t=t)
    if st == "spores":
        return Anim("charge", "three", t=t)
    if st == "stretch":
        return Anim("stretch", "front", prog=_prog(t, dur))
    if st == "meditate":
        return Anim("meditate", "front", t=t)
    if st == "nap":
        return Anim("nap", "front", t=t)
    if st == "sulk":
        return Anim("sulk", "front", t=t)
    if st in ("notice", "tangent"):    # something caught his eye
        return Anim("hurt", "three", frame=0) if t < 0.7 else Anim("shrug", "three", prog=_prog(t - 0.7, max(1.0, dur - 0.7)))
    if st == "spot_icon":
        return Anim("hurt", "three", frame=0)
    if st == "spot_machine":
        return Anim("victory", "front", prog=_prog(t, dur or 1.5))
    if st == "perch":   # sitting on a window with his back to you, watching the desktop
        return Anim("window_sit", "back", t=t)
    if st == "fly":     # carried by the bees
        return Anim("bee_carry", "front", t=t)
    if st == "kroger":  # crouching over the find, holding it up
        return Anim("clearance_inspect", "side", prog=_prog(t, dur))
    if st == "vending":
        if t < 4.6:
            return Anim("think", "side", t=t)
        return Anim("victory" if d.get("joy") else "sad_slump", "front", prog=_prog(t - 4.6, 2.0))
    if st == "gs_roll":
        m = getattr(b, "gs", {}).get("machine")
        if m is not None and m.pull_t is not None:   # at the lever
            return Anim("lever_pull", "side", prog=_prog(m.pull_t, 0.6))
        if t < 1.3:
            return Anim("shrug", "side", prog=_prog(t, 1.3))
        if m is not None and m.stopped:
            prized = CONSOLES[b.gs["idx"]][2] >= 150   # losing a valuable one hurts
            return Anim("sad_slump" if prized else "shrug", "three", prog=_prog(t - 4.8, 2.0))
        return Anim("think", "side", t=t)
    if st == "gs_scalper":
        if 8.2 < t < 10.4:       # the headshake
            return Anim("shrug", "side", t=t, speed=2.0)
        return Anim("think" if 3.4 < t < 8.2 else "idle", "side", t=t)
    if st == "gs_door":
        end, sold = d.get("end"), d.get("sold")
        if t < 1.5:
            return Anim("sad_walk", "side", t=t, speed=2.0)   # out of breath
        if sold and end == "pittance":
            return Anim("sad_slump", "three", prog=_prog(t - 8.2, 1.5))
        if sold and end == "bonus":
            return Anim("victory", "front", prog=_prog(t - 7.4, 1.5)) if t < 11.4 else Anim("dance_disco", "front", t=t,
                                                                                         speed=sum(ANIMS["dance_disco"]["ms"]) / 1000.0 / BEAT)
        if end == "keep" and t > 8.2:
            return Anim("sulk", "front", t=t)
        return Anim("talk" if t > 3.6 else "idle", "side", t=t)
    if st == "idle":
        kind = d.get("kind")
        if kind == "yawn":
            return Anim("stretch", "front", prog=_prog(t, dur))
        if kind == "choose":     # "I choose you!": wand out, then the swing
            return Anim("attack", "side", t=max(0.0, t - 3.0)) if t > 3.0 else Anim("charge", "side", t=t)
        if kind == "box":
            return Anim("attack", "side", t=t * 1.4, speed=1.0)
    return Anim("idle", "three", t=t)


def pick(action, t, phase=None, frame=None, prog=None):
    a = ANIMS[action]
    count = len(a["ms"])
    if frame is not None:
        return min(frame, count - 1)
    if prog is not None:
        return min(count - 1, int(prog * count))
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


def _wand_transition(b):
    """The wand is only in his hand around the wand animations. Returns ('draw_wand'|'holster_wand', seconds)
    while he is pulling it out or putting it away, else None."""
    st = b.__dict__.setdefault("_wand", {"armed": False, "play": None, "t": 0.0})
    want = anim_for(b).action in ARMED
    dt = getattr(b, "_dt", 1 / 60)
    if st["play"]:
        st["t"] += dt
        if st["t"] * 1000 >= sum(ANIMS[st["play"]]["ms"]):
            st["armed"] = st["play"] == "draw_wand"
            st["play"] = None
    if not st["play"]:
        if want and not st["armed"]:
            st["play"], st["t"] = "draw_wand", 0.0
        elif not want and st["armed"]:
            st["play"], st["t"] = "holster_wand", 0.0
    return (st["play"], st["t"]) if st["play"] else None


FADE = 0.12   # seconds to crossfade when the animation or direction changes


def _ground(b, an):
    """How far off the floor he is, in rig units. The sprites already hop, crouch and lean in their own art,
    so the old rig's jump/bob/lean are not applied; only being carried or perched lifts him."""
    air = getattr(b, "air", 0.0)
    if an.action == "window_sit":     # the seat sits on the title bar
        return air + 12 * max(0.0, min(1.0, b.pose.bob / 26.0))
    if an.action == "meditate":       # a gentle float
        return air + 5 * (1 + math.sin(b.clock * 1.3))
    return air + an.up


def draw_sprite(p, x, floor, facing, scale, pose, buddy):
    st = buddy.__dict__.setdefault("_spr", {"key": None, "old": None, "fade": 1.0, "last": None, "x": x, "dist": 0.0})
    st["dist"] += abs(x - st["x"])
    st["x"] = x
    buddy._spr_dist = st["dist"]
    an = anim_for(buddy)
    trans = _wand_transition(buddy)
    if trans:
        an = Anim(trans[0], "three", t=trans[1])
    direction = VIEWS[an.view][0 if facing > 0 else 1]
    pm = frame(an.action, direction, pick(an.action, an.t * an.speed, an.phase, an.frame, an.prog))
    if pm.isNull():
        return
    a = ANIMS[an.action]
    anchor = a["feet"] if an.action == "bee_carry" else a["ay"]   # carried by the bees: hang by the feet line
    cur = (pm, a["ax"], anchor, a["size"])
    key = (an.action, direction)
    if key != st["key"]:
        if st["last"] is not None:
            st["old"], st["fade"] = st["last"], 0.0
        st["key"] = key
    st["last"] = cur
    st["fade"] = min(1.0, st["fade"] + getattr(buddy, "_dt", 1 / 60) / FADE)
    sx = 1.0
    if buddy.turn_t < 0.22:   # turning around: a quick squash, as in the cartoon
        sx = 1 - 0.28 * math.sin(min(1.0, buddy.turn_t / 0.22) * math.pi)
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(x, floor - _ground(buddy, an) * scale)
    p.rotate(an.tilt * facing)
    if st["old"] is not None and st["fade"] < 1.0:
        opm, oax, oay, osize = st["old"]
        p.save()
        p.setOpacity(1.0 - st["fade"])
        p.scale(sx * scale * osize, scale * osize)
        p.drawPixmap(QPointF(-oax, -oay), opm)
        p.restore()
        p.setOpacity(st["fade"])
    p.scale(sx * scale * a["size"], scale * a["size"])
    p.drawPixmap(QPointF(-a["ax"], -anchor), pm)
    p.restore()


def thumbnail():
    """A standing frame for the settings picker."""
    return frame("idle", "SE", 0)
