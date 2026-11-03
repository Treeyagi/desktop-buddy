"""Puppet rig for the buddy, in the style of character/reference-ultimate-pull.jpg:
chunky ink outlines, soft cel shading, big glossy eyes, chibi proportions.
Purple star bucket hat with a red mushroom, rainbow-striped hoodie with white
drawstrings, jeans, chunky grey sneakers, ginger beard going grey at the chin.

A Pose is a bag of joint angles and face settings; draw_buddy() paints it.
Rig space faces right (3/4 view), feet at (0, 0), y down, about 1 unit = 1 px
at scale 1. Angles are degrees: 0 points straight down, positive swings forward.
"""
import math
from dataclasses import dataclass, fields

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QBrush, QColor, QLinearGradient, QPainter, QPainterPath,
                         QPen, QPolygonF, QRadialGradient)

INK = QColor(30, 22, 40)
WHITE = QColor(255, 255, 255)
SKIN = QColor(255, 222, 194)
SKIN_LIGHT = QColor(255, 238, 218)
SKIN_SHADE = QColor(238, 174, 140)
SKIN_BACK = QColor(236, 196, 168)
NOSE = QColor(248, 172, 146)
BEARD = QColor(208, 112, 54)
BEARD_LIGHT = QColor(232, 146, 78)
BEARD_DARK = QColor(150, 72, 32)
BEARD_GREY = QColor(240, 236, 230)
HAIR = QColor(150, 82, 40)
BROW = QColor(86, 50, 30)
IRIS_IN = QColor(46, 36, 120)
IRIS_OUT = QColor(112, 124, 240)
MOUTH = QColor(104, 22, 40)
TONGUE = QColor(244, 112, 128)
BLUSH = QColor(255, 116, 136)
TEAR = QColor(132, 210, 255)
STRIPES = [QColor(226, 84, 176), QColor(238, 68, 70), QColor(248, 146, 50), QColor(252, 214, 66),
           QColor(110, 202, 92), QColor(56, 180, 208), QColor(76, 116, 216)]
SLEEVE = [QColor(230, 92, 198), QColor(156, 96, 226), QColor(62, 188, 214)]
CUFF = QColor(46, 150, 186)
HOOD = QColor(136, 78, 200)
HOOD_IN = QColor(62, 176, 206)
JEANS = QColor(52, 72, 146)
JEANS_BACK = QColor(36, 50, 108)
JEANS_LIGHT = QColor(98, 124, 200)
SHOE = QColor(226, 230, 238)
SHOE_DARK = QColor(146, 152, 170)
HAT_LIGHT = QColor(184, 126, 238)
HAT = QColor(144, 86, 210)
HAT_DARK = QColor(100, 56, 164)
GOLD = QColor(255, 214, 58)
MUSH_RED = QColor(228, 52, 48)
MUSH_STEM = QColor(252, 238, 212)
LEAF = QColor(98, 200, 92)
LEAF_DARK = QColor(52, 132, 60)

# (x, y, radius) in hat space
CROWN_STARS = ((-17, -14, 5.0), (19, -19, 4.2), (-4, -24, 3.4))
BRIM_STARS = ((-39, 4, 3.8), (38, 4, 3.8), (-16, 9, 3.4), (22, 9, 3.2))


@dataclass
class Pose:
    lift: float = 0.0        # whole body off the floor (jumps, floating)
    bob: float = 0.0         # hips down (+) / up (-)
    lean: float = 0.0        # torso tilt, + = forward
    sx: float = 1.0          # squash and stretch
    sy: float = 1.0
    hip_f: float = 0.0       # near leg
    knee_f: float = 4.0
    hip_b: float = 0.0       # far leg
    knee_b: float = 4.0
    sh_f: float = 10.0       # near arm
    el_f: float = 16.0
    sh_b: float = -12.0      # far arm
    el_b: float = 12.0
    reach_f: float = 1.0     # rubber-hose arm stretch, for big gestures
    reach_b: float = 1.0
    back_front: float = 0.0  # > 0.5 draws the far arm over the face (beard scratch, hugs)
    head: float = 0.0        # head tilt
    hat: float = 0.0         # extra hat tilt
    look_x: float = 0.3      # pupils, -1..1
    look_y: float = 0.0
    blink: float = 0.0       # 0 open .. 1 shut
    brow: float = 0.0        # -1 frown .. 1 raised
    quirk: float = 0.0       # extra raise on the near brow
    smile: float = 0.6       # -1 frown .. 1 big smile
    mouth_open: float = 0.0
    blush: float = 0.3
    tears: float = 0.0       # streams of (happy or sad) tears
    sparkle: float = 0.0     # extra eye shine when excited
    eyes: str = "open"       # open | happy | closed
    mouth: str = "smile"     # smile | o
    hand_f: str = "fist"     # fist | open | point
    hand_b: str = "fist"


_FLOAT_FIELDS = [f.name for f in fields(Pose) if f.type in (float, "float")]
_OTHER_FIELDS = [f.name for f in fields(Pose) if f.name not in _FLOAT_FIELDS]


def lerp_pose(a, b, k):
    out = Pose()
    for name in _FLOAT_FIELDS:
        va = getattr(a, name)
        setattr(out, name, va + (getattr(b, name) - va) * k)
    for name in _OTHER_FIELDS:
        setattr(out, name, getattr(b if k >= 0.5 else a, name))
    return out


def ease(k):
    k = max(0.0, min(1.0, k))
    return k * k * (3 - 2 * k)


def lerp(a, b, k):
    return a + (b - a) * k


def _dir(a):
    r = math.radians(a)
    return QPointF(math.sin(r), math.cos(r))


