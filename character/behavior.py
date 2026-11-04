"""The buddy: position, current action, blended pose, springs, bees and effects.

Each action is a method _<name>(dt) that returns the target Pose for this
frame (and may spawn effects). Switching actions blends from the old pose,
so nothing ever snaps. For now a simple random director picks the next
action; the attention/ module will take that job over later.
"""
import math
import random
from dataclasses import replace

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath

from character.bees import Hive
from character.effects import Effects
from character.props import Machine
from character.moves import DANCE_MOVES, dance_pose, fists_up, gait_pose, hug, palms_up, scratch_beard, shrug
from character.rig import INK, Pose, _pen, draw_buddy, ease, lerp, lerp_pose, skeleton, to_world
from character.adhd import ADHD_ACTIONS, AdhdMixin
from character.moments import MomentsMixin
from character.scenes import SCENES, SceneMixin

# name: (weight when picked at random, duration range in seconds)
ACTIONS = {
    "idle": (3.0, (2.8, 4.8)),
    "jump": (2.0, (1.25, 1.25)),
    "wave": (1.5, (2.4, 2.4)),
    "dance": (1.6, (7.6, 11.4)),   # a routine of 4 to 6 moves (see _start_dance)
    "spores": (2.0, (4.6, 4.6)),
    "meditate": (1.0, (7.0, 8.0)),
    "nap": (0.4, (8.0, 9.0)),
    "stretch": (0.4, (2.8, 2.8)),
    "quip": (1.4, (3.4, 3.4)),
}
DEMO_ORDER = ["walk", "kroger", "jump", "wave", "vending", "spores", "dance", "walk",
              "quip", "kroger", "meditate", "nap", "vending", "idle"]

VOICE_ACTIONS = {"listen", "think", "answer"}  # push-to-talk conversation (voice-in/)

# how the activity setting (0 chill .. 1 hyper) and quiet mode shape his day
CALM = {"idle", "meditate", "nap", "stretch"}
LIVELY = {"jump", "dance", "spores", "wave", "quip", "kroger", "vending"}

GREETINGS = ["hey hey!", "howdy!", "yo!"]
QUIPS = ["ahh... life is good.", "alrighty then!", "hmm hmm hmm ♪", "deep breaths. good vibes.",
         "who's got snacks?", "the bees get it.", "stay groovy.", "what a time to be alive."]


class Follower:
    """A point that chases a target like it's on a spring (for the floppy hat)."""

    def __init__(self, k=80.0, d=8.0):
        self.k, self.d = k, d
        self.x = self.y = None
        self.vx = self.vy = 0.0

    def step(self, tx, ty, dt):
        if self.x is None:
            self.x, self.y = tx, ty
        self.vx += (self.k * (tx - self.x) - self.d * self.vx) * dt
        self.vy += (self.k * (ty - self.y) - self.d * self.vy) * dt
        self.x += self.vx * dt
        self.y += self.vy * dt


IDLE_CYCLE = {"yawn": 4.0, "owl": 4.4, "neck": 3.7, "pebble": 3.4, "choose": 5.0, "box": 3.2}   # seconds an idle needs
DANCE_BPM = 126   # house tempo; the dance moves and the notes follow it
HUM_LINES = ["mm-hm-hmmm~", "doo doo da-doo~", "mm mm mmm-mm~", "hm hm-hm hmmm~", "dun dun dun-dun~"]


