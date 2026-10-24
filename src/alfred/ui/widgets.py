"""Custom widgets: glass cards, toggles, buttons, chips, keycaps, progress."""
from __future__ import annotations

import random

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from alfred.ui import icons
from alfred.ui import theme as T


def _anim(parent, start, end, ms, setter, curve=QEasingCurve.Type.OutCubic) -> QVariantAnimation:
    a = QVariantAnimation(parent)
    a.setStartValue(start)
    a.setEndValue(end)
    a.setDuration(ms)
    a.setEasingCurve(curve)
    a.valueChanged.connect(setter)
    return a


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------
_NOISE: QImage | None = None


def noise_tile() -> QImage:
    global _NOISE
    if _NOISE is None:
        rnd = random.Random(7)
        img = QImage(128, 128, QImage.Format.Format_ARGB32_Premultiplied)
        for y in range(128):
            for x in range(128):
                v = rnd.randint(0, 255)
                a = 7
                img.setPixelColor(x, y, QColor(v, v, v, a))
        _NOISE = img
    return _NOISE


class Backdrop(QWidget):
    """Deep black background with discreet golden ambient light and film grain."""

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        p.fillRect(r, QColor(T.BLACK))
        w, h = r.width(), r.height()
        g1 = QRadialGradient(QPointF(w * 0.86, h * -0.05), max(w, h) * 0.65)
        g1.setColorAt(0.0, T.qc(T.GOLD, 34))
        g1.setColorAt(0.45, T.qc(T.GOLD, 10))
        g1.setColorAt(1.0, T.qc(T.GOLD, 0))
        p.fillRect(r, g1)
        g2 = QRadialGradient(QPointF(w * 0.05, h * 1.05), max(w, h) * 0.7)
        g2.setColorAt(0.0, QColor(40, 46, 66, 70))
        g2.setColorAt(1.0, QColor(40, 46, 66, 0))
        p.fillRect(r, g2)
        p.drawTiledPixmap(r, _noise_pixmap())


_NOISE_PM = None


def _noise_pixmap():
    global _NOISE_PM
    if _NOISE_PM is None:
        from PySide6.QtGui import QPixmap

        _NOISE_PM = QPixmap.fromImage(noise_tile())
    return _NOISE_PM


# ---------------------------------------------------------------------------
# Glass card
# ---------------------------------------------------------------------------
class GlassCard(QFrame):
    def __init__(self, parent=None, radius: float = 18, accent: bool = False, padding: int = 20):
        super().__init__(parent)
        self.radius = radius
        self.accent = accent
        self._glow = 0.0
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(padding, padding, padding, padding)
        self.lay.setSpacing(12)

    def set_glow(self, v: float):
        self._glow = v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, self.radius, self.radius)
        fill = QLinearGradient(r.topLeft(), r.bottomLeft())
        fill.setColorAt(0, QColor(255, 255, 255, 13))
        fill.setColorAt(1, QColor(255, 255, 255, 5))
        p.fillPath(path, QColor(21, 23, 30, 170))
        p.fillPath(path, fill)
        if self.accent or self._glow > 0:
            glow = QRadialGradient(QPointF(r.right() - r.width() * 0.2, r.top()), r.width() * 0.7)
            glow.setColorAt(0, T.qc(T.GOLD, int(26 + 30 * self._glow)))
            glow.setColorAt(1, T.qc(T.GOLD, 0))
            p.fillPath(path, glow)
        border = QLinearGradient(r.topLeft(), r.bottomRight())
        a = 0.10 + 0.25 * self._glow
        border.setColorAt(0, QColor(255, 255, 255, int(255 * (0.10 + a * 0.4))))
        border.setColorAt(0.5, QColor(255, 255, 255, 14))
        border.setColorAt(1, T.qc(T.GOLD, int(255 * (0.10 + a)) if self.accent else 30))
        p.setPen(QPen(border, 1))
        p.drawPath(path)
        # top inner highlight
        hl = QLinearGradient(r.left(), 0, r.right(), 0)
        hl.setColorAt(0, QColor(255, 255, 255, 0))
        hl.setColorAt(0.5, QColor(255, 255, 255, 34))
        hl.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(QPen(hl, 1))
        p.drawLine(QPointF(r.left() + self.radius, r.top() + 1), QPointF(r.right() - self.radius, r.top() + 1))


