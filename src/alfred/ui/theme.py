"""Visual identity: palette, typography and the global stylesheet."""
from __future__ import annotations

import logging

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

from alfred.core import paths

log = logging.getLogger(__name__)

# Palette ---------------------------------------------------------------------
BLACK = "#08090D"
GRAPHITE = "#15171E"
GRAPHITE_2 = "#1C1F28"
GOLD = "#D4AF37"
GOLD_LIGHT = "#FFD84D"
WHITE = "#F5F5F5"
MUTED = "#9A9DA8"
FAINT = "#5E6270"
SUCCESS = "#5BD69A"
DANGER = "#FF6B6B"
WARNING = "#F2B84B"


def qc(hex_color: str, alpha: int = 255) -> QColor:
    """QColor from hex with an alpha in 0..255."""
    c = QColor(hex_color)
    c.setAlpha(max(0, min(255, int(alpha))))
    return c


# Typography ------------------------------------------------------------------
SANS = "Inter"
DISPLAY = "Inter Display"
SERIF_ITALIC = "Lora"
_loaded = False


def load_fonts() -> None:
    global _loaded, SANS, DISPLAY
    if _loaded:
        return
    folder = paths.asset_path("fonts")
    families = set()
    for f in sorted(folder.glob("*.[ot]tf")):
        fid = QFontDatabase.addApplicationFont(str(f))
        if fid >= 0:
            families.update(QFontDatabase.applicationFontFamilies(fid))
    if "Inter" not in families:
        SANS = "Segoe UI Variable Text"
    if "Inter Display" not in families:
        DISPLAY = SANS
    log.debug("Fontes carregadas: %s", sorted(families))
    _loaded = True


def font(size: float = 10, weight: QFont.Weight = QFont.Weight.Normal, family: str | None = None,
         italic: bool = False, spacing: float | None = None) -> QFont:
    f = QFont(family or SANS)
    f.setPointSizeF(size)
    f.setWeight(weight)
    f.setItalic(italic)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    if spacing is not None:
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, spacing)
    return f


def apply(app: QApplication) -> None:
    load_fonts()
    app.setStyle("Fusion")
    app.setFont(font(9.5))
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BLACK))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(WHITE))
    pal.setColor(QPalette.ColorRole.Base, QColor(GRAPHITE))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(GRAPHITE_2))
    pal.setColor(QPalette.ColorRole.Text, QColor(WHITE))
    pal.setColor(QPalette.ColorRole.Button, QColor(GRAPHITE))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(WHITE))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(GOLD))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(BLACK))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(GRAPHITE))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(WHITE))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(FAINT))
    pal.setColor(QPalette.ColorRole.Link, QColor(GOLD_LIGHT))
    app.setPalette(pal)
    app.setStyleSheet(STYLESHEET)


STYLESHEET = f"""
QWidget {{ color: {WHITE}; }}
QToolTip {{
    background: {GRAPHITE}; color: {WHITE}; border: 1px solid rgba(212,175,55,0.35);
    border-radius: 8px; padding: 6px 10px;
}}
QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 4px 2px 4px 0; }}
QScrollBar::handle:vertical {{ background: rgba(245,245,245,0.12); border-radius: 4px; min-height: 40px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(212,175,55,0.45); }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
QScrollBar:horizontal {{ height: 0; }}
QMenu {{
    background: {GRAPHITE}; border: 1px solid rgba(212,175,55,0.28); border-radius: 12px; padding: 6px;
}}
QMenu::item {{ padding: 8px 28px 8px 14px; border-radius: 8px; color: {WHITE}; }}
QMenu::item:selected {{ background: rgba(212,175,55,0.16); color: {GOLD_LIGHT}; }}
QMenu::item:disabled {{ color: {FAINT}; }}
QMenu::separator {{ height: 1px; background: rgba(245,245,245,0.08); margin: 6px 8px; }}
QMenu::indicator {{ width: 14px; height: 14px; margin-left: 6px; }}
QComboBox {{
    background: rgba(245,245,245,0.05); border: 1px solid rgba(245,245,245,0.10); border-radius: 10px;
    padding: 7px 12px; min-width: 170px; color: {WHITE};
}}
QComboBox:hover {{ border-color: rgba(212,175,55,0.55); }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: {GRAPHITE}; border: 1px solid rgba(212,175,55,0.3); border-radius: 10px; padding: 4px;
    selection-background-color: rgba(212,175,55,0.18); selection-color: {GOLD_LIGHT}; outline: none;
}}
QLineEdit {{
    background: rgba(245,245,245,0.05); border: 1px solid rgba(245,245,245,0.10); border-radius: 10px;
    padding: 7px 12px; color: {WHITE}; selection-background-color: {GOLD}; selection-color: {BLACK};
}}
QLineEdit:focus {{ border-color: rgba(212,175,55,0.7); }}
QSlider::groove:horizontal {{ height: 4px; background: rgba(245,245,245,0.10); border-radius: 2px; }}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {GOLD}, stop:1 {GOLD_LIGHT}); border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {WHITE}; border: 3px solid {GOLD}; width: 12px; height: 12px; margin: -7px 0; border-radius: 9px;
}}
QSlider::handle:horizontal:hover {{ border-color: {GOLD_LIGHT}; }}
QMessageBox {{ background: {GRAPHITE}; }}
QMessageBox QPushButton {{
    background: rgba(245,245,245,0.06); border: 1px solid rgba(245,245,245,0.12); border-radius: 9px;
    padding: 7px 18px; min-width: 80px;
}}
QMessageBox QPushButton:hover {{ border-color: {GOLD}; color: {GOLD_LIGHT}; }}
"""
