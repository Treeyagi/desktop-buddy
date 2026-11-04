"""Render a settings tab to a PNG without touching your real settings.

    python3 tools/render_tab.py behavior out.png
    (tabs: buddy, behavior, look, sayings, claude, "my voice")
"""
import importlib.util
import os
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
tab, out = sys.argv[1].lower(), sys.argv[2]
import settings.store as store  # noqa: E402

cfg = tempfile.mkdtemp()  # a throwaway settings folder
store.DIR, store.PATH, store.PID_PATH = cfg, os.path.join(cfg, "settings.json"), os.path.join(cfg, "x.pid")
sys.argv = [sys.argv[0]]
spec = importlib.util.spec_from_file_location("win", os.path.join(ROOT, "settings", "window.py"))
win = importlib.util.module_from_spec(spec)
spec.loader.exec_module(win)
from PyQt6.QtCore import QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
w = win.SettingsWindow()
w.resize(720, 1150)
w.show()
for i in range(w.tabs.count()):
    if w.tabs.tabText(i).lower() == tab:
        w.tabs.setCurrentIndex(i)
QTimer.singleShot(1000, lambda: (w.grab().save(out), app.quit()))
app.exec()
print(out)
