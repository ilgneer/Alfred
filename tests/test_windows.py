"""Checks that only make sense on a real Windows machine (run by CI on windows-latest)."""
from __future__ import annotations

import os
import sys
import threading
import time

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="somente Windows")


def test_win32_helpers_do_not_crash(qapp_session):
    from PySide6.QtWidgets import QWidget

    from alfred.platform import win32

    assert isinstance(win32.key_down(win32.VK_SHIFT), bool)
    assert win32.primary_button_vk() in (win32.VK_LBUTTON, win32.VK_RBUTTON)
    name, cls = win32.window_info_at_cursor()
    assert isinstance(name, str) and isinstance(cls, str)
    w = QWidget()
    w.show()
    win32.set_dark_titlebar(int(w.winId()))
    win32.create_named_mutex("AlfredAppMutexTest")
    w.close()


@pytest.mark.skipif(os.environ.get("ALFRED_TEST_REGISTRY") != "1",
                    reason="altera o registro do usuário; defina ALFRED_TEST_REGISTRY=1 (CI)")
def test_registry_integration_roundtrip():
    from alfred.platform import integration as I

    I.set_context_menu(True)
    assert I.context_menu_installed()
    I.set_autostart(True)
    assert I.autostart_enabled()
    I.unregister_all()
    assert not I.context_menu_installed()
    assert not I.autostart_enabled()


def test_cancel_kills_child_process_tree():
    from alfred.core import procs

    token = procs.CancelToken()
    errors = []

    def run():
        try:
            procs.run(["cmd", "/c", "ping", "-n", "60", "127.0.0.1"], token=token, timeout=120)
        except procs.Cancelled:
            errors.append("cancelled")

    t = threading.Thread(target=run)
    t.start()
    time.sleep(1.5)
    t0 = time.time()
    token.cancel()
    t.join(15)
    assert not t.is_alive() and errors == ["cancelled"]
    assert time.time() - t0 < 10


def test_sound_player_windows_backend():
    from alfred.ui.sounds import SoundPlayer

    sp = SoundPlayer(True, 60)
    assert sp._win is not None
    for name in ("hover", "select"):
        sp.play(name)  # no audio device on CI: must silently do nothing
    sp.stop()


def test_primary_lock_is_exclusive():
    import subprocess

    src = os.path.join(os.path.dirname(__file__), "..", "src")
    code = (f"import sys; sys.path.insert(0, r'{src}');"
            "from alfred.platform.single_instance import acquire_primary_lock as a;"
            "print(a())")
    from alfred.platform.single_instance import acquire_primary_lock

    assert acquire_primary_lock() is True
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60).stdout.strip()
    assert out == "False"
