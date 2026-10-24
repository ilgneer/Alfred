"""Shared building blocks for pages."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from alfred.ui import theme as T
from alfred.ui.widgets import Label


class Page(QWidget):
    """Scrollable page with a title and subtitle."""

    def __init__(self, title: str, subtitle: str = "", parent=None, scroll: bool = True):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.body = QVBoxLayout(content)
        self.body.setContentsMargins(36, 30, 36, 30)
        self.body.setSpacing(18)
        head = QVBoxLayout()
        head.setSpacing(4)
        self.title_label = Label(title, 20, QFont.Weight.DemiBold, family=T.DISPLAY)
        head.addWidget(self.title_label)
        if subtitle:
            head.addWidget(Label(subtitle, 10, color=T.MUTED, wrap=True))
        self.body.addLayout(head)
        if scroll:
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setFrameShape(QScrollArea.Shape.NoFrame)
            area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            area.setWidget(content)
            area.viewport().setAutoFillBackground(False)
            outer.addWidget(area)
        else:
            outer.addWidget(content)

    def on_show(self) -> None:
        """Called when the page becomes visible."""


def section_title(text: str) -> Label:
    lab = Label(text.upper(), 8.2, QFont.Weight.DemiBold, color=T.GOLD, spacing=112)
    lab.setContentsMargins(2, 6, 0, 0)
    return lab
