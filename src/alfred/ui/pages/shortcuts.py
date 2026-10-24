"""Atalhos e gestos."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from alfred.ui import theme as T
from alfred.ui.pages.common import Page, section_title
from alfred.ui.widgets import Divider, GlassCard, KeyCap, Label

PLUS = object()


def _row(keys: list, title: str, desc: str) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 8, 0, 8)
    lay.setSpacing(18)
    caps = QHBoxLayout()
    caps.setSpacing(6)
    for k in keys:
        if k is PLUS:
            caps.addWidget(Label("+", 10, color=T.MUTED))
        else:
            caps.addWidget(KeyCap(k, wide=k in ("Shift", "Esc")))
    holder = QWidget()
    holder.setLayout(caps)
    holder.setFixedWidth(230)
    lay.addWidget(holder, 0, Qt.AlignmentFlag.AlignVCenter)
    col = QVBoxLayout()
    col.setSpacing(2)
    col.addWidget(Label(title, 10, QFont.Weight.DemiBold))
    col.addWidget(Label(desc, 9, color=T.MUTED, wrap=True))
    lay.addLayout(col, 1)
    return w


class ShortcutsPage(Page):
    def __init__(self, app, parent=None):
        super().__init__("Atalhos", "Tudo o que dá para fazer sem abrir esta janela.", parent)
        self.body.addWidget(section_title("No Explorador de Arquivos"))
        c1 = GlassCard()
        rows = [
            (["Shift", PLUS, "Arrastar"], "Abrir a roda de conversão",
             "Selecione um ou vários arquivos e comece a arrastá-los segurando Shift. Solte sobre o formato desejado."),
            (["Esc"], "Cancelar",
             "Fecha a roda imediatamente. Nada é convertido, copiado ou movido. Soltar fora da roda também cancela."),
            (["Botão direito"], "Converter com Alfred",
             "No menu de contexto (no Windows 11, em “Mostrar mais opções”). Abre a roda para os itens selecionados."),
            (["Enviar para"], "Alfred",
             "Também disponível no submenu “Enviar para”, criado pelo instalador."),
        ]
        for i, (k, t, d) in enumerate(rows):
            if i:
                c1.lay.addWidget(Divider())
            c1.lay.addWidget(_row(k, t, d))
        self.body.addWidget(c1)

        self.body.addWidget(section_title("Com a roda aberta"))
        c2 = GlassCard()
        rows2 = [
            (["←", "→"], "Navegar pelos formatos", "As setas (ou Tab) percorrem os segmentos no sentido horário."),
            (["Enter"], "Converter", "Confirma o formato destacado."),
            (["1", "…", "9"], "Escolha rápida", "Cada número escolhe o segmento correspondente, a partir do topo."),
            (["Clique no centro"], "Cancelar", "O centro da roda mostra o arquivo e também cancela."),
        ]
        for i, (k, t, d) in enumerate(rows2):
            if i:
                c2.lay.addWidget(Divider())
            c2.lay.addWidget(_row(k, t, d))
        self.body.addWidget(c2)

        self.body.addWidget(section_title("Dentro do Alfred"))
        c3 = GlassCard()
        c3.lay.addWidget(_row(["Soltar na janela"], "Converter",
                              "Arraste arquivos para a área dourada da tela Início."))
        c3.lay.addWidget(Divider())
        c3.lay.addWidget(_row(["X da janela"], "Continuar na bandeja",
                              "Fechar a janela não encerra o Alfred. Use “Sair” no ícone da bandeja."))
        self.body.addWidget(c3)
        self.body.addStretch(1)
