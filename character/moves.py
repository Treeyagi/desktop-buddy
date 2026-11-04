"""Reusable body moves shared by the basic actions and the scenes."""
import math

from character.rig import Pose, lerp_pose


def gait_pose(ph, mood="cheery"):
    """One frame of the walk cycle; ph advances by pi per step."""
    s, c = math.sin(ph), math.cos(ph)
    beat = math.sin(2 * ph)
    pose = Pose(
        bob=1.0 - 3.5 * abs(c), lean=4, hip_f=24 * s, hip_b=-24 * s,
        knee_f=4 + 34 * max(0.0, c), knee_b=4 + 34 * max(0.0, -c),
        sh_f=6 - 26 * s, el_f=22 + 10 * max(0.0, -s), sh_b=-6 + 26 * s, el_b=22 + 10 * max(0.0, s),
        head=3 * beat, look_x=0.5, sy=1 + 0.02 * abs(c), hat=2 * beat,
    )
    if mood == "content":
        pose.eyes, pose.mouth, pose.mouth_open = "happy", "o", 0.06 + 0.08 * abs(beat)
        pose.blush = 0.55
    elif mood == "cheery":
        pose.mouth, pose.mouth_open, pose.brow = "o", 0.18 + 0.32 * abs(beat), 0.35
    elif mood == "strut":
        pose.lean, pose.quirk, pose.smile = -1, 1.0, 0.9
        pose.sh_f, pose.sh_b = 4 - 38 * s, -4 + 38 * s
        pose.head = 2 * beat - 4
    elif mood == "sad":
        pose.lean, pose.head, pose.look_x, pose.look_y = 10, 10 + 1.5 * beat, 0.2, 0.9
        pose.smile, pose.brow, pose.blush = -0.6, -0.3, 0.0
        pose.sh_f, pose.el_f, pose.sh_b, pose.el_b = 4 - 6 * s, 6, -4 + 6 * s, 6
        pose.bob += 2
        pose.hat = 6
    return pose


def dance_pose(b):
    """Victory dance with alternating fist pumps; b advances by 2*pi per beat."""
    half = math.sin(b / 2)
    hop = abs(math.sin(b))
    pump = math.sin(b)
    return Pose(bob=5 * hop - 2, lean=8 * half, hip_f=10 + 22 * half, knee_f=8 + 34 * max(0.0, half),
                hip_b=-22 * half, knee_b=8 + 34 * max(0.0, -half),
                sh_f=115 + 30 * pump, el_f=30 - 20 * pump, reach_f=1.4,
                sh_b=-115 + 30 * pump, el_b=-30 - 20 * pump, reach_b=1.4,
                eyes="happy", mouth="smile", mouth_open=0.45 + 0.25 * hop, smile=1.0,
                head=8 * half, hat=-6 * half, blush=0.8,
                sy=1 + 0.05 * pump, sx=1 - 0.03 * pump)


# --- dance moves --------------------------------------------------------------------------
# Each takes b (advances by 2*pi per beat) and returns a Pose. The dance action chains a few of
# them (behavior.py `_dance`), four beats each, and crossfades from one to the next.

def _party_face(pose, hop=0.0):
    pose.eyes, pose.mouth, pose.smile, pose.blush = "happy", "smile", 1.0, 0.8
    pose.mouth_open = 0.4 + 0.25 * hop
    return pose


def _snap(x, step):
    """Round to a step: the stiff, ticking motion of the robot."""
    return round(x / step) * step


