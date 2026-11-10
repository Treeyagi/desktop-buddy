"""The GameStop run: a scene about selling your childhood console to pay a bill.

gamestop  Mom says one console has to go. A CONSOLE ROLL slot machine rises out of
          the floor and he pulls the lever: whatever lands is what he carries to
          the store on the far side of the screen. Halfway there a scalper pulls
          him aside with a cash offer for it. He turns it down (always), the
          scalper whistles for his goons, and the madness starts: he sprints for
          the door while the goons chase him, a midnight-release stampede runs
          past, a rival kid races him, or it starts pouring. At the door a manager
          makes the trade-in offer: a pittance and a coupon (most of the time), a
          surprise mint-condition payday, or he keeps the console after all.

Props here are original art (consoles are plain silhouettes with their names, no
logos). Every prop has update(dt), draw(p), bounds(), gone and leave(delay), so the
Buddy's prop loop can carry them. Scene states: gs_roll, gs_scalper, gs_madness,
gs_door (the Buddy queues them after a walk).
"""
import math
import random

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QFontMetricsF, QLinearGradient, QPainter, QBrush

from character.moves import dance_pose, fists_up, gait_pose, hold, hug, palms_up, scratch_beard, shrug
from character.props import ease_back, font
from character.rig import GOLD, INK, NO_BRUSH, NO_PEN, WHITE, Pose, _pen, ease, lerp

# name, what the store would give, what the scalper offers (dollars), a line when it lands
CONSOLES = [
    ("NES", 12, 80, "the NES... dad's old NES."),
    ("SNES", 25, 140, "my SNES?! no no no."),
    ("N64", 30, 160, "not the N64!!"),
    ("GameCube", 40, 220, "the GameCube. ouch."),
    ("PS2", 8, 60, "the PS2. well. it's a PS2."),
    ("Dreamcast", 35, 300, "THE DREAMCAST?! mom!!"),
    ("Game Boy", 15, 120, "...the Game Boy."),
    ("Wii", 6, 45, "the Wii. that's fine. fine."),
]
N = len(CONSOLES)


def _r(p, color, x, y, w, h, rad=3.0):
    p.setBrush(QColor(*color))
    p.drawRoundedRect(QRectF(x, y, w, h), rad, rad)


def draw_console(p, i, t=0.0):
    """One console about 48 wide, centered on (0, 0)."""
    name = CONSOLES[i % N][0]
    p.setPen(_pen(INK, 2))
    if name == "NES":
        _r(p, (182, 182, 176), -24, -12, 48, 24)
        _r(p, (50, 50, 56), -18, -6, 24, 5, 1)
        _r(p, (200, 50, 50), 8, -6, 8, 4, 1)
        _r(p, (50, 50, 56), -18, 3, 36, 4, 1)
    elif name == "SNES":
        _r(p, (206, 206, 214), -24, -10, 48, 20, 6)
        _r(p, (110, 100, 150), -8, -6, 16, 8)
        _r(p, (70, 70, 90), -18, 2, 10, 4, 1)
        _r(p, (70, 70, 90), 8, 2, 10, 4, 1)
    elif name == "N64":
        _r(p, (120, 120, 128), -22, -4, 44, 16)
        _r(p, (86, 86, 94), -12, -14, 24, 12, 4)
        for k, c in enumerate(((220, 60, 60), (60, 120, 220), (240, 200, 50), (60, 180, 90))):
            p.setBrush(QColor(*c))
            p.drawEllipse(QPointF(-15 + k * 10, 6), 3, 3)
    elif name == "GameCube":
        _r(p, (112, 86, 190), -18, -12, 36, 26, 6)
        _r(p, (70, 50, 130), -8, -18, 16, 8)
        p.setBrush(QColor(40, 30, 70))
        p.drawEllipse(QPointF(0, 2), 7, 7)
    elif name == "PS2":
        _r(p, (40, 40, 52), -24, -9, 48, 18)
        _r(p, (70, 120, 255), -18, -4, 22, 3, 1)
        _r(p, (90, 90, 104), 10, -4, 8, 8, 1)
    elif name == "Dreamcast":
        _r(p, (234, 234, 238), -22, -14, 44, 28, 4)
        p.setBrush(QColor(240, 130, 40))
        p.drawEllipse(QPointF(-4, 0), 9, 9)
        p.setBrush(QColor(234, 234, 238))
        p.drawEllipse(QPointF(-2, -1), 4, 4)
    elif name == "Game Boy":
        _r(p, (190, 190, 184), -12, -20, 24, 40, 5)
        _r(p, (70, 90, 70), -8, -16, 16, 14, 2)
        p.setBrush(QColor(40, 40, 50))
        p.drawRect(QRectF(-8, 8, 9, 3))
        p.drawRect(QRectF(-5, 5, 3, 9))
        p.setBrush(QColor(180, 40, 90))
        p.drawEllipse(QPointF(6, 8), 2.5, 2.5)
        p.drawEllipse(QPointF(3, 12), 2.5, 2.5)
    else:  # Wii
        _r(p, (238, 238, 242), -9, -20, 18, 40, 4)
        _r(p, (80, 180, 255), -4, -14, 8, 2, 1)
        _r(p, (190, 190, 200), -5, -4, 10, 2, 1)


def draw_cash(p, t=0.0):
    """A little fan of bills."""
    p.setPen(_pen(INK, 1.6))
    for k in (-1, 0, 1):
        p.save()
        p.rotate(k * 14)
        _r(p, (92, 190, 110), -14, -18, 28, 14, 2)
        p.setBrush(QColor(200, 250, 200))
        p.drawEllipse(QPointF(0, -11), 3.5, 3.5)
        p.restore()


class GsProp:
    """Shared prop plumbing: gone flag, timer, a leave(delay) that the Buddy can call."""
    front = False

    def __init__(self, x, floor, scale):
        self.x, self.floor, self.scale = x, floor, scale
        self.gone = False
        self.t = 0.0
        self.leave_in = None
        self.leaving = False

    def leave(self, delay=0.0):
        self.leave_in = delay if self.leave_in is None else min(self.leave_in, delay)

    def _tick(self, dt):
        self.t += dt
        if self.leave_in is not None:
            self.leave_in -= dt
            if self.leave_in <= 0:
                self.leave_in, self.leaving = None, True


