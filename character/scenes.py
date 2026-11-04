"""Scenes: multi-step bits built on top of the basic actions.

kroger   The clearance aisle. He spots a marked-down find, picks it up, scratches
         his beard, daydreams about it, does the math, then: puts it back and
         shrugs, decides it's a steal and stuffs it in his hat, or almost walks
         off with it before putting it back. Most of the time the find is a real
         desktop icon (from desktop-awareness/): three bees lift him up beside
         it, his companion bee fetches a glowing copy, he does the math on the
         file's real size and age, and the bee flies the copy back into its
         slot. A brand-new file on the desktop gets checked out next.
vending  A card vending machine rises out of the floor. He walks over and
         stares at the screen: sold out (shoulders drop, a sad tear, slow walk
         away) or the booster bundle is in stock: he rips it open and pulls
         The Ultimate Pull, a giant holo card, crying tears of joy with his
         fists up like the reference card. A pity counter makes repeat
         letdowns less likely.

Scenes queue a walk and then their own action; Buddy mixes this class in.
"""
import math
import random

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath

from character.moves import dance_pose, fists_up, gait_pose, hold, hug, palms_up, scratch_beard, shrug
from character.props import ITEMS, Item, Machine, draw_item, ease_back, font
from character.rig import GOLD, INK, Pose, _pen, draw_front_hand, ease, lerp, star_polygon

RUMMAGE = 3.4   # seconds flipping through the pack before the last card turns over

SCENES = {"kroger": 1.2, "vending": 0.6, "perch": 1.0}  # random-pick weights
PERCH_LINES = ["nice view.", "best seat in the house.", "comfy.", "don't mind me."]

MATH_LINES = ["{price}", "+ tax...", "need it?", "where'd it go?", "hmm..."]
NAH = ["nah.", "eh... nah.", "not today.", "pass."]
STEAL = ["ooh, a steal!", "SOLD!", "mine now."]
WAITING = ["...", "c'mon...", "please...", "bundle?"]


