"""The conversion wheel: geometry, keyboard, mouse and drag & drop."""
from __future__ import annotations

import math

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, QRect, QSize, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent, QKeyEvent

from alfred.ui.radial import HUB, CatchOverlay, RadialMenu, WheelItem, segment_at, wheel_position


# -- geometry -------------------------------------------------------------------
@pytest.mark.parametrize("n", [1, 2, 3, 5, 8, 9, 12])
def test_segment_centres_map_to_their_index(n):
    for i in range(n):
        ang = math.radians(-90 + i * 360 / n)
        r = 150
        assert segment_at(r * math.cos(ang), r * math.sin(ang), n, 94, 200, 80) == i


def test_segment_hub_and_outside():
    assert segment_at(0, 0, 8, 94, 200, 80) == HUB
    assert segment_at(0, -60, 8, 94, 200, 80) == HUB
    assert segment_at(0, -260, 8, 94, 200, 80) == -1
    assert segment_at(0, -205, 8, 94, 200, 80) == 0  # small slack beyond the rim


def test_wheel_position_centres_on_cursor():
    area = QRect(0, 0, 1920, 1040)
    p = wheel_position(QPoint(960, 500), QSize(500, 500), area)
    assert (p.x(), p.y()) == (710, 250)


@pytest.mark.parametrize("cursor", [QPoint(5, 5), QPoint(1915, 5), QPoint(5, 1035), QPoint(1915, 1035)])
def test_wheel_position_stays_inside_screen(cursor):
    area = QRect(0, 0, 1920, 1040)
    p = wheel_position(cursor, QSize(500, 500), area)
    assert area.contains(QRect(p, QSize(500, 500)))


def test_wheel_position_secondary_monitor_negative_coords():
    area = QRect(-2560, -200, 2560, 1400)  # monitor to the left, above the primary
    p = wheel_position(QPoint(-10, -190), QSize(500, 500), area)
    assert area.contains(QRect(p, QSize(500, 500)))
    assert p.x() < 0


# -- widget behaviour -------------------------------------------------------------
@pytest.fixture
def wheel(qapp_session, tmp_path):
    f = tmp_path / "foto ação.png"
    from PIL import Image

    Image.new("RGB", (40, 30), "gold").save(f)
    w = RadialMenu(reduce_motion=True)
    items = [WheelItem(k, k.upper(), payload=k) for k in ("jpg", "webp", "pdf", "zip")]
    w.open_at(QPoint(400, 400), items, [f], "click")
    yield w, f
    w.hide()
    w.deleteLater()


def _point_for(w: RadialMenu, index: int) -> QPointF:
    n = len(w.state.items)
    ang = math.radians(-90 + index * 360 / n)
    r = (w.R_IN + w.R_OUT) / 2
    return QPointF(w.center.x() + r * math.cos(ang), w.center.y() + r * math.sin(ang))