# ---------------------------------------------------------------------------
# Toggle switch
# ---------------------------------------------------------------------------
class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pos = 1.0 if checked else 0.0
        self._hover = 0.0
        self._a = _anim(self, 0.0, 1.0, 180, self._set_pos)
        self.toggled.connect(self._on_toggled)
        self.setFixedSize(46, 26)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _set_pos(self, v):
        self._pos = float(v)
        self.update()

    def _on_toggled(self, on: bool):
        self._a.stop()
        self._a.setStartValue(self._pos)
        self._a.setEndValue(1.0 if on else 0.0)
        self._a.start()

    def setCheckedSilently(self, on: bool):
        self.blockSignals(True)
        self.setChecked(on)
        self.blockSignals(False)
        self._pos = 1.0 if on else 0.0
        self.update()

    def enterEvent(self, e):
        self._hover = 1.0
        self.update()

    def leaveEvent(self, e):
        self._hover = 0.0
        self.update()

    def sizeHint(self):
        return QSize(46, 26)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        t = self._pos
        off = QColor(255, 255, 255, 22 + int(10 * self._hover))
        on1, on2 = QColor(T.GOLD), QColor(T.GOLD_LIGHT)
        track = QLinearGradient(r.topLeft(), r.topRight())
        track.setColorAt(0, _mix(off, on1, t))
        track.setColorAt(1, _mix(off, on2, t))
        p.setPen(QPen(QColor(255, 255, 255, int(30 * (1 - t))), 1))
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + t * (r.width() - d - 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawEllipse(QRectF(x, r.top() + 4, d, d))
        p.setBrush(_mix(QColor(200, 202, 210), QColor(T.BLACK), t))
        p.drawEllipse(QRectF(x, r.top() + 3, d, d))
        if self.hasFocus():
            p.setPen(QPen(T.qc(T.GOLD_LIGHT, 140), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(-1, -1, 1, 1), r.height() / 2 + 1, r.height() / 2 + 1)


def _mix(a: QColor, b: QColor, t: float) -> QColor:
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t), int(a.alpha() + (b.alpha() - a.alpha()) * t))


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------
class _HoverMixin:
    def _init_hover(self):
        self._hover = 0.0
        self._ha = _anim(self, 0.0, 1.0, 160, self._set_hover)

    def _set_hover(self, v):
        self._hover = float(v)
        self.update()

    def _animate_hover(self, on: bool):
        self._ha.stop()
        self._ha.setStartValue(self._hover)
        self._ha.setEndValue(1.0 if on else 0.0)
        self._ha.start()


