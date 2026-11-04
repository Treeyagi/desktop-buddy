"""Headless stress test: run the buddy through random life, every action and
scene, and random ADHD events, drawing as it goes. Fails loudly on a crash or
if he walks off screen.

    python3 tools/soak.py            # 20 simulated minutes
    python3 tools/soak.py 60         # an hour
"""
import os
import random
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtCore import QPointF  # noqa: E402
from PyQt6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402

app = QGuiApplication([])
from character.adhd import ADHD_ACTIONS  # noqa: E402
from character.behavior import ACTIONS, Buddy  # noqa: E402
from character.scenes import SCENES  # noqa: E402
from core.bus import Bus  # noqa: E402
from core.load import load  # noqa: E402

minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 20
img = QImage(1920, 1050, QImage.Format.Format_ARGB32_Premultiplied)
random.seed(1)

for name in sorted(set(ACTIONS) | set(SCENES) | ADHD_ACTIONS | {"walk"}):
    b = Buddy(1920, 1042, bus=Bus())
    b.do_now(name)
    for i in range(60 * 15):
        b.update(1 / 60)
        if i % 120 == 0:
            p = QPainter(img); b.draw(p); p.end()
print("every action, scene and ADHD move runs")

bus = Bus()
b = Buddy(1920, 1042, scale=1.1, bus=bus)
b.set_screen("X", QPointF(0, 0))
bus.publish("desktop.icons", load("desktop-awareness", "icons").read_icons())
events = [("attention.squirrel", QPointF(900, 900)), ("attention.tangent", None), ("attention.nudge", "hey"),
          ("attention.gaze", {"at": None, "why": "sound"}), ("attention.smug", None),
          ("attention.mood", -0.6), ("attention.mood", 0.8)]
seen = {}
start = time.perf_counter()
for i in range(int(60 * 60 * minutes)):
    if i % 900 == 0:
        bus.publish(*random.choice(events))
    if i % 30 == 0:
        bus.publish("desktop.cursor", QPointF(random.uniform(0, 1920), random.uniform(500, 1040)))
    b.update(1 / 60)
    seen[b.state] = seen.get(b.state, 0) + 1
    assert -1 <= b.x <= 1921, (b.state, b.x)
    if i % 300 == 0:
        p = QPainter(img); b.draw(p); p.end()
print(f"{minutes:g} simulated minutes ok in {time.perf_counter() - start:.0f}s;",
      "states seen:", ", ".join(sorted(seen)))