def dance_disco(b):
    """Point to the sky and across to the floor, hips swinging, like a 70s dance floor."""
    sway = math.sin(b / 2)
    hit = max(0.0, math.sin(b)) ** 2
    base = dict(bob=3 * abs(math.sin(b / 2)) - 1, lean=6 * sway, hip_f=14 * sway, hip_b=-14 * sway,
                knee_f=10 + 14 * max(0.0, sway), knee_b=10 + 14 * max(0.0, -sway), head=7 * sway, hat=-5 * sway,
                look_x=0.8)
    near = Pose(look_y=-0.3, **base)   # near arm points at the sky, far hand on the hip
    near.sh_f, near.el_f, near.reach_f, near.hand_f = 150 + 6 * hit, 4, 1.5, "point"
    near.sh_b, near.el_b, near.hand_b = -38, -85, "fist"
    far = Pose(look_y=0.3, **base)     # then they swap
    far.sh_b, far.el_b, far.reach_b, far.hand_b = -150 - 6 * hit, -4, 1.5, "point"
    far.sh_f, far.el_f, far.hand_f = 38, 85, "fist"
    k = max(0.0, min(1.0, 0.5 - 1.6 * math.sin(b / 4)))   # eases across instead of flipping
    return _party_face(lerp_pose(near, far, k), hit)


def dance_sprinkler(b):
    """Arm out and ticking round in little jerks, other hand behind his head."""
    step = int((b / math.tau) * 2) % 8   # a tick every half beat
    pose = Pose(bob=1.5 * abs(math.sin(b)) + 1, lean=-3, hip_f=5, hip_b=-5, knee_f=10, knee_b=10,
                head=_snap(8 * math.sin(b / 4), 4))
    pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 45 + 14 * step if step < 5 else 45 + 14 * (8 - step), 3, 1.6, "point"
    pose.sh_b, pose.el_b, pose.hand_b = -150, -125, "fist"
    pose.back_front = 0.0
    return _party_face(pose, abs(math.sin(b)))


def dance_roof(b):
    """Raise the roof: both palms pushing up to the beat, knees pulsing."""
    push = math.sin(b)
    pose = Pose(bob=4 * max(0.0, -push) + 1, lean=-4, knee_f=14 + 12 * max(0.0, -push), knee_b=14 + 12 * max(0.0, -push),
                hip_f=6, hip_b=-6, sy=1 - 0.04 * max(0.0, -push), head=6 * math.sin(b / 2))
    pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 100 + 28 * push, 70 - 25 * push, 1.3, "open"
    pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -100 + 28 * push, -70 + 25 * push, 1.3, "open"
    return _party_face(pose, abs(push))


def dance_robot(b):
    """Stiff and ticking: every joint snaps in big steps."""
    t = b / math.tau
    pose = Pose(bob=_snap(3 * math.sin(b), 3), lean=_snap(6 * math.sin(b / 2), 3), head=_snap(14 * math.sin(b / 2), 7),
                hat=_snap(-6 * math.sin(b / 2), 3), hip_f=_snap(16 * math.sin(b / 2), 8), hip_b=_snap(-16 * math.sin(b / 2), 8),
                knee_f=_snap(10 + 12 * max(0.0, math.sin(b / 2)), 6), knee_b=_snap(10 + 12 * max(0.0, -math.sin(b / 2)), 6))
    pose.sh_f, pose.el_f = _snap(70 + 50 * math.sin(b / 2), 25), _snap(80 - 70 * math.sin(b / 2), 40)
    pose.sh_b, pose.el_b = _snap(-70 + 50 * math.sin(b / 2 + math.pi), 25), _snap(-80 + 70 * math.sin(b / 2), 40)
    pose.hand_f = pose.hand_b = "open"
    pose.eyes, pose.mouth, pose.smile, pose.mouth_open = "open", "o", 0.5, 0.15
    pose.look_x = 0.9 if int(t * 2) % 2 == 0 else -0.5
    pose.blush = 0.5
    return pose


def dance_shuffle(b):
    """The running man: quick alternating feet, arms pumping, leaning back."""
    sw = math.sin(b)
    pose = Pose(bob=2 + 2.5 * abs(math.cos(b)), lean=-7, hip_f=26 * sw, hip_b=-26 * sw,
                knee_f=6 + 40 * max(0.0, math.cos(b)), knee_b=6 + 40 * max(0.0, -math.cos(b)), head=4 * sw, hat=3 * sw)
    pose.sh_f, pose.el_f, pose.reach_f = 55 - 50 * sw, 90, 1.1
    pose.sh_b, pose.el_b, pose.reach_b = -55 - 50 * sw, -90, 1.1
    pose.hand_f = pose.hand_b = "fist"
    return _party_face(pose, abs(sw))


