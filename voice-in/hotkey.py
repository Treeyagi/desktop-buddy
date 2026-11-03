"""Push-to-talk as a real KDE global shortcut.

Registers "Desktop Buddy / Push to talk (hold)" with KGlobalAccel over D-Bus,
so it works in any app and also shows up in System Settings > Shortcuts. KDE
reports both the press and the release, so holding the key means talking.
"""
from PyQt6.QtCore import QMetaType, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtDBus import QDBusArgument, QDBusConnection, QDBusInterface
from PyQt6.QtGui import QKeySequence

COMPONENT = "desktop-buddy"
ACTION = "push-to-talk"
ACTION_ID = [COMPONENT, ACTION, "Desktop Buddy", "Push to talk (hold)"]
PATH = "/component/desktop_buddy"
SET_PRESENT, NO_AUTOLOADING = 2, 4


def _action_id():
    return QDBusArgument(ACTION_ID, QMetaType.Type.QStringList.value)


def _check(reply, what):
    if reply.errorName():
        print(f"push-to-talk: {what} failed: {reply.errorMessage()}")
    return reply


def _keys(*keys):
    arg = QDBusArgument()
    arg.beginArray(QMetaType.Type.Int.value)
    for k in keys:
        arg.add(k, QMetaType.Type.Int.value)
    arg.endArray()
    return arg


class PushToTalk(QObject):
    pressed = pyqtSignal()
    released = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = QDBusConnection.sessionBus()
        self.kga = QDBusInterface("org.kde.kglobalaccel", "/kglobalaccel", "org.kde.KGlobalAccel", self.session)
        self.key = None
        self.down = False
        if not self.kga.isValid():
            return
        _check(self.kga.call("doRegister", _action_id()), "registering")
        for signal, slot in (("globalShortcutPressed", self._pressed),
                             ("globalShortcutReleased", self._released)):
            self.session.connect("org.kde.kglobalaccel", PATH, "org.kde.kglobalaccel.Component",
                                 signal, slot)

    @property
    def available(self):
        return self.kga.isValid()

    def set_key(self, text):
        """Bind the shortcut; returns an error message, or None when it's set."""
        if not self.available:
            return "KDE's global shortcuts aren't available."
        seq = QKeySequence(text or "")
        if seq.isEmpty():
            self.clear()
            return None
        key = seq[0].toCombined()
        if key == self.key:
            return None
        if key in self.current_keys():  # already ours (from an earlier run)
            self.key = key
            return None
        ok = self.kga.call("isGlobalShortcutAvailable", key, COMPONENT).arguments()
        if ok and not ok[0]:
            return f"{text} is already used by another shortcut. Pick a different key."
        _check(self.kga.call("setShortcut", _action_id(), _keys(key),
                             QDBusArgument(SET_PRESENT | NO_AUTOLOADING, QMetaType.Type.UInt.value)),
               "setting the key")
        self.key = key
        return None

    def current_keys(self):
        """The keys KDE has bound to push-to-talk right now."""
        args = self.kga.call("shortcut", _action_id()).arguments()
        return list(args[0]) if args and isinstance(args[0], list) else []

    def clear(self):
        if self.available:
            _check(self.kga.call("setShortcut", _action_id(), _keys(),
                                 QDBusArgument(SET_PRESENT | NO_AUTOLOADING, QMetaType.Type.UInt.value)),
                   "clearing the key")
        self.key = None

    @pyqtSlot(str, str, "qlonglong")
    def _pressed(self, component, action, _ts):
        if action == ACTION and not self.down:  # held keys repeat; one press is enough
            self.down = True
            self.pressed.emit()

    @pyqtSlot(str, str, "qlonglong")
    def _released(self, component, action, _ts):
        if action == ACTION and self.down:
            self.down = False
            self.released.emit()
