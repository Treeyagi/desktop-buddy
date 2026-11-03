"""Little particle effects around the buddy: hummed music notes, sparkles,
hearts, falling leaves, dust puffs, snore z's, tear drops, glowing spores from
the mushroom on his hat, and flowers and toadstools that sprout from the
floor. Everything is in screen pixels."""
import math
import random

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QFont, QPainterPath, QPainter

from character.rig import INK, LEAF, NO_PEN, TEAR, _pen, draw_leaf, draw_mushroom, star_polygon

NOTE_COLORS = [QColor(255, 120, 176), QColor(110, 196, 255), QColor(255, 206, 70),
               QColor(140, 228, 130), QColor(196, 146, 255)]
SPARKLE_COLORS = [QColor(255, 236, 120), QColor(190, 255, 170), QColor(255, 255, 255),
                  QColor(150, 230, 255)]
FLOWER_COLORS = [QColor(255, 120, 170), QColor(255, 210, 70), QColor(180, 140, 255),
                 QColor(255, 150, 90), QColor(120, 200, 255)]


class Particle:
    __slots__ = ("kind", "x", "y", "vx", "vy", "life", "age", "size", "color",
                 "text", "rot", "vr", "seed")

    def __init__(self, kind, x, y, vx=0.0, vy=0.0, life=1.5, size=1.0, color=None, text=""):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.life, self.age, self.size, self.color, self.text = life, 0.0, size, color, text
        self.rot = random.uniform(-20, 20)
        self.vr = random.uniform(-60, 60)
        self.seed = random.uniform(0, math.tau)

    def alpha(self):
        k = self.age / self.life
        fade_in = min(1.0, self.age / 0.12)
        fade_out = 1.0 if k < 0.65 else max(0.0, 1 - (k - 0.65) / 0.35)
        return fade_in * fade_out


def _ease_back(k):
    k = max(0.0, min(1.0, k))
    c = 1.9
    return 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2