def dance_headbang(b):
    """EDM energy: deep bounce on every beat, head nodding, fists up on the drop."""
    beat = abs(math.sin(b / 2))
    drop = max(0.0, math.sin(b / 8))   # builds over a bar, then falls
    pose = Pose(bob=7 * beat - 2, lean=10 * math.sin(b), head=16 * math.sin(b), hat=-12 * math.sin(b),
                knee_f=12 + 36 * beat, knee_b=12 + 36 * beat, hip_f=10, hip_b=-10, sy=1 - 0.05 * beat, sx=1 + 0.03 * beat)
    pose.sh_f, pose.el_f, pose.reach_f = 80 + 55 * drop, 70 - 40 * drop, 1.3 + 0.2 * drop
    pose.sh_b, pose.el_b, pose.reach_b = -80 - 55 * drop, -70 + 40 * drop, 1.3 + 0.2 * drop
    pose.hand_f = pose.hand_b = "fist"
    pose.eyes = "happy"
    pose.smile, pose.mouth_open, pose.blush = 0.9, 0.5, 0.9
    return pose


def dance_hips(b):
    """Easy hip circles and wavy arms, a little hippie."""
    c, s = math.cos(b / 2), math.sin(b / 2)
    pose = Pose(bob=2 + 2 * s, lean=12 * c, hip_f=18 * s, hip_b=-18 * s, knee_f=14, knee_b=14, head=-10 * c,
                hat=8 * c, sx=1 + 0.04 * s, sy=1 - 0.03 * s)
    pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 100 + 30 * math.sin(b / 2 + 1), 20 + 25 * s, 1.4, "open"
    pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -100 - 30 * math.sin(b / 2 - 1), -20 - 25 * c, 1.4, "open"
    pose.look_x = 0.6 * c
    pose.eyes = "happy"
    pose.smile, pose.mouth_open, pose.blush = 0.95, 0.3, 0.7
    return pose


def dance_twirl(b):
    """A hop with arms wide and a spin (he squeezes thin as he turns)."""
    p = (b / math.tau / 4) % 1.0          # one spin per four beats
    turn = 0.32 + 0.68 * abs(math.cos(p * math.tau)) if 0.1 < p < 0.9 else 1.0
    air = max(0.0, math.sin(p * math.pi)) ** 0.6
    pose = Pose(lift=14 * air, bob=-2 * air, sx=turn, sy=1 + 0.05 * (1 - turn), knee_f=10 + 20 * (1 - air),
                knee_b=10 + 20 * (1 - air), hip_f=10 * air, hip_b=-10 * air, head=8 * math.sin(b / 2))
    pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 100 + 25 * air, 10, 1.5, "open"
    pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -100 - 25 * air, -10, 1.5, "open"
    return _party_face(pose, air)


def dance_wipers(b):
    """Both index fingers up, swinging side to side like windshield wipers, in time with the beat."""
    sw = math.sin(b / 2)          # one full sweep every two beats
    pose = Pose(bob=1.5 * abs(math.sin(b)) + 1, lean=2 * sw, hip_f=8 * sw, hip_b=-8 * sw, knee_f=10 + 8 * abs(sw),
                knee_b=10 + 8 * abs(sw), head=6 * sw, hat=-4 * sw, look_x=0.4 * sw)
    pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 75, 105 - 65 * sw, 1.5, "point"   # forearm sweeps 180 +/- 65
    pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -75, -105 - 65 * sw, 1.5, "point"
    return _party_face(pose, abs(sw))


def dance_chicken(b):
    """Elbows pumping like wings, head pecking forward on every beat, knees bent."""
    flap = math.sin(b * 2)
    peck = max(0.0, math.sin(b)) ** 2
    pose = Pose(bob=2 + 2 * abs(flap), lean=8 * peck, head=-10 * peck + 4, knee_f=24 + 8 * flap, knee_b=24 - 8 * flap,
                hip_f=8 * flap, hip_b=-8 * flap, look_x=0.8, sy=1 - 0.03 * peck)
    pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 80 + 10 * flap, -80 + 40 * flap, 1.0, "fist"
    pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -80 - 10 * flap, 80 - 40 * flap, 1.0, "fist"
    pose.eyes, pose.mouth, pose.mouth_open, pose.blush = "open", "o", 0.25 * peck + 0.1, 0.6
    return pose


