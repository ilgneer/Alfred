"""Original line-icon set (24×24, 1.6 px stroke) rendered crisply at any DPI."""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_P = {
    "home": '<path d="M4 11.5 12 5l8 6.5"/><path d="M6 10v9.5h12V10"/><path d="M10 19.5v-5h4v5"/>',
    "wheel": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3"/>'
             '<path d="M12 3.5V9M12 15v5.5M3.5 12H9M15 12h5.5"/>',
    "history": '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3"/><path d="M4 4.5V8h3.5"/><path d="M12 8v4.2l2.8 1.8"/>',
    "keyboard": '<rect x="3" y="6.5" width="18" height="11" rx="2.2"/>'
                '<path d="M7 10h.01M10 10h.01M13 10h.01M16 10h.01M7.5 14h9"/>',
    "settings": '<path d="M4.5 7H14M18 7h1.5M4.5 12H8M12 12h7.5M4.5 17H16"/><circle cx="16" cy="7" r="2"/>'
                '<circle cx="10" cy="12" r="2"/><circle cx="18" cy="17" r="2"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><path d="M12 7.7h.01"/>',
    "image": '<rect x="3.5" y="5" width="17" height="14" rx="2.5"/><circle cx="9" cy="10" r="1.6"/>'
             '<path d="M4 17l5-4.5 3.5 3 3-2.5 4.5 4"/>',
    "audio": '<path d="M9 17.5v-11l10-2v11"/><circle cx="6.8" cy="17.5" r="2.2"/><circle cx="16.8" cy="15.5" r="2.2"/>',
    "video": '<rect x="3" y="6" width="13" height="12" rx="2.5"/><path d="M16 10.5l5-3v9l-5-3"/>',
    "gif": '<rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M8 4v16M16 4v16M4 8h4M4 12h4M4 16h4M16 8h4M16 12h4M16 16h4"/>',
    "extract_audio": '<rect x="2.5" y="6" width="11" height="12" rx="2.2"/><path d="M7 10.2v3.6l3-1.8z"/>'
                     '<path d="M16.5 9.5v5M19 7.5v9M21.5 10.5v3"/>',
    "pdf": '<path d="M6.5 3.5h7.5l4.5 4.5v12.5h-12z"/><path d="M14 3.5V8h4.5"/><path d="M9 13.5h6M9 16.5h4"/>',
    "doc": '<path d="M6.5 3.5h7.5l4.5 4.5v12.5h-12z"/><path d="M14 3.5V8h4.5"/><path d="M9 12h6M9 15h6M9 18h3.5"/>',
    "file": '<path d="M6.5 3.5h7.5l4.5 4.5v12.5h-12z"/><path d="M14 3.5V8h4.5"/>',
    "text": '<path d="M5 6h14M5 10h14M5 14h10M5 18h7"/>',
    "markdown": '<rect x="2.5" y="6" width="19" height="12" rx="2.5"/><path d="M6 15V9l2.5 3L11 9v6M15.5 9v6M13.5 13l2 2 2-2"/>',
    "code": '<path d="M8.5 7 3.5 12l5 5M15.5 7l5 5-5 5M13.5 5l-3 14"/>',
    "book": '<path d="M4 5.5c2.5-1 5.5-1 8 .5v13c-2.5-1.5-5.5-1.5-8-.5z"/><path d="M20 5.5c-2.5-1-5.5-1-8 .5v13c2.5-1.5 5.5-1.5 8-.5z"/>',
    "slides": '<rect x="3" y="4.5" width="18" height="12" rx="2"/><path d="M12 16.5V20M8.5 20h7"/><path d="M7 12.5l3-3 2.5 2 4-4"/>',
    "sheet": '<rect x="3.5" y="4" width="17" height="16" rx="2.5"/><path d="M3.5 9h17M3.5 14.5h17M9.5 4v16"/>',
    "table": '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M3.5 10h17M3.5 14.5h17M9 5v14M14.5 5v14"/>',
    "pages": '<rect x="7.5" y="3.5" width="13" height="13" rx="2"/><path d="M4 7.5v10.5a2.5 2.5 0 0 0 2.5 2.5H17"/>'
             '<path d="M8 14l3.5-3 2.5 2 2-1.5 4 3"/>',
    "subtitle": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M7 12.5h3M12.5 12.5H17M7 15.5h6M15 15.5h2"/>',
    "archive": '<rect x="4" y="3.5" width="16" height="17" rx="2.5"/><path d="M12 3.5v2M12 7v2M12 10.5v2"/>'
               '<rect x="10.5" y="13.5" width="3" height="3.5" rx=".8"/>',
    "extract": '<path d="M4 10.5h16v8.5a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 19z"/><path d="M4 10.5l2.5-4h11l2.5 4"/>'
               '<path d="M12 18v-5.5M9.5 15l2.5-2.5 2.5 2.5"/>',
    "merge": '<rect x="3.5" y="3.5" width="7" height="9" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="9" rx="1.5"/>'
             '<path d="M7 12.5v2.5a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2v-2.5M12 17v3.5"/>',
    "folder": '<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2.5h7a2 2 0 0 1 2 2V17.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "close": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "alert": '<path d="M12 4 21 19.5H3z"/><path d="M12 10v4.5M12 17.2h.01"/>',
    "play": '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10 9.2v5.6l4.8-2.8z"/>',
    "volume": '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>',
    "mute": '<path d="M4 9.5h3.5L12 5.5v13l-4.5-4H4z"/><path d="M16 9.5l5 5M21 9.5l-5 5"/>',
    "mouse": '<rect x="7" y="3.5" width="10" height="17" rx="5"/><path d="M12 7v3"/>',
    "cursor": '<path d="M5 4l13 5.5-5.5 2-2 5.5z"/><path d="M13 13l5 5"/>',
    "power": '<path d="M12 4v7"/><path d="M7.2 7a7 7 0 1 0 9.6 0"/>',
    "external": '<path d="M14 4.5h5.5V10M19.5 4.5 11 13"/><path d="M18 13.5v4a2 2 0 0 1-2 2H6.5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>',
    "trash": '<path d="M5 7h14M10 7V4.5h4V7M7 7l1 12.5h8L17 7"/>',
    "sparkle": '<path d="M12 3.5l1.8 5.2 5.2 1.8-5.2 1.8L12 17.5l-1.8-5.2L5 10.5l5.2-1.8z"/>',
    "engine": '<rect x="6.5" y="6.5" width="11" height="11" rx="2"/>'
              '<path d="M9.5 3.5v3M14.5 3.5v3M9.5 17.5v3M14.5 17.5v3M3.5 9.5h3M3.5 14.5h3M17.5 9.5h3M17.5 14.5h3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "stop": '<circle cx="12" cy="12" r="8.5"/><path d="M9 9l6 6M15 9l-6 6"/>',
    "bell": '<path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.5 2h-15z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
    "refresh": '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5V8H16"/>',
    "shield": '<path d="M12 3.5l7 2.5v5.5c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "drop": '<path d="M12 3.5v11M7.5 10l4.5 4.5 4.5-4.5"/><path d="M4.5 15.5v3a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3"/>',
    "license": '<path d="M6.5 3.5h11v17h-11z"/><path d="M9.5 8h5M9.5 11.5h5"/><circle cx="12" cy="16" r="1.6"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    "heart": '<path d="M12 19.5s-7.5-4.4-7.5-10A4.2 4.2 0 0 1 12 7a4.2 4.2 0 0 1 7.5 2.5c0 5.6-7.5 10-7.5 10z"/>',
    "pix": '<path d="M12 3.5 20.5 12 12 20.5 3.5 12z"/><path d="M8 12h8M12 8v8"/>',
    "logs": '<path d="M5 5.5h14M5 10h14M5 14.5h9M5 19h6"/>',
}


