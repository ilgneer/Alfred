"""Application-level behaviour with the real controller (off-screen)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from alfred.core import jobs as J
from alfred.core.settings import Settings, SettingsStore


@pytest.fixture
def controller(qapp_session, tmp_path, monkeypatch):
    monkeypatch.setenv("ALFRED_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("ALFRED_DATA_DIR", str(tmp_path / "data"))
    from alfred.app import AlfredApp

    ctrl = AlfredApp(qapp_session, background=True)
    ctrl.server.close()  # avoid clashing with other tests
    yield ctrl
    ctrl._cleanup()
    ctrl.window.allow_close()
    ctrl.window.close()


def wait_for(cond, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        QApplication.processEvents()
        if cond():
            return True
        time.sleep(0.02)
    return False


def test_open_wheel_and_escape(controller, samples):
    assert controller.open_wheel([samples.get("png")], QPoint(300, 300), "click")
    assert controller.wheel.isVisible() and controller.overlay.isVisible()
    keys = [it.key for it in controller.wheel.state.items]
    assert "jpg" in keys and "png" not in keys
    controller._cancel_wheel("escape")
    assert wait_for(lambda: not controller.wheel.isVisible())
    assert not controller.overlay.isVisible()


def test_unknown_file_shows_error_toast(controller, tmp_path):
    f = tmp_path / "coisa.xyz123"
    f.write_text("?")
    # an unknown extension still offers "compactar em ZIP"
    assert controller.open_wheel([f], QPoint(10, 10))
    controller.wheel.hide()


def test_full_flow_converts_through_runner(controller, samples, tmp_path):
    out = tmp_path / "saida"
    controller.update_setting(output_mode="custom", custom_output_dir=str(out))
    states = []
    controller.job_updated.connect(lambda job: states.append(job.state))
    controller.open_wheel([samples.get("png")], QPoint(300, 300), "click")
    idx = next(i for i, it in enumerate(controller.wheel.state.items) if it.key == "webp")
    controller.wheel.choose(idx)
    assert wait_for(lambda: J.DONE in states, 30)
    assert (out / "Relatório de teste.webp").exists()
    assert controller.history.entries()[0].status == "done"
    assert any(t.kind == "success" for t in controller.toasts.toasts)


def test_closing_window_hides_to_tray(controller):
    controller.has_tray = True
    controller.window.show()
    controller.window.close()
    assert not controller.window.isVisible()
    assert controller.settings.value.tray_hint_shown


def test_settings_toggle_updates_sound_player(controller):
    controller.update_setting(sounds_enabled=False, volume=33)
    assert controller.sounds.enabled is False and controller.sounds.volume == 33
    stored = json.loads(controller.settings.path.read_text(encoding="utf-8"))
    assert stored["volume"] == 33 and stored["sounds_enabled"] is False


def test_all_pages_render(controller):
    for key in ("home", "history", "shortcuts", "settings", "about"):
        controller.window.show_page(key)
        QApplication.processEvents()
        assert controller.window.stack.currentWidget() is controller.window.pages[key]


def test_settings_persist_and_normalize(tmp_path):
    store = SettingsStore(tmp_path / "s.json")
    store.update(volume=150, pdf_dpi=10, output_mode="custom", custom_output_dir="")
    again = SettingsStore(tmp_path / "s.json").value
    assert again.volume == 100 and again.pdf_dpi == 72 and again.output_mode == "same"


def test_corrupted_settings_recover(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{não é json", encoding="utf-8")
    assert SettingsStore(p).value == Settings()
    assert (tmp_path / "s.json.bak").exists()


def test_single_instance_aggregates_files(qapp_session, tmp_path, monkeypatch):
    """A separate process (like Explorer launching Alfred once per file) talks to the primary."""
    import subprocess
    import sys

    from alfred.platform import single_instance as si

    name = f"alfred-test-{tmp_path.name}"
    monkeypatch.setattr(si, "server_name", lambda: name)
    server = si.PrimaryServer()
    assert server.listen()
    batches, messages = [], []
    server.files_batch.connect(batches.append)
    server.message.connect(messages.append)
    files = [str(tmp_path / f"{i}.txt") for i in range(4)]
    src = str(Path(__file__).resolve().parents[1] / "src")
    code = (
        "import sys, json, time; sys.path.insert(0, sys.argv[1]);"
        "from PySide6.QtCore import QCoreApplication; app = QCoreApplication([]);"
        "from alfred.platform import single_instance as si; si.server_name = lambda: sys.argv[2];"
        "files = json.loads(sys.argv[3]); t = time.time();"
        "ok = [si.send_to_primary({'cmd': 'open', 'files': [f]}, 3000) for f in files];"
        "ok.append(si.send_to_primary({'cmd': 'show'}, 3000));"
        "print(json.dumps({'ok': all(ok), 'seconds': time.time() - t}))"
    )
    proc = subprocess.Popen([sys.executable, "-c", code, src, name, json.dumps(files)], stdout=subprocess.PIPE,
                            text=True)
    assert wait_for(lambda: proc.poll() is not None and batches and messages, 20)
    result = json.loads(proc.stdout.read().strip().splitlines()[-1])
    assert result["ok"] and result["seconds"] < 5, result
    assert batches[0] == files
    assert messages[0] == {"cmd": "show"}
    server.close()


def test_sounds_assets_and_scaling():
    import wave

    from alfred.core import paths
    from alfred.ui import sounds

    for name in sounds.NAMES:
        f = paths.asset_path("sounds", f"{name}.wav")
        with wave.open(str(f)) as w:
            dur = w.getnframes() / w.getframerate()
            assert w.getframerate() == 48000 and w.getsampwidth() == 2
            assert 0.03 < dur < 1.6, (name, dur)
    raw = paths.asset_path("sounds", "select.wav").read_bytes()
    half = sounds.scaled_wav(raw, 0.5)
    import array

    def peak(b):
        with wave.open(__import__("io").BytesIO(b)) as w:
            a = array.array("h")
            a.frombytes(w.readframes(w.getnframes()))
            return max(abs(x) for x in a)

    assert abs(peak(half) - peak(raw) * 0.5) <= 2
    assert sounds._gain(0) == 0 and sounds._gain(100) == 1


def test_history_roundtrip(tmp_path):
    from alfred.core.history import History, HistoryEntry

    h = History(tmp_path / "h.jsonl")
    for i in range(510):
        h.add(HistoryEntry(id=str(i), started=1, finished=2, target="PNG", status="done"))
    entries = h.entries()
    assert len(entries) == 500 and entries[0].id == "509"
    h.clear()
    assert h.entries() == []


def test_selftest_report(tmp_path, qapp_session):
    from alfred.selftest import run_self_test

    report = tmp_path / "r.json"
    code = run_self_test(str(report))
    data = json.loads(report.read_text(encoding="utf-8"))
    assert code == 0 and data["ok"], data
    assert all(c["result"] in ("done", "missing-engine") for c in data["checks"])


def test_path_helpers_are_absolute():
    from alfred.core import paths

    assert paths.asset_path("alfred.png").exists()
    assert Path(paths.app_command("--x")[0]).is_absolute()
