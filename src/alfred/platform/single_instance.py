"""One Alfred per user session.

The first process becomes the *primary* and listens on a local socket. Any
later launch (context menu, "Enviar para", Start menu, startup entry) sends
its request to the primary and exits immediately. Explorer launches one
process per selected file; the primary aggregates those arrivals for a short
moment so a multi-selection opens a single wheel.
"""
from __future__ import annotations

import getpass
import hashlib
import json
import logging

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)


def server_name() -> str:
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001
        user = "user"
    return "alfred-v2-" + hashlib.sha1(user.encode("utf-8")).hexdigest()[:12]


_lock_handle = None


def acquire_primary_lock() -> bool:
    """Atomic election of the primary instance (kernel mutex on Windows)."""
    global _lock_handle
    import sys

    if sys.platform == "win32":
        import ctypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = ctypes.c_void_p
        handle = k32.CreateMutexW(None, True, "Local\\" + server_name())
        if not handle:
            return False
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            k32.CloseHandle(ctypes.c_void_p(handle))
            return False
        _lock_handle = handle
        return True
    from PySide6.QtCore import QDir, QLockFile

    lock = QLockFile(QDir.tempPath() + "/" + server_name() + ".lock")
    lock.setStaleLockTime(0)
    if lock.tryLock(50):
        _lock_handle = lock
        return True
    if lock.error() == QLockFile.LockError.LockFailedError and lock.removeStaleLockFile() and lock.tryLock(50):
        _lock_handle = lock
        return True
    return False


def send_to_primary(message: dict, timeout_ms: int = 800) -> bool:
    """Returns True if a primary instance received the message."""
    sock = QLocalSocket()
    sock.connectToServer(server_name())
    if not sock.waitForConnected(timeout_ms):
        return False
    data = (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")
    sock.write(data)
    sock.flush()
    sock.waitForBytesWritten(timeout_ms)
    sock.waitForReadyRead(timeout_ms)  # primary acknowledges with "ok"
    sock.disconnectFromServer()
    return True


class PrimaryServer(QObject):
    message = Signal(dict)
    files_batch = Signal(list)  # aggregated "open" requests

    AGGREGATE_MS = 350

    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self._pending: list[str] = []
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush)
        self.server.newConnection.connect(self._on_connection)

    def listen(self) -> bool:
        name = server_name()
        if self.server.listen(name):
            return True
        # stale socket from a crashed instance
        QLocalServer.removeServer(name)
        ok = self.server.listen(name)
        if not ok:
            log.error("Falha ao abrir canal de instância única: %s", self.server.errorString())
        return ok

    def close(self):
        self.server.close()

    def _on_connection(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: self._read(s))
            sock.disconnected.connect(sock.deleteLater)
            # The client may have written before readyRead was connected: read what is already buffered.
            if sock.bytesAvailable():
                self._read(sock)

    def _read(self, sock: QLocalSocket):
        while sock.canReadLine():
            raw = bytes(sock.readLine()).decode("utf-8", "replace").strip()
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            sock.write(b"ok\n")
            sock.flush()
            self.handle(msg)

    def handle(self, msg: dict):
        if msg.get("cmd") == "open" and msg.get("files"):
            for f in msg["files"]:
                if f not in self._pending:
                    self._pending.append(f)
            self._timer.start(self.AGGREGATE_MS)
        else:
            self.message.emit(msg)

    def _flush(self):
        files, self._pending = self._pending, []
        if files:
            self.files_batch.emit(files)
