"""The conversion wheel — Alfred's signature interaction.

Two cooperating top-level windows are used:

* :class:`RadialMenu` — a small per-pixel-alpha window. Only the circular wheel
  is painted; everything around it is fully transparent (no square window, no
  title bar, no border). It is also an OLE drop target, so during a
  Shift+drag from Windows Explorer the user just releases the file over a
  format.
* :class:`CatchOverlay` — an (invisible, 1 % opacity) window that covers the
  monitor while the wheel is open. Releasing a drag or clicking anywhere
  outside the wheel lands on it and cancels safely: Explorer never receives
  the drop, so nothing is moved or copied.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import (
    QElapsedTimer,
    QObject,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QRunnable,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QImage,
    QImageReader,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

from alfred.core import formats as F
from alfred.platform import win32
from alfred.ui import icons
from alfred.ui import theme as T

HUB = -2  # pseudo index for the centre


# ---------------------------------------------------------------------------
# Pure geometry (unit tested)
# ---------------------------------------------------------------------------
def segment_at(dx: float, dy: float, n: int, r_in: float, r_out: float, hub: float, slack: float = 14) -> int:
    """Index of the segment under (dx, dy) relative to the centre.

    Segment 0 is centred at 12 o'clock and indices grow clockwise.
    Returns ``HUB`` inside the hub, ``-1`` outside the wheel.
    """
    r = math.hypot(dx, dy)
    if r <= hub:
        return HUB
    if n <= 0 or r < r_in - 2 or r > r_out + slack:
        return -1
    angle = (math.degrees(math.atan2(dy, dx)) + 90.0) % 360.0  # 0 = up, clockwise
    span = 360.0 / n
    return int(((angle + span / 2) % 360.0) // span) % n


def wheel_position(cursor: QPoint, size: QSize, area: QRect, margin: int = 6) -> QPoint:
    """Top-left so the wheel is centred on the cursor but fully inside ``area``."""
    x = cursor.x() - size.width() // 2
    y = cursor.y() - size.height() // 2
    x = max(area.left() + margin, min(x, area.right() - size.width() - margin + 1))
    y = max(area.top() + margin, min(y, area.bottom() - size.height() - margin + 1))
    return QPoint(x, y)


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_out_back(t: float, s: float = 1.4) -> float:
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}".replace(".", ",")
        size /= 1024
    return ""


# ---------------------------------------------------------------------------
# Items & thumbnails
# ---------------------------------------------------------------------------
@dataclass
class WheelItem:
    key: str
    label: str
    sublabel: str = ""
    icon: str = "file"
    experimental: bool = False
    note: str = ""
    payload: object = None


@dataclass
class WheelState:
    items: list[WheelItem] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    mode: str = "click"  # "click" | "drag"


class _ThumbSignals(QObject):
    done = Signal(str, QImage)


class _ThumbJob(QRunnable):
    def __init__(self, path: Path, size: int, signals: _ThumbSignals, ffmpeg: str | None):
        super().__init__()
        self.path, self.size, self.signals, self.ffmpeg = path, size, signals, ffmpeg

    def run(self):
        img = QImage()
        try:
            img = load_thumbnail(self.path, self.size, self.ffmpeg)
        except Exception:  # noqa: BLE001
            img = QImage()
        self.signals.done.emit(str(self.path), img)


def load_thumbnail(path: Path, size: int, ffmpeg: str | None = None) -> QImage:
    cat = F.category(path)
    if cat == F.IMAGE:
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        s = reader.size()
        if s.isValid() and s.width() > 0:
            s.scale(size * 2, size * 2, Qt.AspectRatioMode.KeepAspectRatioByExpanding)
            reader.setScaledSize(s)
        img = reader.read()
        if not img.isNull():
            return img
        from alfred.core.converters.images import open_image

        pil = open_image(path).convert("RGBA")
        pil.thumbnail((size * 2, size * 2))
        data = pil.tobytes("raw", "RGBA")
        return QImage(data, pil.width, pil.height, pil.width * 4, QImage.Format.Format_RGBA8888).copy()
    if cat == F.PDF:
        import pymupdf

        with pymupdf.open(str(path)) as doc:
            if doc.needs_pass or doc.page_count == 0:
                return QImage()
            page = doc[0]
            zoom = (size * 2) / max(page.rect.width, page.rect.height)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            return QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
    if cat == F.VIDEO and ffmpeg:
        import tempfile

        from alfred.core.converters.media import thumbnail

        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "t.png"
            if thumbnail(ffmpeg, path, out, size * 2):
                return QImage(str(out)).copy()
    return QImage()


CATEGORY_ICON = {
    F.IMAGE: "image", F.AUDIO: "audio", F.VIDEO: "video", F.PDF: "pdf", F.DOCUMENT: "doc",
    F.PRESENTATION: "slides", F.SPREADSHEET: "sheet", F.SUBTITLE: "subtitle", F.ARCHIVE: "archive",
    F.FOLDER: "folder",
}


# ---------------------------------------------------------------------------
# Catch overlay
# ---------------------------------------------------------------------------
class CatchOverlay(QWidget):
    """Invisible full-monitor window: safe cancel area + Explorer drag detector."""

    file_drag_entered = Signal(list, QPoint)
    drag_left = Signal()
    clicked = Signal()

    def __init__(self):
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.NoDropShadowWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAcceptDrops(True)
        self.setWindowOpacity(0.015)  # invisible, but still hit-testable (alpha > 0)
        self.setWindowTitle("Alfred overlay")
        self.armed_at = 0.0
        self.winId()  # create the native window now so it is registered as drop target

    def arm(self, screen) -> None:
        geo = screen.geometry()
        # 1 px narrower than the monitor: avoids Windows' "full-screen app" heuristics
        self.setGeometry(geo.adjusted(0, 0, -1, 0))
        self.armed_at = time.monotonic()
        if not self.isVisible():
            self.show()
        self.raise_()

    def disarm(self) -> None:
        self.hide()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0))

    def mousePressEvent(self, e):
        self.clicked.emit()

    def dragEnterEvent(self, e):
        urls = [u for u in e.mimeData().urls() if u.isLocalFile()] if e.mimeData().hasUrls() else []
        files = [Path(u.toLocalFile()) for u in urls]
        if files:
            e.setDropAction(Qt.DropAction.IgnoreAction)
            e.accept()
            self.file_drag_entered.emit(files, QCursor.pos())
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        e.ignore()  # dropping here is never allowed -> safe cancel

    def dragLeaveEvent(self, e):
        self.drag_left.emit()

    def dropEvent(self, e):
        e.ignore()


# ---------------------------------------------------------------------------
# The wheel
# ---------------------------------------------------------------------------
class RadialMenu(QWidget):
    chosen = Signal(object, list)        # payload, files
    cancelled = Signal(str)              # reason
    hovered = Signal(int)
    opened = Signal()
    pinned = Signal(list)                # files dropped on the hub (wheel stays open)

    SIZE = 500
    R_OUT = 200.0
    R_IN = 94.0
    HUB_R = 80.0

    def __init__(self, reduce_motion: bool = False):
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.NoDropShadowWindowHint)
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setWindowTitle("Alfred — roda de conversão")
        self.reduce_motion = reduce_motion
        self.state = WheelState()
        self.hover = -1
        self._hover_t: list[float] = []
        self._open_t = 0.0
        self._closing = False
        self._close_reason = ""
        self._flash = -1
        self._flash_t = 0.0
        self._spin = 0.0
        self._thumb: QImage | None = None
        self._clock = QElapsedTimer()
        self._clock.start()
        self._last = 0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._thumb_signals = _ThumbSignals()
        self._thumb_signals.done.connect(self._on_thumb)
        self._pending_choice = None
        self.ffmpeg_path: str | None = None
        self.winId()

    # -- public API ------------------------------------------------------------
    @property
    def center(self) -> QPointF:
        return QPointF(self.width() / 2, self.height() / 2)

    def is_open(self) -> bool:
        return self.isVisible() and not self._closing

    def open_at(self, global_pos: QPoint, items: list[WheelItem], files: list[Path], mode: str = "click") -> None:
        self.state = WheelState(items=list(items), files=[Path(f) for f in files], mode=mode)
        self.hover = -1
        self._hover_t = [0.0] * len(items)
        self._open_t = 1.0 if self.reduce_motion else 0.0
        self._closing = False
        self._flash = -1
        self._thumb = None
        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        if self.windowHandle() is not None and self.windowHandle().screen() is not screen:
            self.windowHandle().setScreen(screen)
        self.move(wheel_position(global_pos, self.size(), screen.availableGeometry()))
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, mode == "drag")
        self.show()
        self.raise_()
        if mode == "click":
            self.activateWindow()
            win32.force_foreground(int(self.winId()))  # Explorer may own the foreground
            self.setFocus(Qt.FocusReason.PopupFocusReason)
        self._last = self._clock.elapsed()
        self._timer.start()
        self._request_thumbnail()
        self.opened.emit()
        self.update()

    def set_mode(self, mode: str) -> None:
        self.state.mode = mode
        if mode == "click":
            self.activateWindow()
            self.setFocus()

    def dismiss(self, reason: str = "cancel") -> None:
        if not self.isVisible() or self._closing:
            return
        self._closing = True
        self._close_reason = reason
        if self.reduce_motion:
            self._finish_close()
        else:
            self._timer.start()

    def choose(self, index: int) -> None:
        if not (0 <= index < len(self.state.items)) or self._closing:
            return
        self._flash = index
        self._flash_t = 0.0
        item = self.state.items[index]
        self._pending_choice = (item.payload, list(self.state.files))
        self.dismiss("chosen")

    # -- animation ---------------------------------------------------------------
    def _tick(self):
        now = self._clock.elapsed()
        dt = min(0.05, (now - self._last) / 1000.0)
        self._last = now
        busy = False
        if self._closing:
            self._open_t -= dt / (0.16 if self._flash >= 0 else 0.13)
            if self._flash >= 0:
                self._flash_t = min(1.0, self._flash_t + dt / 0.16)
            if self._open_t <= 0:
                self._finish_close()
                return
            busy = True
        elif self._open_t < 1.0:
            self._open_t = min(1.0, self._open_t + dt / 0.26)
            busy = True
        for i in range(len(self._hover_t)):
            target = 1.0 if i == self.hover else 0.0
            cur = self._hover_t[i]
            if abs(cur - target) > 0.001:
                step = dt / (0.11 if target > cur else 0.18)
                self._hover_t[i] = min(target, cur + step) if target > cur else max(target, cur - step)
                busy = True
        if not self.reduce_motion:
            self._spin = (self._spin + dt * 40) % 360  # slow ambient rotation
        if not busy and self.reduce_motion:
            self._timer.stop()
        else:
            self._timer.setInterval(16 if busy else 33)  # idle shimmer at ~30 fps
        self.update()

    def _finish_close(self):
        self._timer.stop()
        self._open_t = 0.0
        self.hide()
        reason = self._close_reason
        choice = self._pending_choice
        self._pending_choice = None
        self._closing = False
        if reason == "chosen" and choice is not None:
            self.chosen.emit(choice[0], choice[1])
        else:
            self.cancelled.emit(reason)

    # -- thumbnails ----------------------------------------------------------------
    def _request_thumbnail(self):
        files = self.state.files
        if len(files) != 1 or files[0].is_dir():
            return
        QThreadPool.globalInstance().start(_ThumbJob(files[0], 64, self._thumb_signals, self.ffmpeg_path))

    def _on_thumb(self, path: str, img: QImage):
        if self.state.files and str(self.state.files[0]) == path and not img.isNull():
            self._thumb = img
            self.update()

    # -- hit testing -----------------------------------------------------------------
    def index_at(self, pos: QPointF) -> int:
        c = self.center
        return segment_at(pos.x() - c.x(), pos.y() - c.y(), len(self.state.items),
                          self.R_IN, self.R_OUT, self.HUB_R)

    def _set_hover(self, idx: int):
        if idx == HUB:
            idx = -1
        if idx != self.hover:
            self.hover = idx
            if idx >= 0:
                self.hovered.emit(idx)
            if not self._timer.isActive():
                self._timer.start()
            self.update()

    # -- mouse / keyboard (click mode) ---------------------------------------------------
    def mouseMoveEvent(self, e):
        self._set_hover(self.index_at(e.position()))

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            if e.button() == Qt.MouseButton.RightButton:
                self.dismiss("cancel")
            return
        idx = self.index_at(e.position())
        if idx >= 0:
            self.choose(idx)
        elif idx == HUB:
            self.dismiss("cancel")
        else:
            self.dismiss("outside")

    def leaveEvent(self, e):
        if self.state.mode == "click":
            self._set_hover(-1)

    def keyPressEvent(self, e):
        n = len(self.state.items)
        k = e.key()
        if k == Qt.Key.Key_Escape:
            self.dismiss("escape")
        elif n and k in (Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Tab):
            self._set_hover((self.hover + 1) % n if self.hover >= 0 else 0)
        elif n and k in (Qt.Key.Key_Left, Qt.Key.Key_Up, Qt.Key.Key_Backtab):
            self._set_hover((self.hover - 1) % n if self.hover >= 0 else n - 1)
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space) and self.hover >= 0:
            self.choose(self.hover)
        elif Qt.Key.Key_1 <= k <= Qt.Key.Key_9 and k - Qt.Key.Key_1 < n:
            self.choose(k - Qt.Key.Key_1)
        else:
            super().keyPressEvent(e)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)

    # -- drag & drop (drag mode) ------------------------------------------------------------
    def _local_files(self, mime) -> list[Path]:
        if not mime.hasUrls():
            return []
        return [Path(u.toLocalFile()) for u in mime.urls() if u.isLocalFile()]

    def dragEnterEvent(self, e):
        if self._closing or not self._local_files(e.mimeData()):
            e.ignore()
            return
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()

    def dragMoveEvent(self, e):
        idx = self.index_at(e.position())
        self._set_hover(idx)
        if idx >= 0 or idx == HUB:
            # Always COPY: the source (Explorer) must never delete/move the original.
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._set_hover(-1)

    def dropEvent(self, e):
        idx = self.index_at(e.position())
        files = self._local_files(e.mimeData()) or self.state.files
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()
        if idx >= 0:
            self.state.files = files
            self.choose(idx)
        elif idx == HUB:
            self.state.files = files
            self.set_mode("click")
            self.pinned.emit(files)
        else:
            self.dismiss("outside")

    # -- painting ----------------------------------------------------------------------
    def _segment_path(self, a0: float, a1: float, r_in: float, r_out: float, gap_px: float = 2.2) -> QPainterPath:
        c = self.center
        g_out = math.degrees(gap_px / r_out)
        g_in = math.degrees(gap_px / r_in)
        o0, o1 = a0 + g_out, a1 - g_out
        i0, i1 = a0 + g_in, a1 - g_in
        path = QPainterPath()
        path.moveTo(c.x() + r_in * math.cos(math.radians(i0)), c.y() + r_in * math.sin(math.radians(i0)))
        path.lineTo(c.x() + r_out * math.cos(math.radians(o0)), c.y() + r_out * math.sin(math.radians(o0)))
        path.arcTo(QRectF(c.x() - r_out, c.y() - r_out, 2 * r_out, 2 * r_out), -o0, -(o1 - o0))
        path.lineTo(c.x() + r_in * math.cos(math.radians(i1)), c.y() + r_in * math.sin(math.radians(i1)))
        path.arcTo(QRectF(c.x() - r_in, c.y() - r_in, 2 * r_in, 2 * r_in), -i1, (i1 - i0))
        path.closeSubpath()
        return path

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        if not self.state.items and not self.isVisible():
            return
        c = self.center
        if self._closing and self._flash >= 0:
            k = ease_out_cubic(1 - self._open_t)
            scale = 1.0 + 0.05 * k
            opacity = max(0.0, self._open_t)
        elif self._closing:
            scale = 0.92 + 0.08 * self._open_t
            opacity = max(0.0, self._open_t)
        else:
            e = ease_out_back(self._open_t, 1.2)
            scale = 0.84 + 0.16 * e
            opacity = ease_out_cubic(self._open_t)
        p.setOpacity(opacity)
        p.translate(c)
        p.scale(scale, scale)
        p.translate(-c)
        self._paint_base(p, c)
        self._paint_segments(p, c)
        self._paint_hub(p, c)

    def _paint_base(self, p: QPainter, c: QPointF):
        ro, ri = self.R_OUT, self.R_IN
        # soft shadow
        shadow = QRadialGradient(c, ro + 40)
        shadow.setColorAt(0.70, QColor(0, 0, 0, 120))
        shadow.setColorAt(0.86, QColor(0, 0, 0, 50))
        shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shadow)
        p.drawEllipse(c, ro + 40, ro + 40)
        # glass annulus
        ring = QPainterPath()
        ring.addEllipse(c, ro + 2, ro + 2)
        inner = QPainterPath()
        inner.addEllipse(c, ri - 4, ri - 4)
        ring = ring.subtracted(inner)
        glass = QRadialGradient(c, ro + 2)
        glass.setColorAt(0.45, QColor(10, 11, 16, 168))
        glass.setColorAt(1.0, QColor(21, 23, 30, 190))
        p.fillPath(ring, glass)
        sheen = QRadialGradient(QPointF(c.x() - ro * 0.45, c.y() - ro * 0.55), ro * 1.1)
        sheen.setColorAt(0, QColor(255, 255, 255, 22))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillPath(ring, sheen)
        # golden rim, sweeping in on open and slowly rotating
        cone = QConicalGradient(c, -self._spin)
        cone.setColorAt(0.00, T.qc(T.GOLD_LIGHT, 230))
        cone.setColorAt(0.18, T.qc(T.GOLD, 70))
        cone.setColorAt(0.50, T.qc(T.GOLD, 150))
        cone.setColorAt(0.75, T.qc(T.GOLD, 50))
        cone.setColorAt(1.00, T.qc(T.GOLD_LIGHT, 230))
        pen = QPen(cone, 1.4)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        sweep = 360 * ease_out_cubic(min(1.0, self._open_t * 1.25)) if not self._closing else 360
        rect = QRectF(c.x() - ro - 6, c.y() - ro - 6, 2 * (ro + 6), 2 * (ro + 6))
        p.drawArc(rect, 90 * 16, int(-sweep * 16))
        p.setPen(QPen(QColor(255, 255, 255, 16), 1))
        p.drawEllipse(c, ro + 1.5, ro + 1.5)

    def _paint_segments(self, p: QPainter, c: QPointF):
        items = self.state.items
        n = len(items)
        if not n:
            return
        span = 360.0 / n
        label_font = T.font(12.5 if n <= 8 else 11, QFont.Weight.DemiBold, spacing=104)
        sub_font = T.font(7.2, QFont.Weight.Medium)
        for i, item in enumerate(items):
            # stagger the appearance of each segment
            st = 0.0 if self._closing else min(1.0, max(0.0, (self._open_t - i * (0.35 / n)) / 0.65))
            seg_alpha = 1.0 if self._closing else ease_out_cubic(st)
            if seg_alpha <= 0.01:
                continue
            h = self._hover_t[i] if i < len(self._hover_t) else 0.0
            flash = self._flash_t if i == self._flash else 0.0
            a0 = -90 - span / 2 + i * span
            a1 = a0 + span
            grow = 9 * h + 6 * flash
            r_out = self.R_OUT - 4 * (1 - seg_alpha) + grow
            r_in = self.R_IN + 1.5 * h
            path = self._segment_path(a0, a1, r_in, r_out)
            p.save()
            p.setOpacity(p.opacity() * seg_alpha)
            if h > 0.01:
                for k, (w, a) in enumerate(((14, 18), (8, 34), (3.5, 70))):
                    p.setPen(QPen(T.qc(T.GOLD_LIGHT, int(a * h)), w, Qt.PenStyle.SolidLine,
                                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawPath(path)
                    _ = k
            base = QRadialGradient(c, r_out)
            base.setColorAt(r_in / r_out, QColor(255, 255, 255, 8))
            base.setColorAt(1.0, QColor(255, 255, 255, 20))
            p.setPen(Qt.PenStyle.NoPen)
            p.fillPath(path, base)
            if h > 0.01 or flash > 0:
                gold = QRadialGradient(c, r_out)
                k = max(h, flash)
                gold.setColorAt(r_in / r_out, T.qc(T.GOLD, int(225 * k)))
                gold.setColorAt(1.0, T.qc(T.GOLD_LIGHT, int(245 * k)))
                p.fillPath(path, gold)
                if flash > 0:
                    p.fillPath(path, QColor(255, 255, 255, int(120 * (1 - flash))))
            p.setPen(QPen(QColor(255, 255, 255, int(20 + 30 * h)), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            # content
            mid = math.radians(a0 + span / 2)
            lr = (r_in + r_out) / 2 + 2
            cx, cy = c.x() + lr * math.cos(mid), c.y() + lr * math.sin(mid)
            dark = h > 0.5 or flash > 0.3
            icon_col = T.BLACK if dark else T.GOLD
            text_col = QColor(T.BLACK) if dark else QColor(T.WHITE)
            isz = 30 + 3 * h
            icons.paint(p, item.icon, QRectF(cx - isz / 2, cy - isz / 2 - 15, isz, isz), icon_col, 1.6)
            p.setFont(label_font)
            p.setPen(text_col)
            fm = QFontMetrics(label_font)
            label = fm.elidedText(item.label, Qt.TextElideMode.ElideRight, 86)
            p.drawText(QRectF(cx - 50, cy + 4, 100, 20), Qt.AlignmentFlag.AlignCenter, label)
            if item.sublabel:
                p.setFont(sub_font)
                sc = QColor(T.BLACK) if dark else QColor(T.MUTED)
                sc.setAlpha(200)
                p.setPen(sc)
                p.drawText(QRectF(cx - 50, cy + 21, 100, 14), Qt.AlignmentFlag.AlignCenter, item.sublabel)
            if item.experimental:
                dot = QPointF(cx + fm.horizontalAdvance(label) / 2 + 7, cy + 11)
                p.setPen(QPen(QColor(T.BLACK) if dark else T.qc(T.GOLD, 200), 1.2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                path_d = QPainterPath()
                path_d.moveTo(dot + QPointF(0, -3.2))
                path_d.lineTo(dot + QPointF(3.2, 0))
                path_d.lineTo(dot + QPointF(0, 3.2))
                path_d.lineTo(dot + QPointF(-3.2, 0))
                path_d.closeSubpath()
                p.drawPath(path_d)
            p.restore()

    def _paint_hub(self, p: QPainter, c: QPointF):
        r = self.HUB_R
        hub = QRadialGradient(QPointF(c.x(), c.y() - r * 0.4), r * 1.4)
        hub.setColorAt(0, QColor(30, 33, 42, 250))
        hub.setColorAt(1, QColor(8, 9, 13, 250))
        p.setPen(QPen(T.qc(T.GOLD, 170), 1.4))
        p.setBrush(hub)
        p.drawEllipse(c, r, r)
        p.setPen(QPen(QColor(255, 255, 255, 14), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, r - 5, r - 5)
        files = self.state.files
        items = self.state.items
        title_font = T.font(9, QFont.Weight.DemiBold)
        small = T.font(7.4, QFont.Weight.Medium)
        if self.hover >= 0 and self.hover < len(items):
            it = items[self.hover]
            src = F.extension(files[0]).upper() if len(files) == 1 else f"{len(files)} arquivos"
            p.setFont(small)
            p.setPen(QColor(T.MUTED))
            p.drawText(QRectF(c.x() - r, c.y() - 40, 2 * r, 16), Qt.AlignmentFlag.AlignCenter, src)
            icons.paint(p, "arrow", QRectF(c.x() - 9, c.y() - 24, 18, 18), T.GOLD, 1.8)
            big = T.font(17, QFont.Weight.Bold, spacing=104)
            p.setFont(big)
            p.setPen(QColor(T.GOLD_LIGHT))
            p.drawText(QRectF(c.x() - r, c.y() - 6, 2 * r, 30), Qt.AlignmentFlag.AlignCenter, it.label)
            sub = "Experimental" if it.experimental else (it.sublabel or "")
            if it.note and not it.sublabel:
                sub = it.note
            if sub:
                p.setFont(small)
                p.setPen(QColor(T.WARNING) if it.experimental else QColor(T.MUTED))
                p.drawText(QRectF(c.x() - r + 16, c.y() + 24, 2 * r - 32, 30),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, sub)
            return
        # idle: thumbnail / icon + name + format
        if self._thumb is not None:
            tr = 30.0
            clip = QPainterPath()
            clip.addEllipse(QPointF(c.x(), c.y() - 18), tr, tr)
            p.save()
            p.setClipPath(clip)
            img = self._thumb
            scale = (2 * tr) / min(img.width(), img.height())
            w, h = img.width() * scale, img.height() * scale
            p.drawImage(QRectF(c.x() - w / 2, c.y() - 18 - h / 2, w, h), img)
            p.restore()
            p.setPen(QPen(T.qc(T.GOLD, 160), 1.2))
            p.drawEllipse(QPointF(c.x(), c.y() - 18), tr, tr)
        else:
            cat = F.category(files[0]) if len(files) == 1 else ""
            name = CATEGORY_ICON.get(cat, "file") if files else "file"
            if len(files) > 1:
                name = "pages"
            icons.paint(p, name, QRectF(c.x() - 20, c.y() - 40, 40, 40), T.GOLD, 1.5)
        if files:
            fm = QFontMetrics(title_font)
            title = files[0].name if len(files) == 1 else f"{len(files)} arquivos"
            p.setFont(title_font)
            p.setPen(QColor(T.WHITE))
            p.drawText(QRectF(c.x() - r + 8, c.y() + 14, 2 * r - 16, 18), Qt.AlignmentFlag.AlignCenter,
                       fm.elidedText(title, Qt.TextElideMode.ElideMiddle, int(2 * r - 22)))
            if len(files) == 1 and files[0].is_file():
                try:
                    info = f"{F.extension(files[0]).upper()} · {human_size(files[0].stat().st_size)}"
                except OSError:
                    info = F.extension(files[0]).upper()
            else:
                cats = {F.category(f) for f in files}
                info = F.category_label(next(iter(cats))) if len(cats) == 1 else "seleção mista"
            p.setFont(small)
            p.setPen(QColor(T.MUTED))
            p.drawText(QRectF(c.x() - r, c.y() + 32, 2 * r, 14), Qt.AlignmentFlag.AlignCenter, info)
        hint = "solte num formato · Esc cancela" if self.state.mode == "drag" else "Esc cancela"
        p.setFont(T.font(6.6))
        p.setPen(QColor(T.FAINT))
        p.drawText(QRectF(c.x() - r, c.y() + 48, 2 * r, 12), Qt.AlignmentFlag.AlignCenter, hint)
