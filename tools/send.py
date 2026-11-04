"""Send a command to the running buddy over his local socket.

    python3 tools/send.py dance               # do an action or scene now
    python3 tools/send.py quip "hello there"  # say a specific line
    python3 tools/send.py --focus 25          # start a focus timer (0 stops it)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PyQt6.QtCore import QCoreApplication  # noqa: E402
from PyQt6.QtNetwork import QLocalSocket  # noqa: E402

from settings.store import SOCKET  # noqa: E402

args = sys.argv[1:]
if not args:
    sys.exit(__doc__)
msg = {"focus": int(args[1])} if args[0] == "--focus" else {"do": args[0]}
if len(args) > 1 and args[0] != "--focus":
    msg["text"] = args[1]
app = QCoreApplication([])
sock = QLocalSocket()
sock.connectToServer(SOCKET)
if not sock.waitForConnected(500):
    sys.exit("the buddy isn't running")
sock.write((json.dumps(msg) + "\n").encode())
sock.flush()
sock.waitForBytesWritten(500)
print("sent", msg)
