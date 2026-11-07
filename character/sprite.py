"""The sprite character: Inzo, a hand-drawn walk sheet (8 directions x 6 frames) in character/sprites/inzo/.

An alternative to the vector rig (settings: "character"). He only has walk frames, so walking plays the
cycle on the side rows, and everything else is a front or three-quarter view with the pose's lift, bob,
squash and lean applied to the whole picture. Rows: 0 front, 1 front 3/4 right, 2 side right, 3 back 3/4 right,
4 back, 5 back 3/4 left, 6 side left, 7 front 3/4 left.
"""
import math
import os

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPainter, QPixmap

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprites", "inzo")
HEIGHT = 190.0   # drawn height at scale 1.0, a touch taller than a frame so he matches the cartoon's size
_frames = {}


def frame(row, col):
    key = (row, col % 6)
    if key not in _frames:
        _frames[key] = QPixmap(os.path.join(DIR, f"{key[0]}_{key[1]}.png"))
    return _frames[key]


def draw_sprite(p, x, floor, facing, scale, pose, phase=None, clock=0.0):
    """phase: walk-cycle phase (advances pi per step) while walking, else None."""
    if phase is not None:
        row = 2 if facing > 0 else 6
        col = int(phase / (2 * math.pi) * 6) % 6
    else:
        row, col = (1 if facing > 0 else 7), 1
    pm = frame(row, col)
    if pm.isNull():
        return
    k = scale * HEIGHT / 166.0
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(x, floor - (pose.lift - pose.bob) * scale)
    p.rotate(pose.lean * 0.5 * facing)
    p.scale(pose.sx * k, pose.sy * k)
    p.drawPixmap(QPointF(-pm.width() / 2, -pm.height()), pm)
    p.restore()


def thumbnail():
    """A front-facing frame for the settings picker."""
    return frame(0, 1)
