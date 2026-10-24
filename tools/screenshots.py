"""Renders the real Qt interface off-screen and saves PNG screenshots.

    python tools/screenshots.py [pasta_de_saida]

Used to document the UI (docs/screenshots) and to visually review changes
without a Windows desktop. The wheel is composited over a sample "desktop"
so the transparency around it is visible.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_tmp = tempfile.mkdtemp(prefix="alfred-shots-")
os.environ["ALFRED_CONFIG_DIR"] = str(Path(_tmp) / "cfg")
os.environ["ALFRED_DATA_DIR"] = str(Path(_tmp) / "data")

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QRadialGradient  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from alfred.core import engines as engines_mod  # noqa: E402
from alfred.core.history import History, HistoryEntry  # noqa: E402
from alfred.ui import theme  # noqa: E402


def desktop(w: int, h: int) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor("#24324a"))
    g.setColorAt(0.5, QColor("#3c4f6e"))
    g.setColorAt(1, QColor("#1b2233"))
    p.fillRect(img.rect(), g)
    r = QRadialGradient(QPointF(w * 0.2, h * 0.3), w * 0.4)
    r.setColorAt(0, QColor(120, 160, 220, 120))
    r.setColorAt(1, QColor(120, 160, 220, 0))
    p.fillRect(img.rect(), r)
    # a fake Explorer window behind the wheel
    p.setBrush(QColor(32, 32, 32, 245))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(40, 40, w * 0.62, h - 80), 10, 10)
    p.setBrush(QColor(45, 45, 45))
    p.drawRect(QRectF(40, 40, w * 0.62, 44))
    p.setPen(QColor(220, 220, 220))
    f = theme.font(9)
    p.setFont(f)
    for i, name in enumerate(["Relatório 2026.pdf", "Foto da viagem.heic", "Entrevista.mp4", "Planilha.xlsx",
                              "Apresentação.pptx", "Legendas.srt", "Backup.rar"]):
        y = 110 + i * 34
        p.setBrush(QColor(70, 110, 170, 120) if i == 1 else QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(52, y - 20, w * 0.6 - 24, 30))
        p.setPen(QColor(230, 230, 230))
        p.drawText(QPointF(90, y), name)
    p.end()
    return img


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    theme.apply(app)
    hist = History()

    now = time.time()
    samples = [("Foto da viagem.heic", "JPG", "done", 1), ("Entrevista.mp4", "MP3 só áudio", "done", 1),
               ("Contrato.docx", "PDF", "done", 1), ("Relatório anual.pdf", "DOCX", "done", 1),
               ("Backup.rar", "Extrair aqui", "failed", 0), ("Planilha.xls", "XLSX", "done", 1)]
    for i, (name, target, status, n) in enumerate(samples):
        hist.add(HistoryEntry(id=str(i), started=now - 3600 + i * 60, finished=now - 3590 + i * 61, target=target,
                              status=status, sources=[f"C:/Users/voce/Documentos/{name}"],
                              outputs=[f"C:/Users/voce/Documentos/{name}.out"] * n,
                              errors=[] if n else ["Arquivo protegido por senha não é suportado."]))
    from alfred.app import AlfredApp

    ctrl = AlfredApp(app, background=True)
    ctrl._on_engines(engines_mod.get())
    win = ctrl.window
    win.resize(1180, 780)
    win.show()
    for key in ("home", "history", "shortcuts", "settings", "about"):
        win.show_page(key)
        t_end = time.time() + 0.5
        while time.time() < t_end:
            app.processEvents()
        page = win.pages[key]
        if hasattr(page, "on_show"):
            page.on_show()
        app.processEvents()
        img = win.grab()
        img.save(str(out / f"janela_{key}.png"))
        if key == "settings":
            # full scrolled settings page
            content = page.findChild(type(page.body.parentWidget()))
            _ = content
    # wheel -------------------------------------------------------------------
    from alfred.ui.radial import RadialMenu

    sample_dir = Path(_tmp) / "amostras"
    sample_dir.mkdir()
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (640, 420), (30, 60, 90))
    d = ImageDraw.Draw(im)
    for i in range(0, 640, 8):
        d.line([(i, 420), (320, 160)], fill=(240, 180 - i // 8, 60))
    d.ellipse((380, 40, 520, 180), fill=(255, 220, 120))
    photo = sample_dir / "Foto da viagem.jpg"
    im.save(photo)
    pdf = sample_dir / "Relatório anual 2026.pdf"
    import pymupdf

    doc = pymupdf.open()
    pg = doc.new_page()
    pg.insert_text((72, 100), "Relatório anual", fontsize=28)
    doc.save(str(pdf))
    video = sample_dir / "Entrevista.mp4"
    video.write_bytes(b"0" * 1000)
    for name, files, hover in (("roda_imagem", [photo], -1), ("roda_imagem_hover", [photo], 1),
                               ("roda_pdf_hover", [pdf], 0), ("roda_video", [video], 3)):
        items = ctrl.build_items(files)
        wheel = RadialMenu()
        wheel.open_at(QPoint(600, 400), items, files, "drag" if "video" in name else "click")
        for _ in range(40):
            app.processEvents()
            wheel._tick()
        wheel._open_t = 1.0
        wheel._spin = 30
        if hover >= 0:
            wheel.hover = hover
            wheel._hover_t = [1.0 if i == hover else 0.0 for i in range(len(items))]
        if name == "roda_imagem":
            from alfred.ui.radial import load_thumbnail

            wheel._thumb = load_thumbnail(photo, 64)
        wheel.update()
        app.processEvents()
        shot = wheel.grab().toImage()
        bg = desktop(900, 620)
        p = QPainter(bg)
        p.drawImage(QPointF(330, 70), shot)
        p.end()
        bg.save(str(out / f"{name}.png"))
        wheel.hide()
        wheel.deleteLater()
    # toast -----------------------------------------------------------------------
    from alfred.ui.toast import Toast

    t = Toast("success")
    from alfred.ui import theme as T

    t.set_icon("check", T.SUCCESS)
    t.set_text("Pronto, senhor.", "1 arquivo criado em PNG")
    t.set_actions([("Abrir", "external", lambda: None), ("Mostrar na pasta", "folder", lambda: None)])
    t.adjustSize()
    t.show()
    app.processEvents()
    bg = desktop(520, 220)
    p = QPainter(bg)
    p.drawImage(QPointF(60, 30), t.grab().toImage())
    p.end()
    bg.save(str(out / "notificacao.png"))
    t2 = Toast("info")
    t2.set_icon("video", T.GOLD)
    t2.set_text("Entrevista.mp4", "Convertendo → WEBM · 42%")
    t2.progress.show()
    t2.progress.setValue(0.42)
    t2.set_actions([("Cancelar", "stop", lambda: None)])
    t2.adjustSize()
    t2.show()
    app.processEvents()
    bg = desktop(520, 220)
    p = QPainter(bg)
    p.drawImage(QPointF(60, 30), t2.grab().toImage())
    p.end()
    bg.save(str(out / "notificacao_progresso.png"))
    ctrl._cleanup()
    print("capturas em", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "screenshots")