class Buddy(SceneMixin, AdhdMixin, MomentsMixin):
    def __init__(self, width, floor, scale=1.0, demo=False, bus=None, screen_id=0):
        self.width, self.floor, self.scale = width, floor, scale
        self.x = width * 0.3
        self.facing = 1
        self.clock = 0.0
        self.fx = Effects(scale)
        self.pose = Pose()
        self.base_pose = Pose()      # the pose before floating in the air is added
        self.from_pose = Pose()
        self.air = 0.0               # rig units off the floor while the bees carry him
        self.blend = 1.0
        self.tip = Follower()
        self.hat_bend, self.hat_squash = 0.0, 1.0
        self.blink_in, self.blink_t = 2.0, -1.0
        self.look, self.look_to, self.look_in = [0.3, 0.0], [0.3, 0.0], 0.0
        self.bubble = None
        self.thought = None
        self.props = []
        self.pity = 0  # vending letdowns in a row
        self.screen_id = screen_id
        self.icons = []              # desktop icons on this screen, from desktop-awareness/
        self.all_icons = []
        self.activity = 0.5          # 0 chill .. 1 hyper (settings)
        self.quiet = False           # no bubbles, no big scenes (settings)
        self.scenes_enabled = True   # off for small previews
        self.behaviors = {}          # name -> {"on": bool, "often": multiplier} (settings)
        self.vend_odds, self.vend_pity = 0.5, 0.15
        self.pack_odds = 0.25   # chance the pack's last card is a hit (settings: pack_hit_odds)
        self.icon_visits = True      # kroger scenes use real desktop icons
        self.new_file_reaction = True
        self.do_after_landing = None
        self.windows = []                 # windows on this screen, from desktop-awareness/
        self.all_windows = []
        self.screen_name = ""
        self.screen_origin = QPointF(0, 0)
        self.perched = False              # sitting on a title bar (perch scene)
        self.quips = list(QUIPS)          # his sayings (editable in settings)
        self.greetings = list(GREETINGS)
        self.pending_icon = None     # a new file to go check out
        self.hive = Hive(scale)
        self.hive.buddy = self
        self.bee_mode = "orbit"      # what the companion bee is up to: orbit | rest | dance
        self.companion = self.hive.spawn(self._bee_spot, from_edge=False)
        self.demo = demo
        self.demo_i = 0
        self.locked = None
        self.queue = []
        self._dt = 0.0
        self._font = QFont()
        self._font.setBold(True)
        self._font.setPixelSize(max(9, int(15 * scale)))
        if bus:
            bus.subscribe("voice.listening", self._on_listening)
            bus.subscribe("voice.thinking", self._on_heard)
            bus.subscribe("voice.say", self._on_reply)  # voice-out/speak.py passes voice.reply on, with audio ready
            bus.subscribe("voice.mouth", lambda level: setattr(self, "mouth_level", level))
            bus.subscribe("voice.cancel", lambda _: self.state in VOICE_ACTIONS and self.do_now("idle"))
            bus.subscribe("desktop.windows", self._on_windows)
            bus.subscribe("desktop.icons", self._on_icons)
            bus.subscribe("desktop.icon_added", self._on_icon_added)
        self.bus = bus
        self.humming = False      # a happy walk with a hum bubble (and sound, if hum_sound is on)
        self.last_facing, self.turn_t = self.facing, 1.0
        self.hums = True          # the "hum" setting
        self.dance_mode = False   # settings: dance nonstop, music or not
        self.music_on = False     # music is playing from a browser or player (attention.music)
        self.dance_at = 0.0
        self.mouth_level = None   # from the audio while he speaks out loud
        self.speech_seconds = 0.0
        self._adhd_init(bus)
        self.enter("walk" if demo else "idle")

    def set_area(self, width, floor):
        self.width, self.floor = width, floor
        self.x = max(60 * self.scale, min(width - 60 * self.scale, self.x))

    def _on_icons(self, icons):
        self.all_icons = icons
        self.icons = [i for i in icons if i.screen == self.screen_id]

    def set_screen_id(self, screen_id):
        self.screen_id = screen_id
        self._on_icons(self.all_icons)

    # push-to-talk (voice-in/) ------------------------------------------------
    def _on_listening(self, down):
        if down:
            self.do_now("listen")
        elif self.state == "listen":
            self.bubble = None
            self.enter("think")

    def _on_heard(self, text):
        if self.state not in ("listen", "think"):
            self.enter("think")
        short = text if len(text) <= 34 else text[:33].rsplit(" ", 1)[0].rstrip(",.;") + "…"
        quote = f"\"{short}\""
        self.think("math", 60, lines=[quote] * 5 + ["hmm...", "..."], side=-1, force=True)

    def _on_reply(self, reply):
        self.thought = None
        text = (reply or {}).get("text") or (reply or {}).get("error") or "..."
        self.speech_seconds = float((reply or {}).get("seconds") or 0)  # > 0: audio is playing
        self.do_now("answer", text)

    def set_screen(self, name, origin):
        """Which monitor he's on (for matching up KWin's windows)."""
        self.screen_name, self.screen_origin = name, QPointF(origin)
        self._on_windows(self.all_windows)

    def _on_windows(self, windows):
        self.all_windows = windows
        self.windows = [w for w in windows if w.showing and w.output == self.screen_name]

    def set_scale(self, scale):
        """Resize him live (the size setting)."""
        self.scale = scale
        self.fx.scale = scale
        self.hive.scale = scale
        for bee in self.hive.bees:
            bee.scale = scale
        self._font.setPixelSize(max(9, int(15 * scale)))
        self.x = max(60 * scale, min(self.width - 60 * scale, self.x))

    def _on_icon_added(self, icon):
        if icon.screen == self.screen_id and self.new_file_reaction and self.icon_visits:
            self.pending_icon = icon

    def set_companion(self, on):
        """The companion bee (settings): buzz off, or come back from the sky."""
        if on and self.companion is None:
            self.companion = self.hive.spawn(self._bee_spot)
        elif not on and self.companion is not None:
            self.hive.dismiss(self.companion)
            self.companion = None

    def interrupt(self):
        """Drop whatever he's doing, tidily: put props away, call off errands."""
        self.queue.clear()
        self.thought = None
        self.pending_icon = None
        for q in self.props:
            if isinstance(q, Machine):
                q.leave(0.3)
            elif q.grab > 0 or q.carrier is not None or q.fly is not None or q.alpha < 1:
                q.gone = True
                for _ in range(8):
                    self.fx.sparkle(q.x, q.y, speed=60)
            elif q.expire is None:
                q.expire = 3.0  # a find he never got to fades away
        for bee in self.hive.bees:
            if getattr(bee, "helper", False):
                self.hive.dismiss(bee)
        if self.companion:
            self.companion.target, self.companion.speed, self.companion.wiggle = self._bee_spot, 320, 1.0

    def do_now(self, name, text=None):
        """Do this right now (the settings window's "Do it now" and "Say it now")."""
        if name not in ACTIONS and name not in SCENES and name not in VOICE_ACTIONS | ADHD_ACTIONS | {"walk", "notice"}:
            return
        self.interrupt()
        if self.air > 1:  # land first
            self.do_after_landing = (name, text)
            self.enter("fly", to=0.0)
            return
        self.air = 0.0
        name, data = self._setup(name, text)
        self.enter(name, **data)

    def _setup(self, name, text=None):
        if name in SCENES:
            return self.setup_scene(name)
        return name, ({"text": text} if text else {})

    def _bee_spot(self):
        """Where the companion bee wants to be right now."""
        s = self.scale
        t = self.clock
        if self.pose is None:
            return QPointF(self.x, self.floor - 150 * s)
        if self.bee_mode == "rest":
            m = self._anchor("mushroom")
            return QPointF(m.x(), m.y() - 14 * s)
        head = self._anchor("C")
        if self.bee_mode == "dance":
            return head + QPointF(math.cos(t * 4.0) * 75, math.sin(t * 4.0) * 40 - 40) * s
        return head + QPointF(math.cos(t * 0.8) * 70, math.sin(t * 1.3) * 22 - 78) * s

    # director -------------------------------------------------------------
    def force(self, name):
        """Repeat one action or scene forever (used by --action and the preview)."""
        self.locked = name
        self.queue.clear()
        name, data = self.pick_next()
        self.enter(name, **data)

    def enter(self, name, **data):
        self.from_pose = self.base_pose
        self.blend = 0.0
        self.state = name
        self.perched = False
        self.t = 0.0
        self.done = False
        self.data = data
        lo, hi = ACTIONS.get(name, (0, (0, 0)))[1]
        self.dur = random.uniform(lo, hi)
        if name == "idle":  # chill means longer pauses, hyper means fidgety
            self.dur *= 1.5 - self.activity
        if name != "walk":
            self._hum(False)
        if name not in ("nap", "meditate"):
            self.bee_mode = "orbit"
            if self.companion:
                self.companion.wiggle = 1.0
        start = getattr(self, "_start_" + name, None)
        if start:
            start()

    def pick_next(self):
        if self.queue:
            return self.queue.pop(0)
        if self.do_after_landing:
            (name, text), self.do_after_landing = self.do_after_landing, None
            return self._setup(name, text)
        adhd = self.adhd_next()  # focus timer, a nudge he still owes you
        if adhd:
            return adhd
        if self.pending_icon and self.air < 1 and not self.quiet and self.scenes_enabled:
            icon, self.pending_icon = self.pending_icon, None
            if self.icon_visible(icon):  # can't see it behind a window? then he didn't notice
                return self.setup_scene("kroger", icon=icon, fresh=True)
        if self.locked:
            name = self.locked
        elif self.demo:
            self.demo_i = (self.demo_i + 1) % len(DEMO_ORDER)
            name = DEMO_ORDER[self.demo_i]
        elif self.state != "walk" and random.random() < 0.55 + 0.3 * self.activity:
            name = "walk"
        else:
            weights = {n: w for n, (w, _) in ACTIONS.items()}
            if self.scenes_enabled:
                weights.update(SCENES)
            for n in weights:
                if n in CALM:
                    weights[n] *= (1.6 - self.activity) * (1 - 0.3 * self.mood)
                elif n in LIVELY:
                    weights[n] *= (0.4 + 1.2 * self.activity) * (1 + 0.6 * self.mood)
                b = self.behaviors.get(n, {})
                weights[n] *= float(b.get("often", 1.0)) if b.get("on", True) else 0.0
            if self.quiet:
                weights = {n: w for n, w in weights.items() if n in CALM}
            weights = {n: w for n, w in weights.items() if w > 0}
            name = random.choices(list(weights), list(weights.values()))[0] if weights else "walk"
        if name in SCENES:
            return self.setup_scene(name)
        return name, {}

    # per frame ------------------------------------------------------------
    def update(self, dt):
        dt = min(dt, 0.05)
        self.clock += dt
        self.t += dt
        self._dt = dt
        target = getattr(self, "_" + self.state)(dt)
        if self.blend < 1.0:
            self.blend = min(1.0, self.blend + dt / 0.25)
            pose = lerp_pose(self.from_pose, target, ease(self.blend))
        else:
            pose = target
        self.base_pose = pose
        if self.air > 0.01:
            pose = self._float(replace(pose))

        pose = self.adhd_mood(pose)
        if self.facing != self.last_facing:   # turning around: a quick squash and bounce instead of a snap
            self.last_facing = self.facing
            self.turn_t = 0.0
        if self.turn_t < 0.22:
            self.turn_t += dt
            k = math.sin(min(1.0, self.turn_t / 0.22) * math.pi)
            if self.state != "dance":
                pose.sx *= 1 - 0.28 * k
                pose.sy *= 1 + 0.05 * k
                pose.head += 6 * k
        if pose.eyes == "open":
            self.blink_in -= dt
            if self.blink_in <= 0:
                self.blink_t = 0.0
                self.blink_in = random.uniform(1.8, 5.0)
                if random.random() < 0.15:
                    self.blink_in = 0.3  # double blink
            if self.blink_t >= 0:
                self.blink_t += dt
                pose.blink = max(pose.blink, math.sin(min(1.0, self.blink_t / 0.16) * math.pi))
                if self.blink_t > 0.16:
                    self.blink_t = -1.0
        if pose.tears > 0.5:
            self._every("tear", 0.18, self._drip)
        self.pose = pose

        head = self.world(skeleton(pose)["C"])
        self.tip.step(head.x(), head.y(), dt)
        bend = (head.x() - self.tip.x) * self.facing / self.scale
        self.hat_bend = max(-24.0, min(28.0, bend * 1.2 + 2 * math.sin(self.clock * 1.3)))
        self.hat_squash = max(0.82, min(1.18, 1 + (head.y() - self.tip.y) / self.scale * 0.01))

        self.fx.update(dt)
        self.hive.update(dt, self.clock, self.width, self.floor + 60 * self.scale)
        self.update_props(dt)
        if self.bubble:
            self.bubble["age"] += dt
            if self.bubble["age"] > self.bubble["life"]:
                self.bubble = None

        if self.done or (self.state != "walk" and self.t >= self.dur):
            name, data = self.pick_next()
            self.enter(name, **data)

    def _drip(self):
        for side, name in ((-1, "eye_b"), (1, "eye_f")):
            e = self._anchor(name)
            self.fx.tear(e.x() + self.facing * side * 8 * self.scale, e.y() + 14 * self.scale,
                         self.facing * side)

    def _float(self, pose):
        """Legs dangle and kick happily while the bees carry him."""
        if self.perched:  # sitting on a title bar: the pose already has his legs right
            pose.lift += self.air
            return pose
        k = min(1.0, self.air / 40)
        sway = math.sin(self.clock * 3.2)
        pose.hip_f = lerp(pose.hip_f, 18 + 14 * sway, k)
        pose.knee_f = lerp(pose.knee_f, 30 + 16 * max(0.0, sway), k)
        pose.hip_b = lerp(pose.hip_b, -8 - 14 * sway, k)
        pose.knee_b = lerp(pose.knee_b, 36 + 16 * max(0.0, -sway), k)
        pose.lift += self.air + 4 * math.sin(self.clock * 1.7) * k
        return pose

    def world(self, pt):
        return to_world(self.x, self.floor, self.facing, self.scale, self.pose, pt)

    def say(self, text, life=2.6, force=False):
        if self.quiet and not force:  # quiet mode, unless you asked him something
            return
        self.bubble = {"text": text, "age": 0.0, "life": life}

    def bounds(self):
        s = self.scale
        r = QRectF(self.x - 130 * s, self.floor - (self.pose.lift + 240) * s, 260 * s, 260 * s)
        if self.bubble:
            r = r.united(self._bubble_rect().adjusted(-6, -6, 6, 30 * s))
        return r.united(self.fx.bounds()).united(self.props_bounds()).united(self.hive.bounds())

    # drawing --------------------------------------------------------------
    def draw(self, p):
        self.draw_props_behind(p)
        draw_buddy(p, self.x, self.floor, self.facing, self.scale, self.pose,
                   self.hat_bend, self.hat_squash, self.clock)
        self.draw_props_front(p)
        self.hive.draw(p)
        self.fx.draw(p)
        self.draw_thought(p)
        self.draw_focus_timer(p)
        if self.bubble:
            self._draw_bubble(p)

    def _bubble_rect(self):
        s = self.scale
        top = self.world(skeleton(self.pose)["hat_top"])
        # long lines wrap onto more lines instead of running off the screen
        fm = QFontMetricsF(self._font)
        box = fm.boundingRect(QRectF(0, 0, 280 * s, 2000), 0x0084 | 0x1000, self.bubble["text"])
        tw = box.width() + 28 * s
        h = max(32 * s, box.height() + 18 * s)
        cx = max(tw / 2 + 4, min(self.width - tw / 2 - 4, top.x() + self.facing * 30 * s))
        y = top.y() - h - 14 * s
        if y < 4:  # up by the top edge: say it off to the side instead
            head = self._anchor("C")
            cx = head.x() - self.facing * (70 * s + tw / 2)
            cx = max(tw / 2 + 4, min(self.width - tw / 2 - 4, cx))
            y = max(4.0, head.y() - 90 * s)
        return QRectF(cx - tw / 2, y, tw, h)

    def _draw_bubble(self, p):
        s = self.scale
        b = self.bubble
        k = b["age"] / 0.25
        pop = 1 + 2.2 * (k - 1) ** 3 + 1.2 * (k - 1) ** 2 if k < 1 else 1.0
        fade = min(1.0, (b["life"] - b["age"]) / 0.3)
        r = self._bubble_rect()
        head = self.world(skeleton(self.pose)["hat_top"])
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(max(0.0, fade))
        c = r.center()
        p.translate(c)
        p.scale(pop, pop)
        p.translate(-c)
        path = QPainterPath()
        path.addRoundedRect(r, 14 * s, 14 * s)
        tail = QPainterPath(QPointF(r.center().x() - 8 * s, r.bottom() - 2))
        tail.lineTo(head.x() + self.facing * 6 * s, r.bottom() + 12 * s)
        tail.lineTo(r.center().x() + 8 * s, r.bottom() - 2)
        tail.closeSubpath()
        path = path.united(tail)
        p.setPen(_pen(INK, 2.6))
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawPath(path)
        p.setFont(self._font)
        p.setPen(INK)
        p.drawText(r, 0x0084 | 0x1000, b["text"])  # AlignCenter | TextWordWrap
        p.restore()

    # helpers for effects -----------------------------------------------------
    def _anchor(self, name):
        return self.world(skeleton(self.pose)[name])

    def _every(self, key, period, fn):
        left = self.data.get(key, 0.0) - self._dt
        if left <= 0:
            fn()
            left += period
        self.data[key] = left

    def _once(self, key):
        if key in self.data:
            return False
        self.data[key] = True
        return True

    def _head_xy(self, dx, dy):
        h = self._anchor("C")
        s = self.scale
        return h.x() + self.facing * dx * s, h.y() + dy * s

    @staticmethod
    def _xy(pt):
        return pt.x(), pt.y()

    def _eyes_on_bee(self, pose):
        """Point his eyes at the companion bee (easily distracted)."""
        if not self.companion:
            return pose
        head = self._anchor("C")
        dx = (self.companion.x - head.x()) * self.facing / (90 * self.scale)
        dy = (self.companion.y - head.y()) / (90 * self.scale)
        pose.look_x, pose.look_y = max(-1.0, min(1.0, dx)), max(-1.0, min(1.0, dy))
        pose.head += max(-6.0, min(6.0, dy * -6))
        return pose

    # actions ------------------------------------------------------------------
    def _start_walk(self):
        d = self.data
        s = self.scale
        if "target" not in d:
            margin = 120 * s
            for _ in range(10):
                tx = random.uniform(margin, self.width - margin)
                if abs(tx - self.x) > 220 * s:
                    break
            d["target"] = tx
            d["notice"] = (random.uniform(0.25, 0.75) if random.random() < 0.18 else None)
        d.setdefault("speed", random.uniform(75, 120) * s * (0.8 + 0.4 * self.activity))
        d.setdefault("mood", random.choice(["content", "cheery", "strut"]))
        d.setdefault("notice", None)
        self._hum(d["mood"] in ("content", "cheery") and not self.quiet and random.random() < 0.5)
        d.setdefault("start", self.x)
        d.setdefault("phase", 0.0)
        self.facing = 1 if d["target"] >= self.x else -1

    def _hum(self, on):
        on = on and self.hums
        if on != self.humming:
            self.humming = on
            if on:
                self.say(random.choice(HUM_LINES), life=2.6)   # text only; hum sound is off (see hum_sound)
            if self.bus:
                self.bus.publish("buddy.hum", on)

    def _walk(self, dt):
        d = self.data
        step = d["speed"] * dt
        dx = d["target"] - self.x
        if abs(dx) <= step:
            self.x = d["target"]
            self.done = True
        else:
            self.x += step * self.facing
        stride = 28 * self.scale
        d["phase"] += dt * d["speed"] / stride * math.pi / 2
        pose = gait_pose(d["phase"], d["mood"])
        if self.humming:
            pose.mouth_open = 0.1 + 0.08 * abs(math.sin(self.t * 7))   # a closed-ish "mm"
        if d["mood"] in ("content", "cheery"):
            self._every("note", random.uniform(0.45, 0.85),
                        lambda: self.fx.note(*self._head_xy(26, -40)))

        span = abs(d["target"] - d["start"]) or 1.0
        if d["notice"] and abs(self.x - d["start"]) / span > d["notice"]:
            d["notice"] = None
            resume = {k: v for k, v in d.items() if k != "note"}
            self.queue[:0] = [("notice", {}), ("walk", resume)]
            self.done = True
        return pose

    def _start_notice(self):
        self.dur = 1.8
        self.fx.bang(*self._head_xy(-10, -100))

    def _notice(self, dt):
        k = self.t / self.dur
        a = ease(k / 0.12)
        pose = palms_up(Pose(lean=-6 * a, look_x=-1.0 * a, look_y=-0.3, brow=1.0 * a, quirk=0.8,
                             mouth="o", mouth_open=0.45, head=-6 * a, sy=1 + 0.04 * a, sparkle=0.4))
        if k > 0.6:  # ...huh. anyway.
            pose = shrug(Pose(look_x=0.3, smile=0.4))
        return pose

    def _start_idle(self):
        grumpy = getattr(self, "mood", 0.2) < -0.2  # no happy humming when he's in a mood
        hyper = getattr(self, "activity", 0.5)
        kinds = {"breathe": 3, "belly": 0 if grumpy else 2, "scratch": 2, "hum": 0 if grumpy else 3,
                 "tap": 3 if grumpy else 1.5,
                 # newer ones: chill moods yawn and stare at the sky, hyper ones box and swivel
                 "yawn": 0.15, "sky": 1.5, "owl": 1.5, "neck": 1.0,   # content, not sleepy: a yawn is rare
                 "box": 0 if grumpy else 1.5 * (0.4 + hyper), "pebble": 1.5,
                 "choose": 0 if grumpy else 1.5}
        kind = random.choices(list(kinds), list(kinds.values()))[0]
        self.data["kind"] = kind
        self.dur = max(self.dur, IDLE_CYCLE.get(kind, 0))   # a gesture gets to finish

    def _idle(self, dt):
        t = self.t
        br = math.sin(t * 2.2)
        self.look_in -= dt
        if self.look_in <= 0:
            self.look_to = [random.uniform(-0.9, 1.0), random.uniform(-0.6, 0.4)]
            self.look_in = random.uniform(0.6, 1.8)
        for i in (0, 1):
            self.look[i] += (self.look_to[i] - self.look[i]) * min(1.0, dt * 10)
        pose = Pose(bob=br * 1.2, sy=1 + br * 0.012, sh_f=8 + br * 2, el_f=16, sh_b=-10 - br * 2,
                    el_b=12, look_x=self.look[0], look_y=self.look[1],
                    head=self.look[1] * -6 + self.look[0] * 2)
        kind = self.data.get("kind", "breathe")
        if kind == "breathe":
            self._eyes_on_bee(pose)  # watching the bee buzz around
        elif kind == "belly":
            pose.sh_f, pose.el_f, pose.hand_f = 30, -110, "open"  # hand on his belly
            pose.eyes, pose.smile, pose.blush = "happy", 0.9, 0.6
            pose.bob += 0.8 * br
        elif kind == "scratch":
            scratch_beard(pose, t, 7)
            pose.look_x, pose.look_y, pose.brow, pose.quirk, pose.smile = 0.6, -0.6, -0.2, 0.7, 0.2
            pose.head = -4
        elif kind == "hum":
            pose.mouth, pose.mouth_open = "o", 0.1 + 0.08 * abs(math.sin(t * 5))
            pose.head += 4 * math.sin(t * 4)
            pose.hat = 3 * math.sin(t * 4)
            if math.sin(t * 0.9) > 0:
                pose.eyes = "happy"
            self._every("note", 0.9, lambda: self.fx.note(*self._head_xy(24, -40)))
        elif kind == "tap":
            tap = max(0.0, math.sin(t * 9))
            hug(pose)
            pose.hand_f = pose.hand_b = "fist"
            pose.hip_f, pose.knee_f = 10 * tap, 4 + 16 * tap
            pose.look_x, pose.brow, pose.smile, pose.quirk = 1.0, 0.2, 0.3, 0.6
        else:
            getattr(self, "_idle_" + kind)(pose, t, br)
        return pose

    # more idles: each shapes the pose it is given (t = seconds into the idle, br = breathing) ----------
    def _idle_yawn(self, pose, t, br):
        u = (t % 4.0) / 4.0
        y = math.sin(min(1.0, u / 0.7) * math.pi) ** 0.8 if u < 0.7 else 0.0   # the yawn swells and fades
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 15 + 135 * y, 18, 1 + 0.35 * y, "open"
        pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -15 - 135 * y, -18, 1 + 0.35 * y, "open"
        pose.lean, pose.sy, pose.sx = -7 * y, 1 + 0.05 * y, 1 - 0.02 * y
        pose.head = -9 * y
        pose.mouth, pose.mouth_open = "o", 0.95 * y
        if y > 0.35:
            pose.eyes, pose.tears = "closed", 0.3 * y
        if y > 0.9 and self._once(f"yawn{int(t // 4)}"):
            self.fx.zz(*self._head_xy(24, -30))

    def _idle_sky(self, pose, t, br):
        rock = math.sin(t * 1.1)
        pose.sh_f, pose.el_f, pose.sh_b, pose.el_b = -32, 8, -36, 6   # hands behind his back
        pose.lean, pose.head, pose.look_x, pose.look_y = -3 + 3 * rock, -9, 0.3, -0.95
        pose.hip_f, pose.hip_b = 4 * rock, -4 * rock
        pose.eyes = "open"
        pose.smile, pose.sparkle, pose.blush = 0.7, 0.4, 0.5
        if math.sin(t * 0.7) > 0.5:
            pose.mouth, pose.mouth_open = "o", 0.2

    def _idle_owl(self, pose, t, br):
        """Slow, wide-eyed head swivels, like the owls he loves."""
        target = (1.0, 0.0, -1.0, 0.0)[int(t / 1.1) % 4]
        self.data["lx"] = self.data.get("lx", 0.0) + (target - self.data.get("lx", 0.0)) * min(1.0, self._dt * 7)
        lx = self.data["lx"]
        pose.look_x, pose.look_y, pose.head, pose.hat = lx, -0.1, 15 * lx, -7 * lx
        pose.brow, pose.sparkle, pose.mouth_open, pose.smile = 1.0, 0.5, 0.0, 0.35
        pose.lean = 2 * lx
        pose.blink = max(pose.blink, 0.0)
        if abs(lx) > 0.95 and int(t / 1.1) % 2 == 0:
            pose.quirk = 0.9   # one eyebrow up: "whoo?"

    def _idle_neck(self, pose, t, br):
        roll = math.sin(t * 1.7)
        pose.head, pose.hat, pose.lean = 20 * roll, -9 * roll, 2 * roll
        pose.sh_f, pose.sh_b = 10 + 24 * math.sin(t * 3.4), -12 + 24 * math.sin(t * 3.4 + math.pi)   # shoulder rolls
        pose.eyes, pose.mouth, pose.mouth_open, pose.smile = "closed", "o", 0.12, 0.4

    def _idle_box(self, pose, t, br):
        """Shadow boxing: quick alternating jabs, bouncing on his toes."""
        jab_f, jab_b = max(0.0, math.sin(t * 6.0)), max(0.0, math.sin(t * 6.0 + math.pi))
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 48 + 40 * jab_f, 115 - 110 * jab_f, 1 + 0.45 * jab_f, "fist"
        pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -48 - 40 * jab_b, -115 + 110 * jab_b, 1 + 0.45 * jab_b, "fist"
        bounce = abs(math.sin(t * 3.0))
        pose.bob, pose.knee_f, pose.knee_b = 3 * bounce, 12 + 14 * bounce, 12 + 14 * bounce
        pose.hip_f, pose.hip_b, pose.lean = 8, -8, 5 + 4 * (jab_f - jab_b)
        pose.brow, pose.smile, pose.mouth, pose.mouth_open = -0.3, 0.45, "o", 0.1 + 0.2 * max(jab_f, jab_b)
        pose.look_x = 0.9
        if max(jab_f, jab_b) > 0.97:
            self._every("tsh", 0.35, lambda: self.fx.dust(self.x, self.floor, 2))

    def _idle_pebble(self, pose, t, br):
        """Scuffs his shoe, kicks a pebble, and watches it go."""
        u = (t % 3.4) / 3.4
        kick = 0.0
        if u < 0.45:       # wind up, staring at the ground
            wind = ease(u / 0.45)
            pose.hip_f, pose.knee_f = -18 * wind, 4 + 40 * wind
            pose.look_x, pose.look_y, pose.head = 0.7, 0.8, 8 * wind
        elif u < 0.57:     # kick
            kick = (u - 0.45) / 0.12
            pose.hip_f, pose.knee_f = lerp(-18, 52, ease(kick)), lerp(44, 6, ease(kick))
            pose.look_x, pose.look_y = 0.7, 0.8
            if self._once(f"kick{int(t // 3.4)}"):
                self.fx.dust(self.x + 38 * self.scale * self.facing, self.floor, 5)
        else:              # follow it with his eyes
            fly = (u - 0.57) / 0.43
            pose.hip_f, pose.knee_f = lerp(52, 0, ease(fly * 2)), lerp(6, 4, ease(fly * 2))
            pose.look_x, pose.look_y, pose.head = 0.4 + 0.6 * fly, 0.7 - 1.0 * fly, 3 - 6 * fly
            pose.brow = 0.6 * (1 - fly)
        pose.sh_f, pose.el_f, pose.sh_b, pose.el_b = 20, 25, -20, 20
        pose.smile = 0.6

    def _idle_choose(self, pose, t, br):
        """The Pokemon throw: ball up, wind up, 'I choose you!', and point."""
        u = (t % 5.0) / 5.0
        cyc = int(t // 5.0)
        pose.look_x, pose.smile, pose.sparkle, pose.blush = 0.9, 0.95, 0.5, 0.6
        if u < 0.38:       # holding the ball up, looking at it
            pose.sh_f, pose.el_f, pose.hand_f = 90, 95, "fist"
            pose.look_y, pose.eyes, pose.lean = -0.2, "open", 3
            pose.sh_b, pose.el_b = -30, 40
            if u > 0.12:
                self._every("glint", 0.25, lambda: self.fx.sparkle(*self._xy(self._anchor("hand_f")), speed=40))
        elif u < 0.52:     # wind up and throw
            k = (u - 0.38) / 0.14
            pose.sh_f, pose.el_f = lerp(90, 175, ease(min(1, k * 1.8))) if k < 0.55 else lerp(175, 80, ease((k - 0.55) / 0.45)), \
                lerp(95, 20, ease(min(1, k * 1.8))) if k < 0.55 else lerp(20, 4, ease((k - 0.55) / 0.45))
            pose.hand_f, pose.lean, pose.reach_f = "fist" if k < 0.7 else "point", lerp(-8, 8, ease(k)), 1.0 + 0.5 * k
            pose.sh_b, pose.el_b = -40, 50
            pose.mouth, pose.mouth_open = "o", 0.6
            if k > 0.55 and self._once(f"throw{cyc}"):
                self.say("I choose you!", life=2.2)
                for _ in range(8):
                    self.fx.sparkle(*self._xy(self._anchor("hand_f")), speed=120)
        else:              # held, pointing, proud
            pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 82, 4, 1.5, "point"
            pose.lean, pose.head, pose.quirk, pose.mouth_open = 8, -3, 0.8, 0.3 if u < 0.65 else 0.0
            pose.sh_b, pose.el_b = -30, 60

    def _quip(self, dt):
        t = self.t
        pose = Pose(bob=math.sin(t * 2.2) * 1.2, look_x=0.6, look_y=-0.1, quirk=0.8)
        if self._once("said"):
            self.say(self.data.get("text") or random.choice(self.quips or QUIPS), life=self.dur - 0.3)
        talking = t < 1.6
        pose.mouth_open = 0.25 + 0.2 * abs(math.sin(t * 9)) if talking else 0.0
        pose.smile = 0.85
        pose.sh_f, pose.el_f, pose.hand_f = 55 + 8 * math.sin(t * 3), 50, "open"
        pose.head = 3 * math.sin(t * 2)
        return pose

    def _start_jump(self):
        if not self.locked and not self.demo and not self.queue and random.random() < 0.3:
            self.queue.append(("jump", {"double": True}))  # hop hop!

    def _jump(self, dt):
        k = self.t / self.dur
        if k < 0.22:  # crouch, arms swing back
            a = ease(k / 0.22)
            return Pose(bob=10 * a, hip_f=34 * a, knee_f=4 + 62 * a, hip_b=26 * a, knee_b=4 + 58 * a,
                        lean=10 * a, sy=1 - 0.15 * a, sx=1 + 0.1 * a, sh_f=-30 * a, el_f=10,
                        sh_b=-50 * a, el_b=10, brow=0.5 * a, quirk=0.5 * a, smile=0.8)
        if k < 0.82:  # airborne, fists up
            u = (k - 0.22) / 0.6
            if self._once("launch"):
                self.fx.dust(self.x, self.floor, 6)
            stretch = max(0.0, 1 - u / 0.35)
            tuck = math.sin(u * math.pi)
            pose = fists_up(Pose(lift=4 * 86 * u * (1 - u), sy=1 + 0.14 * stretch, sx=1 - 0.08 * stretch,
                                 hip_f=20 + 40 * tuck, knee_f=20 + 80 * tuck, hip_b=10 + 30 * tuck,
                                 knee_b=20 + 75 * tuck, eyes="happy", mouth="smile", mouth_open=0.7,
                                 smile=1.0, blush=0.7, head=-4, hat=-8 * tuck), pump=tuck)
            if 0.4 < u < 0.6:
                self._every("spark", 0.05, lambda: self.fx.sparkle(*self._xy(self._anchor("hand_f"))))
            return pose
        u = (k - 0.82) / 0.18
        if self._once("land"):
            self.fx.dust(self.x, self.floor, 8)
        a = 1 - ease(u)
        return Pose(sy=1 - 0.17 * a, sx=1 + 0.13 * a, bob=9 * a, hip_f=26 * a, knee_f=4 + 50 * a,
                    hip_b=22 * a, knee_b=4 + 46 * a, lean=6 * a, mouth="smile", mouth_open=0.4,
                    smile=1.0, eyes="happy", blush=0.5, sh_f=30 * a, sh_b=-40 * a, hat=6 * a)

    def _wave(self, dt):
        w = math.sin(self.t * 11)
        if self._once("hi") and (self.data.get("text") or random.random() < 0.6):
            self.say(self.data.get("text") or random.choice(self.greetings or GREETINGS), life=1.8)
        return Pose(sh_f=105, el_f=50 + 26 * w, reach_f=1.35, hand_f="open", lean=-3, smile=1.0,
                    mouth="smile", mouth_open=0.4, quirk=0.8, blush=0.6, look_x=0.7, look_y=-0.2,
                    head=4 * math.sin(self.t * 3), bob=1.5 * abs(w), sparkle=0.3)

    def _start_dance(self):
        """A routine: a few different moves, four beats each, picked at random (always opens with the pump)."""
        beats = 4
        self.data["seg"] = beats * 60.0 / DANCE_BPM
        n = max(2, round(self.dur / self.data["seg"]))
        if "routine" not in self.data:
            if self.dance_mode:   # nonstop: skip the pump opener so back-to-back routines vary
                self.data["routine"] = random.sample(list(DANCE_MOVES), min(n, len(DANCE_MOVES)))
            else:
                others = random.sample([m for m in DANCE_MOVES if m != "pump"], min(n - 1, len(DANCE_MOVES) - 1))
                self.data["routine"] = ["pump"] + others
        self.dur = self.data["seg"] * len(self.data["routine"])

    def _dance(self, dt):
        b = self.t * math.tau * DANCE_BPM / 60.0
        self.bee_mode = "dance"
        d = self.data
        routine, seg = d["routine"], d["seg"]
        i = min(len(routine) - 1, int(self.t / seg))
        move = routine[i]
        pose = DANCE_MOVES[move](b)
        into = self.t - i * seg
        if i > 0 and into < 0.3:   # crossfade from the move before, so nothing snaps
            pose = lerp_pose(DANCE_MOVES[routine[i - 1]](b), pose, ease(into / 0.3))
        if move == "twirl":
            if self.dance_spin(b):
                self.facing = -self.facing
        elif self.t > self.dur / 2 and self._once("flip"):
            self.facing = -self.facing
        self._every("heart", 0.9, lambda: self.fx.heart(*self._head_xy(random.uniform(-30, 30), -70)))
        self._every("note", 0.5, lambda: self.fx.note(*self._head_xy(random.uniform(-40, 40), -50)))
        if move in ("pump", "disco", "roof", "headbang"):
            self._every("spark", 0.15, lambda: self.fx.sparkle(*self._xy(self._anchor("hand_f")), speed=90))
        if move == "headbang" and abs(math.sin(b / 2)) > 0.97:
            self._every("dust", 0.5, lambda: self.fx.dust(self.x, self.floor, 3))
        return pose

    def dance_spin(self, b):
        """True twice per spin, when he's edge-on: the moment to swap which way he faces."""
        p = (b / math.tau / 4) % 1.0
        edge = int(p * 2 + 0.5)   # 0 before the first edge-on moment, then 1, then 2
        last = self.data.get("edge", 0)
        self.data["edge"] = edge
        return edge != last and edge in (1, 2)

    def _spores(self, dt):
        """Shakes his hat so the mushroom puffs glowing spores, stomps, and
        toadstools and flowers pop up around him."""
        k = self.t / self.dur
        t = self.t
        if k < 0.1:  # wind-up
            a = ease(k / 0.1)
            return Pose(bob=6 * a, knee_f=4 + 20 * a, knee_b=4 + 20 * a, sy=1 - 0.06 * a,
                        brow=0.8 * a, quirk=1.0 * a, smile=0.9, sh_f=30 * a, sh_b=-30 * a)
        if k < 0.55:  # shimmy shimmy
            wig = math.sin(t * 26)
            m = self._anchor("mushroom")
            self._every("spore", 0.03, lambda: self.fx.spore(m.x(), m.y()))
            return Pose(sx=1 + 0.05 * wig, sy=1 - 0.03 * wig, hat=12 * wig, head=7 * math.sin(t * 13),
                        lean=4 * math.sin(t * 13), sh_f=60 + 18 * wig, el_f=40, hand_f="open",
                        sh_b=-60 + 18 * wig, el_b=-40, hand_b="open", eyes="happy", mouth="o",
                        mouth_open=0.5, blush=0.7, hip_f=6 * wig, hip_b=-6 * wig)
        if k < 0.68:  # big stomp
            u = (k - 0.55) / 0.13
            lift = math.sin(min(1.0, u / 0.7) * math.pi / 2) if u < 0.7 else 1 - (u - 0.7) / 0.3
            if u > 0.85 and self._once("stomp"):
                self.fx.dust(self.x, self.floor, 10)
                s = self.scale
                for i in range(random.randint(3, 5)):
                    side = 1 if i % 2 == 0 else -1
                    sx = self.x + side * (45 + i * random.uniform(18, 30)) * s
                    if 10 < sx < self.width - 10:
                        self.fx.sprout(sx, self.floor, mushroom=random.random() < 0.55)
                m = self._anchor("mushroom")
                for _ in range(16):
                    self.fx.spore(m.x(), m.y())
            return Pose(hip_f=45 * lift, knee_f=4 + 70 * lift, bob=3 * lift, lean=-4 * lift,
                        sh_f=50, el_f=30, sh_b=-50, el_b=-30, brow=1.0, quirk=1.0, mouth="smile",
                        mouth_open=0.6, smile=1.0, sy=1 - 0.08 * (1 - lift) * (u > 0.7))
        a = ease((k - 0.68) / 0.12)  # admire the garden
        self._every("heart", 0.5, lambda: self.fx.heart(*self._head_xy(random.uniform(-20, 20), -70)))
        return hug(Pose(eyes="happy", smile=1.0, mouth="smile", mouth_open=0.3, blush=0.9,
                        look_y=0.8, head=8 * a, lean=4 * a, hand_f="fist", hand_b="fist"))

    def _meditate(self, dt):
        """Sits cross-legged, hands on his knees, breathing slowly; floats a little in the middle."""
        t = self.t
        self.bee_mode = "orbit"
        settle = ease(min(1.0, t / 1.0))                       # sinks into the sit
        rise = ease(min(1.0, max(0.0, (t - 1.8) / 1.2), max(0.0, (self.dur - 0.8 - t) / 1.0)))
        breath = (math.sin(t * 1.5) + 1) / 2                   # in and out, about every four seconds
        if t > 1.8 and self._once("om"):
            self.say("ommm...", life=2.4)
        m = self._anchor("mushroom")
        self._every("spore", 0.45 - 0.2 * rise, lambda: self.fx.spore(m.x(), m.y()))
        if rise > 0.5:
            self._every("glow", 0.7, lambda: self.fx.sparkle(*self._head_xy(random.uniform(-45, 45), -20), speed=25))
        pose = Pose(lift=(16 + 5 * math.sin(t * 1.3)) * rise, bob=26 * settle,
                    hip_f=lerp(0, 82, settle), knee_f=lerp(4, 172, settle),     # near shin folds flat under him
                    hip_b=lerp(0, 95, settle), knee_b=lerp(4, 176, settle),     # far shin tucks across it
                    lean=3 * breath, sy=1 + 0.03 * breath, sx=1 - 0.012 * breath,
                    sh_f=lerp(10, 58, settle), el_f=lerp(16, 22, settle), hand_f="open",    # hands rest on his knees
                    sh_b=lerp(-12, 32, settle), el_b=lerp(12, 28, settle), hand_b="open",
                    eyes="closed", mouth="smile", smile=0.55, blush=0.45,
                    head=2.5 * math.sin(t * 0.7) - 2, hat=2 * math.sin(t * 0.7 + 1))
        return pose

    def _nap(self, dt):
        t = self.t
        snore = (math.sin(t * 1.6) + 1) / 2
        waking = t > self.dur - 0.9
        self.bee_mode = "orbit" if waking else "rest"
        if self.companion:
            self.companion.wiggle = 1.0 if waking else 0.1
        pose = Pose(bob=28, hip_f=86, knee_f=22, hip_b=80, knee_b=28, lean=-14, head=-14,
                    sh_f=30, el_f=-110, hand_f="open", sh_b=-10, el_b=40,
                    eyes="closed", mouth="o", mouth_open=0.1 + 0.3 * snore,
                    sy=1 + 0.02 * snore, blush=0.45, hat=-6)
        if waking:
            pose = palms_up(pose)
            pose.eyes, pose.brow, pose.mouth_open, pose.head, pose.look_x = "open", 1.0, 0.5, -4, 0.9
            if self._once("wake"):
                self.fx.bang(*self._head_xy(10, -100), "?!")
                if not self.locked:
                    self.queue.insert(0, ("stretch", {}))
        else:
            self._every("z", 1.1, lambda: self.fx.zz(*self._head_xy(24, -30)))
        return pose

    def _start_listen(self):
        self.dur = 90  # until you let go of the key
        self.say("I'm listening…", life=90, force=True)

    def _listen(self, dt):
        t = self.t
        nod = math.sin(t * 2.4)
        pose = Pose(lean=7, head=9 + 2 * nod, look_x=0.2, look_y=-0.1, brow=0.6, quirk=0.6,
                    mouth="o", mouth_open=0.12, sparkle=0.3, bob=0.8 * nod)
        pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 100, 95, 1.15, "open"  # hand cupped by his face
        pose.sh_b, pose.el_b = -14, 16
        return pose

    def _start_think(self):
        self.dur = 120  # until Claude answers

    def _think(self, dt):
        """Hyperfocus while Claude works: squinting, pacing a little, scratching his beard."""
        t = self.t
        step = math.sin(t * 3.2)
        pose = Pose(look_x=0.4, look_y=-0.8, brow=-0.5, quirk=0.8, smile=0.0, head=-5 + 2 * step,
                    hip_f=10 * step, knee_f=6 + 10 * max(0.0, step), hip_b=-10 * step,
                    knee_b=6 + 10 * max(0.0, -step), bob=-1.5 * abs(step), lean=3)
        if not self.thought:
            self.think("math", 120, lines=["hmm...", "...", "hmm...", "..."], side=-1, force=True)
        return scratch_beard(pose, t, 15)

    def _start_answer(self):
        text = self.data.get("text") or "..."
        self.dur = min(24.0, 2.5 + len(text) / 14)
        if self.speech_seconds:
            self.dur = min(60.0, self.speech_seconds + 0.8)
        self.say(text, life=self.dur - 0.2, force=True)

    def _answer(self, dt):
        t = self.t
        talking = t < self.dur - 1.0
        if self.mouth_level is not None:  # lips follow the audio
            talking = False
        gesture = math.sin(t * 2.1)
        pose = Pose(smile=0.8, quirk=0.6 + 0.3 * math.sin(t * 0.9), brow=0.3, look_x=0.5,
                    mouth_open=(0.2 + 0.35 * abs(math.sin(t * 11))) if talking else 0.0,
                    head=4 * math.sin(t * 1.7), bob=1.2 * abs(math.sin(t * 2.2)))
        if self.mouth_level is not None:
            pose.mouth_open = 0.08 + 0.8 * self.mouth_level
        pose.sh_f, pose.el_f, pose.hand_f = 55 + 15 * gesture, 50 + 15 * gesture, "open"
        pose.sh_b, pose.el_b, pose.hand_b = -40 - 12 * gesture, -45, "open"
        return pose

    def _stretch(self, dt):
        k = self.t / self.dur
        if k < 0.7:
            a = ease(k / 0.25)
            return Pose(sh_f=lerp(10, 115, a), el_f=lerp(16, 45, a), reach_f=lerp(1, 1.5, a),
                        sh_b=lerp(-12, -115, a), el_b=lerp(12, -45, a), reach_b=lerp(1, 1.5, a),
                        hand_f="open", hand_b="open", lean=-8 * a, sy=1 + 0.07 * a, sx=1 - 0.04 * a,
                        eyes="closed", mouth="o", mouth_open=0.95 * a, brow=-0.3 * a, head=-6 * a,
                        tears=0.25 * a)
        a = ease((k - 0.7) / 0.3)
        shake = math.sin(self.t * 30) * (1 - a)
        return Pose(sh_f=lerp(115, 10, a), el_f=lerp(45, 16, a), reach_f=lerp(1.5, 1, a),
                    sh_b=lerp(-115, -12, a) + 10 * shake, el_b=lerp(-45, 12, a), reach_b=lerp(1.5, 1, a),
                    lean=lerp(-8, 0, a), smile=0.9, eyes="open", brow=0.3, head=4 * shake,
                    hat=6 * shake, blush=0.4)