class PrimaryButton(QPushButton, _HoverMixin):
    """Gold call-to-action."""

    def __init__(self, text: str, icon_name: str | None = None, parent=None):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self._init_hover()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(T.font(10, QFont.Weight.DemiBold))
        self.setMinimumHeight(42)
        fm = QFontMetrics(self.font())
        self.setMinimumWidth(fm.horizontalAdvance(text) + (64 if icon_name else 40))

    def enterEvent(self, e):
        self._animate_hover(True)

    def leaveEvent(self, e):
        self._animate_hover(False)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if not self.isEnabled():
            p.setBrush(QColor(255, 255, 255, 18))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 12, 12)
            p.setPen(QColor(T.FAINT))
            p.setFont(self.font())
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())
            return
        if self._hover > 0:
            for i, alpha in enumerate((26, 16, 8)):
                g = r.adjusted(-2 - i * 2, -2 - i * 2, 2 + i * 2, 2 + i * 2)
                p.setPen(QPen(T.qc(T.GOLD_LIGHT, int(alpha * self._hover)), 2))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(g, 13 + i * 2, 13 + i * 2)
        grad = QLinearGradient(r.topLeft(), r.bottomRight())
        k = 0.12 * self._hover
        grad.setColorAt(0, QColor(T.GOLD).lighter(int(100 + 100 * k)))
        grad.setColorAt(1, QColor(T.GOLD_LIGHT).lighter(int(100 + 60 * k)))
        if self.isDown():
            grad = QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0, QColor(T.GOLD).darker(112))
            grad.setColorAt(1, QColor(T.GOLD_LIGHT).darker(112))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(r, 12, 12)
        sheen = QLinearGradient(r.topLeft(), r.bottomLeft())
        sheen.setColorAt(0, QColor(255, 255, 255, 70))
        sheen.setColorAt(0.5, QColor(255, 255, 255, 0))
        p.setBrush(sheen)
        p.drawRoundedRect(r, 12, 12)
        p.setFont(self.font())
        fm = QFontMetrics(self.font())
        tw = fm.horizontalAdvance(self.text())
        iw = 18 if self.icon_name else 0
        gap = 8 if self.icon_name else 0
        x = r.center().x() - (tw + iw + gap) / 2
        if self.icon_name:
            icons.paint(p, self.icon_name, QRectF(x, r.center().y() - 9, 18, 18), T.BLACK, 1.9)
        p.setPen(QColor(T.BLACK))
        p.drawText(QRectF(x + iw + gap, r.top(), tw + 4, r.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())


class GhostButton(QPushButton, _HoverMixin):
    def __init__(self, text: str = "", icon_name: str | None = None, parent=None, compact: bool = False):
        super().__init__(text, parent)
        self.icon_name = icon_name
        self._init_hover()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(T.font(9.5, QFont.Weight.Medium))
        h = 34 if compact else 40
        self.setMinimumHeight(h)
        fm = QFontMetrics(self.font())
        w = fm.horizontalAdvance(text) + (26 if text else 0) + (24 if icon_name else 0) + (8 if text and icon_name else 0)
        self.setMinimumWidth(max(h, w + 8))

    def enterEvent(self, e):
        self._animate_hover(True)

    def leaveEvent(self, e):
        self._animate_hover(False)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        h = self._hover
        p.setBrush(QColor(255, 255, 255, int(10 + 10 * h)) if not self.isDown() else QColor(255, 255, 255, 30))
        p.setPen(QPen(_mix(QColor(255, 255, 255, 26), T.qc(T.GOLD, 170), h), 1))
        p.drawRoundedRect(r, 11, 11)
        color = _mix(QColor(T.WHITE), QColor(T.GOLD_LIGHT), h) if self.isEnabled() else QColor(T.FAINT)
        fm = QFontMetrics(self.font())
        tw = fm.horizontalAdvance(self.text()) if self.text() else 0
        iw = 18 if self.icon_name else 0
        gap = 8 if self.icon_name and self.text() else 0
        x = r.center().x() - (tw + iw + gap) / 2
        if self.icon_name:
            icons.paint(p, self.icon_name, QRectF(x, r.center().y() - 9, 18, 18), color.name())
        if self.text():
            p.setFont(self.font())
            p.setPen(color)
            p.drawText(QRectF(x + iw + gap, r.top(), tw + 4, r.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())


class IconButton(QAbstractButton, _HoverMixin):
    def __init__(self, icon_name: str, tooltip: str = "", size: int = 30, parent=None, danger: bool = False):
        super().__init__(parent)
        self.icon_name = icon_name
        self.danger = danger
        self._init_hover()
        self.setFixedSize(size, size)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, e):
        self._animate_hover(True)

    def leaveEvent(self, e):
        self._animate_hover(False)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        accent = T.DANGER if self.danger else T.GOLD_LIGHT
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(T.qc(accent, int(30 * self._hover)) if self._hover else QColor(255, 255, 255, 8))
        p.drawEllipse(r)
        s = r.width() * 0.55
        col = _mix(QColor(T.MUTED), QColor(accent), self._hover).name()
        icons.paint(p, self.icon_name, QRectF(r.center().x() - s / 2, r.center().y() - s / 2, s, s), col, 1.8)


# ---------------------------------------------------------------------------
# Labels, chips, keycaps
# ---------------------------------------------------------------------------
class Label(QLabel):
    def __init__(self, text: str = "", size: float = 9.5, weight=QFont.Weight.Normal, color: str = T.WHITE,
                 parent=None, family: str | None = None, italic: bool = False, wrap: bool = False,
                 spacing: float | None = None):
        super().__init__(text, parent)
        self.setFont(T.font(size, weight, family, italic, spacing))
        self.setStyleSheet(f"color: {color}; background: transparent;")
        self.setWordWrap(wrap)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", mode=Qt.TextElideMode.ElideMiddle, parent=None):
        super().__init__(parent)
        self._full = text
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def setText(self, text: str):  # noqa: N802
        self._full = text
        self.setToolTip(text)
        self._refresh()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refresh()

    def _refresh(self):
        fm = QFontMetrics(self.font())
        super().setText(fm.elidedText(self._full, self._mode, max(10, self.width())))


class Chip(QWidget):
    """Small rounded status pill with a dot."""

    def __init__(self, text: str, tone: str = "gold", parent=None, dot: bool = True):
        super().__init__(parent)
        self.text = text
        self.tone = tone
        self.dot = dot
        self.setFont(T.font(8.5, QFont.Weight.Medium))
        fm = QFontMetrics(self.font())
        self.setFixedHeight(26)
        self.setMinimumWidth(fm.horizontalAdvance(text) + (34 if dot else 22))

    def set(self, text: str, tone: str | None = None):
        self.text = text
        if tone:
            self.tone = tone
        fm = QFontMetrics(self.font())
        self.setMinimumWidth(fm.horizontalAdvance(text) + (34 if self.dot else 22))
        self.update()

    def color(self) -> str:
        return {"gold": T.GOLD_LIGHT, "ok": T.SUCCESS, "bad": T.DANGER, "muted": T.MUTED,
                "warn": T.WARNING}.get(self.tone, T.GOLD_LIGHT)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        c = QColor(self.color())
        bg = QColor(c)
        bg.setAlpha(22)
        bd = QColor(c)
        bd.setAlpha(70)
        p.setPen(QPen(bd, 1))
        p.setBrush(bg)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        x = r.left() + 11
        if self.dot:
            p.setPen(Qt.PenStyle.NoPen)
            glow = QColor(c)
            glow.setAlpha(60)
            p.setBrush(glow)
            p.drawEllipse(QPointF(x + 3, r.center().y()), 5, 5)
            p.setBrush(c)
            p.drawEllipse(QPointF(x + 3, r.center().y()), 3, 3)
            x += 12
        p.setPen(c if self.tone != "muted" else QColor(T.MUTED))
        p.setFont(self.font())
        p.drawText(QRectF(x, r.top(), r.right() - x - 8, r.height()), Qt.AlignmentFlag.AlignVCenter, self.text)


class KeyCap(QWidget):
    def __init__(self, text: str, parent=None, wide: bool = False):
        super().__init__(parent)
        self.text = text
        self.setFont(T.font(9, QFont.Weight.DemiBold))
        fm = QFontMetrics(self.font())
        self.setFixedSize(max(36, fm.horizontalAdvance(text) + 24) + (24 if wide else 0), 34)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 120))
        p.drawRoundedRect(r.translated(0, 3), 8, 8)
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor(46, 49, 60))
        g.setColorAt(1, QColor(30, 32, 40))
        p.setBrush(g)
        p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawRoundedRect(r, 8, 8)
        p.setPen(QColor(T.WHITE))
        p.setFont(self.font())
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text)