class SceneMixin:
    # setup ------------------------------------------------------------------
    def setup_scene(self, name, **kw):
        return getattr(self, "_scene_" + name)(**kw)

    def _scene_kroger(self, icon=None, fresh=False):
        visible = [i for i in self.icons if self.icon_visible(i)]
        if icon is None and visible and self.icon_visits and random.random() < 0.75:
            icon = random.choice(visible)
        if icon is not None:
            return self._scene_kroger_icon(icon, fresh)
        s = self.scale
        margin = 140 * s
        side = random.choice([-1, 1])
        if not margin < self.x + side * 300 * s < self.width - margin:
            side = -side
        x = max(margin, min(self.width - margin, self.x + side * random.uniform(220, 420) * s))
        item = Item(random.choice(ITEMS), x, self.floor - 20 * s, s)
        self.props.append(item)
        side = 1 if x >= self.x else -1
        self.queue.append(("kroger", {"item": item}))
        return "walk", {"target": x - side * 58 * s, "mood": random.choice(["content", "cheery"]),
                        "notice": None}

    def _scene_kroger_icon(self, icon, fresh):
        s = self.scale
        c = icon.center
        side = 1 if self.x <= c.x() else -1
        x = c.x() - side * 100 * s
        if not 60 * s < x < self.width - 60 * s:
            side = -side
            x = c.x() - side * 100 * s
        x = max(60 * s, min(self.width - 60 * s, x))
        # hover low enough that his hat and the lifting bees stay on screen
        feet = max(c.y() + 190 * s, 250 * s)
        air = max(0.0, (self.floor - feet) / s)
        item = Item("icon", c.x(), c.y(), s, pixmap=icon.pixmap())
        item.alpha = 0.0
        item.math = [icon.size_text(), icon.age_text(),
                     random.choice(["need it?", "worth the space?", "where'd it go?"]), "hmm..."]
        self.props.append(item)
        self.queue += [("walk", {"target": x, "mood": "cheery", "speed": 120 * s, "notice": None}),
                       ("fly", {"to": air}),
                       ("kroger", {"item": item, "airborne": air > 1}),
                       ("fly", {"to": 0.0})]
        return "spot_icon", {"icon": icon, "fresh": fresh}

    # windows (from desktop-awareness/windows.py) ------------------------------
    def _win(self, wid):
        return next((w for w in self.windows if w.id == wid), None)

    def local(self, rect):
        """A window rect in this overlay's coordinates."""
        return rect.translated(-self.screen_origin.x(), -self.screen_origin.y())

    def covered(self, x, y, above=-1):
        return any(w.z > above and self.local(w.rect).contains(QPointF(x, y)) for w in self.windows)

    def icon_visible(self, icon):
        c = icon.center
        return not self.covered(c.x(), c.y())

    def perch_spots(self):
        """Title bars with room to sit on: (window, x) pairs, in overlay coordinates."""
        s = self.scale
        spots = []
        for w in self.windows:
            if w.fullscreen:
                continue
            r = self.local(w.rect)
            if not 220 * s < r.top() < self.floor - 200 * s:
                continue
            left = max(r.left() + 60 * s, 70 * s)
            right = min(r.right() - 60 * s, self.width - 70 * s)
            if right - left < 60 * s:
                continue
            for _ in range(6):  # a spot on the bar no window above is covering
                x = random.uniform(left, right)
                if not self.covered(x, r.top() - 10 * s, above=w.z) and not self.covered(x, r.top() + 4, above=w.z):
                    spots.append((w, x))
                    break
        return spots

    def _perch_air(self, wid):
        w = self._win(wid)
        if w is None:
            return None
        return max(0.0, (self.floor - self.local(w.rect).top()) / self.scale)

    def _scene_perch(self):
        spots = self.perch_spots()
        if not spots:
            return "idle", {}
        w, x = random.choice(spots)
        s = self.scale
        self.queue += [("fly", {"to": self._perch_air(w.id), "win": w.id}),
                       ("perch", {"win": w.id, "dx": x - self.local(w.rect).left()}),
                       ("fly", {"to": 0.0})]
        return "walk", {"target": x, "mood": "cheery", "speed": 120 * s, "notice": None}

    def _start_perch(self):
        for bee in getattr(self, "lift_bees", []):  # he's standing on his own now
            self.hive.dismiss(bee)
        self.lift_bees = []
        self.perched = True
        self.dur = random.uniform(9, 14)
        self.say(random.choice(PERCH_LINES), life=1.6)

    def _perch(self, dt):
        """Sits on a window's title bar, legs dangling, and rides along if it moves."""
        d = self.data
        s = self.scale
        w = self._win(d["win"])
        if w is None or w.fullscreen:  # the window's gone: the bees will catch him
            if self._once("fell"):
                self.say("whoa!", life=1.2)
                self.done = True
            return palms_up(Pose(brow=1.0, mouth="o", mouth_open=0.7, look_y=0.8))
        r = self.local(w.rect)
        x = max(r.left() + 30 * s, min(r.right() - 30 * s, r.left() + d["dx"]))
        if dt > 0 and abs(x - self.x) / dt > 500 * s and self.t > 0.5:
            d["wild"] = 0.7  # someone's dragging the window around
        self.x = x
        t, end = self.t, self.dur
        sit = ease((t - 1.0) / 0.5) * (1 - ease((t - (end - 1.0)) / 0.6))
        self.air = max(0.0, (self.floor - r.top()) / s - 12 * sit)
        kick = math.sin(t * 3.0)
        pose = Pose(bob=26 * sit, hip_f=lerp(0, 72, sit) + 16 * kick * sit, knee_f=lerp(4, 80, sit) + 10 * kick * sit,
                    hip_b=lerp(0, 66, sit) - 16 * kick * sit, knee_b=lerp(4, 84, sit) - 10 * kick * sit,
                    sh_f=lerp(10, 24, sit), el_f=lerp(16, -40, sit), hand_f="open",
                    sh_b=lerp(-12, -24, sit), el_b=lerp(12, 40, sit), hand_b="open",
                    smile=0.9, blush=0.5, head=3 * math.sin(t * 1.3))
        if sit > 0.5:
            self._eyes_on_bee(pose)
            if math.sin(t * 0.7) > 0.3:  # hums a little tune
                pose.mouth, pose.mouth_open = "o", 0.12 + 0.08 * abs(math.sin(t * 5))
                self._every("note", 0.9, lambda: self.fx.note(*self._head_xy(24, -40)))
        if d.get("wild", 0) > 0:
            d["wild"] -= dt
            if self._once("whoa-ride"):
                self.say(random.choice(["whoa whoa whoa!", "wheee!", "easy, easy!"]), life=1.4)
            pose = palms_up(pose)
            pose.brow, pose.mouth, pose.mouth_open, pose.sparkle = 1.0, "o", 0.6, 0.6
        return pose

    def _scene_vending(self):
        s = self.scale
        if any(isinstance(q, Machine) for q in self.props):
            return "idle", {}
        side = 1 if self.x < self.width / 2 else -1
        mx = self.width - 110 * s if side > 0 else 110 * s
        m = Machine(mx, self.floor, s)
        self.props.insert(0, m)
        self.queue += [("walk", {"target": mx - side * 118 * s, "mood": "cheery",
                                 "speed": 110 * s, "notice": None}),
                       ("vending", {"machine": m})]
        return "spot_machine", {"machine": m}

    # props ------------------------------------------------------------------
    def update_props(self, dt):
        s = self.scale
        for q in self.props:
            q.update(dt)
            if not isinstance(q, Item):
                continue
            if q.fly is not None:
                q.fly = min(1.0, q.fly + dt / 0.6)
                k = ease(q.fly)
                to = self._anchor("hat_top")
                q.x = lerp(q.fly_from.x(), to.x(), k)
                q.y = lerp(q.fly_from.y(), to.y() + 30 * s, k) - 60 * s * math.sin(k * math.pi)
                q.size = q.fly_size * (1 - 0.95 * k)
                q.angle += 720 * dt
                if q.fly >= 1:
                    for _ in range(14):
                        self.fx.sparkle(q.x, q.y, speed=120)
                    q.gone = True
            elif q.free:
                if not q.settled:
                    q.vy += 2200 * s * dt
                    q.x += q.vx * dt
                    q.y += q.vy * dt
                    q.angle += q.spin * dt
                    ground = self.floor - 10 * s
                    if q.y >= ground:
                        q.y = ground
                        if abs(q.vy) > 160 * s:   # a bounce or two, then it lies there
                            q.vy *= -0.38
                            q.vx *= 0.55
                            q.spin *= 0.4
                        else:
                            q.settled = True
            elif q.carrier is not None:
                q.x, q.y = q.carrier.x, q.carrier.y + 18 * s
                if q.deliver_to is not None and q.carrier.arrived(14):  # back in its slot
                    q.alpha = max(0.0, q.alpha - dt / 0.25)
                    if q.alpha <= 0:
                        q.gone = True
                        self._release_bee(q.carrier)
                        for _ in range(10):
                            self.fx.sparkle(q.x, q.y, speed=70)
            elif q.grab > 0:
                h = self._anchor("hand_f")
                tx = h.x() + self.facing * q.hold[0] * s
                ty = h.y() + q.hold[1] * s
                q.x, q.y = lerp(q.rest.x(), tx, q.grab), lerp(q.rest.y(), ty, q.grab)
            else:
                q.x, q.y = q.rest.x(), q.rest.y()
        self.props = [q for q in self.props if not q.gone]
        if self.thought:
            self.thought["age"] += dt
            if self.thought["age"] > self.thought["life"]:
                self.thought = None

    def props_bounds(self):
        r = QRectF()
        for q in self.props:
            r = r.united(q.bounds())
        if self.thought:
            r = r.united(self._thought_rect().adjusted(-10, -10, 10, 60 * self.scale))
        return r

    def _in_hand(self, q):
        return isinstance(q, Item) and q.fly is None and q.carrier is None and q.grab >= 0.5

    def draw_props_behind(self, p):
        for q in self.props:
            if isinstance(q, Machine) or (q.carrier is None and q.fly is None and not self._in_hand(q)):
                q.draw(p)

    def draw_props_front(self, p):
        held = False
        for q in self.props:
            if isinstance(q, Item) and not q.behind and (self._in_hand(q) or q.carrier or q.fly is not None):
                q.draw(p)
                held = held or (self._in_hand(q) and q.grab >= 0.9)
        if held:  # fingers wrap around whatever he's holding
            draw_front_hand(p, self.x, self.floor, self.facing, self.scale, self.pose)

    def think(self, kind, life, item=None, lines=None, side=1, force=False):
        """Thought cloud; side=1 puts it in front of him, -1 behind."""
        if self.quiet and not force:
            return
        self.thought = {"kind": kind, "age": 0.0, "life": life, "item": item,
                        "lines": lines or [], "side": side}

    def _thought_rect(self):
        s = self.scale
        top = self._anchor("hat_top")
        cx = top.x() + self.thought["side"] * self.facing * 80 * s
        y = top.y() - 40 * s
        if y < 4:  # up by the top edge: think off to the side, away from the icons
            cx = self._anchor("C").x() - self.facing * 130 * s
            y = 4.0
        cx = max(80 * s, min(self.width - 80 * s, cx))
        return QRectF(cx - 62 * s, y, 124 * s, 80 * s)

    def draw_thought(self, p):
        if not self.thought:
            return
        s = self.scale
        th = self.thought
        r = self._thought_rect()
        c = r.center()
        head = self._anchor("C")
        pop = ease_back(th["age"] / 0.3)
        fade = max(0.0, min(1.0, (th["life"] - th["age"]) / 0.3))
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(fade)
        p.setPen(_pen(INK, 2.2 * s))
        p.setBrush(QColor(255, 255, 255, 245))
        base = QPointF(c.x(), r.bottom())
        for f, rad in ((0.35, 4), (0.65, 7)):
            pt = head + (base - head) * f
            p.drawEllipse(pt + QPointF(0, -14 * s * f), rad * s * pop, rad * s * pop)
        cloud = QPainterPath()
        for dx, dy, rad in ((0, 4, 30), (-34, 8, 22), (34, 8, 22), (-17, -14, 24),
                            (18, -15, 23), (0, 20, 20), (-22, 20, 16), (22, 20, 16)):
            blob = QPainterPath()
            blob.addEllipse(c + QPointF(dx, dy) * s * pop, rad * s * pop, rad * s * pop)
            cloud = cloud.united(blob)
        p.drawPath(cloud)
        if th["kind"] == "dream":
            p.save()
            p.translate(c + QPointF(0, 4 * s))
            p.rotate(math.sin(th["age"] * 3) * 8)
            k = 1.15 * s * pop
            p.scale(k, k)
            draw_item(p, th["item"].kind, th["age"], tag=False, pixmap=th["item"].pixmap)
            p.restore()
            p.setPen(_pen(INK, 1))
            for i, (dx, dy) in enumerate(((-36, -6), (34, -12), (28, 22))):
                tw = 0.6 + 0.4 * math.sin(th["age"] * 8 + i * 2)
                p.setBrush(GOLD if i != 1 else QColor(255, 120, 170))
                p.drawPolygon(star_polygon(c.x() + dx * s, c.y() + dy * s, 6 * s * tw, points=4, inner=0.35))
        else:
            lines = th["lines"]
            text = lines[min(len(lines) - 1, int(th["age"] / 0.45))] if lines else "..."
            p.setFont(font((15 if len(text) <= 12 else 12) * s))
            p.setPen(INK)
            p.drawText(QRectF(c.x() - 52 * s, c.y() - 22 * s, 104 * s, 50 * s), 0x0084 | 0x1000, text)
        p.restore()

    # kroger: the clearance aisle ------------------------------------------------
    def _start_kroger(self):
        d = self.data
        item = d["item"]
        self.facing = 1 if item.x >= self.x else -1
        d.setdefault("airborne", False)
        d["outcome"] = random.choices(["nah", "steal", "almost"], [0.55, 0.25, 0.2])[0]
        # up in the air the bee needs time to fetch the copy, and to fly it back
        d["by_bee"] = item.kind == "icon"  # a real icon's glowing copy is fetched and returned by a bee
        d["fetch"] = 2.4 if d["by_bee"] else 0.8
        d["rel"] = 1.8 if d["by_bee"] else 0.8
        extra = (d["fetch"] - 0.8) + (d["rel"] - 0.8)
        self.dur = {"nah": 9.4, "steal": 9.8, "almost": 12.8}[d["outcome"]] + extra
        d["home"] = self.x
        d["slot"] = QPointF(item.rest)  # where an icon copy goes back to

    def _kroger(self, dt):
        d = self.data
        item = d["item"]
        t = self.t
        s = self.scale
        up = d["airborne"]
        if t < 0.7:  # spotted it
            if not up and self._once("spot"):
                self.fx.bang(*self._head_xy(-10, -100))
            a = ease(t / 0.25)
            return Pose(lean=(-4 if up else 8) * a, look_x=1.0, look_y=(-0.7 if up else 0.8) * a,
                        brow=1.0 * a, quirk=0.8, mouth="o", mouth_open=0.4, head=(-6 if up else 8) * a,
                        sparkle=0.6)
        fetch_end = 0.7 + d["fetch"]
        if t < fetch_end:  # pick it up (up in the air, the bee fetches a copy)
            u = (t - 0.7) / d["fetch"]
            if d["by_bee"]:
                return self._bee_fetch(u, item)
            item.grab = ease((u - 0.4) / 0.5)
            return self._bend(math.sin(min(1.0, u) * math.pi), item.grab)
        t -= d["fetch"] - 0.8  # the rest of the timeline is the same either way
        if t < 2.9:  # inspect: turn it over, scratch the beard
            item.angle = 18 * math.sin(t * 4)
            return scratch_beard(hold(Pose(look_x=1.0, look_y=0.1, quirk=1.0, brow=0.4, mouth="o",
                                           mouth_open=0.15, head=6 * math.sin(t * 2), lean=3)), t, 9)
        if t < 5.1:  # daydream about what he could do with it
            item.angle *= 0.9
            if self._once("dream"):
                self.think("dream", 2.1, item=item)
            self._every("heart", 0.6, lambda: self.fx.heart(*self._head_xy(-20, -50)))
            return hold(Pose(eyes="happy", smile=1.0, mouth="smile", mouth_open=0.2, blush=0.85,
                             head=-6 + 3 * math.sin(t * 2.5), lean=-3 + 2 * math.sin(t * 2.5),
                             sh_b=-30, el_b=-20, hand_b="open"))
        if t < 6.9:  # does the real math
            if self._once("math"):
                if item.math:
                    self.think("math", 1.8, lines=item.math)
                else:
                    lines = [ln.format(price=item.price) for ln in MATH_LINES]
                    self.think("math", 1.8, lines=[lines[0]] + random.sample(lines[1:4], 2) + ["hmm..."])
            return scratch_beard(hold(Pose(look_x=0.4, look_y=-0.7, brow=-0.4, quirk=0.6, smile=-0.1,
                                           head=5, lean=1), up=-5), t, 16)
        return getattr(self, "_kroger_" + d["outcome"])(t - 6.9, item, s)

    def _bend(self, a, grab=0.0):
        """Crouch down toward something on the floor in front of him (a 0..1)."""
        pose = Pose(lean=24 * a, bob=13 * a, hip_f=30 * a, knee_f=4 + 58 * a, hip_b=20 * a,
                    knee_b=4 + 52 * a, look_x=1.0, look_y=0.9, brow=0.3, smile=0.7,
                    sh_b=-20 * a, el_b=20)
        pose.sh_f, pose.el_f, pose.hand_f = lerp(10, 30, a), lerp(16, -10, a), "open"
        if grab > 0.5 and a < 0.6:
            hold(pose)
        return pose

    def _errand_bee(self):
        """The companion bee, or (if it's switched off) a helper bee that flies in."""
        bee = self.data.get("bee")
        if bee is None:
            bee = self.companion
            if bee is None:
                bee = self.hive.spawn(self._bee_spot)
                bee.helper = True
            self.data["bee"] = bee
        return bee

    def _release_bee(self, bee):
        if getattr(bee, "helper", False):
            self.hive.dismiss(bee)
        else:
            bee.target, bee.speed, bee.wiggle = self._bee_spot, 320, 1.0

    def _bee_fetch(self, u, item):
        """u runs 0..1: the companion bee flies up, grabs a glowing copy of the
        icon and brings it down to his hand."""
        s = self.scale
        bee = self._errand_bee()
        item.alpha = min(1.0, u / 0.25)
        if bee and self._once("send"):
            bee.target = lambda: item.rest
            bee.wiggle, bee.speed = 0.15, 420
        if bee and item.carrier is None and item.grab == 0 and (bee.arrived(14) or u > 0.45):
            if self._once("grabbed"):
                item.carrier = bee
                bee.target = lambda: self._anchor("hand_f") + QPointF(self.facing * 18 * s, -16 * s)
                self.fx.sparkle(item.x, item.y, speed=80)
        if item.carrier is not None and (bee.arrived(16) or u > 0.9) and self._once("handoff"):
            item.carrier = None
            item.rest = QPointF(item.x, item.y)
            item.grab = 0.01
            self._release_bee(bee)
        if item.grab > 0:
            item.grab = min(1.0, item.grab + self._dt / 0.2)
        self._every("spark", 0.08, lambda: self.fx.sparkle(item.x, item.y, speed=40))
        reach = item.grab < 0.5
        pose = Pose(look_x=0.8, look_y=-0.6 if u < 0.5 else 0.2, brow=0.8, quirk=1.0, mouth="o",
                    mouth_open=0.4, sparkle=0.5)
        if reach:  # "gimme gimme"
            pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 120, 20 + 15 * math.sin(self.t * 14), 1.3, "open"
        else:
            hold(pose)
        return pose

    def _bee_return(self, u, item):
        """u runs 0..1: the bee takes the copy back up into its slot, where it fades."""
        if self._once("takeback"):
            self.data.pop("bee", None)
            bee = self._errand_bee()
            item.rest = QPointF(item.x, item.y)
            item.grab = 0.0
            slot = self.data["slot"]
            if bee:
                item.carrier, item.deliver_to = bee, slot
                bee.target = lambda: slot
                bee.wiggle, bee.speed = 0.15, 360
            else:
                item.gone = True
        return palms_up(Pose(look_x=0.8, look_y=-0.6, smile=0.6, brow=0.4))

    def _put_back(self, u, item):
        """u runs 0..1 over 0.8s: crouch, set it down, stand back up."""
        if self._once("rest"):
            item.rest = QPointF(item.x, self.floor - 20 * self.scale)
            item.angle = 0
        item.grab = 1 - ease((u - 0.25) / 0.35)
        return self._bend(math.sin(min(1.0, u) * math.pi), item.grab)

    def _release(self, u, item):
        return (self._bee_return if self.data["by_bee"] else self._put_back)(u, item)

    def _done_with(self, item):
        if not self.data["by_bee"]:
            item.expire = 6.0

    def _kroger_nah(self, u, item, s):
        rel = self.data["rel"]
        if u < rel:
            return self._release(u / rel, item)
        if self._once("nah"):
            self.say(random.choice(NAH), life=1.8)
            self._done_with(item)
        return shrug(Pose(look_x=0.6))

    def _kroger_steal(self, u, item, s):
        if u < 1.4:  # hug it and hop
            if self._once("steal"):
                self.say(random.choice(STEAL), life=1.6)
            self._every("heart", 0.22, lambda: self.fx.heart(*self._xy(self._anchor("hand_f"))))
            item.hold = (6.0, -10.0)
            return hug(Pose(lift=18 * abs(math.sin(u * 7)), eyes="happy", smile=1.0, mouth="smile",
                            mouth_open=0.55, blush=1.0, head=-4, hat=-6 * abs(math.sin(u * 7))))
        if self._once("poof"):  # into the hat it goes
            item.fly, item.fly_from, item.fly_size = 0.0, QPointF(item.x, item.y), item.size
            item.grab = 0.0
        pose = Pose(eyes="happy", smile=1.0, mouth="smile", mouth_open=0.3, blush=0.8,
                    look_y=-1.0, quirk=0.8, head=-6)
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 140, 20, 1.5, "open"  # pats the hat
        return pose

    def _kroger_almost(self, u, item, s):
        if u < 0.4:  # turns to leave with it
            if self._once("take"):
                self.facing = -self.facing
                self.say("i'll take it!", life=1.4)
            return hold(Pose(smile=0.9, mouth="smile", mouth_open=0.3, eyes="happy"))
        if u < 1.7:  # three happy steps away
            self.x = max(60 * s, min(self.width - 60 * s, self.x + self.facing * 60 * s * self._dt))
            return hold(gait_pose((u - 0.4) * 5, "content"))
        if u < 2.5:  # wait...
            if self._once("wait"):
                self.fx.bang(*self._head_xy(-10, -100))
            return hold(Pose(look_x=-1.0, brow=1.0, quirk=1.0, mouth="o", mouth_open=0.4, head=-6))
        if u < 3.8:  # back to the shelf
            if self._once("back"):
                self.facing = -self.facing
            home = self.data["home"]
            step = 60 * s * self._dt
            self.x = home if abs(home - self.x) <= step else self.x + step * (1 if home > self.x else -1)
            return hold(gait_pose((u - 2.5) * 5, "sad"))
        rel = self.data["rel"]
        if u < 3.8 + rel:
            return self._release((u - 3.8) / rel, item)
        if self._once("nope"):
            self.say("...nope.", life=1.6)
            self._done_with(item)
        return shrug(Pose(look_x=0.6))

    # getting up to the icons: the bees lift him ----------------------------------
    def _start_spot_icon(self):
        icon = self.data["icon"]
        self.dur = 1.6
        self.facing = 1 if icon.center.x() >= self.x else -1
        self.fx.bang(*self._head_xy(-10, -100))
        if self.data.get("fresh"):
            self.say("ooh, new!", life=1.5)

    def _spot_icon(self, dt):
        a = ease(self.t / 0.3)
        pose = Pose(lean=-7 * a, head=-10 * a, look_x=0.6, look_y=-1.0 * a, brow=1.0 * a,
                    quirk=0.9, mouth="o", mouth_open=0.4, sparkle=0.6)
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 110, 40, 1.3, "point"
        return pose

    def _start_fly(self):
        d = self.data
        if d.get("win"):  # flying up to a window's title bar
            to = self._perch_air(d["win"])
            d["to"] = self.air if to is None else to
        d["from"] = self.air
        rising = d["to"] > d["from"]
        s = self.scale
        travel = max(0.9, abs(d["to"] - d["from"]) * s / 300)
        crew = getattr(self, "lift_bees", [])
        if abs(d["to"] - d["from"]) > 1 and (rising or not crew):
            # call in the lift crew: a bee on each side of his hat brim, one on top
            spots = [("brim_f", QPointF(4, -8)), ("brim_b", QPointF(-4, -8)),
                     ("hat_top", QPointF(0, -8))]
            self.lift_bees = []
            for name, off in spots:
                bee = self.hive.spawn(lambda n=name, o=off: self._anchor(n) + QPointF(
                    self.facing * o.x() * s, o.y() * s))
                bee.wiggle, bee.speed = 0.08, 620
                self.lift_bees.append(bee)
            d["gather"] = 1.4 if rising else 0.9
            self.dur = d["gather"] + travel
        else:
            d["gather"] = 0.0
            self.dur = travel

    def _fly(self, dt):
        d = self.data
        if d.get("win"):  # the window may move while he's on the way up
            to = self._perch_air(d["win"])
            if to is not None:
                d["to"] = to
        rising = d["to"] > d["from"]
        bees = getattr(self, "lift_bees", [])
        if self.t < d["gather"]:  # waiting for the bees to grab on
            if rising and self._once("whoa") and bees:
                self.say(random.choice(["whoa whoa!", "beeee buddies!", "up we go!"]), life=1.3)
            return palms_up(Pose(look_y=-0.8, look_x=0.4, brow=0.9, quirk=1.0, mouth="o",
                                 mouth_open=0.5, sparkle=0.5))
        u = (self.t - d["gather"]) / max(0.01, self.dur - d["gather"])
        self.air = lerp(d["from"], d["to"], ease(u))
        if self.air > 2:
            feet = self.world(QPointF(0, 0))
            self._every("trail", 0.05, lambda: self.fx.sparkle(
                feet.x() + random.uniform(-14, 14) * self.scale, feet.y(), speed=30))
        if not rising and u >= 0.98 and self._once("land"):
            self.fx.dust(self.x, self.floor, 8)
            for bee in bees:
                self.hive.dismiss(bee)
            self.lift_bees = []
        pose = Pose(look_x=0.6, look_y=-0.5 if rising else 0.7, smile=1.0, mouth="smile",
                    mouth_open=0.5, eyes="open" if rising else "happy", blush=0.6, sparkle=0.5)
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 90 + 10 * math.sin(self.t * 6), 30, 1.2, "open"
        pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -90 - 10 * math.sin(self.t * 6), -30, 1.2, "open"
        return pose

    # vending: the card machine --------------------------------------------------
    def _start_spot_machine(self):
        m = self.data["machine"]
        self.dur = 1.5
        self.facing = 1 if m.x >= self.x else -1
        self.fx.bang(*self._head_xy(-10, -100), "!!")

    def _spot_machine(self, dt):
        hop = math.sin(min(1.0, self.t / 0.45) * math.pi)
        return palms_up(Pose(lift=16 * hop, brow=1.0, quirk=1.0, mouth="o", mouth_open=0.6, look_x=1.0,
                             look_y=-0.2, lean=-4, sy=1 + 0.05 * hop, sparkle=0.8))

    def _start_vending(self):
        d = self.data
        m = d["machine"]
        self.facing = 1 if m.x >= self.x else -1
        joy = random.random() < min(0.95, self.vend_odds + self.vend_pity * self.pity)
        self.pity = 0 if joy else self.pity + 1
        d["joy"] = joy
        d["hit"] = joy and random.random() < self.pack_odds   # the pack itself is a long shot
        self.dur = (12.4 + RUMMAGE if d["hit"] else 17.2) if joy else 7.6
        m.screen = "check"

    def _vending(self, dt):
        d = self.data
        m = d["machine"]
        t = self.t
        if t < 4.6:  # stares at the screen, tapping his foot, scratching his beard
            if t > 1.4 and self._once("wait"):
                self.think("math", 2.6, lines=random.sample(WAITING, 3), side=-1)
            tap = max(0.0, math.sin(t * 9))
            return scratch_beard(Pose(lean=4 + 4 * ease(t / 4.6), look_x=1.0, look_y=-0.5, head=-4,
                                      brow=0.3 + 0.3 * math.sin(t * 1.3), quirk=0.5 + 0.5 * math.sin(t * 0.7),
                                      hip_f=10 * tap, knee_f=4 + 16 * tap, mouth="o", mouth_open=0.1), t, 14)
        if self._once("reveal"):
            m.screen = "instock" if d["joy"] else "soldout"
            m.flash = d["joy"]
        return (self._vending_joy if d["joy"] else self._vending_sad)(t - 4.6, m)

    def _vending_sad(self, u, m):
        if u < 0.8:  # blank stare
            return Pose(look_x=1.0, look_y=-0.5, brow=0.7, smile=-0.2, mouth="smile")
        if self._once("sigh"):
            self.say("...sold out.", life=2.0)
            s = self.scale
            away = -self.facing
            target = max(100 * s, min(self.width - 100 * s, self.x + away * random.uniform(300, 450) * s))
            self.queue.insert(0, ("walk", {"target": target, "mood": "sad", "speed": 38 * s,
                                           "notice": None}))
            m.leave(delay=3.0)
        a = ease((u - 0.8) / 0.8)
        return Pose(lean=12 * a, head=12 * a, look_x=0.4, look_y=0.9 * a, smile=-0.7, brow=-0.3,
                    sh_f=lerp(10, 2, a), el_f=lerp(16, 4, a), sh_b=lerp(-12, -2, a), el_b=lerp(12, 4, a),
                    bob=3 * a, sy=1 - 0.03 * a, blush=0.0, tears=0.35 * a, hat=8 * a)

    def _vending_joy(self, u, m):
        s = self.scale
        d = self.data
        if u < 0.6:  # wait, WHAT
            if self._once("what"):
                self.fx.bang(*self._head_xy(-10, -100), "!!")
            return palms_up(Pose(brow=1.0, quirk=1.0, mouth="o", mouth_open=0.9, lean=-8, sy=1.05,
                                 look_x=1.0, look_y=-0.6, sparkle=1.0))
        if u < 1.8:  # jumps for joy
            if self._once("yes"):
                self.say("IN STOCK?!", life=1.4)
                self.fx.dust(self.x, self.floor, 6)
            k = (u - 0.6) / 1.2
            self._every("spark", 0.06, lambda: self.fx.sparkle(*self._xy(self._anchor("hand_f")), speed=100))
            return fists_up(Pose(lift=80 * math.sin(k * math.pi), hip_f=40, knee_f=80, hip_b=25, knee_b=75,
                                 eyes="happy", mouth="smile", mouth_open=0.7, smile=1.0, blush=0.9,
                                 sy=1 + 0.08 * math.sin(k * math.pi)), pump=math.sin(k * math.pi))
        if u < 2.5:  # the machine drops the bundle; grab it
            if self._once("dispense"):
                tray = m.tray()
                prize = Item("bundle", tray.x(), tray.y(), s, tag=False)
                prize.size = 0.85
                d["prize"] = prize
                self.props.append(prize)
                for _ in range(10):
                    self.fx.sparkle(tray.x(), tray.y(), speed=90)
            prize = d["prize"]
            prize.grab = ease((u - 2.0) / 0.4)
            return self._bend(math.sin(min(1.0, (u - 1.8) / 0.7) * math.pi), prize.grab)
        prize = d["prize"]
        if u < 3.6:  # rip it open...
            prize.angle = 10 * math.sin(u * 40) * (u > 2.9)
            if u > 3.3 and self._once("rip"):
                prize.gone = True
                for _ in range(24):
                    self.fx.sparkle(prize.x, prize.y, speed=160)
            return hug(Pose(brow=0.9, quirk=1.0, mouth="o", mouth_open=0.5, look_x=0.6, look_y=0.6,
                            head=6, sparkle=0.6, sx=1 + 0.03 * math.sin(u * 40)))
        if u < 3.6 + RUMMAGE:
            return self._vending_rummage(u - 3.6, d)
        u -= RUMMAGE
        if self._once("flip"):
            self._flip_last_card(d)
        if not d["hit"]:
            return self._vending_dud(u - 3.6, m)
        card = d["card"]
        if u < 6.6:  # THE ULTIMATE PULL: card up behind him, fists up, tears of joy
            k = ease((u - 3.6) / 0.6)
            top = self._anchor("C")
            card.rest = QPointF(lerp(card.x, top.x() - self.facing * 28 * s, k),
                                lerp(card.y, top.y() - 62 * s, k))
            card.size = lerp(0.6, 2.7, ease_back((u - 3.6) / 0.7))
            card.angle = -6 * self.facing + 3 * math.sin(u * 3)
            if self._once("pull"):
                self.say("THE ULTIMATE PULL!!", life=2.6)
                m.leave(delay=2.0)
                self.bee_mode = "dance"
                d["cheer"] = [self.hive.spawn(lambda i=i: self._anchor("C") + QPointF(
                    math.cos(self.clock * 3 + i * 2.1) * 95, math.sin(self.clock * 3 + i * 2.1) * 45 - 50) * s)
                    for i in range(2)]
            self._every("heart", 0.3, lambda: self.fx.heart(*self._head_xy(random.uniform(-50, 50), -60)))
            self._every("spark", 0.08, lambda: self.fx.sparkle(card.x + random.uniform(-40, 40) * s,
                                                               card.y + random.uniform(-50, 50) * s, speed=50))
            pump = math.sin(u * 9)
            return fists_up(Pose(eyes="open", mouth="smile", mouth_open=1.0, smile=0.85, brow=0.6,
                                 tears=1.0, sparkle=1.0, blush=0.9, look_y=-0.2, bob=2 * abs(pump),
                                 sy=1 + 0.02 * pump, head=3 * pump), pump=pump)
        if u < 7.0 and self._once("stash"):  # into the hat for safekeeping
            card.behind = False
            card.fly, card.fly_from, card.fly_size = 0.0, QPointF(card.x, card.y), card.size
            for bee in d.get("cheer", []):
                self.hive.dismiss(bee)
        b = (u - 6.6) * math.tau * 2.1
        self._every("note", 0.45, lambda: self.fx.note(*self._head_xy(random.uniform(-40, 40), -50)))
        pose = dance_pose(b)
        pose.tears = max(0.0, 1 - (u - 6.6) / 1.2)
        return pose

    def _toss(self, kind, x, y, vx, vy, spin, size=0.9):
        """A card (or the empty wrapper) thrown into the air; it lands, bounces, lies there and fades."""
        q = Item(kind, x, y, self.scale, tag=False)
        q.size, q.free, q.vx, q.vy, q.spin = size, True, vx, vy, spin
        q.expire = random.uniform(3.2, 4.2)
        self.props.append(q)

    def _vending_rummage(self, u, d):
        """Flips through the pack one card at a time, tossing each over his shoulder, down to the last one."""
        s = self.scale
        card = d.get("card")
        if card is None:   # the stack in his hand, face down
            card = d["card"] = Item("card_back", d["prize"].x, d["prize"].y, s, tag=False)
            card.size, card.grab = 0.9, 1.0
            self.props.append(card)
            self.say("okay, okay...", life=1.0)
        n = int((u - 0.2) / 0.3) if u > 0.2 else -1
        if 0 <= n < 9 and n > d.get("flicked", -1):   # nine flicked off, the tenth stays in his hand
            d["flicked"] = n
            self._toss(random.choice(["common_card", "energy_card"]), card.x, card.y,
                       -self.facing * random.uniform(120, 260) * s, -random.uniform(300, 480) * s,
                       random.uniform(-500, 500))
            line = {2: "nope.", 5: "meh.", 7: "come ON."}.get(n)
            if line:
                self.say(line, life=0.8)
        tense = ease((u - 2.6) / 0.8) if u > 2.6 else 0.0
        if tense > 0 and self._once("last"):
            self.say("...the last one.", life=1.6)
        flick = max(0.0, math.sin((u - 0.2) * math.tau / 0.3)) if 0.2 < u < 2.6 else 0.0
        self._every("spark", 0.1, lambda: self.fx.sparkle(card.x, card.y, speed=50) if tense > 0.3 else None)
        return hug(Pose(brow=0.5 + 0.5 * tense, quirk=1.0, mouth="o", mouth_open=0.15 + 0.4 * tense, look_x=0.5,
                        look_y=0.9, head=3 + 4 * flick, bob=1.5 * flick, sparkle=0.8 * tense,
                        sx=1 + 0.03 * tense * math.sin(u * 45)))

    def _flip_last_card(self, d):
        """The tenth card turns over: the holo (a hit), or a common or an energy (a dud)."""
        card = d["card"]
        if d["hit"]:
            card.kind, card.size, card.behind = "card", 0.6, True
            card.rest = QPointF(card.x, card.y)
            card.grab = 0.0
        else:
            card.kind = random.choice(["common_card", "energy_card"])
            card.size = 1.3

    def _vending_dud(self, k, m):
        """A common or an energy at the back: tears build, the pack and cards fly, then he shakes it off."""
        s = self.scale
        d = self.data
        card = d["card"]
        if k < 1.0:   # staring at it
            if self._once("dud"):
                self.say("...an energy." if card.kind == "energy_card" else "...a common.", life=1.8)
            return hug(Pose(brow=-0.1, mouth="o", mouth_open=0.2, look_y=0.9, smile=0.0, head=4, sy=0.99))
        if k < 2.6:   # the tears build
            a = ease((k - 1.0) / 1.6)
            wob = math.sin(k * 25)
            return hug(Pose(brow=-0.5 * a, smile=-0.8 * a, tears=a, look_y=0.9, head=8 * a + wob * 1.5 * a,
                            lean=6 * a, mouth="smile", mouth_open=0.2 * a, bob=2 * a, hat=6 * a, blush=0.0,
                            sx=1 + 0.012 * wob * a))
        if k < 3.0:   # THROWS IT ALL
            if self._once("toss"):
                h = self._anchor("hand_f")
                card.gone = True
                for _ in range(10):
                    self._toss(random.choice(["common_card", "energy_card", "card_back"]), h.x(), h.y(),
                               random.uniform(-280, 280) * s, -random.uniform(550, 900) * s,
                               random.choice((-1, 1)) * random.uniform(300, 900))
                self._toss("bundle", h.x(), h.y(), -self.facing * 60 * s, -1050 * s, 720, size=0.85)
                self.say("WHYYY", life=1.4)
                self.fx.dust(self.x, self.floor, 5)
                m.leave(delay=1.5)
            return fists_up(Pose(lift=14, eyes="closed", mouth="o", mouth_open=1.0, tears=1.0, brow=-0.6,
                                 lean=-6, sy=1.05), pump=1.0)
        if k < 4.4:   # watching them rain down
            a = ease((k - 3.0) / 0.5)
            return Pose(lean=8 * a, head=10 * a, look_y=0.9, tears=1.0 - 0.3 * a, smile=-0.8, brow=-0.4,
                        mouth="smile", mouth_open=0.2, bob=2 * a, hat=8 * a,
                        sh_f=lerp(150, 6, a), el_f=lerp(10, 8, a), sh_b=lerp(-150, -6, a), el_b=lerp(-10, -8, a))
        if self._once("anyway"):   # ...and back to his goofy self
            self.say("...anyway!", life=1.6)
            for _ in range(10):
                self.fx.sparkle(*self._head_xy(random.uniform(-40, 40), -40), speed=80)
        a = ease((k - 4.4) / 0.5)
        hop = math.sin(min(1.0, (k - 4.4) / 0.6) * math.pi)
        return palms_up(Pose(lift=16 * hop, eyes="happy", mouth="smile", mouth_open=0.6, smile=1.0, blush=0.8,
                             tears=max(0.0, 0.7 - 2 * a), brow=0.4, quirk=0.8, sy=1 + 0.05 * hop, sparkle=0.6 * a))

