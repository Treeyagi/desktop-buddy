"""How he acts out the ADHD engine (attention/engine.py): chasing the cursor,
getting distracted, wandering off on tangents, nudging you, being smug, sulking
when ignored, sitting with you through a focus timer, and moods.

He only takes the bait when he's free (walking, idling, chatting); in the
middle of a scene or a conversation he stays on task. Buddy mixes this in.
"""
import math
import random
import time

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter

from character.moves import gait_pose, hug, palms_up, scratch_beard, shrug
from character.rig import INK, Pose, _pen, ease
from character.props import font

ADHD_ACTIONS = {"chase", "pounce", "gaze", "tangent", "nudge", "smug", "sulk", "focus_sit"}
INTERRUPTIBLE = {"idle", "walk", "quip", "wave", "stretch", "notice"}

OPENERS = ["so I was thinking we should—", "okay, the plan for today is—", "you know what we need?",
           "alright, listen. step one is—"]
TANGENTS = ["do bees ever get bored of flowers?", "what if pockets had pockets?",
            "clouds are just sky sheep. think about it.", "how does a mushroom know it's a mushroom?",
            "remind me to buy socks.", "imagine a hoodie with a built-in nap.",
            "who decided pizza is a circle that lives in a square?", "I wonder what my shoes think of me."]