class Divider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0, QColor(255, 255, 255, 0))
        g.setColorAt(0.5, QColor(255, 255, 255, 22))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(self.rect(), g)


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------
class SlimProgress(QWidget):
    """Thin gold progress bar; animated shimmer when indeterminate."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value: float | None = 0.0
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._tick)
        self.setFixedHeight(6)

    def setValue(self, v: float | None):  # noqa: N802
        self.value = v
        if v is None and not self._timer.isActive():
            self._timer.start()
        elif v is not None and self._timer.isActive():
            self._timer.stop()
        self.update()

    def _tick(self):
        self._phase = (self._phase + 0.018) % 1.0
        self.update()

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        rad = r.height() / 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 18))
        p.drawRoundedRect(r, rad, rad)
        g = QLinearGradient(r.topLeft(), r.topRight())
        g.setColorAt(0, QColor(T.GOLD))
        g.setColorAt(1, QColor(T.GOLD_LIGHT))
        p.setBrush(g)
        if self.value is None:
            w = r.width() * 0.28
            x = -w + (r.width() + w) * self._phase
            p.setClipRect(r)
            p.drawRoundedRect(QRectF(x, 0, w, r.height()), rad, rad)
        else:
            p.drawRoundedRect(QRectF(0, 0, max(r.height(), r.width() * self.value), r.height()), rad, rad)


# ---------------------------------------------------------------------------
# Setting row
# ---------------------------------------------------------------------------
class SettingRow(QWidget):
    def __init__(self, title: str, description: str, control: QWidget, icon_name: str | None = None, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(14)
        if icon_name:
            ic = QLabel()
            ic.setPixmap(icons.pixmap(icon_name, T.GOLD, 20, self.devicePixelRatioF()))
            ic.setFixedWidth(24)
            lay.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(Label(title, 10, QFont.Weight.DemiBold))
        if description:
            texts.addWidget(Label(description, 8.8, color=T.MUTED, wrap=True))
        lay.addLayout(texts, 1)
        lay.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