class SlotMachine(GsProp):
    """CONSOLE ROLL: one reel of consoles and a lever. pull(i) spins it to land on console i."""
    W, H = 130, 236
    SPIN = 3.4

    def __init__(self, x, floor, scale):
        super().__init__(x, floor, scale)
        self.k = 0.0
        self.pos = 0.0
        self.pos0 = self.target = 0.0
        self.spin_t = None
        self.pull_t = None
        self.lever = 0.0
        self.stopped = False
        self.flash = 0.0

    def tray(self):
        return QPointF(self.x, self.floor - 24 * self.scale)

    def pull(self, result):
        base = math.ceil(self.pos)
        self.pos0 = self.pos
        self.target = base + 3 * N + ((result - base) % N)
        self.spin_t = self.pull_t = 0.0
        self.stopped = False

    def update(self, dt):
        self._tick(dt)
        self.k = max(0.0, self.k - dt / 0.7) if self.leaving else min(1.0, self.k + dt / 0.8)
        if self.leaving and self.k <= 0:
            self.gone = True
        if self.pull_t is not None:
            self.pull_t += dt
            self.lever = math.sin(min(1.0, self.pull_t / 0.6) * math.pi)
            if self.pull_t > 0.6:
                self.pull_t, self.lever = None, 0.0
        if self.spin_t is not None:
            self.spin_t += dt
            k = min(1.0, self.spin_t / self.SPIN)
            self.pos = self.pos0 + (self.target - self.pos0) * (1 - (1 - k) ** 3)
            if k >= 1:
                self.spin_t, self.pos, self.stopped, self.flash = None, self.target, True, 2.0
        self.flash = max(0.0, self.flash - dt)

    def bounds(self):
        s = self.scale
        return QRectF(self.x - 110 * s, self.floor - 250 * s, 220 * s, 262 * s)

    def draw(self, p):
        s = self.scale
        shown = ease_back(self.k) if not self.leaving else ease(self.k)
        if shown <= 0.001:
            return
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(NO_PEN)
        p.setBrush(QColor(10, 0, 30, int(70 * min(1.0, shown))))
        p.drawEllipse(QPointF(self.x, self.floor + 2 * s), 72 * s * min(1.0, shown), 8 * s)
        p.setClipRect(QRectF(self.x - 120 * s, 0, 240 * s, self.floor + 3 * s))
        p.translate(self.x, self.floor + (1 - shown) * (self.H + 12) * s)
        p.scale(s, s)
        self._body(p)
        p.restore()

    def _body(self, p):
        t = self.t
        # lever on the right
        p.setPen(_pen(INK, 5))
        base = QPointF(62, -110)
        a = math.radians(-62 + 112 * self.lever)
        tip = base + QPointF(math.sin(a) * 52, math.cos(a) * -52)
        p.drawLine(base, tip)
        p.setPen(_pen(INK, 2.5))
        p.setBrush(QColor(230, 50, 60))
        p.drawEllipse(tip, 9, 9)
        # cabinet
        body = QLinearGradient(-62, 0, 62, 0)
        body.setColorAt(0, QColor(150, 30, 60))
        body.setColorAt(0.55, QColor(220, 60, 90))
        body.setColorAt(1, QColor(140, 28, 56))
        p.setPen(_pen(INK, 3))
        p.setBrush(QBrush(body))
        p.drawRoundedRect(QRectF(-62, -230, 124, 226), 16, 16)
        p.setBrush(QColor(40, 30, 60))
        p.drawRect(QRectF(-54, -6, 16, 6))
        p.drawRect(QRectF(38, -6, 16, 6))
        # marquee
        p.setBrush(QColor(30, 24, 64))
        p.drawRoundedRect(QRectF(-55, -222, 110, 34), 8, 8)
        p.setPen(NO_PEN)
        for i in range(9):
            on = (i + int(t * (12 if self.flash else 4))) % 3 == 0
            p.setBrush(QColor(255, 226, 90) if on else QColor(110, 86, 50))
            p.drawEllipse(QPointF(-48 + i * 12, -216), 2.6, 2.6)
        p.setFont(font(11))
        p.setPen(GOLD)
        p.drawText(QRectF(-55, -212, 110, 22), 0x0084, "CONSOLE ROLL")
        # reel window
        p.setPen(_pen(INK, 2.6))
        p.setBrush(QColor(246, 242, 230))
        win = QRectF(-46, -184, 92, 100)
        p.drawRoundedRect(win, 6, 6)
        p.save()
        p.setClipRect(win.adjusted(2, 2, -2, -2))
        mid = round(self.pos)
        frac = self.pos - mid
        for k in range(-2, 3):
            p.save()
            p.translate(0, -134 + (k - frac) * 46)
            draw_console(p, (mid + k) % N, t)
            p.restore()
        p.restore()
        p.setPen(_pen(GOLD, 2))
        p.drawLine(QPointF(-46, -157), QPointF(-34, -157))
        p.drawLine(QPointF(46, -157), QPointF(34, -157))
        p.drawLine(QPointF(-46, -111), QPointF(-34, -111))
        p.drawLine(QPointF(46, -111), QPointF(34, -111))
        # label
        p.setPen(_pen(INK, 2))
        p.setBrush(QColor(18, 44, 30))
        p.drawRoundedRect(QRectF(-50, -78, 100, 20), 4, 4)
        p.setFont(font(11))
        if self.spin_t is not None:
            text, fg = "ROLLING" + "." * (int(t * 5) % 4), QColor(120, 255, 150)
        elif self.stopped:
            text = CONSOLES[round(self.pos) % N][0].upper()
            fg = GOLD if int(t * 6) % 2 else QColor(140, 255, 160)
        else:
            text, fg = "PULL!", QColor(120, 255, 150)
        p.setPen(fg)
        p.drawText(QRectF(-50, -78, 100, 20), 0x0084, text)
        # tray
        p.setPen(_pen(INK, 2.2))
        p.setBrush(QColor(22, 16, 38))
        p.drawRoundedRect(QRectF(-40, -38, 80, 22), 4, 4)
        p.setPen(_pen(INK, 1.2))
        p.setBrush(GOLD)
        for sx in (-49, 49):
            p.drawEllipse(QPointF(sx, -27), 5, 5)