class AdhdMixin:
    def _adhd_init(self, bus):
        self.mood = 0.2
        self.focus_until = None
        self.focus_total = 1.0
        self.cursor_local = None
        self.cursor_seen = 0.0
        self.pending_nudge = None
        self.tangents = list(TANGENTS)
        if not bus:
            return
        bus.subscribe("desktop.cursor", self._on_cursor)
        bus.subscribe("attention.squirrel", self._on_squirrel)
        bus.subscribe("attention.gaze", self._on_gaze)
        bus.subscribe("attention.tangent", lambda _: self._free() and self.enter("tangent"))
        bus.subscribe("attention.nudge", self._on_nudge)
        bus.subscribe("attention.smug", lambda _: self._free() and self.enter("smug"))
        bus.subscribe("attention.sulk", lambda _: self._free() and self.enter("sulk"))
        bus.subscribe("attention.mood", lambda m: setattr(self, "mood", float(m)))
        bus.subscribe("attention.focus", self._on_focus)
        bus.subscribe("attention.focus_done", self._on_focus_done)

    # plumbing ---------------------------------------------------------------------------
    def _free(self):
        return (self.state in INTERRUPTIBLE and self.air < 1 and not self.queue
                and self.focus_until is None and self.scenes_enabled)

    def _here(self, pt):
        """A global point in his overlay's coordinates, or None if it's on another monitor."""
        if pt is None:
            return None
        local = QPointF(pt.x() - self.screen_origin.x(), pt.y() - self.screen_origin.y())
        if 0 <= local.x() <= self.width and 0 <= local.y() <= self.floor + 60 * self.scale:
            return local
        return None

    def _on_cursor(self, pt):
        local = self._here(pt)
        if local is None or self.cursor_local is None or (local - self.cursor_local).manhattanLength() > 2:
            self.cursor_seen = self.clock  # when it last actually moved
        self.cursor_local = local

    def _on_squirrel(self, pt):
        if self._free() and self._here(pt) is not None:
            self.enter("chase")

    def _on_gaze(self, d):
        if self._free():
            self.enter("gaze", at=self._here(d.get("at")), why=d.get("why", "window"))

    def _on_nudge(self, text):
        if self._free():
            self.enter("nudge", text=text)
        else:
            self.pending_nudge = text  # say it when he's done with what he's doing

    def _on_focus(self, d):
        if d:
            self.focus_until, self.focus_total = d["until"], max(1.0, d["minutes"] * 60.0)
            self.interrupt()
            s = self.scale
            spot = 150 * s if self.x < self.width / 2 else self.width - 150 * s
            walk = ("walk", {"target": spot, "mood": "content", "notice": None})
            if self.air > 1:
                self.queue[:0] = [walk, ("focus_sit", {})]
                self.enter("fly", to=0.0)
            else:
                self.queue[:0] = [("focus_sit", {})]
                self.enter(*walk[:1], **walk[1])
        else:
            self.focus_until = None
            if self.state == "focus_sit":
                self.enter("stretch")

    def _on_focus_done(self, _):
        self.focus_until = None
        self.interrupt()
        self.queue[:0] = [("stretch", {})]
        self.enter("dance")
        self.say("break time! nice work.", life=3.0, force=True)

    def adhd_next(self):
        """Called by pick_next before anything random."""
        if self.focus_until is not None:
            return "focus_sit", {}
        if self.pending_nudge:
            text, self.pending_nudge = self.pending_nudge, None
            return "nudge", {"text": text}
        return None

    def adhd_mood(self, pose):
        """Mood shows on his face: frowny when grumpy, extra cheery when delighted."""
        m = self.mood
        if pose.eyes == "open" and self.state not in ("answer", "listen"):
            if m < -0.2:
                pose.brow = min(pose.brow, m * 0.8)
                pose.smile = min(pose.smile, 0.6 + m)
            elif m > 0.6:
                pose.blush = max(pose.blush, 0.5)
                pose.smile = max(pose.smile, 0.8)
        return pose

    def draw_focus_timer(self, p):
        if self.focus_until is None or self.state != "focus_sit":
            return
        left = max(0.0, self.focus_until - time.monotonic())
        s = self.scale
        top = self._anchor("hat_top")
        r = QRectF(top.x() - 34 * s, top.y() - 30 * s, 68 * s, 22 * s)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(_pen(INK, 2 * s))
        p.setBrush(QColor(255, 255, 255, 235))
        p.drawRoundedRect(r, 11 * s, 11 * s)
        done = 1 - left / self.focus_total
        p.setPen(_pen(QColor(120, 200, 120), 3 * s))
        p.drawLine(QPointF(r.left() + 10 * s, r.bottom() - 4 * s),
                   QPointF(r.left() + 10 * s + (r.width() - 20 * s) * done, r.bottom() - 4 * s))
        p.setFont(font(13 * s))
        p.setPen(INK)
        p.drawText(r.adjusted(0, -2 * s, 0, -2 * s), 0x0084, f"{int(left // 60):d}:{int(left % 60):02d}")
        p.restore()

    # the moves ---------------------------------------------------------------------------
    def _start_chase(self):
        self.dur = random.uniform(4.5, 7.0)
        self.fx.bang(*self._head_xy(-10, -100), "!")

    def _chase(self, dt):
        """Squirrel! Runs after the mouse cursor and pounces when it stops near him."""
        d = self.data
        s = self.scale
        c = self.cursor_local if self.clock - self.cursor_seen < 4 or self.t < 4 else None
        if c is None:
            self.done = True
            return shrug(Pose(look_x=0.8))
        dx = c.x() - self.x
        step = 270 * s * dt
        if abs(dx) > 18 * s:
            self.facing = 1 if dx > 0 else -1
            self.x += max(-step, min(step, dx))
        d["phase"] = d.get("phase", 0.0) + dt * 14
        pose = gait_pose(d["phase"], "cheery") if abs(dx) > 18 * s else Pose()
        head_y = self._anchor("C").y()
        pose.lean = 10 if abs(dx) > 18 * s else 4
        pose.look_x = 1.0
        pose.look_y = max(-1.0, min(1.0, (c.y() - head_y) / (120 * s)))
        pose.mouth, pose.mouth_open, pose.smile, pose.sparkle = "smile", 0.55, 1.0, 0.7
        still = self.clock - self.cursor_seen > 0.6
        if abs(dx) < 30 * s and still and c.y() > self.floor - 320 * s and self.t > 0.8:
            self.queue.insert(0, ("pounce", {}))
            self.done = True
        return pose

    def _start_pounce(self):
        self.dur = 1.25
        self.say(random.choice(["gotcha!", "got it!", "mine!"]), life=1.6)

    def _pounce(self, dt):
        return self._jump(dt)

    def _start_gaze(self):
        self.dur = 3.6
        at = self.data.get("at")
        if at is not None and abs(at.x() - self.x) > 20 * self.scale:
            self.facing = 1 if at.x() > self.x else -1
        if self.data.get("why") == "sound":
            self.say(random.choice(["ooh, tunes?", "what's that?", "ooh, a jam."]), life=1.6)
        else:
            self.fx.bang(*self._head_xy(-10, -100), "?")

    def _gaze(self, dt):
        """Something caught his eye: stare, drift a few steps toward it, then 'anyway'."""
        t = self.t
        s = self.scale
        at = self.data.get("at")
        sound = self.data.get("why") == "sound"
        look_y = -0.3
        if at is not None:
            look_y = max(-1.0, min(1.0, (at.y() - self._anchor("C").y()) / (200 * s)))
        if t < 1.3:
            pose = Pose(look_x=1.0, look_y=look_y, brow=0.9, quirk=0.8, mouth="o", mouth_open=0.35,
                        head=-6 * ease(t / 0.3), lean=-3, sparkle=0.5)
            if sound:
                pose.head = 6 * math.sin(t * 9)
                pose.eyes, pose.mouth_open = "happy", 0.2
            return pose
        if t < 2.6:
            if at is not None:
                self.x += self.facing * 40 * s * dt
                self.data["phase"] = self.data.get("phase", 0.0) + dt * 5
                pose = gait_pose(self.data["phase"], "content")
                pose.look_x, pose.look_y = 1.0, look_y
                return pose
            pose = Pose(eyes="happy", mouth="o", mouth_open=0.2, head=7 * math.sin(t * 9),
                        bob=2 * abs(math.sin(t * 9)))
            self._every("note", 0.5, lambda: self.fx.note(*self._head_xy(24, -40)))
            return pose
        if self._once("anyway"):
            self.say(random.choice(["...anyway.", "where was I?", "huh. okay."]), life=1.2)
        return shrug(Pose(look_x=0.4))

    def _start_tangent(self):
        self.dur = 7.6
        self.say(random.choice(OPENERS), life=1.6)

    def _tangent(self, dt):
        """Starts a thought, gets yanked away by another one, comes back."""
        t = self.t
        if t < 1.6:
            pose = Pose(look_x=0.6, mouth_open=0.25 + 0.2 * abs(math.sin(t * 10)), smile=0.7)
            pose.sh_f, pose.el_f, pose.hand_f = 55, 50, "open"
            return pose
        if t < 3.1:
            if self._once("wait"):
                self.facing = -self.facing
                self.say("wait, unrelated, but...", life=1.5)
            return palms_up(Pose(look_x=1.0, look_y=-0.4, brow=1.0, quirk=1.0, mouth="o",
                                 mouth_open=0.4, sparkle=0.6))
        if t < 6.1:
            if self._once("tangent"):
                line = self.data.get("text") or random.choice(self.tangents or TANGENTS)
                self.say(line, life=2.9)
            pose = Pose(look_x=0.5, look_y=-0.3, quirk=0.8, smile=0.8,
                        mouth_open=0.2 + 0.2 * abs(math.sin(t * 10)) if t < 5.0 else 0.0)
            pose.sh_f, pose.el_f, pose.hand_f = 60 + 10 * math.sin(t * 3), 50, "open"
            return pose
        if self._once("back"):
            self.facing = -self.facing
            self.say("anyway.", life=1.3)
        return scratch_beard(Pose(look_x=0.3, smile=0.4), t, 12)

    def _start_nudge(self):
        self.dur = 4.8
        self.say(self.data.get("text") or "take a break, champ.", life=4.6)

    def _nudge(self, dt):
        t = self.t
        pose = Pose(look_x=0.4, look_y=-0.1, quirk=0.7, smile=0.8, brow=0.3,
                    mouth_open=0.2 + 0.2 * abs(math.sin(t * 9)) if t < 3.2 else 0.0,
                    head=3 * math.sin(t * 2))
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 85, 25, 1.25, "point"
        return pose

    def _start_smug(self):
        self.dur = 2.8
        self.say(random.choice(["told ya.", "see? genius.", "you're welcome."]), life=2.2)

    def _smug(self, dt):
        pose = hug(Pose(quirk=1.0, smile=0.75, look_x=0.6, head=-7, lean=-4, blush=0.4))
        pose.hand_f = pose.hand_b = "fist"
        return pose

    def _start_sulk(self):
        self.dur = 7.0

    def _sulk(self, dt):
        """Ignored for a long time: sits on the floor, arms crossed, sighs."""
        t = self.t
        if 0.8 < t and self._once("sigh"):
            self.say(random.choice(["nobody talks to me anymore...", "hmph.", "fine. I'll just sit here."]),
                     life=2.6)
        sit = ease(t / 0.6) * (1 - ease((t - (self.dur - 0.7)) / 0.6))
        pose = hug(Pose(bob=26 * sit, hip_f=80 * sit, knee_f=4 + 20 * sit, hip_b=74 * sit,
                        knee_b=4 + 26 * sit, lean=8, head=10, look_y=0.6, look_x=-0.3,
                        brow=-0.7, smile=-0.6, blush=0.0))
        pose.hand_f = pose.hand_b = "fist"
        pose.sy = 1 - 0.015 * math.sin(t * 1.4)
        return pose

    def _start_focus_sit(self):
        self.dur = 3600  # until the timer runs out

    def _focus_sit(self, dt):
        """Sits quietly beside you through a focus timer."""
        t = self.t
        breathe = math.sin(t * 1.2)
        pose = Pose(bob=24, hip_f=102, knee_f=152, hip_b=96, knee_b=146, sh_f=30, el_f=20,
                    hand_f="open", sh_b=-20, el_b=40, hand_b="open", look_x=0.6, look_y=-0.2,
                    smile=0.5, sy=1 + 0.012 * breathe, head=2 * breathe, brow=0.1)
        return pose
