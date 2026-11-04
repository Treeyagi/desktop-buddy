"""Render a contact sheet of every action (frames across, actions down) to a
PNG, without touching the desktop. Handy for checking art changes.

Run: python3 character/preview.py out.png [--cols 5] [--scale 1.0]
"""
import argparse
import os
import random
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter  # noqa: E402

from character.behavior import ACTIONS, Buddy  # noqa: E402

TILE_W, TILE_H = 340, 400


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--actions", default="walk,notice," + ",".join(ACTIONS))
    args = ap.parse_args()
    app = QGuiApplication(sys.argv)  # noqa: F841
    random.seed(7)

    actions = args.actions.split(",")
    img = QImage(TILE_W * args.cols, TILE_H * len(actions), QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    bg = QLinearGradient(0, 0, 0, img.height())
    bg.setColorAt(0, QColor(70, 50, 120))
    bg.setColorAt(1, QColor(30, 30, 60))
    p.fillRect(img.rect(), bg)
    label = QFont()
    label.setPixelSize(16)
    label.setBold(True)

    for row, name in enumerate(actions):
        b = Buddy(4000, TILE_H - 40, scale=args.scale)
        b.x = 2000
        b.force(name.split(":")[0])
        if name.startswith("dance:"):   # "dance:disco" shows just that dance move
            b.data["routine"] = [name.split(":")[1]]
            b.data["seg"] = 60.0 / 126 * 4
            b.dur = b.data["seg"]
            name = "dance"
        elif name.startswith("idle:"):  # "idle:owl" shows just that idle
            b.data["kind"] = name.split(":")[1]
            b.dur = max(3.0, __import__("character.behavior", fromlist=["IDLE_CYCLE"]).IDLE_CYCLE.get(b.data["kind"], 3.0))
            name = "idle"
        if name == "walk":
            b.data.update(target=99999, notice=None)
        for _ in range(60 * 60):  # scenes start by walking over; skip ahead to the scene itself
            if b.state == name:
                break
            b.update(1 / 60)
        total = b.dur if b.dur else 2.0
        for col in range(args.cols):
            when = total * (col + 0.5) / args.cols
            while b.t < when and b.state == name:
                b.update(1 / 60)
            ox, oy = col * TILE_W, row * TILE_H
            p.save()
            p.setClipRect(QRectF(ox, oy, TILE_W, TILE_H))
            p.fillRect(QRectF(ox, oy + TILE_H - 40, TILE_W, 40), QColor(40, 90, 60))
            p.translate(ox + TILE_W / 2 - b.x, oy)
            b.draw(p)
            p.restore()
            p.setPen(QColor(255, 255, 255, 200))
            p.setFont(label)
            p.drawText(QPointF(ox + 10, oy + 22), f"{name}  t={b.t:.1f}s")
    p.end()
    img.save(args.out)
    print(args.out, img.width(), img.height())


if __name__ == "__main__":
    main()
