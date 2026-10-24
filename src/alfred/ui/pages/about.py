"""Sobre o Alfred."""
from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout

from alfred import DEVELOPER, SLOGAN, YOUTUBE_URL, __version__
from alfred.core import engines, paths
from alfred.ui import theme as T
from alfred.ui.pages.common import Page, section_title
from alfred.ui.pages.home import LogoOrb
from alfred.ui.widgets import Divider, GhostButton, GlassCard, Label, PrimaryButton


class AboutPage(Page):
    def __init__(self, app, parent=None):
        super().__init__("Sobre o Alfred", "", parent)
        hero = GlassCard(radius=22, accent=True, padding=30)
        row = QHBoxLayout()
        row.setSpacing(30)
        row.addWidget(LogoOrb(190), 0, Qt.AlignmentFlag.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(6)
        col.addStretch(1)
        col.addWidget(Label("ALFRED", 30, QFont.Weight.DemiBold, family=T.DISPLAY, spacing=118))
        col.addWidget(Label("Conversor universal de arquivos para Windows", 11, color=T.GOLD_LIGHT))
        col.addSpacing(6)
        col.addWidget(Label(f"“{SLOGAN}”", 13, family=T.SERIF_ITALIC, italic=True, color=T.WHITE, wrap=True))
        col.addSpacing(10)
        col.addWidget(Label(f"Versão {__version__} · Edição {paths.edition()} · {engines.python_runtime()}", 9,
                            color=T.MUTED))
        col.addStretch(1)
        row.addLayout(col, 1)
        hero.lay.addLayout(row)
        self.body.addWidget(hero)

        self.body.addWidget(section_title("Desenvolvedor"))
        dev = GlassCard()
        drow = QHBoxLayout()
        dcol = QVBoxLayout()
        dcol.setSpacing(2)
        dcol.addWidget(Label(DEVELOPER, 14, QFont.Weight.DemiBold))
        dcol.addWidget(Label("Criado e mantido por @ilgn3r. Acompanhe novidades e tutoriais no canal.", 9.5,
                             color=T.MUTED, wrap=True))
        drow.addLayout(dcol, 1)
        yt = PrimaryButton("Canal no YouTube", "play")
        yt.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(YOUTUBE_URL)))
        drow.addWidget(yt)
        dev.lay.addLayout(drow)
        self.body.addWidget(dev)

        self.body.addWidget(section_title("Licenças"))
        lic = GlassCard()
        lic.lay.addWidget(Label(
            "O código do Alfred é software livre sob a licença GNU AGPL-3.0: você pode usar, estudar, "
            "modificar e redistribuir — inclusive vender —, desde que o código-fonte acompanhe. "
            "O logotipo e a arte do personagem não fazem parte dessa licença.", 9.5, color=T.MUTED, wrap=True))
        lic.lay.addWidget(Label(
            "Motores incluídos: FFmpeg (GPL), Pandoc (GPL), LibreOffice (MPL-2.0, edição completa), 7-Zip (LGPL + "
            "restrição unRAR), PyMuPDF (AGPL), Qt/PySide6 (LGPL), fontes Inter e Lora (OFL).", 9.5, color=T.MUTED,
            wrap=True))
        lic.lay.addWidget(Divider())
        brow = QHBoxLayout()
        b1 = GhostButton("Licenças de terceiros", "license", compact=True)
        b1.clicked.connect(lambda: app.open_path(paths.install_dir() / "licenses"))
        b2 = GhostButton("Código-fonte", "code", compact=True)
        b2.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(app.source_url)))
        brow.addWidget(b1)
        brow.addWidget(b2)
        brow.addStretch(1)
        lic.lay.addLayout(brow)
        lic.lay.addWidget(Label("Projeto independente, sem afiliação com DC Comics, Warner Bros. ou qualquer marca "
                                "de terceiros.", 8.5, color=T.FAINT, wrap=True))
        self.body.addWidget(lic)
        self.body.addStretch(1)