def test_escape_closes_without_choosing(wheel, qtbot):
    w, _ = wheel
    chosen, cancelled = [], []
    w.chosen.connect(lambda *a: chosen.append(a))
    w.cancelled.connect(cancelled.append)
    QApplicationSend(w, QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert not w.isVisible()
    assert cancelled == ["escape"] and chosen == []


def test_keyboard_navigation_and_enter(wheel):
    w, f = wheel
    chosen = []
    w.chosen.connect(lambda payload, files: chosen.append((payload, files)))
    for key in (Qt.Key.Key_Right, Qt.Key.Key_Right):
        QApplicationSend(w, QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
    assert w.hover == 1
    QApplicationSend(w, QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
    assert chosen == [("webp", [f])]


def test_number_key_picks_segment(wheel):
    w, _ = wheel
    chosen = []
    w.chosen.connect(lambda payload, files: chosen.append(payload))
    QApplicationSend(w, QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_3, Qt.KeyboardModifier.NoModifier))
    assert chosen == ["pdf"]


def test_click_segment_chooses(wheel, qtbot):
    w, _ = wheel
    chosen = []
    w.chosen.connect(lambda payload, files: chosen.append(payload))
    qtbot.mouseClick(w, Qt.MouseButton.LeftButton, pos=_point_for(w, 2).toPoint())
    assert chosen == ["pdf"]


def test_click_hub_cancels(wheel, qtbot):
    w, _ = wheel
    cancelled = []
    w.cancelled.connect(cancelled.append)
    qtbot.mouseClick(w, Qt.MouseButton.LeftButton, pos=w.center.toPoint())
    assert cancelled == ["cancel"] and not w.isVisible()


def test_click_outside_ring_cancels(wheel, qtbot):
    w, _ = wheel
    cancelled = []
    w.cancelled.connect(cancelled.append)
    qtbot.mouseClick(w, Qt.MouseButton.LeftButton, pos=QPoint(3, 3))
    assert cancelled == ["outside"]


def _mime(files):
    m = QMimeData()
    m.setUrls([QUrl.fromLocalFile(str(f)) for f in files])
    return m


def test_drop_on_segment_is_copy_and_chooses(wheel):
    w, f = wheel
    w.set_mode("drag")
    chosen = []
    w.chosen.connect(lambda payload, files: chosen.append((payload, files)))
    mime = _mime([f])
    actions = Qt.DropAction.CopyAction | Qt.DropAction.MoveAction | Qt.DropAction.LinkAction
    pos = _point_for(w, 0)
    enter = QDragEnterEvent(pos.toPoint(), actions, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    w.dragEnterEvent(enter)
    assert enter.isAccepted() and enter.dropAction() == Qt.DropAction.CopyAction
    move = QDragMoveEvent(pos.toPoint(), actions, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    w.dragMoveEvent(move)
    assert move.isAccepted() and move.dropAction() == Qt.DropAction.CopyAction  # never MOVE
    assert w.hover == 0
    drop = QDropEvent(pos, actions, mime, Qt.MouseButton.NoButton, Qt.KeyboardModifier.ShiftModifier)
    w.dropEvent(drop)
    assert drop.dropAction() == Qt.DropAction.CopyAction
    assert chosen == [("jpg", [f])]


def test_drag_outside_ring_is_rejected(wheel):
    w, f = wheel
    w.set_mode("drag")
    mime = _mime([f])
    move = QDragMoveEvent(QPoint(2, 2), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, mime,
                          Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    move.accept()
    w.dragMoveEvent(move)
    assert not move.isAccepted()


def test_drop_on_hub_pins_wheel(wheel):
    w, f = wheel
    w.set_mode("drag")
    pinned = []
    w.pinned.connect(pinned.append)
    mime = _mime([f])  # QDropEvent keeps only a pointer: the QMimeData must outlive it
    drop = QDropEvent(w.center, Qt.DropAction.CopyAction, mime, Qt.MouseButton.NoButton,
                      Qt.KeyboardModifier.NoModifier)
    w.dropEvent(drop)
    assert pinned and w.isVisible() and w.state.mode == "click"


def test_drag_leave_clears_hover(wheel):
    w, _ = wheel
    w.hover = 1
    w.dragLeaveEvent(QDragLeaveEvent())
    assert w.hover == -1


def test_overlay_never_accepts_drop(qapp_session, tmp_path):
    ov = CatchOverlay()
    seen = []
    ov.file_drag_entered.connect(lambda files, pos: seen.append(files))
    f = tmp_path / "a.txt"
    f.write_text("x")
    mime = _mime([f])
    enter = QDragEnterEvent(QPoint(5, 5), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction, mime,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
    ov.dragEnterEvent(enter)
    assert seen and seen[0][0] == f
    move = QDragMoveEvent(QPoint(6, 6), Qt.DropAction.MoveAction, mime, Qt.MouseButton.LeftButton,
                          Qt.KeyboardModifier.ShiftModifier)
    move.accept()
    ov.dragMoveEvent(move)
    assert not move.isAccepted(), "a área fora da roda deve recusar o drop (cancelamento seguro)"
    ov.deleteLater()


def test_overlay_ignores_non_file_drags(qapp_session):
    ov = CatchOverlay()
    seen = []
    ov.file_drag_entered.connect(lambda files, pos: seen.append(files))
    m = QMimeData()
    m.setText("texto")
    enter = QDragEnterEvent(QPoint(5, 5), Qt.DropAction.CopyAction, m, Qt.MouseButton.LeftButton,
                            Qt.KeyboardModifier.NoModifier)
    ov.dragEnterEvent(enter)
    assert not seen and not enter.isAccepted()
    ov.deleteLater()


def test_wheel_is_frameless_translucent_tool(qapp_session):
    w = RadialMenu()
    flags = w.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert w.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    w.deleteLater()


def test_wheel_paints_transparent_corners(qapp_session, wheel):
    w, _ = wheel
    img = w.grab().toImage()
    assert img.pixelColor(2, 2).alpha() == 0, "não pode existir fundo quadrado atrás da roda"
    assert img.pixelColor(w.width() - 3, w.height() - 3).alpha() == 0
    c = img.pixelColor(int(w.center.x()), int(w.center.y()))
    assert c.alpha() > 200


def QApplicationSend(widget, event):  # noqa: N802
    from PySide6.QtWidgets import QApplication

    QApplication.sendEvent(widget, event)