class Effects:
    def __init__(self, scale=1.0):
        self.scale = scale
        self.items = []
        self._fonts = {}

    # spawners -------------------------------------------------------------
    def note(self, x, y):
        s = self.scale
        self.items.append(Particle("note", x, y, random.uniform(-18, 18) * s, -48 * s,
                                   life=random.uniform(1.8, 2.6), size=random.uniform(0.8, 1.25),
                                   color=random.choice(NOTE_COLORS), text=random.choice("♪♫♪♬")))

    def sparkle(self, x, y, speed=70.0):
        a = random.uniform(0, math.tau)
        v = random.uniform(0.4, 1.0) * speed * self.scale
        self.items.append(Particle("sparkle", x, y, math.cos(a) * v, math.sin(a) * v - 15 * self.scale,
                                   life=random.uniform(0.7, 1.3), size=random.uniform(0.6, 1.3),
                                   color=random.choice(SPARKLE_COLORS)))

    def heart(self, x, y):
        s = self.scale
        self.items.append(Particle("heart", x, y, random.uniform(-14, 14) * s, -40 * s,
                                   life=random.uniform(1.8, 2.4), size=random.uniform(0.8, 1.2),
                                   color=QColor(255, 96, 146)))

    def leaf(self, x, y):
        s = self.scale
        self.items.append(Particle("leaf", x, y, random.uniform(-15, 15) * s, 26 * s,
                                   life=random.uniform(3.0, 4.5), size=random.uniform(0.8, 1.2),
                                   color=random.choice([LEAF, QColor(150, 214, 90), QColor(232, 190, 70)])))

    def dust(self, x, y, n=6):
        s = self.scale
        for i in range(n):
            side = -1 if i % 2 else 1
            self.items.append(Particle("dust", x + side * random.uniform(4, 16) * s, y,
                                       side * random.uniform(30, 80) * s, -random.uniform(8, 30) * s,
                                       life=random.uniform(0.45, 0.7), size=random.uniform(0.7, 1.2)))

    def zz(self, x, y):
        s = self.scale
        self.items.append(Particle("text", x, y, 14 * s, -26 * s, life=2.4,
                                   size=random.uniform(0.8, 1.2), color=QColor(150, 190, 255), text="z"))

    def bang(self, x, y, text="!"):
        self.items.append(Particle("bang", x, y, 0, -10 * self.scale, life=1.1, size=1.3,
                                   color=QColor(255, 220, 60), text=text))

    def sprout(self, x, floor, mushroom=False):
        q = Particle("sprout", x, floor, life=random.uniform(18, 26), size=random.uniform(0.8, 1.25),
                     color=random.choice(FLOWER_COLORS))
        q.text = "mushroom" if mushroom else ""
        self.items.append(q)

    def tear(self, x, y, side):
        s = self.scale
        self.items.append(Particle("tear", x, y, side * random.uniform(30, 70) * s,
                                   -random.uniform(40, 90) * s, life=random.uniform(0.7, 1.0),
                                   size=random.uniform(0.8, 1.2), color=TEAR))

    def spore(self, x, y):
        s = self.scale
        a = random.uniform(-math.pi, 0)
        v = random.uniform(20, 60) * s
        self.items.append(Particle("spore", x, y, math.cos(a) * v, math.sin(a) * v,
                                   life=random.uniform(1.4, 2.4), size=random.uniform(0.6, 1.2),
                                   color=random.choice([QColor(200, 255, 170), QColor(255, 236, 140),
                                                        QColor(255, 180, 220)])))

    # simulation -----------------------------------------------------------
    def update(self, dt):
        alive = []
        for q in self.items:
            q.age += dt
            if q.age >= q.life:
                continue
            q.rot += q.vr * dt
            if q.kind == "note" or q.kind == "heart":
                q.x += (q.vx + math.sin(q.age * 4 + q.seed) * 22 * self.scale) * dt
                q.y += q.vy * dt
            elif q.kind == "leaf":
                q.x += (q.vx + math.sin(q.age * 2.5 + q.seed) * 40 * self.scale) * dt
                q.y += q.vy * dt
                q.rot = math.sin(q.age * 2.5 + q.seed) * 50
            elif q.kind == "tear":
                q.vy += 420 * self.scale * dt
                q.x += q.vx * dt
                q.y += q.vy * dt
            elif q.kind == "spore":
                q.vx *= 1 - 1.2 * dt
                q.vy = q.vy * (1 - 1.2 * dt) + 8 * self.scale * dt
                q.x += (q.vx + math.sin(q.age * 3 + q.seed) * 12 * self.scale) * dt
                q.y += q.vy * dt
            elif q.kind in ("sparkle", "dust"):
                q.vx *= 1 - 2.5 * dt
                q.vy *= 1 - 2.5 * dt
                q.x += q.vx * dt
                q.y += q.vy * dt
            elif q.kind != "sprout":
                q.x += q.vx * dt
                q.y += q.vy * dt
            alive.append(q)
        self.items = alive

    def bounds(self):
        r = QRectF()
        pad = 40 * self.scale
        for q in self.items:
            if q.kind == "sprout":
                box = QRectF(q.x - pad, q.y - 70 * self.scale * q.size, 2 * pad, 76 * self.scale * q.size)
            else:
                box = QRectF(q.x - pad, q.y - pad, 2 * pad, 2 * pad)
            r = r.united(box)
        return r

    # drawing --------------------------------------------------------------
    def _font(self, px):
        px = max(6, int(px))
        if px not in self._fonts:
            f = QFont()
            f.setPixelSize(px)
            f.setBold(True)
            self._fonts[px] = f
        return self._fonts[px]

    def draw(self, p):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.scale
        for q in self.items:
            a = q.alpha()
            if a <= 0:
                continue
            p.setOpacity(a)
            p.save()
            p.translate(q.x, q.y)
            getattr(self, "_draw_" + q.kind)(p, q, s)
            p.restore()
        p.restore()

    def _text(self, p, q, px, outline=2.2):
        path = QPainterPath()
        path.addText(0, 0, self._font(px), q.text)
        c = path.boundingRect().center()
        p.translate(-c.x(), -c.y())
        p.setPen(_pen(INK, outline))
        p.setBrush(q.color)
        p.drawPath(path)

    def _draw_note(self, p, q, s):
        p.rotate(q.rot * 0.4)
        self._text(p, q, 24 * s * q.size)

    def _draw_text(self, p, q, s):
        p.rotate(-12)
        self._text(p, q, (16 + 10 * q.age / q.life) * s * q.size, 1.8)

    def _draw_bang(self, p, q, s):
        pop = _ease_back(q.age / 0.25)
        p.scale(pop, pop)
        self._text(p, q, 34 * s * q.size, 2.6)

    def _draw_sparkle(self, p, q, s):
        tw = 0.6 + 0.4 * math.sin(q.age * 18 + q.seed)
        r = 7 * s * q.size * tw
        p.setPen(_pen(INK, 1.0))
        p.setBrush(q.color)
        p.drawPolygon(star_polygon(0, 0, r, points=4, inner=0.3, spin=q.rot * 0.02))

    def _draw_heart(self, p, q, s):
        k = 9 * s * q.size * (0.85 + 0.15 * math.sin(q.age * 10))
        p.scale(k / 10, k / 10)
        path = QPainterPath(QPointF(0, 8))
        path.cubicTo(-12, 0, -10, -10, 0, -5)
        path.cubicTo(10, -10, 12, 0, 0, 8)
        p.setPen(_pen(INK, 2.0))
        p.setBrush(q.color)
        p.drawPath(path)
        p.setPen(NO_PEN)
        p.setBrush(QColor(255, 255, 255, 170))
        p.drawEllipse(QPointF(-5, -4), 2.2, 1.6)

    def _draw_leaf(self, p, q, s):
        draw_leaf(p, QPointF(0, 0), q.rot, 13 * s * q.size, q.color)

    def _draw_dust(self, p, q, s):
        r = (4 + 12 * q.age / q.life) * s * q.size
        p.setPen(NO_PEN)
        p.setBrush(QColor(235, 230, 245, 170))
        p.drawEllipse(QPointF(0, 0), r, r * 0.8)

    def _draw_tear(self, p, q, s):
        r = 3.2 * s * q.size
        drop = QPainterPath(QPointF(0, -r * 1.8))
        drop.cubicTo(r * 0.9, -r * 0.4, r, r * 0.9, 0, r)
        drop.cubicTo(-r, r * 0.9, -r * 0.9, -r * 0.4, 0, -r * 1.8)
        p.setPen(_pen(INK, 1.2))
        p.setBrush(q.color)
        p.drawPath(drop)
        p.setPen(NO_PEN)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(QPointF(-r * 0.3, 0), r * 0.25, r * 0.4)

    def _draw_spore(self, p, q, s):
        r = 3 * s * q.size * (0.8 + 0.2 * math.sin(q.age * 9 + q.seed))
        c = QColor(q.color)
        c.setAlpha(90)
        p.setPen(NO_PEN)
        p.setBrush(c)
        p.drawEllipse(QPointF(0, 0), r * 2.2, r * 2.2)
        p.setBrush(q.color)
        p.drawEllipse(QPointF(0, 0), r, r)

    def _draw_sprout(self, p, q, s):
        if q.text == "mushroom":
            g = _ease_back(q.age / 0.9)
            if g > 0.02:
                draw_mushroom(p, 0, 0, 0.9 * s * q.size * g,
                              cap=q.color if q.seed > 3 else QColor(228, 52, 48))
            return
        g = _ease_back(q.age / 1.1)
        h = 34 * s * q.size * g
        if h <= 0.5:
            return
        stem = QPainterPath(QPointF(0, 0))
        stem.quadTo(5 * s, -h * 0.5, 0, -h)
        p.setPen(_pen(INK, 5 * s))
        p.drawPath(stem)
        p.setPen(_pen(LEAF, 3 * s))
        p.drawPath(stem)
        leaf = 11 * s * q.size * g
        draw_leaf(p, QPointF(1.5 * s, -h * 0.45), -30 + math.sin(q.age * 2 + q.seed) * 6, leaf)
        draw_leaf(p, QPointF(1.5 * s, -h * 0.55), -150 - math.sin(q.age * 2 + q.seed) * 6, leaf * 0.9)
        bloom = _ease_back((q.age - 0.8) / 0.5)
        if bloom > 0:
            top = QPointF(0, -h)
            r = 5 * s * q.size * bloom
            p.setPen(_pen(INK, 1.4))
            p.setBrush(q.color)
            for i in range(5):
                a = q.seed + i * math.tau / 5 + math.sin(q.age * 1.5) * 0.15
                p.drawEllipse(top + QPointF(math.cos(a), math.sin(a)) * r * 1.05, r * 0.75, r * 0.75)
            p.setBrush(QColor(255, 226, 90))
            p.drawEllipse(top, r * 0.6, r * 0.6)
