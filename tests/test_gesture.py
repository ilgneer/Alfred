"""Shift + drag state machine (pure logic, runs on any OS)."""
from __future__ import annotations

from alfred.platform.gesture import ARMED, IDLE, GestureDetector, Sample


def feed(det, *samples):
    out = []
    for s in samples:
        out.extend(det.feed(s))
    return out


def test_arms_only_after_threshold_with_shift():
    det = GestureDetector("shift", origin_ok=lambda: True)
    ev = feed(det, Sample(True, shift=True, pos=(100, 100)), Sample(True, shift=True, pos=(105, 104)))
    assert ev == [] and det.state != ARMED
    ev = feed(det, Sample(True, shift=True, pos=(120, 100)))
    assert ev == ["arm"] and det.state == ARMED
    ev = feed(det, Sample(False, shift=True, pos=(300, 300)))
    assert ev == ["release"] and det.state == IDLE


def test_plain_drag_without_shift_never_arms():
    det = GestureDetector("shift", origin_ok=lambda: True)
    ev = feed(det, Sample(True, pos=(0, 0)), Sample(True, pos=(200, 0)), Sample(False, pos=(200, 0)))
    assert ev == []


def test_shift_pressed_during_drag_also_arms():
    det = GestureDetector("shift", origin_ok=lambda: True)
    ev = feed(det, Sample(True, pos=(0, 0)), Sample(True, pos=(40, 0)), Sample(True, shift=True, pos=(60, 0)))
    assert ev == ["arm"]


def test_shift_click_without_movement_is_ignored():
    det = GestureDetector("shift", origin_ok=lambda: True)
    ev = feed(det, Sample(True, shift=True, pos=(10, 10)), Sample(False, shift=True, pos=(10, 10)))
    assert ev == []


def test_drag_not_started_in_explorer_is_ignored():
    det = GestureDetector("shift", origin_ok=lambda: False)
    ev = feed(det, Sample(True, shift=True, pos=(0, 0)), Sample(True, shift=True, pos=(300, 0)))
    assert ev == []


def test_origin_checked_once_at_press():
    calls = []

    def origin():
        calls.append(1)
        return True

    det = GestureDetector("shift", origin_ok=origin)
    feed(det, *[Sample(True, shift=True, pos=(i * 5, 0)) for i in range(10)])
    assert len(calls) == 1


def test_escape_while_armed_cancels_and_suppresses_release():
    det = GestureDetector("shift", origin_ok=lambda: True)
    feed(det, Sample(True, shift=True, pos=(0, 0)), Sample(True, shift=True, pos=(50, 0)))
    ev = feed(det, Sample(True, shift=True, esc=True, pos=(60, 0)))
    assert "cancel" in ev and "esc" in ev
    ev = feed(det, Sample(False, pos=(60, 0)))
    assert ev == [] and det.state == IDLE


def test_escape_edge_only_once():
    det = GestureDetector()
    ev = feed(det, Sample(False, esc=True), Sample(False, esc=True), Sample(False, esc=False), Sample(False, esc=True))
    assert ev.count("esc") == 2


def test_modifier_variants():
    det = GestureDetector("shift+ctrl", origin_ok=lambda: True)
    ev = feed(det, Sample(True, shift=True, pos=(0, 0)), Sample(True, shift=True, pos=(80, 0)))
    assert ev == []
    ev = feed(det, Sample(True, shift=True, ctrl=True, pos=(90, 0)))
    assert ev == ["arm"]
    det = GestureDetector("shift+alt", origin_ok=lambda: True)
    ev = feed(det, Sample(True, shift=True, alt=True, pos=(0, 0)), Sample(True, shift=True, alt=True, pos=(80, 0)))
    assert ev == ["arm"]


def test_rearms_on_next_drag():
    det = GestureDetector("shift", origin_ok=lambda: True)
    for _ in range(3):
        ev = feed(det, Sample(True, shift=True, pos=(0, 0)), Sample(True, shift=True, pos=(30, 30)),
                  Sample(False, pos=(30, 30)))
        assert ev == ["arm", "release"]
