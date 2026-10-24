"""Main window: glass sidebar + animated pages."""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QUrl,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QDesktopServices, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractButton,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from alfred import DEVELOPER, YOUTUBE_URL
from alfred.core import paths
from alfred.platform import win32
from alfred.ui import icons
from alfred.ui import theme as T
from alfred.ui.pages.about import AboutPage
from alfred.ui.pages.history import HistoryPage
from alfred.ui.pages.home import HomePage
from alfred.ui.pages.settings import SettingsPage
from alfred.ui.pages.shortcuts import ShortcutsPage
from alfred.ui.widgets import Backdrop, Chip, Label

NAV = [("home", "Início", "home"), ("history", "Histórico", "history"), ("shortcuts", "Atalhos", "keyboard"),
       ("settings", "Configurações", "settings"), ("about", "Sobre", "info")]


class NavButton(QAbstractButton):
    def __init__(self, key: str, text: str, icon_name: str, parent=None):
        super().__init__(parent)
        self.key = key
        self.label = text
        self.icon_name = icon_name
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(44)
        self._hover = 0.0
        self._ha = QVariantAnimation(self)
        self._ha.setDuration(150)
        self._ha.valueChanged.connect(self._set_hover)
        self.setFont(T.font(10, QFont.Weight.Medium))

    def _set_hover(self, v):
        self._hover = float(v)
        self.update()

    def enterEvent(self, e):
        self._ha.stop()
        self._ha.setStartValue(self._hover)
        self._ha.setEndValue(1.0)
        self._ha.start()

    def leaveEvent(self, e):
        self._ha.stop()
        self._ha.setStartValue(self._hover)
        self._ha.setEndValue(0.0)
        self._ha.start()

    def sizeHint(self):
        return QSize(200, 44)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0, 2, 0, -2)
        if self.isChecked():
            g = QLinearGradient(r.topLeft(), r.topRight())
            g.setColorAt(0, T.qc(T.GOLD, 46))
            g.setColorAt(1, T.qc(T.GOLD, 6))
            p.setBrush(g)
            p.setPen(QPen(T.qc(T.GOLD, 60), 1))
            p.drawRoundedRect(r, 12, 12)
        elif self._hover > 0:
            p.setBrush(QColor(255, 255, 255, int(12 * self._hover)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(r, 12, 12)
        col = T.GOLD_LIGHT if self.isChecked() else (T.WHITE if self._hover > 0.5 else "#C9CBD2")
        icons.paint(p, self.icon_name, QRectF(r.left() + 14, r.center().y() - 10, 20, 20),
                    T.GOLD_LIGHT if self.isChecked() else T.MUTED if self._hover < 0.5 else T.WHITE, 1.7)
        p.setPen(QColor(col))
        p.setFont(self.font())
        p.drawText(QRectF(r.left() + 46, r.top(), r.width() - 50, r.height()),
                   Qt.AlignmentFlag.AlignVCenter, self.label)


class Sidebar(QWidget):
    page_selected = Signal(str)

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setFixedWidth(236)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 22, 18, 18)
        lay.setSpacing(4)
        brand = QHBoxLayout()
        brand.setSpacing(12)
        logo = QLabel()
        pm = QPixmap(str(paths.asset_path("alfred_tray.png")))
        dpr = self.devicePixelRatioF()
        pm = pm.scaled(int(44 * dpr), int(44 * dpr), Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        logo.setPixmap(pm)
        logo.setFixedSize(46, 46)
        brand.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addWidget(Label("ALFRED", 14, QFont.Weight.DemiBold, family=T.DISPLAY, spacing=122))
        col.addWidget(Label("Conversor universal", 8.4, color=T.MUTED))
        brand.addLayout(col, 1)
        lay.addLayout(brand)
        lay.addSpacing(26)
        self.buttons: dict[str, NavButton] = {}
        for key, text, icon_name in NAV:
            b = NavButton(key, text, icon_name)
            b.clicked.connect(lambda _c=False, k=key: self.select(k))
            lay.addWidget(b)
            self.buttons[key] = b
        lay.addStretch(1)
        self.chip = Chip("Gesto ativo", "ok")
        lay.addWidget(self.chip, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addSpacing(10)
        credit = Label(f"por {DEVELOPER}", 8.6, color=T.MUTED)
        credit.setCursor(Qt.CursorShape.PointingHandCursor)
        credit.setToolTip(YOUTUBE_URL)
        credit.mousePressEvent = lambda e: QDesktopServices.openUrl(QUrl(YOUTUBE_URL))
        lay.addWidget(credit)
        self.select("home", emit=False)

    def select(self, key: str, emit: bool = True):
        for k, b in self.buttons.items():
            b.setChecked(k == key)
        if emit:
            self.page_selected.emit(key)

    def set_gesture_state(self, text: str, tone: str):
        self.chip.set(text, tone)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        p.fillRect(r, QColor(21, 23, 30, 150))
        g = QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QColor(255, 255, 255, 10))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(r, g)
        line = QLinearGradient(r.topRight(), r.bottomRight())
        line.setColorAt(0, T.qc(T.GOLD, 0))
        line.setColorAt(0.3, T.qc(T.GOLD, 70))
        line.setColorAt(1, T.qc(T.GOLD, 0))
        p.setPen(QPen(line, 1))
        p.drawLine(QPointF(r.right() - 0.5, r.top()), QPointF(r.right() - 0.5, r.bottom()))


class MainWindow(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Alfred")
        self.setMinimumSize(860, 560)
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is not None:
            self.resize(min(1140, int(screen.width() * 0.9)), min(760, int(screen.height() * 0.9)))
        else:
            self.resize(1140, 760)
        self.setAcceptDrops(False)  # the drop zone handles drops
        self._allow_close = False
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.backdrop = Backdrop(self)
        self.backdrop.lower()
        self.sidebar = Sidebar(app)
        root.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self.pages = {
            "home": HomePage(app),
            "history": HistoryPage(app),
            "shortcuts": ShortcutsPage(app),
            "settings": SettingsPage(app),
            "about": AboutPage(app),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        self.sidebar.page_selected.connect(self.show_page)
        self._anim = None
        self._dark_applied = False

    def resizeEvent(self, e):
        self.backdrop.setGeometry(self.rect())
        super().resizeEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        if not self._dark_applied:
            win32.set_dark_titlebar(int(self.winId()))
            self._dark_applied = True
        current = self.stack.currentWidget()
        if hasattr(current, "on_show"):
            current.on_show()

    def show_page(self, key: str):
        page = self.pages.get(key)
        if page is None:
            return
        self.sidebar.select(key, emit=False)
        if self.stack.currentWidget() is page:
            page.on_show()
            return
        page.on_show()
        self.stack.setCurrentWidget(page)
        if self.app.settings.value.reduce_motion:
            return
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        fade = QPropertyAnimation(effect, b"opacity", page)
        fade.setDuration(220)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        slide = QPropertyAnimation(page, b"pos", page)
        slide.setDuration(260)
        end = page.pos()
        slide.setStartValue(end + QPoint(0, 14))
        slide.setEndValue(end)
        slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.finished.connect(lambda: page.setGraphicsEffect(None))
        group.start()
        self._anim = group

    def bring_to_front(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        win32.force_foreground(int(self.winId()))

    def allow_close(self):
        self._allow_close = True

    def closeEvent(self, e):
        if self._allow_close or not self.app.has_tray:
            e.accept()
            if not self.app.has_tray:
                self.app.quit()
            return
        e.ignore()
        self.hide()
        self.app.window_hidden_to_tray()
