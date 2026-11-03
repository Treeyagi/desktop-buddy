"""Bumblebee buddies, from the reference card.

One companion bee hangs around him (orbits his head, naps on the mushroom on
his hat). Scenes can call in more: bees lift him up to the desktop icons and
carry glowing icon copies back and forth. Each bee chases a target point that
can move every frame; it flies there with a little wobble and buzzes off-screen
when dismissed.
"""
import math
import random

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QRadialGradient

from character.rig import INK, NO_BRUSH, NO_PEN, WHITE, _pen

YELLOW = QColor(255, 204, 44)
YELLOW_LIGHT = QColor(255, 236, 130)


class Bee:
    def __init__(self, x, y, scale, target=None):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.scale = scale
        self.target = target          # callable returning QPointF, or None to hover
        self.wiggle = 1.0             # how much it wanders around the target
        self.speed = 320.0            # px/s at scale 1
        self.seed = random.uniform(0, 100)
        self.face = 1
        self.flap = 0.0
        self.leaving = False
        self.gone = False
        self.size = random.uniform(0.9, 1.1)

    def arrived(self, slack=10.0):
        if not self.target:
            return True
        t = self.target()
        return math.hypot(t.x() - self.x, t.y() - self.y) < slack * self.scale

    def update(self, dt, clock, width, height):
        s = self.scale
        self.flap += dt * 55
        if self.target:
            t = self.target()
            w = self.wiggle * s
            tx = t.x() + math.sin(clock * 2.3 + self.seed) * 14 * w
            ty = t.y() + math.cos(clock * 3.1 + self.seed) * 9 * w
            dx, dy = tx - self.x, ty - self.y
            want = 5.0
            vx, vy = dx * want, dy * want
            top = self.speed * s
            mag = math.hypot(vx, vy)
            if mag > top:
                vx, vy = vx / mag * top, vy / mag * top
            k = min(1.0, dt * 7)
            self.vx += (vx - self.vx) * k
            self.vy += (vy - self.vy) * k
        self.x += self.vx * dt
        self.y += self.vy * dt + math.sin(clock * 7 + self.seed) * 6 * s * dt
        if abs(self.vx) > 12 * s:
            self.face = 1 if self.vx > 0 else -1
        if self.leaving and not (-80 < self.x < width + 80 and -80 < self.y < height + 80):
            self.gone = True

    def bounds(self):
        r = 22 * self.scale
        return QRectF(self.x - r, self.y - r, 2 * r, 2 * r)

    def draw(self, p):
        k = self.scale * self.size
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(self.x, self.y)
        p.scale(self.face * k, k)
        tilt = max(-14.0, min(14.0, self.vy * 0.04 / max(self.scale, 0.1)))
        p.rotate(tilt)
        beat = 0.35 + 0.65 * abs(math.sin(self.flap))
        p.setPen(_pen(QColor(30, 22, 40, 120), 1.2))
        p.setBrush(QColor(225, 244, 255, 175))
        for wx, ang in ((-3, -25), (3, 15)):
            p.save()
            p.translate(wx, -8)
            p.rotate(ang)
            p.drawEllipse(QPointF(0, -4 * beat), 4.5, 7 * beat)
            p.restore()
        body = QPainterPath()
        body.addEllipse(QPointF(0, 0), 10.5, 9)
        g = QRadialGradient(QPointF(3, -3), 12)
        g.setColorAt(0, YELLOW_LIGHT)
        g.setColorAt(1, YELLOW)
        p.setPen(NO_PEN)
        p.setBrush(QBrush(g))
        p.drawPath(body)
        p.save()
        p.setClipPath(body)
        p.setBrush(INK)
        p.drawRect(QRectF(-5.5, -10, 3.4, 20))
        p.drawRect(QRectF(-10.5, -10, 2.6, 20))
        p.restore()
        p.setPen(_pen(INK, 1.8))
        p.setBrush(NO_BRUSH)
        p.drawPath(body)
        stinger = QPainterPath(QPointF(-10, -1.5))
        stinger.lineTo(-14, 0.5)
        stinger.lineTo(-10, 2)
        p.setBrush(INK)
        p.drawPath(stinger)
        p.setPen(_pen(INK, 1.4))
        p.drawLine(QPointF(4, -7.5), QPointF(3, -13))
        p.drawLine(QPointF(7, -7), QPointF(9, -12.5))
        p.setPen(NO_PEN)
        p.drawEllipse(QPointF(3, -13.5), 1.6, 1.6)
        p.drawEllipse(QPointF(9.2, -13), 1.6, 1.6)
        p.drawEllipse(QPointF(3.5, -1.5), 1.9, 2.4)
        p.drawEllipse(QPointF(7.8, -1.5), 1.9, 2.4)
        p.setBrush(WHITE)
        p.drawEllipse(QPointF(3.1, -2.4), 0.7, 0.7)
        p.drawEllipse(QPointF(7.4, -2.4), 0.7, 0.7)
        p.setBrush(QColor(255, 130, 140, 170))
        p.drawEllipse(QPointF(1.5, 2), 1.6, 1.0)
        p.drawEllipse(QPointF(9.4, 2), 1.4, 1.0)
        p.setPen(_pen(INK, 1.2))
        p.setBrush(NO_BRUSH)
        p.drawArc(QRectF(3.4, 0.5, 4.4, 3), 200 * 16, 140 * 16)
        p.restore()


class Hive:
    """The bees around the buddy."""

    def __init__(self, scale):
        self.scale = scale
        self.bees = []
        self.buddy = None

    def spawn(self, target, from_edge=True):
        s = self.scale
        b = self.buddy
        if from_edge and b is not None:  # dive in from the top of the screen above him
            x = b.x + random.uniform(-220, 220) * s
            y = -30.0
        else:
            x, y = target().x(), target().y()
        bee = Bee(x, max(-30.0, y), s, target)
        self.bees.append(bee)
        return bee

    def dismiss(self, bee):
        b = self.buddy
        away = QPointF(-200 if bee.x < b.width / 2 else b.width + 200, bee.y - 300 * self.scale)
        bee.target = lambda: away
        bee.leaving = True
        bee.wiggle = 0.4

    def update(self, dt, clock, width, height):
        for bee in self.bees:
            bee.update(dt, clock, width, height)
        self.bees = [b for b in self.bees if not b.gone]

    def bounds(self):
        r = QRectF()
        for bee in self.bees:
            r = r.united(bee.bounds())
        return r

    def draw(self, p):
        for bee in self.bees:
            bee.draw(p)