class Storefront(GsProp):
    """The store: slides in from the screen edge; its sliding door can open."""
    W, H = 236, 262

    def __init__(self, x, floor, scale, from_right):
        super().__init__(x, floor, scale)
        self.from_right = from_right
        self.k = 0.0
        self.open = 0.0
        self.opening = False

    def update(self, dt):
        self._tick(dt)
        self.k = max(0.0, self.k - dt / 0.9) if self.leaving else min(1.0, self.k + dt / 1.1)
        if self.leaving and self.k <= 0:
            self.gone = True
        self.open = min(1.0, self.open + dt / 0.4) if self.opening else max(0.0, self.open - dt / 0.4)

    def offset(self):
        return (1 - ease(self.k)) * (self.W + 200) * self.scale * (1 if self.from_right else -1)

    def bounds(self):
        s = self.scale
        return QRectF(self.x + self.offset() - 130 * s, self.floor - 290 * s, 260 * s, 300 * s)

    def draw(self, p):
        s = self.scale
        if self.k <= 0.001:
            return
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(self.x + self.offset(), self.floor)
        p.scale(s, s)
        t = self.t
        p.setPen(NO_PEN)
        p.setBrush(QColor(10, 0, 30, 70))
        p.drawEllipse(QPointF(0, 2), 128, 9)
        p.setPen(_pen(INK, 3))
        body = QLinearGradient(0, -240, 0, 0)
        body.setColorAt(0, QColor(58, 58, 74))
        body.setColorAt(1, QColor(36, 36, 48))
        p.setBrush(QBrush(body))
        p.drawRoundedRect(QRectF(-116, -240, 232, 240), 6, 6)
        # sign band + neon
        p.setBrush(QColor(206, 52, 36))
        p.drawRect(QRectF(-116, -262, 232, 44))
        p.setFont(font(24))
        p.setPen(WHITE)
        p.drawText(QRectF(-116, -262, 232, 44), 0x0084, "GAME STOP")
        p.setFont(font(10))
        p.setPen(QColor(255, 230, 120) if int(t * 2) % 2 else QColor(255, 150, 80))
        p.drawText(QRectF(-116, -214, 232, 16), 0x0084, "TRADE-INS  *  USED  *  OPEN")
        # windows full of game cases
        p.setPen(_pen(INK, 2.4))
        for sx in (-108, 52):
            p.setBrush(QColor(28, 34, 60))
            p.drawRoundedRect(QRectF(sx, -190, 56, 110), 4, 4)
            for r in range(4):
                for c in range(3):
                    _r(p, ((220, 70, 70), (80, 160, 230), (240, 190, 60), (110, 200, 120))[(r + c) % 4],
                       sx + 4 + c * 17, -184 + r * 26, 14, 20, 1.5)
        # sliding door
        p.setBrush(QColor(255, 236, 170) if self.open > 0.05 else QColor(30, 40, 64))
        p.drawRect(QRectF(-30, -118, 60, 118))
        o = ease(self.open) * 26
        p.setBrush(QColor(90, 120, 170, 200))
        p.drawRect(QRectF(-30 - o, -118, 30, 118))
        p.drawRect(QRectF(0 + o, -118, 30, 118))
        p.restore()


class GsItem(GsProp):
    """A console or a fan of cash that follows his hand (position set by the scene)."""
    front = True

    def __init__(self, kind, idx, x, y, scale):
        super().__init__(x, 0, scale)
        self.kind, self.idx, self.y = kind, idx, y
        self.size = 1.0
        self.angle = 0.0
        self.alpha = 1.0
        self.pop = 0.0
        self.held = False

    def update(self, dt):
        self._tick(dt)
        self.pop = min(1.0, self.pop + dt / 0.3)
        if self.leaving:
            self.alpha = max(0.0, self.alpha - dt / 0.4)
            if self.alpha <= 0:
                self.gone = True

    def bounds(self):
        r = 40 * self.scale * self.size
        return QRectF(self.x - r, self.y - r, 2 * r, 2 * r)

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
        if self.kind == "cash":
            draw_cash(p, self.t)
        else:
            draw_console(p, self.idx, self.t)
        p.restore()


class Rain(GsProp):
    """A downpour over part of the floor, with splashes."""
    front = True

    def __init__(self, x0, x1, floor, scale):
        super().__init__(x0, floor, scale)
        self.x0, self.x1 = min(x0, x1), max(x0, x1)
        self.drops = [[random.uniform(self.x0, self.x1), random.uniform(0, 1)] for _ in range(70)]
        self.k = 0.0

    def update(self, dt):
        self._tick(dt)
        self.k = max(0.0, self.k - dt / 0.8) if self.leaving else min(1.0, self.k + dt / 0.8)
        if self.leaving and self.k <= 0:
            self.gone = True
        for d in self.drops:
            d[1] += dt * 1.6
            if d[1] > 1:
                d[0], d[1] = random.uniform(self.x0, self.x1), d[1] - 1

    def bounds(self):
        return QRectF(self.x0 - 20, self.floor - 460 * self.scale, self.x1 - self.x0 + 40, 480 * self.scale)

    def draw(self, p):
        s = self.scale
        top, bot = self.floor - 440 * s, self.floor
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(0.7 * ease(self.k))
        p.setPen(_pen(QColor(150, 190, 255), 1.6 * s))
        for x, f in self.drops:
            y = top + (bot - top) * f
            p.drawLine(QPointF(x, y), QPointF(x - 5 * s, y + 15 * s))
        p.setPen(_pen(QColor(190, 220, 255), 1.2 * s))
        p.setBrush(NO_BRUSH)
        for x, f in self.drops[:14]:
            r = (f * 7 % 1) * 9 * s
            p.drawEllipse(QPointF(x, bot - 2 * s), r, r * 0.3)
        p.restore()


