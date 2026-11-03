"""Props the buddy plays with: clearance-aisle finds and the card vending
machine. All original designs (no real logos, brands or card art).

Items are drawn centered on (0, 0) about 40 units tall; the machine is drawn
with its feet at (0, 0). Both live in screen pixels like the effects.
"""
import math
import random

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter,
                         QPainterPath, QRadialGradient)

from character.rig import GOLD, INK, NO_PEN, WHITE, _pen, ease, star_polygon

ITEMS = ["gnome", "lava lamp", "cactus", "rubber duck", "mystery box"]
PRICES = ["$2.50", "$4.99", "$7.49", "$12.99", "$19.99"]
PACK_COLORS = [QColor(255, 110, 120), QColor(110, 190, 255), QColor(255, 200, 70),
               QColor(130, 220, 140), QColor(200, 140, 255), QColor(255, 150, 80)]

_fonts = {}


def font(px):
    px = max(5, int(px))
    if px not in _fonts:
        f = QFont()
        f.setPixelSize(px)
        f.setBold(True)
        _fonts[px] = f
    return _fonts[px]


def ease_back(k):
    k = max(0.0, min(1.0, k))
    return 1 + 2.7 * (k - 1) ** 3 + 1.7 * (k - 1) ** 2


class Item:
    def __init__(self, kind, x, y, scale, tag=True, pixmap=None):
        self.kind, self.scale, self.tag, self.pixmap = kind, scale, tag, pixmap
        self.math = None             # thought-cloud lines for "doing the math"
        self.x, self.y = x, y
        self.rest = QPointF(x, y)    # where it sits when not held
        self.grab = 0.0              # 0 resting .. 1 in the back hand
        self.hold = (26.0, -2.0)     # offset from the hand, rig units
        self.fly = None              # 0..1 while zipping into the hat
        self.fly_from = None
        self.fly_size = 1.0
        self.carrier = None          # a bee carrying it
        self.deliver_to = None       # where that bee drops it off (it fades out there)
        self.behind = False          # drawn behind him (the big card reveal)
        self.angle = 0.0
        self.size = 1.0
        self.pop = 0.0
        self.alpha = 1.0
        self.expire = None
        self.gone = False
        self.t = 0.0
        self.price = random.choice(PRICES)

    def update(self, dt):
        self.t += dt
        self.pop = min(1.0, self.pop + dt / 0.35)
        if self.expire is not None:
            self.expire -= dt
            self.alpha = max(0.0, min(1.0, self.expire / 0.6))
            if self.expire <= 0:
                self.gone = True

    def bounds(self):
        r = 40 * self.scale * self.size
        return QRectF(self.x - r, self.y - r * 1.3, 2 * r, 2.6 * r)

    def draw(self, p):
        k = self.scale * self.size * ease_back(self.pop)
        if self.alpha <= 0 or k <= 0.01:
            return
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self.alpha)
        p.translate(self.x, self.y)
        p.rotate(self.angle)
        p.scale(k, k)
        draw_item(p, self.kind, self.t, self.tag, self.pixmap)
        p.restore()


def draw_item(p, kind, t, tag=True, pixmap=None):
    if kind == "icon":
        _ItemArt.icon(p, t, pixmap)
    else:
        getattr(_ItemArt, kind.replace(" ", "_"))(p, t)
    if tag:
        p.save()
        p.translate(11, -6)
        p.rotate(18)
        p.setPen(_pen(INK, 1.3))
        p.setBrush(QColor(255, 226, 40))
        p.drawRoundedRect(QRectF(0, -5, 15, 10), 2, 2)
        p.setBrush(WHITE)
        p.drawEllipse(QPointF(3, 0), 1.3, 1.3)
        p.setFont(font(8))
        p.setPen(QColor(220, 30, 40))
        p.drawText(QRectF(4, -5, 11, 10), 0x0084, "%")
        p.restore()