def dance_trex(b):
    """Tiny T-rex arms twitching, big stomps side to side, head thrust forward."""
    st = math.sin(b / 2)
    hit = max(0.0, abs(math.sin(b / 2))) ** 3
    pose = Pose(bob=-2 * hit + 2, lean=10, head=6 * math.sin(b), hip_f=20 * st, hip_b=-20 * st,
                knee_f=8 + 38 * max(0.0, st), knee_b=8 + 38 * max(0.0, -st), sx=1 + 0.04 * hit, sy=1 - 0.04 * hit)
    twitch = 6 * math.sin(b * 4)
    pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 18 + twitch, 120, 0.6, "open"
    pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -18 - twitch, -120, 0.6, "open"
    pose.eyes, pose.mouth, pose.mouth_open, pose.brow, pose.blush = "open", "smile", 0.8 * hit + 0.2, 0.9, 0.4
    pose.smile = 0.8
    return pose


def dance_floss(b):
    """Arms swing hard one way while the hips go the other, bouncing on the beat."""
    sw = math.sin(b)
    pose = Pose(bob=2 * abs(math.cos(b)) , lean=-10 * sw, hip_f=-20 * sw, hip_b=20 * sw, knee_f=18, knee_b=18,
                head=5 * sw, hat=-6 * sw)
    pose.sh_f, pose.el_f, pose.reach_f, pose.hand_f = 15 + 70 * sw, 10, 1.1, "fist"
    pose.sh_b, pose.el_b, pose.reach_b, pose.hand_b = -15 + 70 * sw, -10, 1.1, "fist"
    return _party_face(pose, abs(sw))


DANCE_MOVES = {"pump": dance_pose, "disco": dance_disco, "sprinkler": dance_sprinkler, "roof": dance_roof,
               "robot": dance_robot, "shuffle": dance_shuffle, "headbang": dance_headbang,
               "hips": dance_hips, "twirl": dance_twirl, "wipers": dance_wipers, "chicken": dance_chicken,
               "trex": dance_trex, "floss": dance_floss}


def fists_up(pose, pump=0.0):
    """Both fists raised beside his head, like the Ultimate Pull card."""
    pose.sh_f, pose.el_f, pose.reach_f = 120 + 10 * pump, 30 - 10 * pump, 1.5
    pose.sh_b, pose.el_b, pose.reach_b = -120 - 10 * pump, -30 + 10 * pump, 1.5
    pose.hand_f = pose.hand_b = "fist"
    return pose


def hold(pose, up=0.0):
    """Near hand holds something out in front of him."""
    pose.sh_f, pose.el_f, pose.hand_f = 40 + up, 70, "fist"
    return pose


def hug(pose):
    """Both arms wrapped around something at his chest."""
    pose.sh_f, pose.el_f, pose.hand_f = 30, 95, "open"
    pose.sh_b, pose.el_b, pose.hand_b, pose.back_front = 60, 85, "open", 1.0
    return pose


def scratch_beard(pose, t, speed=12.0):
    """Far hand comes round to scratch his chin while he thinks."""
    pose.back_front = 1.0
    pose.sh_b, pose.el_b, pose.hand_b = 70, 70 + 8 * math.sin(t * speed), "point"
    return pose


def shrug(pose):
    pose.sh_f, pose.el_f, pose.hand_f = 45, 75, "open"
    pose.sh_b, pose.el_b, pose.hand_b = -45, -75, "open"
    pose.brow, pose.quirk, pose.smile, pose.mouth_open = 0.7, 1.0, 0.1, 0.0
    pose.head = -6
    return pose


def palms_up(pose):
    """Startled, both hands up and open."""
    pose.sh_f, pose.el_f, pose.hand_f = 70, 60, "open"
    pose.sh_b, pose.el_b, pose.hand_b = -70, -60, "open"
    return pose