# --- people ---------------------------------------------------------------------------------
GAMER_SHIRTS = [(230, 90, 90), (90, 160, 230), (120, 200, 120), (240, 190, 70), (170, 110, 220)]
SKINS = [(244, 206, 170), (222, 170, 128), (176, 122, 90), (120, 82, 60)]
# kind: height in units (buddy-ish scale), coat, pants, hat
FIGURES = {
    "scalper": (176, (96, 84, 50), (44, 40, 40), "fedora"),
    "goon": (166, (34, 34, 44), (24, 24, 30), "beanie"),
    "gamer": (138, None, (60, 70, 120), None),
    "kid": (110, (240, 200, 60), (70, 90, 160), "cap"),
    "manager": (182, (200, 52, 40), (40, 40, 50), "hair"),
}


class Figure(GsProp):
    """A cartoon person: walks to a target (or chases a moving one), tumbles, talks."""

    def __init__(self, kind, x, floor, scale, facing=1):
        super().__init__(x, floor, scale)
        self.kind = kind
        self.h, coat, self.pants, hat = FIGURES[kind]
        self.coat = coat or random.choice(GAMER_SHIRTS)
        self.hat = hat or random.choice(["cap", "band", None])
        self.skin = QColor(*random.choice(SKINS))
        self.facing = facing
        self.mode = "idle"            # idle | walk | tumble
        self.target = x
        self.speed = 0.0
        self.chase = None             # callable giving the x to run at
        self.enters = False           # fades out on arrival (walks into the store)
        self.arrived = False
        self.phase = random.uniform(0, 6)
        self.pop = 0.0
        self.alpha = 1.0
        self.angle = 0.0
        self.vx = 0.0
        self.tt = 0.0
        self.spin = 1
        self.hopped = False
        self.arms = "swing"           # swing | up | cross | open
        self.coat_open = 0.0
        self.mood = "calm"            # calm | angry | happy
        self.bubble = None

    def say(self, text, life=2.4):
        self.bubble = {"text": text, "age": 0.0, "life": life}

    def go(self, target, speed, enters=False):
        self.target, self.speed, self.mode, self.arrived = target, speed, "walk", False
        self.enters = enters

    def trip(self, away):
        self.mode, self.vx, self.chase = "tumble", away * 260 * self.scale, None
        self.tt, self.spin = 0.0, 1 if away > 0 else -1
        self.mood = "angry"

    def update(self, dt):
        self._tick(dt)
        self.pop = min(1.0, self.pop + dt / 0.3)
        if self.bubble:
            self.bubble["age"] += dt
            if self.bubble["age"] > self.bubble["life"]:
                self.bubble = None
        if self.leaving:
            self.alpha = max(0.0, self.alpha - dt / 0.3)
            if self.alpha <= 0:
                self.gone = True
        if self.mode == "walk":
            if self.chase:
                self.target = self.chase()
            dx = self.target - self.x
            step = self.speed * dt
            if abs(dx) <= step and not self.chase:
                self.x, self.mode, self.arrived = self.target, "idle", True
                if self.enters:
                    self.leave(0.0)
            else:
                self.x += step * (1 if dx > 0 else -1)
                self.facing = 1 if dx > 0 else -1
                self.phase += dt * self.speed / (26 * self.scale) * math.pi / 2
        elif self.mode == "tumble":
            self.tt += dt
            self.x += self.vx * dt
            self.vx *= max(0.0, 1 - 2.0 * dt)
            self.angle += 560 * self.spin * dt * (1 if self.tt < 0.7 else 0)
            if self.tt > 1.5:
                self.leave(0.0)

    def bounds(self):
        s = self.scale
        k = self.h / 100 * s
        return QRectF(self.x - 70 * k, self.floor - 150 * k, 140 * k, 160 * k).adjusted(-60 * s, -60 * s, 60 * s, 0)

    def _limb(self, p, a, b, color, w):
        p.setPen(_pen(INK, w + 3))
        p.drawLine(a, b)
        p.setPen(_pen(color, w))
        p.drawLine(a, b)

    def draw(self, p):
        s = self.scale
        k = s * self.h / 100 * ease_back(self.pop)
        if self.alpha <= 0.01 or k <= 0.01:
            return
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self.alpha)
        p.setPen(NO_PEN)
        p.setBrush(QColor(10, 0, 30, 60))
        p.drawEllipse(QPointF(self.x, self.floor + 2 * s), 22 * k, 4 * k)
        p.translate(self.x, self.floor - 45 * k)
        p.rotate(self.angle)
        p.translate(0, 45 * k)
        p.scale(self.facing * k, k)
        self._draw_body(p)
        p.restore()
        if self.bubble:
            self._draw_bubble(p)

    def _draw_body(self, p):
        moving = self.mode == "walk"
        sw = math.sin(self.phase) if moving else 0.0
        pants = QColor(*self.pants)
        coat = QColor(*self.coat)
        for sgn in (-1, 1):  # legs
            a = sgn * sw * 0.7
            hip = QPointF(sgn * 6, -42)
            foot = hip + QPointF(math.sin(a) * 40, math.cos(a) * 40 - (6 * max(0.0, sgn * sw) if moving else 0))
            self._limb(p, hip, foot, pants, 8)
            p.setPen(_pen(INK, 2))
            p.setBrush(QColor(236, 236, 240))
            p.drawEllipse(foot + QPointF(3, 1), 7, 4)
        # torso (a coat reaches the knees)
        long_coat = self.kind in ("scalper", "goon")
        bottom = -26 if long_coat else -38
        p.setPen(_pen(INK, 2.5))
        if self.coat_open > 0:  # coat flung open: lining, goods and all
            o = self.coat_open
            p.setBrush(QColor(30, 24, 30))
            p.drawRoundedRect(QRectF(-12, -82, 24, 56), 3, 3)
            for i, col in enumerate(((220, 70, 70), (90, 170, 240), (240, 200, 60))):
                _r(p, col, -8, -76 + i * 16, 16, 11, 2)
            p.setBrush(coat)
            for sgn in (-1, 1):
                p.drawPolygon([QPointF(sgn * 12, -82), QPointF(sgn * (22 + 16 * o), -70),
                               QPointF(sgn * (24 + 18 * o), -26), QPointF(sgn * 12, -26)])
        else:
            p.setBrush(coat)
            p.drawRoundedRect(QRectF(-15, -82, 30, 82 + bottom), 8, 8)
        if self.kind == "manager":
            p.setBrush(QColor(250, 250, 250))
            p.drawPolygon([QPointF(-4, -82), QPointF(4, -82), QPointF(0, -70)])
            p.setBrush(QColor(30, 30, 40))
            p.drawPolygon([QPointF(-2, -76), QPointF(2, -76), QPointF(3, -52), QPointF(0, -48), QPointF(-3, -52)])
            _r(p, (255, 255, 255), 5, -68, 9, 6, 1)
        # arms
        for sgn in (-1, 1):
            sh = QPointF(sgn * 14, -76)
            if self.arms == "up":
                hand = sh + QPointF(sgn * 8, -28 + 5 * math.sin(self.t * 14 + sgn))
            elif self.arms == "cross":
                hand = QPointF(-sgn * 6, -58)
            elif self.arms == "open":
                hand = sh + QPointF(sgn * 28, 6)
            else:
                a = -sgn * sw * 0.8
                hand = sh + QPointF(math.sin(a) * 28, math.cos(a) * 28)
            self._limb(p, sh, hand, coat, 7)
            p.setPen(_pen(INK, 1.8))
            p.setBrush(self.skin)
            p.drawEllipse(hand, 4.5, 4.5)
        # head
        head = QPointF(0, -94)
        p.setPen(_pen(INK, 2.5))
        p.setBrush(self.skin)
        p.drawEllipse(head, 16, 16)
        self._face(p, head)
        self._hat(p, head)

    def _face(self, p, head):
        p.setPen(NO_PEN)
        if self.kind == "scalper":  # shades
            p.setBrush(QColor(20, 20, 26))
            p.drawRoundedRect(QRectF(-14, -100, 28, 9), 3, 3)
            p.setBrush(QColor(255, 255, 255, 120))
            p.drawRect(QRectF(-10, -98, 5, 2))
        else:
            p.setBrush(INK)
            p.drawEllipse(QPointF(5, -96), 2.4, 3)
            p.drawEllipse(QPointF(-5, -96), 2.4, 3)
        p.setPen(_pen(INK, 2))
        if self.mood == "angry":
            p.drawLine(QPointF(2, -102), QPointF(9, -99))
            p.drawLine(QPointF(-2, -102), QPointF(-9, -99))
            p.drawLine(QPointF(-5, -84), QPointF(5, -85))
        elif self.mood == "happy":
            p.setBrush(QColor(255, 255, 255))
            p.drawChord(QRectF(-6, -90, 12, 8), 0, -180 * 16)
        else:
            p.drawLine(QPointF(-4, -85), QPointF(4, -85))

    def _hat(self, p, head):
        p.setPen(_pen(INK, 2.2))
        if self.hat == "fedora":
            p.setBrush(QColor(54, 46, 40))
            p.drawEllipse(QPointF(0, -108), 24, 5)
            p.drawRoundedRect(QRectF(-12, -128, 24, 22), 6, 6)
            p.setBrush(QColor(170, 40, 40))
            p.drawRect(QRectF(-12, -113, 24, 5))
        elif self.hat == "beanie":
            p.setBrush(QColor(180, 44, 44))
            p.drawChord(QRectF(-17, -112, 34, 34), 0, 180 * 16)
            p.drawRect(QRectF(-17, -106, 34, 6))
        elif self.hat == "cap":
            p.setBrush(QColor(60, 110, 220))
            p.drawChord(QRectF(-17, -112, 34, 30), 0, 180 * 16)
            p.drawRoundedRect(QRectF(4, -104, 20, 5), 2, 2)
        elif self.hat == "band":
            p.setBrush(QColor(230, 60, 80))
            p.drawRect(QRectF(-16, -106, 32, 6))
        elif self.hat == "hair":
            p.setBrush(QColor(60, 40, 30))
            p.drawChord(QRectF(-17, -112, 34, 26), 0, 180 * 16)

    def _draw_bubble(self, p):
        s = self.scale
        b = self.bubble
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(max(0.0, min(1.0, (b["life"] - b["age"]) / 0.3)))
        f = font(max(11, 13 * s))
        fm = QFontMetricsF(f)
        box = fm.boundingRect(QRectF(0, 0, 190 * s, 2000), 0x0084 | 0x1000, b["text"])
        w, h = box.width() + 20 * s, box.height() + 12 * s
        cx = self.x
        y = self.floor - (self.h + 40) * s - h
        r = QRectF(cx - w / 2, y, w, h)
        p.setPen(_pen(INK, 2 * s))
        p.setBrush(WHITE)
        p.drawRoundedRect(r, 10 * s, 10 * s)
        p.drawPolygon([QPointF(cx - 5 * s, r.bottom() - 1), QPointF(cx + 5 * s, r.bottom() - 1),
                       QPointF(cx, r.bottom() + 9 * s)])
        p.setPen(NO_PEN)
        p.setBrush(WHITE)
        p.drawRect(QRectF(cx - 4 * s, r.bottom() - 3, 8 * s, 4))
        p.setFont(f)
        p.setPen(INK)
        p.drawText(r, 0x0084 | 0x1000, b["text"])
        p.restore()