class _ItemArt:
    @staticmethod
    def card(p, t):
        """The Ultimate Pull: an original holo card (no real card art)."""
        rect = QRectF(-15, -21, 30, 42)
        holo = QConicalGradient(QPointF(0, 0), (t * 90) % 360)
        for i, c in enumerate([QColor(255, 120, 200), QColor(255, 220, 90), QColor(140, 240, 160),
                               QColor(110, 200, 255), QColor(190, 140, 255), QColor(255, 120, 200)]):
            holo.setColorAt(i / 5, c)
        p.setPen(_pen(INK, 1.6))
        p.setBrush(QBrush(holo))
        p.drawRoundedRect(rect, 2.6, 2.6)
        art = QRectF(-12.5, -18.5, 25, 21)
        g = QLinearGradient(0, art.top(), 0, art.bottom())
        g.setColorAt(0, QColor(40, 20, 90))
        g.setColorAt(1, QColor(110, 50, 170))
        p.setPen(_pen(INK, 1))
        p.setBrush(QBrush(g))
        p.drawRect(art)
        p.save()
        p.setClipRect(art)
        p.setPen(NO_PEN)
        p.setBrush(QColor(255, 255, 255, 200))
        for sx, sy in ((-9, -15), (8, -14), (-6, -2), (10, -5), (2, -17), (-11, -8)):
            p.drawEllipse(QPointF(sx, sy), 0.6, 0.6)
        glow = QRadialGradient(QPointF(0, -8), 12)
        glow.setColorAt(0, QColor(255, 240, 160, 220))
        glow.setColorAt(1, QColor(255, 200, 80, 0))
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(0, -8), 12, 12)
        p.setPen(_pen(INK, 0.9))
        p.setBrush(GOLD)
        p.drawPolygon(star_polygon(0, -8, 7.5, spin=math.sin(t * 2) * 0.15))
        p.restore()
        p.setPen(_pen(INK, 0.8))
        p.setBrush(QColor(250, 246, 236))
        p.drawRect(QRectF(-12.5, 3.5, 25, 5))
        p.setFont(font(4))
        p.setPen(INK)
        p.drawText(QRectF(-12.5, 3.5, 25, 5), 0x0084, "ULTRA RARE")
        p.setPen(_pen(QColor(150, 140, 170), 0.9))
        for y in (11, 13.5, 16):
            p.drawLine(QPointF(-10, y), QPointF(10, y))
        p.save()  # holo shine sweeping across
        clip = QPainterPath()
        clip.addRoundedRect(rect, 2.6, 2.6)
        p.setClipPath(clip)
        x = -40 + ((t * 30) % 80)
        shine = QPainterPath(QPointF(x, -25))
        shine.lineTo(x + 8, -25)
        shine.lineTo(x - 6, 25)
        shine.lineTo(x - 14, 25)
        shine.closeSubpath()
        p.setPen(NO_PEN)
        p.setBrush(QColor(255, 255, 255, 90))
        p.drawPath(shine)
        p.restore()

    @staticmethod
    def icon(p, t, pixmap):
        """A glowing magic copy of a real desktop icon."""
        glow = QRadialGradient(QPointF(0, 0), 32)
        glow.setColorAt(0, QColor(170, 240, 255, int(150 + 50 * math.sin(t * 5))))
        glow.setColorAt(1, QColor(120, 200, 255, 0))
        p.setPen(NO_PEN)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QPointF(0, 0), 32, 32)
        if pixmap is not None and not pixmap.isNull():
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawPixmap(QRectF(-20, -20, 40, 40), pixmap, QRectF(pixmap.rect()))
            return
        page = QPainterPath(QPointF(-13, -18))
        page.lineTo(6, -18)
        page.lineTo(14, -10)
        page.lineTo(14, 18)
        page.lineTo(-13, 18)
        page.closeSubpath()
        p.setPen(_pen(INK, 1.6))
        p.setBrush(WHITE)
        p.drawPath(page)
        p.setPen(_pen(QColor(150, 160, 180), 1.4))
        for y in (-6, 0, 6, 12):
            p.drawLine(QPointF(-8, y), QPointF(9, y))

    @staticmethod
    def gnome(p, t):
        p.setPen(_pen(INK, 1.8))
        body = QPainterPath(QPointF(-11, 20))
        body.lineTo(11, 20)
        body.lineTo(7, 0)
        body.lineTo(-7, 0)
        body.closeSubpath()
        p.setBrush(QColor(70, 110, 220))
        p.drawPath(body)
        p.setBrush(QColor(60, 40, 30))
        p.drawRect(QRectF(-9.5, 8, 19, 3))
        p.setBrush(QColor(255, 220, 190))
        p.drawEllipse(QPointF(0, -3), 6.5, 6.5)
        beard = QPainterPath(QPointF(-7, -2))
        beard.quadTo(-8, 10, 0, 15)
        beard.quadTo(8, 10, 7, -2)
        beard.quadTo(0, 3, -7, -2)
        p.setBrush(WHITE)
        p.drawPath(beard)
        p.setBrush(QColor(250, 150, 150))
        p.drawEllipse(QPointF(1, -2), 2.6, 2.4)
        hat = QPainterPath(QPointF(-9, -6))
        hat.quadTo(-2, -14, 3 + math.sin(t * 2) * 1.5, -27)
        hat.quadTo(4, -14, 9, -6)
        hat.closeSubpath()
        p.setBrush(QColor(225, 50, 55))
        p.drawPath(hat)

    @staticmethod
    def lava_lamp(p, t):
        p.setPen(_pen(INK, 1.8))
        metal = QLinearGradient(-10, 0, 10, 0)
        metal.setColorAt(0, QColor(130, 130, 150))
        metal.setColorAt(0.6, QColor(225, 225, 235))
        metal.setColorAt(1, QColor(120, 120, 140))
        glass = QPainterPath(QPointF(-6, 6))
        glass.lineTo(-3.5, -16)
        glass.lineTo(3.5, -16)
        glass.lineTo(6, 6)
        glass.closeSubpath()
        g = QLinearGradient(0, -16, 0, 6)
        g.setColorAt(0, QColor(255, 120, 190))
        g.setColorAt(1, QColor(255, 180, 70))
        p.setBrush(QBrush(g))
        p.drawPath(glass)
        p.save()
        p.setClipPath(glass)
        p.setPen(NO_PEN)
        p.setBrush(QColor(255, 70, 70))
        for i in range(3):
            u = (t * 0.18 + i * 0.37) % 1.0
            p.drawEllipse(QPointF(math.sin(t + i * 2) * 1.5, 4 - 20 * u), 2.6 + i * 0.4, 3.2)
        p.restore()
        base = QPainterPath(QPointF(-10, 20))
        base.lineTo(10, 20)
        base.lineTo(6, 6)
        base.lineTo(-6, 6)
        base.closeSubpath()
        p.setBrush(QBrush(metal))
        p.drawPath(base)
        cap = QPainterPath(QPointF(-3.5, -16))
        cap.lineTo(3.5, -16)
        cap.lineTo(2.5, -22)
        cap.lineTo(-2.5, -22)
        cap.closeSubpath()
        p.drawPath(cap)

    @staticmethod
    def cactus(p, t):
        green, dark = QColor(96, 186, 96), QColor(50, 120, 60)
        for arm in (((-5, -4), (-12, -4), (-12, -13)), ((5, -9), (12, -9), (12, -17))):
            path = QPainterPath(QPointF(*arm[0]))
            path.lineTo(*arm[1])
            path.lineTo(*arm[2])
            p.setPen(_pen(INK, 8))
            p.drawPath(path)
            p.setPen(_pen(green, 4.6))
            p.drawPath(path)
        p.setPen(_pen(INK, 1.8))
        p.setBrush(green)
        p.drawRoundedRect(QRectF(-6.5, -22, 13, 30), 6.5, 6.5)
        p.setPen(_pen(dark, 1))
        for y in (-16, -9, -2):
            p.drawLine(QPointF(-3, y), QPointF(-1.8, y + 1.6))
            p.drawLine(QPointF(3, y + 3), QPointF(1.8, y + 4.6))
        p.setPen(_pen(INK, 1.8))
        pot = QPainterPath(QPointF(-12, 8))
        pot.lineTo(12, 8)
        pot.lineTo(9, 20)
        pot.lineTo(-9, 20)
        pot.closeSubpath()
        p.setBrush(QColor(212, 112, 70))
        p.drawPath(pot)
        p.setBrush(QColor(232, 136, 88))
        p.drawRoundedRect(QRectF(-13.5, 4.5, 27, 5.5), 2, 2)
        p.setBrush(QColor(255, 120, 180))
        for i in range(5):
            a = i * math.tau / 5 + t
            p.drawEllipse(QPointF(math.cos(a) * 2.6, -22 + math.sin(a) * 2.6), 2, 2)
        p.setBrush(QColor(255, 220, 80))
        p.drawEllipse(QPointF(0, -22), 1.6, 1.6)

    @staticmethod
    def rubber_duck(p, t):
        p.setPen(_pen(INK, 1.8))
        p.setBrush(QColor(255, 214, 60))
        p.drawEllipse(QPointF(-1, 9), 14, 10)
        p.drawEllipse(QPointF(6, -5), 8.5, 8.5)
        p.setPen(_pen(QColor(220, 160, 30), 1.5))
        p.drawArc(QRectF(-10, 3, 14, 9), 200 * 16, 140 * 16)
        p.setPen(_pen(INK, 1.6))
        beak = QPainterPath(QPointF(12, -6))
        beak.quadTo(20, -6, 20, -3)
        beak.quadTo(16, -1, 12, -2)
        beak.closeSubpath()
        p.setBrush(QColor(255, 140, 40))
        p.drawPath(beak)
        p.setPen(NO_PEN)
        p.setBrush(INK)
        p.drawEllipse(QPointF(8, -8), 1.8, 1.8)
        p.setBrush(WHITE)
        p.drawEllipse(QPointF(8.5, -8.6), 0.7, 0.7)

    @staticmethod
    def mystery_box(p, t):
        p.setPen(_pen(INK, 1.8))
        p.setBrush(QColor(200, 152, 102))
        p.drawRect(QRectF(-15, -12, 30, 32))
        p.setBrush(QColor(176, 128, 82))
        top = QPainterPath(QPointF(-15, -12))
        top.lineTo(-10, -19)
        top.lineTo(20, -19)
        top.lineTo(15, -12)
        top.closeSubpath()
        p.drawPath(top)
        p.setPen(NO_PEN)
        p.setBrush(QColor(236, 210, 160))
        p.drawRect(QRectF(-15, -8, 30, 5))
        p.setFont(font(20))
        p.setPen(QColor(150, 80, 220))
        p.drawText(QRectF(-15, -4, 30, 24), 0x0084, "?")

    @staticmethod
    def bundle(p, t):
        p.setPen(_pen(INK, 1.8))
        g = QLinearGradient(-17, -15, 17, 17)
        g.setColorAt(0, QColor(170, 110, 245))
        g.setColorAt(1, QColor(90, 46, 170))
        p.setBrush(QBrush(g))
        p.drawRoundedRect(QRectF(-17, -15, 34, 32), 3, 3)
        p.setBrush(GOLD)
        p.setPen(_pen(INK, 1.2))
        p.drawPolygon(star_polygon(0, -3, 9, spin=math.sin(t * 2) * 0.2))
        p.setBrush(QColor(255, 226, 120))
        p.drawRect(QRectF(-17, 9, 34, 6))
        p.setFont(font(6))
        p.setPen(INK)
        p.drawText(QRectF(-17, 9, 34, 6), 0x0084, "BUNDLE")
        p.setPen(_pen(QColor(255, 255, 255, 170), 1.6))
        p.drawLine(QPointF(-13, -11), QPointF(-8, -11))


