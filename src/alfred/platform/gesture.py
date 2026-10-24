"""Shift + drag detection for Windows Explorer.

Design (see docs/ARQUITETURA.md):

* No global hooks. A 25 ms timer samples ``GetAsyncKeyState`` — this never
  delays the user's mouse or keyboard, even if Alfred is busy.
* The gesture only arms when the drag **started over an Explorer window or
  the desktop** (process ``explorer.exe``), with the configured modifier held
  and after the cursor moved at least ``THRESHOLD`` pixels. Shift+drag in any
  other program is left untouched.
* Arming only shows the invisible :class:`~alfred.ui.radial.CatchOverlay`.
  The wheel appears when Windows' own OLE drag enters that overlay with real
  files — so rubber-band selections (Shift + drag on empty space) never open
  the wheel.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, QPoint, QTimer, Signal

from alfred.platform import win32

EXPLORER_PROCESSES = {"explorer.exe"}


@dataclass
class Sample:
    button: bool
    shift: bool = False
    ctrl: bool = False
    alt: bool = False
    esc: bool = False
    pos: tuple[int, int] = (0, 0)


IDLE, PRESSED, ARMED = "idle", "pressed", "armed"


class GestureDetector:
    """Pure state machine (unit-tested on any OS)."""

    THRESHOLD = 12

    def __init__(self, modifier: str = "shift", origin_ok: Callable[[], bool] | None = None):
        self.modifier = modifier
        self.origin_ok = origin_ok or (lambda: True)
        self.state = IDLE
        self.origin: tuple[int, int] = (0, 0)
        self._origin_ok = False
        self._esc_was_down = False
        self._escaped = False

    def modifier_ok(self, s: Sample) -> bool:
        if not s.shift:
            return False
        if self.modifier == "shift+ctrl":
            return s.ctrl
        if self.modifier == "shift+alt":
            return s.alt
        return True

    def feed(self, s: Sample) -> list[str]:
        events: list[str] = []
        esc_edge = s.esc and not self._esc_was_down
        self._esc_was_down = s.esc
        if esc_edge:
            events.append("esc")
        if self.state == IDLE:
            if s.button:
                self.state = PRESSED
                self.origin = s.pos
                self._origin_ok = bool(self.origin_ok())
                self._escaped = False
        elif self.state == PRESSED:
            if not s.button:
                self.state = IDLE
            elif self._origin_ok and self.modifier_ok(s) and \
                    math.dist(s.pos, self.origin) >= self.THRESHOLD:
                self.state = ARMED
                events.append("arm")
        elif self.state == ARMED:
            if esc_edge and not self._escaped:
                self._escaped = True
                events.append("cancel")
            if not s.button:
                self.state = IDLE
                if not self._escaped:
                    events.append("release")
        return events


def explorer_under_cursor() -> bool:
    name, _cls = win32.window_info_at_cursor()
    return name in EXPLORER_PROCESSES


class GestureMonitor(QObject):
    """Qt adapter: polls the keyboard/mouse state and emits gesture signals."""

    armed = Signal(QPoint)
    released = Signal()
    cancelled = Signal()
    escape_pressed = Signal()

    def __init__(self, modifier: str = "shift", parent=None):
        super().__init__(parent)
        self.detector = GestureDetector(modifier, explorer_under_cursor)
        self.enabled = False
        self._timer = QTimer(self)
        self._timer.setInterval(25)
        self._timer.timeout.connect(self._poll)
        self.watch_escape = False  # also needed while a click-mode wheel is open

    def set_modifier(self, modifier: str) -> None:
        self.detector.modifier = modifier

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled and win32.IS_WINDOWS
        self._update_timer()

    def set_watch_escape(self, on: bool) -> None:
        self.watch_escape = on and win32.IS_WINDOWS
        self._update_timer()

    def _update_timer(self):
        if self.enabled or self.watch_escape:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()
            self.detector.state = IDLE

    def stop(self) -> None:
        self._timer.stop()

    def _poll(self):
        from PySide6.QtGui import QCursor

        pos = QCursor.pos()
        sample = Sample(
            button=win32.key_down(win32.primary_button_vk()),
            shift=win32.key_down(win32.VK_SHIFT),
            ctrl=win32.key_down(win32.VK_CONTROL),
            alt=win32.key_down(win32.VK_MENU),
            esc=win32.key_down(win32.VK_ESCAPE),
            pos=(pos.x(), pos.y()),
        )
        if not self.enabled:
            # only escape tracking
            if sample.esc and not self.detector._esc_was_down:
                self.escape_pressed.emit()
            self.detector._esc_was_down = sample.esc
            return
        for ev in self.detector.feed(sample):
            if ev == "arm":
                self.armed.emit(pos)
            elif ev == "release":
                self.released.emit()
            elif ev == "cancel":
                self.cancelled.emit()
            elif ev == "esc":
                self.escape_pressed.emit()