# --- the scene ------------------------------------------------------------------------------
MOM = ["mom says one console has to go.", "rent's due. mom picked a console... from a slot machine?",
       "mom: 'sell one. GameStop. today.'"]
GOONS = ["get him!", "the console, kid!", "nobody says no to Gary!"]


class GameStopMixin:
    def _scene_gamestop(self):
        s = self.scale
        if any(isinstance(q, GsProp) and not q.leaving for q in self.props):
            return "idle", {}
        left = self.x < self.width / 2
        mx = 120 * s if left else self.width - 120 * s
        sx = self.width - 170 * s if left else 170 * s
        d = 1 if left else -1                      # which way the store lies
        machine = SlotMachine(mx, self.floor, s)
        store = Storefront(sx, self.floor, s, from_right=left)
        self.props[0:0] = [store, machine]
        idx = random.randrange(N)
        stop = sx - d * 170 * s
        self.gs = {"machine": machine, "store": store, "idx": idx, "dir": d, "stop": stop,
                   "ambush": lerp(mx, stop, random.uniform(0.42, 0.58)), "console": None,
                   "hostiles": [], "extras": [], "rain": None, "rival": None}
        at = mx + d * 135 * s
        self.queue += [("gs_roll", {}),
                       ("walk", {"target": self.gs["ambush"], "mood": "cheery", "speed": 105 * s, "notice": None}),
                       ("gs_scalper", {}), ("gs_madness", {}), ("gs_door", {})]
        return "walk", {"target": at, "mood": "cheery", "speed": 115 * s, "notice": None}

    def gs_update(self, dt):
        """Keeps the console and the cash in his hand."""
        g = getattr(self, "gs", None)
        if not g:
            return
        for q in self.props:
            if isinstance(q, GsItem) and q.held and not q.gone:
                h = self._anchor("hand_f")
                s = self.scale
                q.x, q.y = h.x() + self.facing * 14 * s, h.y() - 4 * s

    def _gs_item(self, kind, at=None):
        a = at or self._anchor("hand_f")
        q = GsItem(kind, self.gs["idx"], a.x(), a.y(), self.scale)
        q.size = 0.9
        self.props.append(q)
        return q

    def _gs_poof(self, q):
        for _ in range(12):
            self.fx.sparkle(q.x, q.y, speed=110)
        q.gone = True

    # 1. the roll -------------------------------------------------------------------------------
    def _start_gs_roll(self):
        g = self.gs
        self.facing = 1 if g["machine"].x >= self.x else -1
        self.dur = 10.4
        self.data["result"] = g["idx"]

    def _gs_roll(self, dt):
        g = self.gs
        m = g["machine"]
        t = self.t
        s = self.scale
        idx = g["idx"]
        if t < 1.3:   # mom's orders
            if self._once("mom"):
                self.say(random.choice(MOM), life=2.8)
            return shrug(Pose(look_x=1.0, look_y=-0.2, smile=-0.1, brow=0.6))
        if t < 1.9:   # reach for the lever
            if self._once("pull"):
                m.pull(idx)
            a = ease((t - 1.3) / 0.3)
            return Pose(lean=8 * a, sh_f=lerp(10, 95, a), el_f=lerp(16, 8, a), reach_f=1.0 + 0.5 * a,
                        hand_f="fist", look_x=1.0, look_y=-0.3, brow=0.6, mouth="o", mouth_open=0.3)
        if t < 1.3 + m.SPIN + 0.1:   # fingers crossed while it spins
            pump = math.sin(t * 18)
            return fists_up(Pose(lean=4, look_x=1.0, look_y=-0.2, brow=0.8, mouth="o", mouth_open=0.4,
                                 sx=1 + 0.01 * pump, hip_f=3 * pump), pump=0.3 * pump)
        u = t - (1.3 + m.SPIN + 0.1)
        name, store_v, scalp_v, line = CONSOLES[idx]
        if u < 1.5:   # it lands
            if self._once("land"):
                self.fx.bang(*self._head_xy(-10, -100), "!!")
                for _ in range(10):
                    self.fx.sparkle(m.x, self.floor - 150 * s, speed=120)
            if u > 0.6 and self._once("line"):
                self.say(line, life=2.6)
            hi = scalp_v >= 150
            return palms_up(Pose(brow=1.0, quirk=1.0, mouth="o", mouth_open=0.7, lean=-6, sy=1.04,
                                 look_x=1.0, look_y=-0.3, tears=0.0 if hi else 0.4, sparkle=0.8))
        if u < 2.9:   # it drops into the tray; he grabs it
            if self._once("drop"):
                g["console"] = self._gs_item("console", m.tray())
            c = g["console"]
            grab = ease((u - 1.8) / 0.5)
            hand = self._anchor("hand_f")
            if c and not c.held:
                tray = m.tray()
                c.x, c.y = lerp(tray.x(), hand.x(), grab), lerp(tray.y(), hand.y(), grab)
                if grab >= 1:
                    c.held = True
            return self._bend(math.sin(min(1.0, (u - 1.5) / 1.0) * math.pi), grab)
        if self._once("hug"):
            self.say("...for the bills.", life=2.2)
            m.leave(1.5)
        k = ease((u - 2.9) / 0.6)
        return hug(Pose(lean=4 * k, head=8 * k, look_x=0.4, look_y=0.8 * k, smile=-0.3, brow=-0.2,
                        tears=0.6 * k, hat=4 * k))

    # 2. the scalper ----------------------------------------------------------------------------
    def _start_gs_scalper(self):
        g = self.gs
        d, s = g["dir"], self.scale
        self.facing = d
        self.dur = 14.5
        x = max(80 * s, min(self.width - 80 * s, self.x + d * 420 * s))
        sc = Figure("scalper", x, self.floor, s, facing=-d)
        sc.arms = "swing"
        g["scalper"] = sc
        self.props.append(sc)

    def _gs_scalper(self, dt):
        g = self.gs
        sc = g["scalper"]
        d, s = g["dir"], self.scale
        name, store_v, scalp_v, _ = CONSOLES[g["idx"]]
        t = self.t
        if t < 0.3:
            return hold(Pose(look_x=0.8))
        if self._once("psst"):
            sc.say("psst. hey, kid.", life=2.0)
            sc.go(self.x + d * 105 * s, 150 * s)
            self.fx.bang(*self._head_xy(-10, -100))
        if t < 2.6:   # startled, then he's pulled aside
            a = ease((t - 0.3) / 0.3)
            return palms_up(Pose(lean=-5 * a, look_x=1.0, brow=1.0 * a, quirk=0.8, mouth="o", mouth_open=0.4,
                                 sx=1 - 0.03 * a, sy=1 + 0.03 * a))
        if t > 3.0:
            sc.coat_open = min(1.0, sc.coat_open + self._dt / 0.35)
        if t < 3.4:
            return Pose(look_x=1.0, brow=0.5, mouth="o", mouth_open=0.2)
        if self._once("offer"):
            sc.say(f"that {name}? ${scalp_v}. cash. right now.", life=3.6)
            self.think("math", 5.0, lines=[f"${scalp_v}!", "cash...", "bills...", "mom...", "hmm..."], side=-1)
        if t < 8.2:   # the temptation: beard scratch, eyes flick between the cash and the console
            look = 1.0 if int(t * 1.3) % 2 == 0 else 0.2
            tap = max(0.0, math.sin(t * 9))
            return scratch_beard(hold(Pose(lean=3, look_x=look, look_y=0.3 if look < 0.5 else -0.2, head=-4,
                                           brow=0.4 + 0.3 * math.sin(t * 1.3), hip_f=8 * tap, mouth="o",
                                           mouth_open=0.1)), t, 12)
        if t < 10.4:  # nope
            if self._once("nope"):
                self.say("no deal. the store's got trade-ins!", life=2.6)
                self.thought = None
            a = ease((t - 8.2) / 0.3)
            sh = math.sin(t * 16)
            return hug(Pose(head=10 * sh * a, lean=-4, look_x=0.0, brow=0.2, smile=-0.2, quirk=0.0,
                            mouth="o", mouth_open=0.1))
        if self._once("snap"):
            sc.coat_open = 0.0
            sc.mood = "angry"
            sc.say("your funeral, kid.", life=2.2)
        if t < 12.2:
            return hug(Pose(lean=-8, look_x=1.0, look_y=-0.2, brow=0.9, mouth="o", mouth_open=0.4))
        if self._once("whistle"):   # goons from behind
            for i in range(2):
                gx = max(-60 * s, min(self.width + 60 * s, self.x - d * (520 + i * 140) * s))
                gn = Figure("goon", gx, self.floor, s, facing=d)
                gn.mood = "angry"
                gn.go(self.x - d * 60 * s, 205 * s)
                gn.chase = lambda: self.x
                if i == 0:
                    gn.say(random.choice(GOONS), life=2.0)
                g["hostiles"].append(gn)
                self.props.append(gn)
            sc.say("*whistle*", life=1.2)
            self.fx.bang(*self._head_xy(-10, -100), "!!")
        return palms_up(Pose(brow=1.0, quirk=1.0, mouth="o", mouth_open=0.8, look_x=-0.8, sy=1.04))

    # 3. the madness ----------------------------------------------------------------------------
    def _start_gs_madness(self):
        g = self.gs
        s = self.scale
        self.facing = g["dir"]
        self.dur = 999.0
        sc = g.get("scalper")
        if sc:
            sc.leave(2.5)
        dist = abs(g["stop"] - self.x)
        d = self.data
        d.update(speed=205 * s, phase=0.0, hop=1.0)
        pool = ["stampede", "rival", "rain"]
        random.shuffle(pool)
        T = dist / d["speed"]
        d["script"] = [(T * 0.30 * random.uniform(0.8, 1.2), pool[0]), (T * 0.58 * random.uniform(0.9, 1.1), pool[1])]
        self.say("RUN!!", life=1.4)

    def _gs_event(self, name):
        g = self.gs
        d, s = g["dir"], self.scale
        if name == "stampede":
            self.say("midnight release?! whoa!", life=2.2)
            for i in range(7):
                x = self.x - d * (300 + i * 70 + random.uniform(0, 40)) * s
                f = Figure("gamer", x, self.floor, s, facing=d)
                f.arms = "up"
                f.mood = "happy"
                f.go(g["stop"] + d * 120 * s, random.uniform(275, 340) * s, enters=True)
                g["hostiles"].append(f)
                g["extras"].append(f)
                self.props.append(f)
                if i == 0:
                    f.say("MIDNIGHT RELEASE!!", life=2.2)
        elif name == "rival":
            x = self.x - d * 380 * s
            kid = Figure("kid", x, self.floor, s, facing=d)
            kid.mood = "happy"
            kid.arms = "swing"
            kid.go(g["stop"] + d * 30 * s, 240 * s, enters=False)
            kid.say("beat ya to the counter!", life=2.4)
            g["rival"] = kid
            g["extras"].append(kid)
            self.props.append(kid)
        elif name == "rain" and not g["rain"]:
            self.say("of course it's raining.", life=2.2)
            lo = g["stop"] - d * 700 * s
            r = Rain(lo, g["stop"] + d * 250 * s, self.floor, s)
            g["rain"] = r
            self.props.append(r)

    def _gs_madness(self, dt):
        g = self.gs
        d = self.data
        s = self.scale
        step = d["speed"] * dt
        dx = g["stop"] - self.x
        sign = 1 if dx >= 0 else -1
        self.facing = sign
        if abs(dx) <= step:
            self.x = g["stop"]
            self.done = True
        else:
            self.x += step * sign
        d["phase"] += dt * d["speed"] / (28 * s) * math.pi / 2
        for ev in list(d["script"]):
            if self.t >= ev[0]:
                d["script"].remove(ev)
                self._gs_event(ev[1])
        pose = gait_pose(d["phase"], "cheery")
        pose.lean, pose.brow, pose.mouth, pose.mouth_open = 14, 1.0, "o", 0.5 + 0.2 * math.sin(self.t * 12)
        pose.look_x, pose.look_y, pose.sparkle = -0.4, -0.1, 0.0
        pose.knee_f, pose.knee_b = pose.knee_f + 10, pose.knee_b + 10
        hold(pose)
        # dodge anything that closes in on him
        d["hop"] = min(1.0, d["hop"] + dt / 0.55)
        for f in g["hostiles"]:
            if f.gone or f.hopped or f.mode == "tumble":
                continue
            if abs(f.x - self.x) < 80 * s:
                f.hopped = True
                if d["hop"] >= 1.0:
                    d["hop"] = 0.0
                    self.fx.dust(self.x, self.floor, 4)
                if f.kind == "goon":
                    f.trip(-sign if f.x < self.x else sign)
                    f.say("OW!", life=1.2)
                    self.say(random.choice(["hup!", "nope!", "bonk!"]), life=0.9)
        if d["hop"] < 1.0:
            k = math.sin(d["hop"] * math.pi)
            pose.lift = 78 * k
            pose.knee_f, pose.knee_b, pose.hip_f, pose.hip_b = 70, 70, 36, -8
            pose.sh_f, pose.el_f = 135, 20
        return pose

    # 4. at the door ----------------------------------------------------------------------------
    def _start_gs_door(self):
        g = self.gs
        d = self.data
        self.facing = g["dir"]
        for f in g["hostiles"]:
            f.leave(0.2)
        if g["rain"]:
            g["rain"].leave(3.0)
        roll = random.random()
        d["end"] = "bonus" if roll < 0.2 else "keep" if roll < 0.45 else "pittance"
        self.dur = {"bonus": 13.8, "keep": 10.5, "pittance": 9.8}[d["end"]]
        if g["rival"] and not g["rival"].gone:
            g["rival"].say("FIRST!", life=2.0)
            g["rival"].leave(3.0)

    def _gs_door(self, dt):
        g = self.gs
        d = self.data
        store, s, dr = g["store"], self.scale, g["dir"]
        name, store_v, scalp_v, _ = CONSOLES[g["idx"]]
        t = self.t
        end = d["end"]
        c = g["console"]
        if t < 1.5:   # out of breath
            k = ease(t / 0.5)
            return Pose(lean=24 * k, bob=10 * k, hip_f=14 * k, knee_f=4 + 24 * k, hip_b=10 * k, knee_b=4 + 20 * k,
                        head=8 * k, look_x=0.6, look_y=0.6, mouth="o", mouth_open=0.5 + 0.3 * math.sin(t * 12),
                        sh_f=lerp(10, 25, k), sh_b=-14)
        if self._once("manager"):
            store.opening = True
            m = Figure("manager", store.x, self.floor, s, facing=-dr)
            m.arms = "cross"
            m.go(self.x + dr * 110 * s, 80 * s)
            m.say("Sir. SIR. We're about to close.", life=2.4)
            g["manager"] = m
            self.props.append(m)
        m = g["manager"]
        if t < 3.6:
            return hold(Pose(lean=-2, look_x=1.0, brow=0.6, mouth="o", mouth_open=0.2, smile=0.2))
        if self._once("trade"):
            self.say("trade-in? please?", life=2.2)
        if t < 5.8:   # the manager squints at it
            if t > 4.4 and self._once("hmm"):
                m.say("hmmmm.", life=1.6)
            m.arms = "cross"
            return hold(Pose(lean=-2, look_x=1.0, brow=0.5, mouth="o", mouth_open=0.1, head=-3, sparkle=0.4), up=10)
        if end == "bonus":
            return self._gs_bonus(t - 5.8, m, c, store_v)
        return self._gs_pittance(t - 5.8, m, c, store_v, end)

    def _gs_pittance(self, u, m, c, store_v, end):
        s, dr = self.scale, self.gs["dir"]
        offer = store_v * 0.11
        if u < 0.1 and self._once("price"):
            m.say(f"${offer:.2f} and a coupon.", life=2.6)
        if u < 2.4:   # ...that's it?
            return shrug(Pose(look_x=1.0, look_y=-0.3, smile=-0.2, brow=0.8, mouth="o", mouth_open=0.2))
        if end == "keep":
            if self._once("nope"):
                self.say("...nope. not for that.", life=2.4)
                m.say("your loss.", life=1.8)
                m.arms = "open"
            a = ease((u - 2.4) / 0.5)
            if self._once("walk"):
                self.queue.insert(0, ("walk", {"target": max(100 * s, min(self.width - 100 * s,
                                                                         self.x - dr * random.uniform(320, 480) * s)),
                                               "mood": "sad", "speed": 55 * s, "notice": None}))
                self.gs["store"].leave(2.0)
                m.leave(1.5)
                if c:
                    c.leave(5.0)
            return hug(Pose(lean=-4 * a, look_x=0.0, smile=-0.3, brow=0.1, mouth="o", mouth_open=0.1,
                            head=10 * math.sin(u * 12) * (u < 3.3)))
        if self._once("sold"):   # takes the coins, hands over the console
            self.say("...that's it?", life=2.4)
            if c:
                c.held = False
                c.x, c.y = m.x, self.floor - 90 * s
                self._gs_poof(c)
            cash = self._gs_item("cash")
            cash.size = 0.7
            cash.held = True
            self.data["cash"] = cash
            m.say("Next!", life=1.4)
            m.leave(2.0)
            self.gs["store"].leave(2.6)
            self.queue.insert(0, ("walk", {"target": max(100 * s, min(self.width - 100 * s,
                                                                     self.x - dr * random.uniform(320, 480) * s)),
                                           "mood": "sad", "speed": 40 * s, "notice": None}))
            self.data["cash"].leave(7.0)
        a = ease((u - 2.4) / 0.8)
        return Pose(lean=10 * a, head=10 * a, look_x=0.4, look_y=0.9 * a, smile=-0.7, brow=-0.3, tears=0.35 * a,
                    sh_f=lerp(40, 4, a), el_f=lerp(70, 6, a), bob=3 * a, hat=8 * a, hand_f="fist")

    def _gs_bonus(self, u, m, c, store_v):
        s = self.scale
        pay = store_v * 3 + 40
        if u < 0.05 and self._once("price"):
            m.say(f"...wait. this is MINT. ${pay}!!", life=3.0)
            m.mood = "happy"
        if u < 1.6:
            if self._once("what"):
                self.fx.bang(*self._head_xy(-10, -100), "!!")
            return palms_up(Pose(brow=1.0, quirk=1.0, mouth="o", mouth_open=0.9, lean=-8, sy=1.05, sparkle=1.0,
                                 look_x=1.0, look_y=-0.4))
        if self._once("sold"):
            if c:
                c.held = False
                c.x, c.y = m.x, self.floor - 90 * s
                self._gs_poof(c)
            cash = self._gs_item("cash")
            cash.held = True
            cash.size = 1.2
            self.data["cash"] = cash
            self.say("MOM IS GONNA FLIP!!", life=2.8)
            self.bee_mode = "dance"
            m.leave(3.0)
            self.gs["store"].leave(5.0)
            self.data["cash"].leave(9.0)
        k = u - 1.6
        b = k * math.tau * 2.1
        self._every("heart", 0.35, lambda: self.fx.heart(*self._head_xy(random.uniform(-50, 50), -60)))
        self._every("spark", 0.12, lambda: self.fx.sparkle(*self._head_xy(random.uniform(-40, 40), -40), speed=100))
        pose = dance_pose(b)
        pose.tears = 0.8
        if k < 4.0:
            return pose
        return fists_up(Pose(eyes="happy", mouth="smile", mouth_open=0.8, smile=1.0, blush=0.9, tears=1.0),
                        pump=math.sin(k * 8))