def _rot(pt, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return QPointF(pt.x() * c - pt.y() * s, pt.x() * s + pt.y() * c)


def _pen(color, width, style=Qt.PenStyle.SolidLine):
    pen = QPen(color, width)
    pen.setStyle(style)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _darker(c, k=0.72):
    return QColor(int(c.red() * k), int(c.green() * k), int(c.blue() * k), c.alpha())


NO_PEN = QPen(Qt.PenStyle.NoPen)
NO_BRUSH = QBrush(Qt.BrushStyle.NoBrush)

UPPER_ARM, FOREARM = 15, 14
THIGH, SHIN = 15, 20


def skeleton(pose):
    """Key points in rig space, shared by drawing, props and effects."""
    H = QPointF(0, -38 + pose.bob)
    up = _dir(180 - pose.lean)
    S = H + up * 36
    C = H + _dir(180 - pose.lean - pose.head * 0.3) * 74 + QPointF(4, 0)
    hr = pose.head + pose.lean * 0.3
    Sf = S + _rot(QPointF(15, 2), pose.lean)
    Sb = S + _rot(QPointF(-15, 2), pose.lean)
    elbow_f = Sf + _dir(pose.sh_f) * UPPER_ARM * pose.reach_f
    hand_f = elbow_f + _dir(pose.sh_f + pose.el_f) * (FOREARM * pose.reach_f + 4)
    elbow_b = Sb + _dir(pose.sh_b) * UPPER_ARM * pose.reach_b
    hand_b = elbow_b + _dir(pose.sh_b + pose.el_b) * (FOREARM * pose.reach_b + 4)
    return dict(H=H, up=up, S=S, C=C, Sf=Sf, Sb=Sb, elbow_f=elbow_f, hand_f=hand_f,
                elbow_b=elbow_b, hand_b=hand_b, head_rot=hr,
                hat_top=C + _rot(QPointF(2, -64), hr),
                mushroom=C + _rot(QPointF(10, -58), hr),
                brim_f=C + _rot(QPointF(50, -27), hr),
                brim_b=C + _rot(QPointF(-45, -27), hr),
                mouth=C + _rot(QPointF(11, 27), hr),
                eye_f=C + _rot(QPointF(18, -2), hr),
                eye_b=C + _rot(QPointF(-5, -2), hr),
                chin=C + _rot(QPointF(8, 40), hr),
                shoulder_f=Sf, shoulder_b=Sb)


def to_world(x, floor, facing, scale, pose, pt):
    return QPointF(x + facing * scale * pose.sx * pt.x(),
                   floor + scale * (-pose.lift + pose.sy * pt.y()))


def star_polygon(cx, cy, r, points=5, inner=0.45, spin=0.0):
    pts = []
    for i in range(points * 2):
        a = -math.pi / 2 + spin + i * math.pi / points
        rr = r if i % 2 == 0 else r * inner
        pts.append(QPointF(cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return QPolygonF(pts)


def draw_leaf(p, pos, angle, size, color=LEAF):
    p.save()
    p.translate(pos)
    p.rotate(angle)
    leaf = QPainterPath(QPointF(0, 0))
    leaf.quadTo(size * 0.5, -size * 0.5, size, 0)
    leaf.quadTo(size * 0.5, size * 0.5, 0, 0)
    p.setPen(_pen(INK, 1.6))
    p.setBrush(color)
    p.drawPath(leaf)
    p.setPen(_pen(LEAF_DARK, 1.1))
    p.drawLine(QPointF(size * 0.15, 0), QPointF(size * 0.8, 0))
    p.restore()


def draw_mushroom(p, cx, base, size=1.0, cap=MUSH_RED):
    """A little toadstool standing on (cx, base)."""
    p.save()
    p.translate(cx, base)
    p.scale(size, size)
    p.setPen(_pen(INK, 2.0))
    p.setBrush(MUSH_STEM)
    stem = QPainterPath(QPointF(-3.5, 0))
    stem.quadTo(-4.5, -6, -3, -9)
    stem.lineTo(3, -9)
    stem.quadTo(4.5, -6, 3.5, 0)
    stem.closeSubpath()
    p.drawPath(stem)
    dome = QPainterPath(QPointF(-10, -8))
    dome.cubicTo(-10, -20, 10, -20, 10, -8)
    dome.quadTo(0, -5, -10, -8)
    g = QRadialGradient(QPointF(-3, -16), 14)
    g.setColorAt(0, cap.lighter(135))
    g.setColorAt(1, cap)
    p.setBrush(QBrush(g))
    p.drawPath(dome)
    p.setPen(NO_PEN)
    p.setBrush(WHITE)
    for sx, sy, r in ((-5, -13, 2.2), (2, -16, 1.8), (6, -11, 1.6), (-1, -10, 1.2)):
        p.drawEllipse(QPointF(sx, sy), r, r * 0.85)
    p.restore()


def _begin(p, x, floor, facing, scale, pose, shadow=True):
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.translate(x, floor)
    p.scale(scale, scale)
    if shadow:
        k = 1.0 / (1.0 + pose.lift / 90.0)
        p.setPen(NO_PEN)
        p.setBrush(QColor(10, 0, 30, int(70 * k)))
        p.drawEllipse(QPointF(0, 3), 34 * k, 7 * k)
    p.translate(0, -pose.lift)
    p.scale(facing * pose.sx, pose.sy)


def draw_buddy(p, x, floor, facing, scale, pose, hat_bend=0.0, hat_squash=1.0, clock=0.0):
    sk = skeleton(pose)
    p.save()
    _begin(p, x, floor, facing, scale, pose)
    if pose.back_front <= 0.5:
        _arm(p, sk["Sb"], pose.sh_b, pose.el_b, pose.hand_b, pose.reach_b, back=True)
    _leg(p, sk["H"] + _rot(QPointF(-8, 0), pose.lean), pose.hip_b, pose.knee_b, back=True)
    _leg(p, sk["H"] + _rot(QPointF(8, 0), pose.lean), pose.hip_f, pose.knee_f, back=False)
    _torso(p, sk["H"], pose.lean, hat_bend)
    # a hanging arm tucks under the beard; a raised one goes in front of the face
    low = sk["hand_f"].y() > sk["Sf"].y() - 4
    if low:
        _arm(p, sk["Sf"], pose.sh_f, pose.el_f, pose.hand_f, pose.reach_f, back=False)
    _head(p, sk["C"], sk["head_rot"], pose, hat_bend, hat_squash, clock)
    if not low:
        _arm(p, sk["Sf"], pose.sh_f, pose.el_f, pose.hand_f, pose.reach_f, back=False)
    if pose.back_front > 0.5:
        _arm(p, sk["Sb"], pose.sh_b, pose.el_b, pose.hand_b, pose.reach_b, back=False)
    p.restore()


def draw_front_hand(p, x, floor, facing, scale, pose):
    """Redraw just the near hand, so it can wrap around something it holds."""
    sk = skeleton(pose)
    p.save()
    _begin(p, x, floor, facing, scale, pose, shadow=False)
    a = pose.sh_f + pose.el_f
    _hand(p, sk["hand_f"], a, pose.hand_f, back=False)
    p.restore()


# limbs ---------------------------------------------------------------------
def _limb_path(root, a1, l1, a2, l2):
    mid = root + _dir(a1) * l1
    end = mid + _dir(a2) * l2
    path = QPainterPath(root)
    path.lineTo(mid)
    path.lineTo(end)
    return path, mid, end


def _arm(p, shoulder, sh, el, hand, reach, back):
    path, elbow, wrist = _limb_path(shoulder, sh, UPPER_ARM * reach, sh + el, FOREARM * reach)
    p.setBrush(NO_BRUSH)
    p.setPen(_pen(INK, 18))
    p.drawPath(path)
    grad = QLinearGradient(shoulder, wrist)
    cols = [_darker(c) for c in SLEEVE] if back else SLEEVE
    grad.setColorAt(0, cols[0])
    grad.setColorAt(0.5, cols[1])
    grad.setColorAt(1, cols[2])
    p.setPen(_pen(QBrush(grad), 13))
    p.drawPath(path)
    # a soft highlight along the top of the sleeve
    p.setPen(_pen(QColor(255, 255, 255, 50 if back else 80), 3))
    side = _rot(_dir(sh), -90) * 3
    p.drawLine(shoulder + side, elbow + side)
    d = _dir(sh + el)
    cuff = _darker(CUFF) if back else CUFF
    p.setPen(_pen(INK, 18))
    p.drawLine(wrist - d * 4, wrist)
    p.setPen(_pen(cuff, 13))
    p.drawLine(wrist - d * 4, wrist)
    p.setPen(_pen(_darker(cuff, 0.8), 1.2))
    for k in (-3.5, 0, 3.5):
        n = _rot(d, 90) * k
        p.drawLine(wrist - d * 4.5 + n, wrist + n)
    _hand(p, wrist + d * 4, sh + el, hand, back)


def _hand(p, center, angle, kind, back):
    skin = SKIN_BACK if back else SKIN
    p.save()
    p.translate(center)
    p.rotate(-angle)  # local +y now points along the forearm, away from the wrist
    if kind == "open":
        for fx, length, tilt in ((-6, 8, -14), (-2, 10, -4), (2.5, 10, 4), (6.5, 8, 14)):
            base = QPointF(fx * 0.8, 3)
            tip = base + _dir(tilt) * length
            p.setPen(_pen(INK, 7.5))
            p.drawLine(base, tip)
            p.setPen(_pen(skin, 4.6))
            p.drawLine(base, tip)
        thumb = QPointF(8, -1)
        p.setPen(_pen(INK, 7.5))
        p.drawLine(thumb, thumb + QPointF(5, 5))
        p.setPen(_pen(skin, 4.6))
        p.drawLine(thumb, thumb + QPointF(5, 5))
        p.setPen(_pen(INK, 2.2))
        p.setBrush(skin)
        p.drawEllipse(QPointF(0, 0), 8, 7.5)
    else:
        if kind == "point":
            p.setPen(_pen(INK, 8))
            p.drawLine(QPointF(-3, 4), QPointF(-3, 16))
            p.setPen(_pen(skin, 5))
            p.drawLine(QPointF(-3, 4), QPointF(-3, 16))
        p.setPen(_pen(INK, 2.2))
        p.setBrush(skin)
        p.drawRoundedRect(QRectF(-8.5, -7, 17, 15), 6.5, 6.5)
        p.setPen(_pen(_darker(skin, 0.7), 1.3))
        for fx in ((-4, 0, 4) if kind == "fist" else (0, 4)):
            p.drawLine(QPointF(fx, 3), QPointF(fx, 7.5))
        p.setPen(_pen(INK, 2.0))
        p.setBrush(skin)
        p.drawEllipse(QPointF(7.5, -1.5), 3.6, 5)  # thumb
    p.restore()


def _leg(p, hip, a, knee, back):
    path, _, foot = _limb_path(hip, a, THIGH, a - knee, SHIN)
    p.setBrush(NO_BRUSH)
    p.setPen(_pen(INK, 19))
    p.drawPath(path)
    p.setPen(_pen(JEANS_BACK if back else JEANS, 14))
    p.drawPath(path)
    if not back:
        p.setPen(_pen(QColor(JEANS_LIGHT.red(), JEANS_LIGHT.green(), JEANS_LIGHT.blue(), 150), 2.4))
        side = _rot(_dir(a), -90) * 3.5
        p.drawLine(hip + side + _dir(a) * 3, hip + side + _dir(a) * (THIGH - 2))
    d = _dir(a - knee)
    at = foot + d * 2
    _shoe(p, at, a - knee, back, "body")
    # baggy jeans flaring out and stacking over the top of the shoe, 2000s style
    n = _rot(d, 90)
    top, bot = foot - d * 21, foot - d * 12
    flare = QPolygonF([top + n * 7.5, top - n * 7.5, bot - n * 10.5, bot + n * 10.5])
    p.setPen(_pen(INK, 2.4))
    p.setBrush(JEANS_BACK if back else JEANS)
    p.drawPolygon(flare)
    p.setPen(_pen(_darker(JEANS_LIGHT, 0.9 if not back else 0.6), 1.3))
    p.drawLine(top + n * 3 + d * 1, bot + n * 6 - d * 1.5)
    p.drawLine(top - n * 2 + d * 3, bot - n * 5 - d * 1)
    p.setPen(_pen(_darker(JEANS_LIGHT, 0.75 if not back else 0.5), 2.2))
    p.drawLine(bot - n * 9.5 - d * 1.2, bot + n * 9.5 - d * 1.2)  # hem
    _shoe(p, at, a - knee, back, "tongue")


# Chunky D3-style skate shoes (shape only, no logos). One style is worn at a
# time; set_shoes() switches it (the settings window will use this).
SHOE_STYLES = {
    "hot pink": dict(upper=QColor(255, 64, 152), shade=QColor(206, 30, 112), loops=QColor(255, 255, 255),
                     laces=QColor(30, 26, 34), sole=QColor(250, 250, 252), outsole=QColor(150, 150, 164),
                     lining=QColor(255, 255, 255), speckle=None, bubble=QColor(255, 64, 152)),
    "dusty pink": dict(upper=QColor(226, 88, 108), shade=QColor(184, 58, 80), loops=QColor(236, 112, 130),
                       laces=QColor(226, 88, 108), sole=QColor(246, 246, 248), outsole=QColor(214, 86, 106),
                       lining=QColor(238, 238, 242), speckle=QColor(46, 56, 110), bubble=QColor(226, 88, 108)),
    "sky blue": dict(upper=QColor(42, 180, 234), shade=QColor(22, 136, 196), loops=QColor(248, 238, 200),
                     laces=QColor(70, 186, 240), sole=QColor(250, 184, 198), outsole=QColor(176, 176, 184),
                     lining=QColor(240, 246, 255), speckle=None, bubble=QColor(42, 180, 234)),
}
shoe_style = "hot pink"
SHOE_SIZE = 0.82  # about 1.5x a normal sneaker on him: big, but not clown shoes


def set_shoes(name):
    global shoe_style
    if name in SHOE_STYLES:
        shoe_style = name


# a fixed sprinkle of speckles on the midsole
_SPECKLES = [(-15, 2.5), (-12, 4.5), (-9, 1.5), (-6, 4), (-2, 2.5), (1, 5), (5, 1.8), (8, 4.2),
             (11, 2.2), (14, 4.8), (17, 1.6), (20, 3.6), (23, 5), (26, 2), (30, 3.8), (32, 1.4)]


def _shoe_colors(back):
    st = SHOE_STYLES.get(shoe_style, SHOE_STYLES["hot pink"])
    if not back:
        return st
    return {k: (_darker(v, 0.8) if isinstance(v, QColor) else v) for k, v in st.items()}


def _shoe(p, at, shin, back, part):
    """Toe points +x, the ankle is at (0, 0) and the sole sits on y = +8."""
    c = _shoe_colors(back)
    p.save()
    p.translate(at)
    p.rotate(-max(-50.0, min(80.0, shin)) * 0.8)
    p.scale(SHOE_SIZE, SHOE_SIZE)
    if part == "tongue":  # big padded tongue flopping forward out over the jeans
        tongue = QPainterPath(QPointF(1, -16))
        tongue.cubicTo(-2, -25, 3, -31, 10, -31)
        tongue.cubicTo(17, -31, 19, -23, 15, -14)
        tongue.closeSubpath()
        g = QLinearGradient(0, -31, 0, -14)
        g.setColorAt(0, c["upper"].lighter(118))
        g.setColorAt(1, c["upper"])
        p.setPen(NO_PEN)
        p.setBrush(QBrush(g))
        p.drawPath(tongue)
        p.save()
        p.setClipPath(tongue)
        p.setBrush(c["lining"])
        p.drawEllipse(QPointF(10, -31.5), 9, 3.2)
        p.restore()
        p.setPen(_pen(c["shade"], 1.2))
        p.setBrush(NO_BRUSH)
        seam = QPainterPath(QPointF(2.5, -18))
        seam.cubicTo(0.5, -24.5, 4, -28, 10, -28)
        seam.cubicTo(15, -28, 16, -22, 13.5, -16)
        p.drawPath(seam)
        p.setPen(_pen(INK, 2.4))
        p.drawPath(tongue)
        p.restore()
        return

    # chunky padded upper: tall ankle, lace line sloping down to a bulbous toe
    upper = QPainterPath(QPointF(-17, -2))
    upper.cubicTo(-22, -10, -20, -20, -12, -22)
    upper.quadTo(-6, -23.5, -1, -20)
    upper.cubicTo(8, -18, 18, -15, 27, -10)
    upper.cubicTo(35, -7, 38, -3, 36, -2)
    upper.closeSubpath()
    g = QRadialGradient(QPointF(6, -17), 32)
    g.setColorAt(0, c["upper"].lighter(124))
    g.setColorAt(0.65, c["upper"])
    g.setColorAt(1, c["shade"])
    p.setPen(_pen(INK, 2.6))
    p.setBrush(QBrush(g))
    p.drawPath(upper)

    def lace_y(x):
        return -20 + (x + 1) * 0.37

    lobes = [(cx, lace_y(cx)) for cx in (2.5, 9.5, 16.5, 23.5)]
    p.save()
    p.setClipPath(upper)
    p.setBrush(NO_BRUSH)
    for cx, top in lobes:  # molded lobes running up to the lace loops
        p.setPen(_pen(c["shade"], 1.7))
        p.drawRoundedRect(QRectF(cx - 3.6, top - 0.5, 7.2, 20), 3.6, 3.6)
    p.setPen(_pen(_darker(c["shade"], 0.85), 1.0))
    for i in range(5):  # little mesh windows between the lobes
        p.drawArc(QRectF(-13 + i * 7, -6.5, 4, 3.5), 0, 180 * 16)
    p.setPen(_pen(c["shade"], 1.2))
    for rx in (28, 30.5, 33):  # ribbed toe cap
        p.drawLine(QPointF(rx, -8), QPointF(rx + 1.4, -2.5))
    p.setPen(_pen(QColor(255, 255, 255, 90), 2.2))
    p.drawArc(QRectF(-18, -21, 14, 16), 100 * 16, 70 * 16)  # shine on the heel padding
    p.restore()

    # heel pull tab and the collar lining
    tab = QPainterPath(QPointF(-15, -20))
    tab.quadTo(-18, -28, -12, -27)
    tab.lineTo(-10.5, -21.5)
    p.setPen(_pen(INK, 4.2))
    p.setBrush(NO_BRUSH)
    p.drawPath(tab)
    p.setPen(_pen(c["upper"], 2.2))
    p.drawPath(tab)
    collar = QPainterPath(QPointF(-12.5, -21.5))
    collar.quadTo(-7, -18.5, -2, -20)
    collar.quadTo(-7, -24, -12.5, -21.5)
    p.setPen(_pen(INK, 1.4))
    p.setBrush(c["lining"])
    p.drawPath(collar)

    # thick sole curving up at the toe, air bubbles, tread underneath
    sole = QPainterPath(QPointF(-18, -4))
    sole.lineTo(31, -4)
    sole.quadTo(39, -5, 38, 1)
    sole.quadTo(37, 8, 29, 8)
    sole.lineTo(-15, 8)
    sole.quadTo(-21.5, 8, -21.5, 2)
    sole.quadTo(-21.5, -4, -18, -4)
    p.setPen(NO_PEN)
    p.setBrush(c["sole"])
    p.drawPath(sole)
    p.save()
    p.setClipPath(sole)
    p.setBrush(c["outsole"])
    p.drawRect(QRectF(-23, 5, 64, 4))
    p.setPen(_pen(_darker(c["outsole"], 0.7), 1))
    for tx in range(-18, 38, 4):
        p.drawLine(QPointF(tx, 5.6), QPointF(tx, 8))
    p.setPen(NO_PEN)
    p.setBrush(QColor(255, 255, 255, 120))
    p.drawRect(QRectF(-22, -4, 62, 2))
    if c["speckle"] is not None:
        p.setBrush(c["speckle"])
        for sx, sy in _SPECKLES:
            p.drawEllipse(QPointF(sx, sy - 3.5), 0.6, 0.6)
    p.setPen(_pen(_darker(c["sole"], 0.8), 1))
    p.drawLine(QPointF(-19, 5), QPointF(36, 5))
    p.restore()
    p.setPen(_pen(INK, 2.4))
    p.setBrush(NO_BRUSH)
    p.drawPath(sole)
    for bx in (-16, -7.5):
        p.setPen(_pen(INK, 1.4))
        p.setBrush(QColor(205, 228, 242))
        p.drawRoundedRect(QRectF(bx, -2.2, 7.5, 5.2), 2.5, 2.5)
        p.setPen(NO_PEN)
        p.setBrush(c["bubble"])
        for k in range(3):
            p.drawEllipse(QPointF(bx + 1.8 + k * 2, 0.4), 0.85, 0.85)
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(QPointF(bx + 1.6, -1.1), 1.2, 0.5)
    p.setPen(_pen(INK, 1.4))
    p.setBrush(_darker(c["sole"], 0.5))
    p.drawEllipse(QPointF(31, 0.5), 2.8, 2)

    # fat laces criss-crossing along the top, threaded through the loops
    p.setBrush(NO_BRUSH)
    segs = []
    for (x0, t0), (x1, t1) in zip(lobes, lobes[1:]):
        segs.append((QPointF(x0, t0 - 0.8), QPointF(x1, t1 + 2.2)))
        segs.append((QPointF(x0, t0 + 2.2), QPointF(x1, t1 - 0.8)))
    ends = QPainterPath(QPointF(2, -16.5))
    ends.quadTo(-5, -15, -4, -8)
    ends.moveTo(2, -16.5)
    ends.quadTo(7, -12, 5, -6.5)
    for width, colr in ((3.6, INK), (2.0, c["laces"])):
        p.setPen(_pen(colr, width))
        for a_, b_ in segs:
            p.drawLine(a_, b_)
        p.drawPath(ends)
    for cx, top in lobes:
        p.setPen(_pen(INK, 1.2))
        p.setBrush(c["loops"])
        p.drawRoundedRect(QRectF(cx - 1.9, top + 1.0, 3.8, 6.4), 1.9, 1.9)
        p.setPen(NO_PEN)
        p.setBrush(c["laces"])  # the lace threading through
        p.drawRoundedRect(QRectF(cx - 0.9, top + 2.1, 1.8, 4.2), 0.9, 0.9)
    p.restore()


# torso ---------------------------------------------------------------------
def _torso(p, hip, lean, swing):
    p.save()
    p.translate(hip)
    p.rotate(lean)
    p.setPen(_pen(INK, 2.6))
    p.setBrush(_darker(HOOD))
    p.drawEllipse(QRectF(-22, -48, 30, 18))  # hood bunched behind the neck

    body = QPainterPath(QPointF(-22, 4))
    body.lineTo(22, 4)
    body.cubicTo(27, -8, 26, -28, 17, -38)
    body.quadTo(0, -44, -17, -38)
    body.cubicTo(-26, -28, -27, -8, -22, 4)
    p.setPen(NO_PEN)
    p.setBrush(STRIPES[0])
    p.drawPath(body)
    p.save()
    p.setClipPath(body)
    band = 48 / len(STRIPES)
    for i, c in enumerate(STRIPES):
        p.setBrush(c)
        p.drawRect(QRectF(-30, -44 + i * band, 60, band + 0.6))
    p.setBrush(_darker(STRIPES[-1], 0.8))
    p.drawRect(QRectF(-30, -2, 60, 7))
    p.setPen(_pen(_darker(STRIPES[-1], 0.6), 1))
    for rx in range(-22, 24, 4):
        p.drawLine(QPointF(rx, -1), QPointF(rx, 4))
    p.setPen(NO_PEN)
    shade = QLinearGradient(-24, 0, 26, 0)
    shade.setColorAt(0, QColor(10, 0, 40, 95))
    shade.setColorAt(0.45, QColor(0, 0, 0, 0))
    shade.setColorAt(0.8, QColor(255, 255, 255, 34))
    shade.setColorAt(1, QColor(0, 0, 0, 30))
    p.setBrush(QBrush(shade))
    p.drawRect(QRectF(-30, -46, 60, 52))
    p.restore()
    p.setPen(_pen(INK, 3))
    p.setBrush(NO_BRUSH)
    p.drawPath(body)
    p.setPen(_pen(QColor(30, 20, 50, 90), 1.6))
    pocket = QPainterPath(QPointF(-12, -2))
    pocket.quadTo(-10, -13, 0, -14)
    pocket.quadTo(11, -13, 14, -2)
    p.drawPath(pocket)

    collar = QPainterPath(QPointF(-18, -37))
    collar.quadTo(0, -25, 18, -37)
    collar.lineTo(14, -42)
    collar.quadTo(0, -34, -14, -42)
    collar.closeSubpath()
    p.setPen(_pen(INK, 2.4))
    p.setBrush(HOOD)
    p.drawPath(collar)
    p.setPen(_pen(HOOD_IN, 1.8))
    p.drawLine(QPointF(-10, -38), QPointF(-4, -34))

    sway = max(-6.0, min(6.0, -swing * 0.25))
    for sx in (-5, 7):
        top = QPointF(sx, -31)
        end = QPointF(sx + sway, -15)
        p.setPen(_pen(INK, 4.8))
        p.drawLine(top, end)
        p.setPen(_pen(QColor(246, 246, 250), 2.6))
        p.drawLine(top, end)
        p.setPen(_pen(INK, 1.2))
        p.setBrush(QColor(170, 176, 190))
        p.drawRoundedRect(QRectF(end.x() - 2.2, end.y() - 1, 4.4, 6), 1.5, 1.5)
    p.restore()


# head ----------------------------------------------------------------------
def _head(p, C, rot, pose, hat_bend, hat_squash, clock):
    p.save()
    p.translate(C)
    p.rotate(rot)

    p.setPen(_pen(INK, 2.4))
    p.setBrush(HAIR)
    p.drawEllipse(QPointF(-26, -12), 9, 11)
    p.setBrush(SKIN)
    p.drawEllipse(QPointF(-29, 3), 7, 9.5)
    p.setPen(_pen(SKIN_SHADE, 2))
    p.drawArc(QRectF(-32, -2, 6, 10), 90 * 16, 180 * 16)

    face = QPainterPath()
    face.addEllipse(QPointF(2, 0), 33, 32)
    grad = QRadialGradient(QPointF(14, -12), 46)
    grad.setColorAt(0, SKIN_LIGHT)
    grad.setColorAt(0.6, SKIN)
    grad.setColorAt(1, SKIN_SHADE)
    p.setPen(NO_PEN)
    p.setBrush(QBrush(grad))
    p.drawPath(face)
    p.save()
    p.setClipPath(face)
    c = QColor(BLUSH)
    c.setAlpha(int(150 * max(0.0, min(1.0, pose.blush))))
    p.setBrush(c)
    p.drawEllipse(QPointF(28, 10), 6.5, 3.8)
    p.drawEllipse(QPointF(-12, 11), 6, 3.5)
    p.restore()
    p.setPen(_pen(INK, 3))
    p.setBrush(NO_BRUSH)
    p.drawPath(face)

    _beard(p)
    _mouth(p, pose)
    stache = QPainterPath(QPointF(-3, 20))
    stache.cubicTo(0, 12, 8, 11, 11, 16)
    stache.cubicTo(14, 11, 23, 12, 26, 20)
    stache.cubicTo(20, 23, 14, 21, 11, 19)
    stache.cubicTo(8, 22, 2, 23, -3, 20)
    p.setPen(_pen(INK, 2.0))
    p.setBrush(BEARD_LIGHT)
    p.drawPath(stache)
    p.setPen(_pen(BEARD_DARK, 1.1))
    p.drawLine(QPointF(4, 16), QPointF(6, 19))
    p.drawLine(QPointF(17, 16), QPointF(16, 19))

    _eye(p, -5, -2, 10.5, 12.5, pose)
    _eye(p, 18, -2, 11.5, 13.5, pose)
    p.setPen(_pen(INK, 2.2))
    p.setBrush(NOSE)
    p.drawEllipse(QPointF(10, 11), 6, 5)
    p.setPen(NO_PEN)
    p.setBrush(QColor(255, 255, 255, 150))
    p.drawEllipse(QPointF(8, 9), 2, 1.4)
    if pose.tears > 0.03:
        _tears(p, pose.tears, clock)

    _hat(p, hat_bend, hat_squash, pose.hat)

    for ex, ry, extra in ((-5, 12.5, 0.0), (18, 13.5, pose.quirk)):
        y0 = -2 - ry - 6 - pose.brow * 4 - extra * 6
        brow = QPainterPath(QPointF(ex - 10, y0 + 3 - pose.brow * 1.5 + max(0.0, -pose.brow) * 3))
        brow.quadTo(ex, y0 - 3 - extra * 2, ex + 10, y0 + 2 + pose.brow * 0.8)
        p.setPen(_pen(INK, 8))
        p.setBrush(NO_BRUSH)
        p.drawPath(brow)
        p.setPen(_pen(BROW, 5.2))
        p.drawPath(brow)
    p.restore()


def _beard(p):
    beard = QPainterPath(QPointF(-30, -8))
    beard.cubicTo(-33, 16, -18, 42, 6, 45)
    beard.cubicTo(26, 45, 38, 26, 35, 4)
    beard.cubicTo(32, 13, 27, 16, 22, 17)
    beard.cubicTo(14, 19, 4, 19, -4, 16)
    beard.cubicTo(-14, 12, -22, 4, -30, -8)
    p.setPen(NO_PEN)
    g = QLinearGradient(0, -8, 0, 40)
    g.setColorAt(0, BEARD)
    g.setColorAt(1, BEARD_LIGHT)
    p.setBrush(QBrush(g))
    p.drawPath(beard)
    p.save()
    p.setClipPath(beard)
    grey = QRadialGradient(QPointF(8, 44), 22)
    grey.setColorAt(0, BEARD_GREY)
    grey.setColorAt(0.55, QColor(BEARD_GREY.red(), BEARD_GREY.green(), BEARD_GREY.blue(), 200))
    grey.setColorAt(1, QColor(BEARD_GREY.red(), BEARD_GREY.green(), BEARD_GREY.blue(), 0))
    p.setBrush(QBrush(grey))
    p.drawEllipse(QPointF(8, 44), 22, 20)
    p.setPen(_pen(BEARD_DARK, 1.3))
    for bx, by, dx in ((-24, 8, 1), (-18, 20, 1), (-8, 30, 0.5), (24, 30, -0.6), (30, 18, -1), (-27, -2, 1)):
        p.drawLine(QPointF(bx, by), QPointF(bx + dx * 1.5, by + 3.5))
    p.setPen(_pen(QColor(190, 186, 182), 1.2))
    for bx, by in ((2, 38), (10, 40), (16, 36)):
        p.drawLine(QPointF(bx, by), QPointF(bx + 0.6, by + 3))
    p.restore()
    p.setPen(_pen(INK, 2.8))
    p.setBrush(NO_BRUSH)
    p.drawPath(beard)


def _eye(p, cx, cy, rx, ry, pose):
    if pose.eyes == "happy":
        p.setPen(_pen(INK, 3.6))
        p.setBrush(NO_BRUSH)
        p.drawArc(QRectF(cx - rx * 0.9, cy - ry * 0.35, 2 * rx * 0.9, ry * 1.1), 15 * 16, 150 * 16)
        return
    if pose.eyes == "closed" or pose.blink > 0.88:
        p.setPen(_pen(INK, 3.4))
        p.setBrush(NO_BRUSH)
        p.drawArc(QRectF(cx - rx * 0.9, cy - ry * 0.6, 2 * rx * 0.9, ry * 0.95), 195 * 16, 150 * 16)
        return
    p.save()
    p.translate(cx, cy)
    p.scale(1, max(0.12, 1 - pose.blink))
    eye = QPainterPath()
    eye.addEllipse(QPointF(0, 0), rx, ry)
    p.setPen(NO_PEN)
    p.setBrush(WHITE)
    p.drawPath(eye)
    p.save()
    p.setClipPath(eye)
    ix = 1.5 + pose.look_x * rx * 0.32
    iy = 1 + pose.look_y * ry * 0.32
    ir = rx * 0.68
    g = QRadialGradient(QPointF(ix, iy + ir * 0.35), ir * 1.1)
    g.setColorAt(0, IRIS_OUT)
    g.setColorAt(0.75, IRIS_IN)
    g.setColorAt(1, QColor(26, 20, 70))
    p.setBrush(QBrush(g))
    p.drawEllipse(QPointF(ix, iy), ir, ir * 1.08)
    p.setBrush(QColor(14, 10, 30))
    pr = rx * (0.3 + 0.08 * pose.sparkle)
    p.drawEllipse(QPointF(ix, iy), pr, pr * 1.08)
    p.setBrush(QColor(200, 196, 220, 70))
    p.drawEllipse(QPointF(0, -ry * 0.75), rx * 1.1, ry * 0.5)  # lid shadow
    if pose.tears > 0.03:
        water = QColor(TEAR)
        water.setAlpha(int(200 * min(1.0, pose.tears)))
        p.setBrush(water)
        p.drawEllipse(QPointF(0, ry * 0.95), rx * 1.05, ry * 0.32 * min(1.0, pose.tears * 1.4))
    p.setBrush(WHITE)
    p.drawEllipse(QPointF(ix - ir * 0.38, iy - ir * 0.42), ir * 0.34, ir * 0.36)
    p.drawEllipse(QPointF(ix + ir * 0.38, iy + ir * 0.36), ir * 0.14, ir * 0.14)
    if pose.sparkle > 0.05:
        p.setBrush(QColor(255, 255, 255, int(230 * min(1.0, pose.sparkle))))
        p.drawPolygon(star_polygon(ix + ir * 0.15, iy - ir * 0.05, ir * 0.42, points=4, inner=0.3))
    p.restore()
    p.setPen(_pen(INK, 2.6))
    p.setBrush(NO_BRUSH)
    p.drawPath(eye)
    p.setPen(_pen(INK, 3.6))
    p.drawArc(QRectF(-rx, -ry, 2 * rx, 2 * ry), 30 * 16, 120 * 16)  # heavier upper lid
    p.restore()


def _tears(p, amount, clock):
    """Streams running down both cheeks, like the card."""
    k = min(1.0, amount)
    for cx, cy, side in ((-5, 9, -1), (18, 10, 1)):
        length = 6 + 13 * k
        wob = math.sin(clock * 9 + cx) * 1.5
        path = QPainterPath(QPointF(cx + side * 2, cy))
        path.cubicTo(cx + side * 8 + wob, cy + length * 0.3, cx + side * 3 - wob, cy + length * 0.7,
                     cx + side * 7, cy + length)
        w = 2.5 + 3 * k
        p.setBrush(NO_BRUSH)
        p.setPen(_pen(INK, w + 3))
        p.drawPath(path)
        p.setPen(_pen(TEAR, w))
        p.drawPath(path)
        p.setPen(_pen(QColor(255, 255, 255, 200), 1.4))
        p.drawPath(path.translated(-side * w * 0.2, 0))
        end = QPointF(cx + side * 7, cy + length + 2)
        p.setPen(_pen(INK, 1.6))
        p.setBrush(TEAR)
        p.drawEllipse(end, w * 0.65, w * 0.8)


def _mouth(p, pose):
    mx, my = 11, 27
    if pose.mouth == "o":
        rx = 3.6 + 4.0 * pose.mouth_open
        ry = 3.6 + 8.0 * pose.mouth_open
        p.setPen(_pen(INK, 2.4))
        p.setBrush(MOUTH)
        p.drawEllipse(QPointF(mx, my + ry * 0.3), rx, ry)
        if pose.mouth_open > 0.3:
            p.setPen(NO_PEN)
            p.setBrush(TONGUE)
            p.drawEllipse(QPointF(mx, my + ry * 0.85), rx * 0.65, ry * 0.32)
        return
    s = pose.smile
    o = pose.mouth_open
    w = 9 + 3 * max(s, 0) + 5 * o
    if o < 0.08:
        path = QPainterPath(QPointF(mx - w, my - s * 3))
        path.quadTo(mx, my + s * 7, mx + w, my - s * 3)
        p.setPen(_pen(INK, 3))
        p.setBrush(NO_BRUSH)
        p.drawPath(path)
        return
    h = 4 + 17 * o
    path = QPainterPath(QPointF(mx - w, my - s * 3))
    path.quadTo(mx, my + s * 1.5, mx + w, my - s * 3)
    path.quadTo(mx + w * 0.4, my + h + s * 4, mx, my + h + s * 4)
    path.quadTo(mx - w * 0.4, my + h + s * 4, mx - w, my - s * 3)
    p.setPen(NO_PEN)
    p.setBrush(MOUTH)
    p.drawPath(path)
    p.save()
    p.setClipPath(path)
    p.setBrush(WHITE)
    top = my - s * 3 - 5
    p.drawRect(QRectF(mx - w, top, 2 * w, 9 + s * 0.5))
    p.setPen(_pen(QColor(200, 196, 210), 1))
    for tx in (-w * 0.5, 0, w * 0.5):
        p.drawLine(QPointF(mx + tx, top + 3), QPointF(mx + tx, top + 9))
    p.setPen(NO_PEN)
    p.setBrush(TONGUE)
    p.drawEllipse(QPointF(mx + 1, my + h + s * 3), w * 0.62, h * 0.45)
    p.restore()
    p.setPen(_pen(INK, 2.6))
    p.setBrush(NO_BRUSH)
    p.drawPath(path)


def _hat(p, bend, squash, tilt):
    p.save()
    p.translate(2, -30)
    p.rotate(-5 + tilt - bend * 0.35)
    sq = squash
    crown = QPainterPath(QPointF(-29, -2))
    crown.cubicTo(-31, -20 * sq, -18, -31 * sq, 2, -31 * sq)
    crown.cubicTo(22, -31 * sq, 32, -20 * sq, 29, -2)
    crown.closeSubpath()
    g = QLinearGradient(-30, 0, 30, 0)
    g.setColorAt(0, HAT_DARK)
    g.setColorAt(0.6, HAT_LIGHT)
    g.setColorAt(1, HAT)
    p.setPen(_pen(INK, 2.8))
    p.setBrush(QBrush(g))
    p.drawPath(crown)
    p.setPen(_pen(HAT_LIGHT.lighter(115), 1.3, Qt.PenStyle.DashLine))
    p.setBrush(NO_BRUSH)
    seam = QPainterPath(QPointF(-12, -4))
    seam.quadTo(-12, -22 * sq, 2, -29 * sq)
    seam.moveTo(16, -4)
    seam.quadTo(17, -22 * sq, 4, -29 * sq)
    p.drawPath(seam)
    p.setPen(_pen(INK, 1.4))
    p.setBrush(GOLD)
    for sx, sy, r in CROWN_STARS:
        p.drawPolygon(star_polygon(sx, sy * sq, r))
    draw_mushroom(p, 8, -20 * sq, 0.95)
    band = QPainterPath(QPointF(-29.5, -1))
    band.lineTo(29.5, -1)
    band.lineTo(28.8, -8)
    band.lineTo(-28.8, -8)
    band.closeSubpath()
    p.setPen(_pen(INK, 2.2))
    p.setBrush(HAT_DARK)
    p.drawPath(band)

    brim = QPainterPath(QPointF(-34, -4))
    brim.quadTo(2, 2, 36, -4)
    brim.quadTo(46, -1, 49, 5)
    brim.quadTo(2, 18, -47, 5)
    brim.quadTo(-44, -1, -34, -4)
    g = QLinearGradient(0, -4, 0, 16)
    g.setColorAt(0, HAT)
    g.setColorAt(1, HAT_LIGHT)
    p.setPen(_pen(INK, 2.8))
    p.setBrush(QBrush(g))
    p.drawPath(brim)
    p.setPen(_pen(HAT_LIGHT.lighter(120), 1.3, Qt.PenStyle.DashLine))
    p.setBrush(NO_BRUSH)
    stitch = QPainterPath(QPointF(-41, 5))
    stitch.quadTo(2, 15, 43, 5)
    p.drawPath(stitch)
    p.setPen(_pen(INK, 1.3))
    p.setBrush(GOLD)
    for sx, sy, r in BRIM_STARS:
        p.drawPolygon(star_polygon(sx, sy, r))
    p.restore()
