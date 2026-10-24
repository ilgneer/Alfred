"""Início: drop zone, status and the live conversion queue."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QConicalGradient, QFont, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from alfred.core import jobs as J
from alfred.core import paths
from alfred.ui import icons
from alfred.ui import theme as T
from alfred.ui.pages.common import Page, section_title
from alfred.ui.widgets import (
    Chip,
    ElidedLabel,
    GhostButton,
    GlassCard,
    IconButton,
    Label,
    PrimaryButton,
    SlimProgress,
)


class LogoOrb(QWidget):
    """The logo inside a slowly rotating golden ring."""

    def __init__(self, size: int = 150, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0.0
        self._glow = 0.0
        self.logo = QPixmap(str(paths.asset_path("alfred.png")))
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_glow(self, v: float):
        self._glow = v
        self.update()

    def _tick(self):
        if self.isVisible():
            self._angle = (self._angle + 0.9) % 360
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self.width() / 2 - 8
        halo = QRadialGradient(c, r + 8)
        halo.setColorAt(0.7, T.qc(T.GOLD, int(40 + 50 * self._glow)))
        halo.setColorAt(1.0, T.qc(T.GOLD, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(c, r + 8, r + 8)
        cone = QConicalGradient(c, -self._angle)
        cone.setColorAt(0, T.qc(T.GOLD_LIGHT, 255))
        cone.setColorAt(0.25, T.qc(T.GOLD, 40))
        cone.setColorAt(0.5, T.qc(T.GOLD, 160))
        cone.setColorAt(0.75, T.qc(T.GOLD, 30))
        cone.setColorAt(1, T.qc(T.GOLD_LIGHT, 255))
        p.setPen(QPen(cone, 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(c, r, r)
        inner = r - 8
        clip = QPainterPath()
        clip.addEllipse(c, inner, inner)
        p.setClipPath(clip)
        p.drawPixmap(QRectF(c.x() - inner, c.y() - inner, 2 * inner, 2 * inner), self.logo, QRectF(self.logo.rect()))


class DropZone(GlassCard):
    files_dropped = Signal(list, QPoint)
    browse = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, radius=22, accent=True, padding=28)
        self.setAcceptDrops(True)
        self.setMinimumHeight(230)
        row = QHBoxLayout()
        row.setSpacing(30)
        self.orb = LogoOrb(168)
        row.addWidget(self.orb, 0, Qt.AlignmentFlag.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addStretch(1)
        col.addWidget(Label("Solte seus arquivos aqui", 19, QFont.Weight.DemiBold, family=T.DISPLAY))
        col.addWidget(Label("Ou, no Explorador de Arquivos, arraste qualquer arquivo segurando Shift: "
                            "a roda de conversão aparece ao lado do cursor.", 10, color=T.MUTED, wrap=True))
        slogan = Label("“Algumas tarefas é melhor deixar para o Alfred.”", 11, family=T.SERIF_ITALIC,
                       italic=True, color=T.GOLD_LIGHT)
        col.addSpacing(4)
        col.addWidget(slogan)
        col.addSpacing(10)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.pick = PrimaryButton("Escolher arquivos", "plus")
        self.pick.clicked.connect(self.browse.emit)
        btns.addWidget(self.pick)
        btns.addStretch(1)
        col.addLayout(btns)
        col.addStretch(1)
        row.addLayout(col, 1)
        self.lay.addLayout(row)
        self._pulse = 0.0

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.isLocalFile() for u in e.mimeData().urls()):
            e.setDropAction(Qt.DropAction.CopyAction)
            e.accept()
            self.set_glow(1.0)
            self.orb.set_glow(1.0)
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()

    def dragLeaveEvent(self, e):
        self.set_glow(0.0)
        self.orb.set_glow(0.0)

    def dropEvent(self, e):
        self.set_glow(0.0)
        self.orb.set_glow(0.0)
        files = [Path(u.toLocalFile()) for u in e.mimeData().urls() if u.isLocalFile()]
        e.setDropAction(Qt.DropAction.CopyAction)
        e.accept()
        if files:
            self.files_dropped.emit(files, self.mapToGlobal(e.position().toPoint()))

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._glow > 0:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(T.qc(T.GOLD_LIGHT, 200), 1.6, Qt.PenStyle.DashLine)
            pen.setDashPattern([6, 5])
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(8, 8, -8, -8), 16, 16)


class StatCard(GlassCard):
    def __init__(self, icon_name: str, title: str, value: str, parent=None):
        super().__init__(parent, radius=16, padding=16)
        row = QHBoxLayout()
        row.setSpacing(12)
        self.icon = IconBadge(icon_name)
        row.addWidget(self.icon)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.value = Label(value, 15, QFont.Weight.DemiBold, family=T.DISPLAY)
        col.addWidget(self.value)
        col.addWidget(Label(title, 8.6, color=T.MUTED))
        row.addLayout(col, 1)
        self.lay.addLayout(row)

    def set_value(self, v: str):
        self.value.setText(v)


class IconBadge(QWidget):
    def __init__(self, icon_name: str, size: int = 40, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(T.qc(T.GOLD, 70), 1))
        p.setBrush(T.qc(T.GOLD, 26))
        p.drawRoundedRect(r, 12, 12)
        s = r.width() * 0.5
        icons.paint(p, self.icon_name, QRectF(r.center().x() - s / 2, r.center().y() - s / 2, s, s), T.GOLD_LIGHT, 1.7)


STATE_TEXT = {J.QUEUED: "Na fila", J.RUNNING: "Convertendo", J.DONE: "Concluído", J.PARTIAL: "Concluído com avisos",
              J.FAILED: "Falhou", J.CANCELLED: "Cancelado"}


class JobRow(QWidget):
    cancel = Signal(str)
    reveal = Signal(object)

    def __init__(self, job: J.Job, parent=None):
        super().__init__(parent)
        self.job_id = job.id
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 8, 4, 8)
        lay.setSpacing(14)
        self.badge = IconBadge(job.target.icon, 38)
        lay.addWidget(self.badge)
        col = QVBoxLayout()
        col.setSpacing(5)
        top = QHBoxLayout()
        self.title = ElidedLabel(job.title)
        self.title.setFont(T.font(9.8, QFont.Weight.DemiBold))
        self.title.setStyleSheet(f"color: {T.WHITE};")
        top.addWidget(self.title, 1)
        self.target = Chip(f"→ {job.target.label}", "gold", dot=False)
        top.addWidget(self.target)
        col.addLayout(top)
        self.progress = SlimProgress()
        col.addWidget(self.progress)
        self.status = ElidedLabel("")
        self.status.setFont(T.font(8.6))
        self.status.setStyleSheet(f"color: {T.MUTED};")
        col.addWidget(self.status)
        lay.addLayout(col, 1)
        self.action = IconButton("stop", "Cancelar", 32, danger=True)
        self.action.clicked.connect(self._action)
        lay.addWidget(self.action)
        self._done = False
        self.outputs: list[Path] = []
        self.update_job(job)

    def _action(self):
        if self._done:
            if self.outputs:
                self.reveal.emit(self.outputs[0])
        else:
            self.cancel.emit(self.job_id)

    def update_job(self, job: J.Job):
        self.progress.setValue(job.progress if job.state == J.RUNNING else (1.0 if job.finished_ok else 0.0))
        detail = job.message or STATE_TEXT.get(job.state, "")
        if job.state == J.RUNNING and job.progress is not None:
            detail = f"{detail} · {int(job.progress * 100)}%"
        if job.state in J.FINAL_STATES:
            self._done = True
            self.outputs = list(job.outputs)
            if job.state in (J.DONE, J.PARTIAL):
                n = len(job.outputs)
                detail = f"{STATE_TEXT[job.state]} · {n} {'arquivo' if n == 1 else 'arquivos'}"
                self.action.icon_name = "folder"
                self.action.danger = False
                self.action.setToolTip("Mostrar na pasta")
                self.target.set(f"✓ {job.target.label}", "ok")
            else:
                self.action.icon_name = "close"
                self.action.setToolTip("Remover da lista")
                self.action.danger = False
                self.target.set(STATE_TEXT[job.state], "bad" if job.state == J.FAILED else "muted")
                if job.errors:
                    detail = job.errors[0]
            self.action.update()
        self.status.setText(detail)


class HomePage(Page):
    def __init__(self, app, parent=None):
        super().__init__("Bem-vindo de volta", "Selecionou. Arrastou. Escolheu. Converteu.", parent)
        self.app = app
        self.drop = DropZone()
        self.drop.browse.connect(app.browse_files)
        self.drop.files_dropped.connect(lambda files, pos: app.open_wheel(files, pos, "click"))
        self.body.addWidget(self.drop)

        grid = QGridLayout()
        grid.setSpacing(14)
        self.stat_today = StatCard("check", "conversões hoje", "0")
        self.stat_engines = StatCard("engine", "motores ativos", "…")
        self.stat_gesture = StatCard("cursor", "gesto no Explorer", "…")
        grid.addWidget(self.stat_today, 0, 0)
        grid.addWidget(self.stat_engines, 0, 1)
        grid.addWidget(self.stat_gesture, 0, 2)
        self.body.addLayout(grid)

        self.body.addWidget(section_title("Atividade"))
        self.jobs_card = GlassCard(padding=14)
        self.jobs_layout = QVBoxLayout()
        self.jobs_layout.setSpacing(2)
        self.jobs_card.lay.addLayout(self.jobs_layout)
        self.empty = QWidget()
        el = QHBoxLayout(self.empty)
        el.setContentsMargins(6, 10, 6, 10)
        el.addWidget(Label("Nenhuma conversão ainda. Quando o Alfred trabalhar, você acompanha tudo por aqui.",
                           9.5, color=T.MUTED, wrap=True), 1)
        self.history_btn = GhostButton("Ver histórico", "history", compact=True)
        self.history_btn.clicked.connect(lambda: app.show_page("history"))
        el.addWidget(self.history_btn)
        self.jobs_layout.addWidget(self.empty)
        self.body.addWidget(self.jobs_card)
        self.body.addStretch(1)
        self.rows: dict[str, JobRow] = {}
        app.job_updated.connect(self.on_job)
        app.engines_ready.connect(lambda _e: self.refresh())
        app.settings_changed.connect(self.refresh)

    def on_show(self):
        self.refresh()

    def refresh(self):
        self.stat_today.set_value(str(self.app.history.count_today()))
        eng = self.app.engines
        if eng is None:
            self.stat_engines.set_value("detectando…")
        else:
            keys = ("ffmpeg", "pandoc", "libreoffice", "sevenzip", "pymupdf")
            ok = sum(1 for k in keys if eng.infos.get(k) and eng.infos[k].available)
            self.stat_engines.set_value(f"{ok} de {len(keys)}")
        s = self.app.settings.value
        if not self.app.gesture_supported:
            self.stat_gesture.set_value("só no Windows")
        else:
            self.stat_gesture.set_value("Ativo" if s.explorer_gesture else "Desativado")

    def on_job(self, job: J.Job):
        row = self.rows.get(job.id)
        if row is None:
            row = JobRow(job)
            row.cancel.connect(self._row_action)
            row.reveal.connect(self.app.reveal)
            self.rows[job.id] = row
            self.jobs_layout.insertWidget(0, row)
            self.empty.hide()
            # keep the list short
            while len(self.rows) > 6:
                oldest = next(iter(self.rows))
                self.rows.pop(oldest).deleteLater()
        row.update_job(job)
        if job.state in J.FINAL_STATES:
            self.refresh()

    def _row_action(self, job_id: str):
        job = self.app.runner.jobs.get(job_id) if self.app.runner else None
        if job and job.state not in J.FINAL_STATES:
            self.app.cancel_job(job_id)
        else:
            row = self.rows.pop(job_id, None)
            if row:
                row.deleteLater()
            if not self.rows:
                self.empty.show()
