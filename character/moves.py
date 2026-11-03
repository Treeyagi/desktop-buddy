"""Reusable body moves shared by the basic actions and the scenes."""
import math

from character.rig import Pose


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
