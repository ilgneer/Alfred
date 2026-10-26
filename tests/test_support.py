"""Apoie o projeto (Pix)."""
from __future__ import annotations

import time

from alfred import support


def test_pix_payload_crc_is_valid():
    assert support.payload_is_valid()
    assert not support.payload_is_valid(support.PIX_PAYLOAD[:-1] + "0")


def test_qr_asset_encodes_the_payload():
    import cv2

    from alfred.core import paths

    img = cv2.imread(str(paths.asset_path("pix_qr.png")))
    value, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
    assert value == support.PIX_PAYLOAD


def test_popup_frequency():
    now = time.time()
    assert support.should_show_popup(True, 0, now)
    assert not support.should_show_popup(True, now - 3600, now)
    assert support.should_show_popup(True, now - 8 * 86400, now)
    assert not support.should_show_popup(False, 0, now)


def test_dialog_copies_code_and_saves_choice(qapp_session, tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("ALFRED_DATA_DIR", str(tmp_path / "data"))
    from PySide6.QtGui import QGuiApplication

    from alfred.app import AlfredApp

    app = AlfredApp(qapp_session, background=True)
    app.server.close()
    try:
        dlg = app.show_support(from_popup=True)
        dlg.copy_code()
        assert QGuiApplication.clipboard().text() == support.PIX_PAYLOAD
        dlg.dont_show.setChecked(True)
        dlg.reject()
        assert app.settings.value.support_popup is False
    finally:
        app._cleanup()
        app.window.allow_close()
        app.window.close()
