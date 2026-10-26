"""Configurações."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QMessageBox,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from alfred.core import paths
from alfred.core.settings import SUBFOLDER_NAME, Settings
from alfred.ui import sounds
from alfred.ui import theme as T
from alfred.ui.pages.common import Page, section_title
from alfred.ui.widgets import Chip, Divider, ElidedLabel, GhostButton, GlassCard, Label, SettingRow, ToggleSwitch

OUTPUT_LABELS = [("same", "Na mesma pasta do original"), ("subfolder", f"Na subpasta “{SUBFOLDER_NAME}”"),
                 ("custom", "Em uma pasta que eu escolher")]
VIDEO_LABELS = [("compact", "Compacta (arquivos menores)"), ("balanced", "Equilibrada (recomendado)"),
                ("high", "Alta (arquivos maiores)")]
MODIFIER_LABELS = [("shift", "Shift + arrastar"), ("shift+ctrl", "Shift + Ctrl + arrastar"),
                   ("shift+alt", "Shift + Alt + arrastar")]
DPI_CHOICES = [150, 200, 300, 600]


def combo(options, current) -> QComboBox:
    c = QComboBox()
    for key, label in options:
        c.addItem(label, key)
    idx = max(0, c.findData(current))
    c.setCurrentIndex(idx)
    c.setCursor(Qt.CursorShape.PointingHandCursor)
    return c


class SettingsPage(Page):
    def __init__(self, app, parent=None):
        super().__init__("Configurações", "Ajuste o Alfred ao seu jeito. Tudo é salvo automaticamente.", parent)
        self.app = app
        s = app.settings.value
        win = app.gesture_supported

        # Integração ---------------------------------------------------------
        self.body.addWidget(section_title("Integração com o Windows"))
        card = GlassCard()
        self.t_gesture = ToggleSwitch(s.explorer_gesture)
        self.t_gesture.toggled.connect(lambda v: app.update_setting(explorer_gesture=v))
        card.lay.addWidget(SettingRow("Roda no Explorador de Arquivos",
                                      "Arraste arquivos com a tecla escolhida para abrir a roda de conversão.",
                                      self.t_gesture, "cursor"))
        self.c_mod = combo(MODIFIER_LABELS, s.gesture_modifier)
        self.c_mod.currentIndexChanged.connect(lambda _i: app.update_setting(gesture_modifier=self.c_mod.currentData()))
        card.lay.addWidget(SettingRow("Gesto", "Com “Shift + arrastar”, o Shift deixa de mover arquivos no Explorer "
                                      "enquanto o Alfred estiver aberto.", self.c_mod, "keyboard"))
        card.lay.addWidget(Divider())
        self.t_menu = ToggleSwitch(s.context_menu)
        self.t_menu.toggled.connect(lambda v: app.update_setting(context_menu=v))
        card.lay.addWidget(SettingRow("Menu “Converter com Alfred”", "Item no clique direito de arquivos e pastas.",
                                      self.t_menu, "external"))
        self.t_start = ToggleSwitch(s.start_with_windows)
        self.t_start.toggled.connect(lambda v: app.update_setting(start_with_windows=v))
        card.lay.addWidget(SettingRow("Iniciar com o Windows", "O Alfred fica discreto na bandeja, pronto para o gesto.",
                                      self.t_start, "power"))
        if not win:
            for w in (self.t_gesture, self.c_mod, self.t_menu, self.t_start):
                w.setEnabled(False)
            card.lay.addWidget(Label("Estas opções só funcionam no Windows.", 8.8, color=T.WARNING))
        self.body.addWidget(card)

        # Saída ------------------------------------------------------------------
        self.body.addWidget(section_title("Arquivos convertidos"))
        out = GlassCard()
        self.c_out = combo(OUTPUT_LABELS, s.output_mode)
        self.c_out.currentIndexChanged.connect(self._output_changed)
        out.lay.addWidget(SettingRow("Onde salvar", "O original nunca é alterado nem sobrescrito.", self.c_out, "folder"))
        row = QHBoxLayout()
        row.setContentsMargins(38, 0, 0, 0)
        self.path_label = ElidedLabel(s.custom_output_dir or "Nenhuma pasta escolhida")
        self.path_label.setStyleSheet(f"color: {T.MUTED};")
        row.addWidget(self.path_label, 1)
        self.b_choose = GhostButton("Escolher pasta…", "folder", compact=True)
        self.b_choose.clicked.connect(self._choose_dir)
        row.addWidget(self.b_choose)
        self.custom_row = QWidget()
        self.custom_row.setLayout(row)
        self.custom_row.setVisible(s.output_mode == "custom")
        out.lay.addWidget(self.custom_row)
        out.lay.addWidget(Divider())
        self.t_open = ToggleSwitch(s.open_folder_when_done)
        self.t_open.toggled.connect(lambda v: app.update_setting(open_folder_when_done=v))
        out.lay.addWidget(SettingRow("Abrir a pasta ao concluir", "", self.t_open, "external"))
        self.t_notify = ToggleSwitch(s.notify_when_done)
        self.t_notify.toggled.connect(lambda v: app.update_setting(notify_when_done=v))
        out.lay.addWidget(SettingRow("Avisar quando terminar", "Notificação discreta no canto da tela.", self.t_notify, "bell"))
        self.body.addWidget(out)

        # Qualidade -------------------------------------------------------------
        self.body.addWidget(section_title("Qualidade"))
        q = GlassCard()
        self.c_video = combo(VIDEO_LABELS, s.video_quality)
        self.c_video.currentIndexChanged.connect(lambda _i: app.update_setting(video_quality=self.c_video.currentData()))
        q.lay.addWidget(SettingRow("Vídeo", "Equilíbrio entre tamanho e qualidade (H.264 / VP9).", self.c_video, "video"))
        self.s_jpg, jpg_box = self._slider(60, 100, s.jpg_quality, lambda v: app.update_setting(jpg_quality=v))
        q.lay.addWidget(SettingRow("Qualidade JPEG", "Também usada nas páginas de PDF exportadas em JPG.", jpg_box,
                                   "image"))
        self.c_dpi = combo([(d, f"{d} DPI") for d in DPI_CHOICES], s.pdf_dpi)
        self.c_dpi.currentIndexChanged.connect(lambda _i: app.update_setting(pdf_dpi=self.c_dpi.currentData()))
        q.lay.addWidget(SettingRow("Resolução das páginas", "PDF e apresentações exportados como imagem.", self.c_dpi,
                                   "pages"))
        self.body.addWidget(q)

        # Sons -------------------------------------------------------------------
        self.body.addWidget(section_title("Sons"))
        snd = GlassCard()
        self.t_sound = ToggleSwitch(s.sounds_enabled)
        self.t_sound.toggled.connect(lambda v: app.update_setting(sounds_enabled=v))
        snd.lay.addWidget(SettingRow("Efeitos sonoros", "Sons originais criados para o Alfred.", self.t_sound, "play"))
        self.s_vol, vol_box = self._slider(0, 100, s.volume, self._volume_changed, suffix="%")
        snd.lay.addWidget(SettingRow("Volume", "", vol_box, "volume"))
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setContentsMargins(38, 4, 0, 4)
        for i, name in enumerate(sounds.NAMES):
            b = GhostButton(sounds.LABELS[name], "play", compact=True)
            b.clicked.connect(lambda _c=False, n=name: app.sounds.play(n, force=True))
            grid.addWidget(b, i // 3, i % 3)
        snd.lay.addLayout(grid)
        self.body.addWidget(snd)

        # Aparência --------------------------------------------------------------
        self.body.addWidget(section_title("Aparência"))
        ap = GlassCard()
        self.t_motion = ToggleSwitch(s.reduce_motion)
        self.t_motion.toggled.connect(lambda v: app.update_setting(reduce_motion=v))
        ap.lay.addWidget(SettingRow("Reduzir animações", "Abre e fecha a roda sem transições.", self.t_motion,
                                    "sparkle"))
        self.body.addWidget(ap)

        # Motores ----------------------------------------------------------------
        self.body.addWidget(section_title("Motores de conversão"))
        self.eng_card = GlassCard()
        self.eng_list = QVBoxLayout()
        self.eng_list.setSpacing(6)
        self.eng_card.lay.addLayout(self.eng_list)
        eb = QHBoxLayout()
        self.edition = Label("", 9, color=T.MUTED)
        eb.addWidget(self.edition)
        eb.addStretch(1)
        redetect = GhostButton("Detectar novamente", "refresh", compact=True)
        redetect.clicked.connect(app.redetect_engines)
        eb.addWidget(redetect)
        self.eng_card.lay.addLayout(eb)
        self.body.addWidget(self.eng_card)

        # Apoie o projeto ------------------------------------------------------
        self.body.addWidget(section_title("Apoie o projeto"))
        sup = GlassCard(accent=True)
        b_pix = GhostButton("Apoiar via Pix", "heart", compact=True)
        b_pix.clicked.connect(lambda: app.show_support())
        sup.lay.addWidget(SettingRow("Pague um cafezinho para o mordomo",
                                     "O Alfred é gratuito e sem anúncios. Se ele te ajuda no dia a dia, um Pix de "
                                     "qualquer valor mantém o projeto vivo.", b_pix, "heart"))
        self.t_support = ToggleSwitch(s.support_popup)
        self.t_support.toggled.connect(lambda v: app.update_setting(support_popup=v))
        sup.lay.addWidget(SettingRow("Lembrete ao abrir", "No máximo uma vez por semana, só quando a janela abrir.",
                                     self.t_support, "bell"))
        self.body.addWidget(sup)

        # Avançado -------------------------------------------------------------
        self.body.addWidget(section_title("Avançado"))
        adv = GlassCard()
        row = QHBoxLayout()
        row.setSpacing(10)
        b_logs = GhostButton("Abrir logs", "logs", compact=True)
        b_logs.clicked.connect(lambda: app.open_path(paths.logs_dir()))
        b_cfg = GhostButton("Pasta de configurações", "folder", compact=True)
        b_cfg.clicked.connect(lambda: app.open_path(paths.config_dir()))
        b_reset = GhostButton("Restaurar padrões", "refresh", compact=True)
        b_reset.clicked.connect(self._reset)
        row.addWidget(b_logs)
        row.addWidget(b_cfg)
        row.addStretch(1)
        row.addWidget(b_reset)
        adv.lay.addLayout(row)
        self.body.addWidget(adv)
        self.body.addStretch(1)
        app.engines_ready.connect(self.show_engines)
        if app.engines is not None:
            self.show_engines(app.engines)

    # -- helpers ---------------------------------------------------------------------
    def _slider(self, lo, hi, value, on_change, suffix=""):
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(lo, hi)
        s.setValue(value)
        s.setFixedWidth(180)
        s.setCursor(Qt.CursorShape.PointingHandCursor)
        lab = Label(f"{value}{suffix}", 9.5, QFont.Weight.DemiBold, color=T.GOLD_LIGHT)
        lab.setFixedWidth(42)
        s.valueChanged.connect(lambda v: lab.setText(f"{v}{suffix}"))
        s.sliderReleased.connect(lambda: on_change(s.value()))
        s.valueChanged.connect(lambda v: None if s.isSliderDown() else on_change(v))
        lay.addWidget(s)
        lay.addWidget(lab)
        return s, box

    def _volume_changed(self, v: int):
        self.app.update_setting(volume=v)
        self.app.sounds.play("select", force=True)

    def _output_changed(self, _i):
        mode = self.c_out.currentData()
        self.custom_row.setVisible(mode == "custom")
        if mode == "custom" and not self.app.settings.value.custom_output_dir:
            self._choose_dir()
            if not self.app.settings.value.custom_output_dir:
                self.c_out.setCurrentIndex(0)
                return
        self.app.update_setting(output_mode=mode)

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Pasta para os arquivos convertidos",
                                             self.app.settings.value.custom_output_dir or str(Path.home()))
        if d:
            self.path_label.setText(d)
            self.app.update_setting(custom_output_dir=d, output_mode="custom")

    def _reset(self):
        box = QMessageBox(self)
        box.setWindowTitle("Restaurar padrões")
        box.setText("Voltar todas as configurações para o padrão?")
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if box.exec() == QMessageBox.StandardButton.Yes:
            defaults = Settings()
            self.app.update_setting(**{k: getattr(defaults, k) for k in (
                "sounds_enabled", "volume", "explorer_gesture", "gesture_modifier", "context_menu",
                "start_with_windows", "output_mode", "custom_output_dir", "open_folder_when_done",
                "notify_when_done", "video_quality", "jpg_quality", "pdf_dpi", "reduce_motion")})
            self.sync()

    def sync(self):
        s = self.app.settings.value
        for toggle, value in ((self.t_gesture, s.explorer_gesture), (self.t_menu, s.context_menu),
                              (self.t_start, s.start_with_windows), (self.t_open, s.open_folder_when_done),
                              (self.t_notify, s.notify_when_done), (self.t_sound, s.sounds_enabled),
                              (self.t_motion, s.reduce_motion), (self.t_support, s.support_popup)):
            toggle.setCheckedSilently(value)
        for c, v in ((self.c_mod, s.gesture_modifier), (self.c_out, s.output_mode), (self.c_video, s.video_quality),
                     (self.c_dpi, s.pdf_dpi)):
            c.blockSignals(True)
            c.setCurrentIndex(max(0, c.findData(v)))
            c.blockSignals(False)
        self.custom_row.setVisible(s.output_mode == "custom")
        for sl, v in ((self.s_jpg, s.jpg_quality), (self.s_vol, s.volume)):
            sl.blockSignals(True)
            sl.setValue(v)
            sl.blockSignals(False)

    def on_show(self):
        self.sync()

    def show_engines(self, eng):
        while self.eng_list.count():
            item = self.eng_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        rows = [("ffmpeg", "Áudio e vídeo"), ("pandoc", "Documentos e e-books"),
                ("libreoffice", "Word, PowerPoint, Excel e ODF"), ("sevenzip", "RAR e 7Z"),
                ("pymupdf", "PDF"), ("pdf2docx", "PDF → Word"), ("heif", "Fotos HEIC")]
        for key, purpose in rows:
            info = eng.infos.get(key)
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 2, 0, 2)
            name = Label(info.name if info else key, 9.8, QFont.Weight.DemiBold)
            name.setFixedWidth(170)
            lay.addWidget(name)
            lay.addWidget(Label(purpose, 9, color=T.MUTED), 1)
            if info and info.available:
                detail = " · ".join(x for x in (info.version, info.source) if x)
                lay.addWidget(Chip(detail or "disponível", "ok"))
            else:
                lay.addWidget(Chip("ausente", "bad"))
            w.setToolTip(info.path if info and info.path else (info.detail if info else ""))
            self.eng_list.addWidget(w)
        self.edition.setText(f"Edição: {paths.edition().capitalize()}")
