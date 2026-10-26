"""“Apoie o projeto via Pix” — glass dialog with QR code and Pix copia e cola."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from alfred import support
from alfred.core import paths
from alfred.ui import theme as T
from alfred.ui.widgets import GhostButton, IconButton, Label, PrimaryButton


class QrCard(QWidget):
    """The QR code on a white rounded card (scanners need contrast)."""

    def __init__(self, size: int = 220, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.qr = QPixmap(str(paths.asset_path("pix_qr.png")))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(QPen(T.qc(T.GOLD, 200), 2))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(r, 18, 18)
        inner = r.adjusted(12, 12, -12, -12)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)  # keep modules crisp
        p.drawPixmap(inner, self.qr, QRectF(self.qr.rect()))


class SupportDialog(QDialog):
    copied = Signal()

    def __init__(self, app, parent=None, from_popup: bool = False):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.app = app
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setWindowTitle(support.TITLE)
        self.setFixedWidth(720)

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 28, 28)
        root.setSpacing(16)

        top = QHBoxLayout()
        title = Label(support.TITLE, 20, QFont.Weight.DemiBold, family=T.DISPLAY)
        top.addWidget(title)
        top.addStretch(1)
        close = IconButton("close", "Fechar", 32)
        close.clicked.connect(self.reject)
        top.addWidget(close)
        root.addLayout(top)

        body = QHBoxLayout()
        body.setSpacing(26)
        texts = QVBoxLayout()
        texts.setSpacing(10)
        texts.addWidget(Label(support.MESSAGE, 10, color=T.WHITE, wrap=True))
        texts.addWidget(Label(support.MESSAGE_2, 10, color=T.MUTED, wrap=True))
        texts.addWidget(Label("“Algumas tarefas é melhor deixar para o Alfred.”", 10.5, family=T.SERIF_ITALIC,
                              italic=True, color=T.GOLD_LIGHT, wrap=True))
        texts.addStretch(1)
        body.addLayout(texts, 1)
        qr_col = QVBoxLayout()
        qr_col.setSpacing(6)
        qr_col.addWidget(QrCard(220), 0, Qt.AlignmentFlag.AlignHCenter)
        cap = Label(f"Pix para {support.PIX_RECEIVER}", 8.8, color=T.MUTED)
        cap.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        qr_col.addWidget(cap)
        body.addLayout(qr_col)
        root.addLayout(body)

        root.addWidget(Label("PIX COPIA E COLA", 8.2, QFont.Weight.DemiBold, color=T.GOLD, spacing=112))
        row = QHBoxLayout()
        row.setSpacing(10)
        self.code = QLineEdit(support.PIX_PAYLOAD)
        self.code.setReadOnly(True)
        self.code.setCursorPosition(0)
        self.code.setFont(T.font(9))
        self.code.setMinimumHeight(40)
        row.addWidget(self.code, 1)
        self.copy_btn = PrimaryButton("Copiar código Pix", "copy")
        self.copy_btn.setMinimumWidth(200)
        self.copy_btn.clicked.connect(self.copy_code)
        row.addWidget(self.copy_btn)
        root.addLayout(row)
        self.feedback = Label("", 9, QFont.Weight.Medium, color=T.SUCCESS)
        root.addWidget(self.feedback)

        bottom = QHBoxLayout()
        self.dont_show = QCheckBox("Não mostrar ao abrir o Alfred")
        self.dont_show.setStyleSheet(f"QCheckBox {{ color: {T.MUTED}; spacing: 8px; }}")
        self.dont_show.setChecked(not app.settings.value.support_popup)
        self.dont_show.setVisible(from_popup)
        bottom.addWidget(self.dont_show)
        bottom.addStretch(1)
        later = GhostButton("Agora não" if from_popup else "Fechar", compact=True)
        later.clicked.connect(self.reject)
        bottom.addWidget(later)
        root.addLayout(bottom)
        root.addWidget(Label(support.FOOTNOTE, 8.4, color=T.FAINT, wrap=True))
        self.finished.connect(self._save_choice)
        self._from_popup = from_popup

    def copy_code(self):
        QGuiApplication.clipboard().setText(support.PIX_PAYLOAD)
        self.feedback.setText("Código Pix copiado! Agora é só colar no app do seu banco. Obrigado, de coração.")
        self.copy_btn.setText("Copiado ✓")
        self.app.sounds.play("success")
        self.copied.emit()
        QTimer.singleShot(2500, lambda: self.copy_btn.setText("Copiar código Pix"))

    def _save_choice(self, _result):
        if self._from_popup:
            self.app.update_setting(support_popup=not self.dont_show.isChecked())

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        parent = self.parentWidget()
        if parent is not None and parent.isVisible():
            geo = parent.frameGeometry()
            self.move(geo.center() - self.rect().center())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(8, 8, -8, -8)
        for i in range(8, 0, -1):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 9))
            p.drawRoundedRect(r.adjusted(-i, -i + 3, i, i + 3), 24 + i, 24 + i)
        path = QPainterPath()
        path.addRoundedRect(r, 24, 24)
        p.fillPath(path, QColor(14, 15, 20, 246))
        glow = QLinearGradient(r.topRight(), r.bottomLeft())
        glow.setColorAt(0, T.qc(T.GOLD, 40))
        glow.setColorAt(0.5, T.qc(T.GOLD, 0))
        p.fillPath(path, glow)
        border = QLinearGradient(r.topLeft(), r.bottomRight())
        border.setColorAt(0, T.qc(T.GOLD, 170))
        border.setColorAt(1, QColor(255, 255, 255, 25))
        p.setPen(QPen(border, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

