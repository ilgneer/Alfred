"""Floating glass notifications (job progress and results), bottom-right."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from alfred.ui import icons
from alfred.ui import theme as T
from alfred.ui.widgets import ElidedLabel, GhostButton, IconButton, Label, SlimProgress

WIDTH = 380


class Toast(QWidget):
    closed = Signal(object)
    open_folder = Signal(object)
    open_file = Signal(object)
    cancel = Signal(str)

    def __init__(self, kind: str = "info"):
        flags = (Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.NoDropShadowWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedWidth(WIDTH)
        self.kind = kind
        self.job_id: str | None = None
        self.outputs: list[Path] = []
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.dismiss)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 18, 18)
        root.setSpacing(10)
        top = QHBoxLayout()
        top.setSpacing(12)
        self.icon = QLabel()
        self.icon.setFixedSize(30, 30)
        top.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        self.title = ElidedLabel("")
        self.title.setFont(T.font(10, QFont.Weight.DemiBold))
        self.title.setStyleSheet(f"color: {T.WHITE}; background: transparent;")
        self.body = Label("", 8.8, color=T.MUTED, wrap=True)
        texts.addWidget(self.title)
        texts.addWidget(self.body)
        top.addLayout(texts, 1)
        self.close_btn = IconButton("close", "Fechar", 26)
        self.close_btn.clicked.connect(self.dismiss)
        top.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(top)
        self.progress = SlimProgress()
        root.addWidget(self.progress)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        self.actions.addStretch(1)
        root.addLayout(self.actions)
        self._buttons: list[QWidget] = []
        self.progress.hide()
        self.set_icon("info")

    # -- content --------------------------------------------------------------
    def set_icon(self, name: str, color: str = T.GOLD):
        self.icon.setPixmap(icons.pixmap(name, color, 26, self.devicePixelRatioF()))

    def set_text(self, title: str, body: str = ""):
        self.title.setText(title)
        self.body.setText(body)
        self.body.setVisible(bool(body))
        self.adjustSize()

    def set_actions(self, actions: list[tuple[str, str, object]]):
        for b in self._buttons:
            b.deleteLater()
        self._buttons = []
        for text, icon_name, cb in actions:
            b = GhostButton(text, icon_name, compact=True)
            b.clicked.connect(cb)
            self.actions.addWidget(b)
            self._buttons.append(b)
        self.adjustSize()

    def auto_hide(self, ms: int):
        self._hide_timer.start(ms)

    def enterEvent(self, e):
        if self._hide_timer.isActive():
            self._hide_timer.stop()
            self._resume = True

    def leaveEvent(self, e):
        if getattr(self, "_resume", False):
            self._resume = False
            self._hide_timer.start(2500)

    def dismiss(self):
        self._hide_timer.stop()
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(160)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.finished.connect(self._closed)
        anim.start()
        self._fade = anim

    def _closed(self):
        self.hide()
        self.closed.emit(self)
        self.deleteLater()

    # -- painting ------------------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        for i in range(6, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 10))
            p.drawRoundedRect(r.adjusted(-i, -i + 3, i, i + 3), 18 + i, 18 + i)
        path = QPainterPath()
        path.addRoundedRect(r, 18, 18)
        p.fillPath(path, QColor(17, 19, 25, 238))
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor(255, 255, 255, 14))
        g.setColorAt(1, QColor(255, 255, 255, 2))
        p.fillPath(path, g)
        accent = {"success": T.SUCCESS, "error": T.DANGER}.get(self.kind, T.GOLD)
        border = QLinearGradient(r.topLeft(), r.topRight())
        border.setColorAt(0, T.qc(accent, 150))
        border.setColorAt(1, QColor(255, 255, 255, 22))
        p.setPen(QPen(border, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(T.qc(accent, 220))
        p.drawRoundedRect(QRectF(r.left() + 1, r.top() + 18, 3, r.height() - 36), 1.5, 1.5)


class ToastManager:
    MARGIN = 14
    GAP = 4

    def __init__(self):
        self.toasts: list[Toast] = []
        self.by_job: dict[str, Toast] = {}

    def _screen(self):
        return QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()

    def show(self, toast: Toast):
        toast.closed.connect(self._remove)
        self.toasts.append(toast)
        toast.adjustSize()
        toast.setWindowOpacity(0.0)
        self._layout(new=toast)
        toast.show()
        anim = QPropertyAnimation(toast, b"windowOpacity", toast)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        toast._fade_in = anim

    def _remove(self, toast: Toast):
        if toast in self.toasts:
            self.toasts.remove(toast)
        for k, v in list(self.by_job.items()):
            if v is toast:
                del self.by_job[k]
        self._layout()

    def _layout(self, new: Toast | None = None):
        area = self._screen().availableGeometry()
        y = area.bottom() - self.MARGIN
        for t in reversed(self.toasts):
            t.adjustSize()
            h = t.height()
            target = QPoint(area.right() - t.width() - self.MARGIN + 1, y - h + 1)
            if t is new:
                t.move(target + QPoint(30, 0))
                slide = QPropertyAnimation(t, b"pos", t)
                slide.setDuration(260)
                slide.setStartValue(target + QPoint(30, 0))
                slide.setEndValue(target)
                slide.setEasingCurve(QEasingCurve.Type.OutCubic)
                slide.start()
                t._slide = slide
            elif t.pos() != target:
                mv = QPropertyAnimation(t, b"pos", t)
                mv.setDuration(180)
                mv.setEndValue(target)
                mv.setEasingCurve(QEasingCurve.Type.OutCubic)
                mv.start()
                t._move = mv
            y -= h + self.GAP

    def info(self, title: str, body: str = "", icon_name: str = "info", ms: int = 5000, kind: str = "info") -> Toast:
        t = Toast(kind)
        t.set_icon(icon_name, {"error": T.DANGER, "success": T.SUCCESS}.get(kind, T.GOLD))
        t.set_text(title, body)
        self.show(t)
        if ms:
            t.auto_hide(ms)
        return t

    def clear(self):
        for t in list(self.toasts):
            t.hide()
            t.deleteLater()
        self.toasts.clear()
        self.by_job.clear()
