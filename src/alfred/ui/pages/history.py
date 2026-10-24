"""Histórico de conversões."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QFont, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from alfred.core.history import HistoryEntry
from alfred.ui import icons
from alfred.ui import theme as T
from alfred.ui.pages.common import Page
from alfred.ui.widgets import Chip, ElidedLabel, GhostButton, GlassCard, IconButton, Label

STATUS = {"done": ("Concluído", "ok"), "partial": ("Com avisos", "warn"), "failed": ("Falhou", "bad"),
          "cancelled": ("Cancelado", "muted")}


def when(ts: float) -> str:
    lt = time.localtime(ts)
    today = time.localtime()
    if lt.tm_yday == today.tm_yday and lt.tm_year == today.tm_year:
        return time.strftime("hoje, %H:%M", lt)
    return time.strftime("%d/%m/%Y %H:%M", lt)


class StatusDot(QWidget):
    def __init__(self, ok: bool, parent=None):
        super().__init__(parent)
        self.ok = ok
        self.setFixedSize(34, 34)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        col = T.SUCCESS if self.ok else T.DANGER
        p.setPen(QPen(T.qc(col, 90), 1))
        p.setBrush(T.qc(col, 28))
        p.drawEllipse(r)
        s = 16
        icons.paint(p, "check" if self.ok else "alert", QRectF(r.center().x() - s / 2, r.center().y() - s / 2, s, s),
                    col, 2)


class HistoryRow(QWidget):
    def __init__(self, entry: HistoryEntry, app, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 6, 4, 6)
        lay.setSpacing(14)
        ok = entry.status in ("done", "partial")
        lay.addWidget(StatusDot(ok))
        col = QVBoxLayout()
        col.setSpacing(3)
        names = [Path(s).name for s in entry.sources]
        title = names[0] if len(names) == 1 else f"{names[0]} + {len(names) - 1}" if names else "—"
        t = ElidedLabel(title)
        t.setFont(T.font(9.8, QFont.Weight.DemiBold))
        col.addWidget(t)
        detail = f"{when(entry.finished)} · {entry.duration:.1f} s".replace(".", ",")
        if entry.outputs:
            detail += f" · {len(entry.outputs)} {'saída' if len(entry.outputs) == 1 else 'saídas'}"
        if entry.errors:
            detail += f" · {entry.errors[0]}"
        d = ElidedLabel(detail, Qt.TextElideMode.ElideRight)
        d.setFont(T.font(8.6))
        d.setStyleSheet(f"color: {T.MUTED};")
        col.addWidget(d)
        lay.addLayout(col, 1)
        label, tone = STATUS.get(entry.status, ("?", "muted"))
        lay.addWidget(Chip(f"→ {entry.target}", "gold", dot=False))
        lay.addWidget(Chip(label, tone))
        outputs = [Path(o) for o in entry.outputs if Path(o).exists()]
        if outputs:
            b1 = IconButton("external", "Abrir", 32)
            b1.clicked.connect(lambda: app.open_path(outputs[0]))
            b2 = IconButton("folder", "Mostrar na pasta", 32)
            b2.clicked.connect(lambda: app.reveal(outputs[0]))
            lay.addWidget(b1)
            lay.addWidget(b2)


class HistoryPage(Page):
    def __init__(self, app, parent=None):
        super().__init__("Histórico", "As últimas 500 conversões ficam guardadas só neste computador.", parent)
        self.app = app
        bar = QHBoxLayout()
        self.count = Label("", 9.5, color=T.MUTED)
        bar.addWidget(self.count)
        bar.addStretch(1)
        self.clear_btn = GhostButton("Limpar histórico", "trash", compact=True)
        self.clear_btn.clicked.connect(self._clear)
        bar.addWidget(self.clear_btn)
        self.body.addLayout(bar)
        self.card = GlassCard(padding=12)
        self.list = QVBoxLayout()
        self.list.setSpacing(0)
        self.card.lay.addLayout(self.list)
        self.body.addWidget(self.card)
        self.body.addStretch(1)
        app.history_changed.connect(self.on_show)

    def on_show(self):
        while self.list.count():
            item = self.list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        entries = self.app.history.entries()[:200]
        self.count.setText(f"{len(self.app.history.entries())} registros" if entries else "")
        self.clear_btn.setEnabled(bool(entries))
        if not entries:
            self.list.addWidget(Label("Nada por aqui ainda. Suas conversões aparecerão nesta lista.", 10,
                                      color=T.MUTED))
            return
        for e in entries:
            self.list.addWidget(HistoryRow(e, self.app))

    def _clear(self):
        box = QMessageBox(self)
        box.setWindowTitle("Limpar histórico")
        box.setText("Apagar a lista de conversões? Os arquivos convertidos não serão apagados.")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.button(QMessageBox.StandardButton.Yes).setText("Limpar")
        box.button(QMessageBox.StandardButton.No).setText("Cancelar")
        if box.exec() == QMessageBox.StandardButton.Yes:
            self.app.history.clear()
            self.on_show()