def svg(name: str, color: str = "#F5F5F5", stroke: float = 1.6) -> bytes:
    body = _P.get(name, _P["file"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>').encode()


@lru_cache(maxsize=512)
def pixmap(name: str, color: str = "#F5F5F5", size: int = 20, dpr: float = 1.0, stroke: float = 1.6) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg(name, color, stroke)))
    px = max(1, round(size * dpr))
    image = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    p = QPainter(image)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p, QRectF(0, 0, px, px))
    p.end()
    pm = QPixmap.fromImage(image)
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str = "#F5F5F5", size: int = 20) -> QIcon:
    ic = QIcon()
    for dpr in (1.0, 1.25, 1.5, 2.0):
        ic.addPixmap(pixmap(name, color, size, dpr))
    return ic


@lru_cache(maxsize=512)
def _renderer(name: str, color: str, stroke: float) -> QSvgRenderer:
    return QSvgRenderer(QByteArray(svg(name, color, stroke)))


def paint(painter: QPainter, name: str, rect: QRectF, color: str, stroke: float = 1.6) -> None:
    """Draw an icon directly with a QPainter (vector, any scale)."""
    _renderer(name, color, round(stroke, 2)).render(painter, rect)


def names() -> list[str]:
    return sorted(_P)


def size(px: int) -> QSize:
    return QSize(px, px)