class Machine:
    """An original card vending machine that rises out of the floor."""
    W, H = 124, 224

    def __init__(self, x, floor, scale):
        self.x, self.floor, self.scale = x, floor, scale
        self.k = 0.0
        self.state = "rise"          # rise | idle | leave
        self.screen = "hello"        # hello | check | soldout | instock
        self.flash = False
        self.leave_in = None
        self.gone = False
        self.t = 0.0

    def leave(self, delay=0.0):
        self.leave_in = delay

    def tray(self):
        return QPointF(self.x, self.floor - 26 * self.scale)

    def update(self, dt):
        self.t += dt
        if self.leave_in is not None:
            self.leave_in -= dt
            if self.leave_in <= 0:
                self.state, self.leave_in = "leave", None
        if self.state == "rise":
            self.k = min(1.0, self.k + dt / 0.8)
            if self.k >= 1:
                self.state = "idle"
        elif self.state == "leave":
            self.k = max(0.0, self.k - dt / 0.7)
            if self.k <= 0:
                self.gone = True

    def bounds(self):
        s = self.scale
        return QRectF(self.x - 80 * s, self.floor - 250 * s, 160 * s, 262 * s)

    def draw(self, p):
        s = self.scale
        shown = ease_back(self.k) if self.state == "rise" else ease(self.k)
        if shown <= 0.001:
            return
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(NO_PEN)
        p.setBrush(QColor(10, 0, 30, int(70 * min(1.0, shown))))
        p.drawEllipse(QPointF(self.x, self.floor + 2 * s), 72 * s * min(1.0, shown), 8 * s)
        p.setClipRect(QRectF(self.x - 100 * s, 0, 200 * s, self.floor + 3 * s))
        p.translate(self.x, self.floor + (1 - shown) * (self.H + 12) * s)
        p.scale(s, s)
        self._body(p)
        p.restore()

    def _body(self, p):
        t = self.t
        body = QLinearGradient(-62, 0, 62, 0)
        body.setColorAt(0, QColor(86, 46, 160))
        body.setColorAt(0.6, QColor(140, 84, 220))
        body.setColorAt(1, QColor(78, 40, 146))
        p.setPen(_pen(INK, 3))
        p.setBrush(QBrush(body))
        p.drawRoundedRect(QRectF(-62, -224, 124, 220), 14, 14)
        p.setBrush(QColor(40, 30, 60))
        p.drawRect(QRectF(-54, -6, 16, 6))
        p.drawRect(QRectF(38, -6, 16, 6))

        # marquee with chasing bulbs
        p.setBrush(QColor(30, 28, 70))
        p.drawRoundedRect(QRectF(-55, -216, 110, 30), 8, 8)
        p.setPen(NO_PEN)
        for i in range(9):
            if self.flash:
                on = (i + int(t * 10)) % 2 == 0
            else:
                on = i % 3 == int(t * 3) % 3
            p.setBrush(QColor(255, 226, 90) if on else QColor(110, 86, 50))
            p.drawEllipse(QPointF(-48 + i * 12, -210), 2.6, 2.6)
        p.setFont(font(12))
        p.setPen(GOLD)
        p.drawText(QRectF(-55, -206, 110, 18), 0x0084, "CARD-O-MATIC")

        # status screen
        bg, fg, text = QColor(18, 44, 30), QColor(120, 255, 150), "INSERT COIN"
        if self.screen == "check":
            text = "CHECKING" + "." * (int(t * 3) % 4)
        elif self.screen == "soldout":
            bg, fg, text = QColor(60, 14, 22), QColor(255, 90, 90), "SOLD OUT"
        elif self.screen == "instock":
            fg = GOLD if int(t * 6) % 2 else QColor(140, 255, 160)
            text = "IN STOCK!"
        p.setPen(_pen(INK, 2))
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(-50, -180, 100, 20), 4, 4)
        p.setFont(font(11))
        p.setPen(fg)
        p.drawText(QRectF(-50, -180, 100, 20), 0x0084, text)

        # glass case of packs, with the bundle front and center on top
        glass = QLinearGradient(0, -154, 0, -46)
        glass.setColorAt(0, QColor(40, 54, 110))
        glass.setColorAt(1, QColor(22, 26, 60))
        p.setPen(_pen(INK, 2.4))
        p.setBrush(QBrush(glass))
        p.drawRoundedRect(QRectF(-50, -154, 100, 108), 6, 6)
        p.setPen(_pen(QColor(150, 150, 170), 1.2))
        for r in range(4):
            y = -148 + r * 26
            p.drawLine(QPointF(-46, y + 22), QPointF(46, y + 22))
        p.setPen(_pen(INK, 1.2))
        for r in range(4):
            for c in range(4):
                if r == 0 and c in (1, 2):
                    continue
                p.setBrush(PACK_COLORS[(r * 4 + c) % len(PACK_COLORS)])
                p.drawRoundedRect(QRectF(-44 + c * 23, -147 + r * 26, 18, 20), 2, 2)
        if self.screen == "soldout":
            p.setPen(_pen(QColor(255, 90, 90), 2.5))
            p.drawLine(QPointF(-12, -144), QPointF(12, -130))
            p.drawLine(QPointF(12, -144), QPointF(-12, -130))
        else:
            if self.screen == "instock":
                p.setPen(NO_PEN)
                p.setBrush(QColor(255, 236, 120, int(110 + 80 * math.sin(t * 10))))
                p.drawEllipse(QPointF(0, -137), 22, 15)
            p.save()
            p.translate(0, -137)
            p.scale(0.62, 0.62)
            draw_item(p, "bundle", t, tag=False)
            p.restore()
        p.setPen(NO_PEN)
        p.setBrush(QColor(255, 255, 255, 40))
        shine = QPainterPath(QPointF(-40, -154))
        shine.lineTo(-22, -154)
        shine.lineTo(-48, -60)
        shine.lineTo(-50, -80)
        shine.closeSubpath()
        p.drawPath(shine)

        # pickup tray and decals
        p.setPen(_pen(INK, 2.2))
        p.setBrush(QColor(22, 16, 38))
        p.drawRoundedRect(QRectF(-40, -38, 80, 22), 4, 4)
        p.setPen(_pen(QColor(120, 110, 150), 1.5))
        p.drawLine(QPointF(-36, -35), QPointF(36, -35))
        p.setPen(_pen(INK, 1.2))
        p.setBrush(GOLD)
        for sx in (-49, 49):
            p.drawPolygon(star_polygon(sx, -27, 6))
