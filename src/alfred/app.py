"""Application controller: wires tray, window, wheel, gesture, jobs and IPC."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCursor, QDesktopServices, QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QSystemTrayIcon

from alfred import APP_ID, APP_NAME, __version__
from alfred.core import engines as engines_mod
from alfred.core import jobs as J
from alfred.core import paths, routes
from alfred.core.context import Options
from alfred.core.history import History
from alfred.core.settings import SettingsStore, consume_installer_defaults
from alfred.platform import integration, single_instance, win32
from alfred.platform.gesture import GestureMonitor
from alfred.ui import theme
from alfred.ui import theme as T
from alfred.ui.radial import CatchOverlay, RadialMenu, WheelItem
from alfred.ui.sounds import SoundPlayer
from alfred.ui.toast import Toast, ToastManager

log = logging.getLogger(__name__)

try:  # written by the release workflow
    from alfred._build_info import REPO_URL  # type: ignore
except Exception:  # noqa: BLE001
    REPO_URL = "https://github.com/ilgn3r/alfred"


class AlfredApp(QObject):
    job_updated = Signal(object)
    engines_ready = Signal(object)
    settings_changed = Signal()
    history_changed = Signal()
    _job_from_thread = Signal(object)
    _engines_from_thread = Signal(object)

    def __init__(self, qapp: QApplication, background: bool = False):
        super().__init__()
        self.qapp = qapp
        self.source_url = REPO_URL
        self.settings = SettingsStore()
        fresh_install = consume_installer_defaults(self.settings)
        self.history = History()
        s = self.settings.value
        self.sounds = SoundPlayer(s.sounds_enabled, s.volume)
        self.engines: engines_mod.Engines | None = None
        self.gesture_supported = win32.IS_WINDOWS
        self._quitting = False
        self._session_ending = False
        self._drag_session = False

        self._job_from_thread.connect(self._on_job, Qt.ConnectionType.QueuedConnection)
        self._engines_from_thread.connect(self._on_engines, Qt.ConnectionType.QueuedConnection)
        self.runner = J.JobRunner(self._options, self.history, self._job_from_thread.emit)
        self.toasts = ToastManager()

        # wheel ---------------------------------------------------------------
        self.overlay = CatchOverlay()
        self.wheel = RadialMenu(reduce_motion=s.reduce_motion)
        self.wheel.chosen.connect(self._on_wheel_chosen)
        self.wheel.cancelled.connect(self._on_wheel_cancelled)
        self.wheel.hovered.connect(lambda _i: self.sounds.play("hover"))
        self.overlay.clicked.connect(lambda: self.wheel.dismiss("outside"))
        self.overlay.file_drag_entered.connect(self._on_overlay_drag)
        self._overlay_timeout = QTimer(self)
        self._overlay_timeout.setSingleShot(True)
        self._overlay_timeout.timeout.connect(self._overlay_expired)

        # gesture ----------------------------------------------------------------
        self.gesture = GestureMonitor(s.gesture_modifier, self)
        self.gesture.armed.connect(self._on_gesture_armed)
        self.gesture.released.connect(lambda: QTimer.singleShot(150, self._end_drag_session))
        self.gesture.cancelled.connect(lambda: self._cancel_wheel("escape"))
        self.gesture.escape_pressed.connect(lambda: self._cancel_wheel("escape"))
        self.gesture.set_enabled(s.explorer_gesture)

        # window & tray ------------------------------------------------------------
        from alfred.ui.main_window import MainWindow
        from alfred.ui.tray import Tray

        self.has_tray = QSystemTrayIcon.isSystemTrayAvailable()
        self.window = MainWindow(self)
        self.window.setWindowIcon(QIcon(str(paths.asset_path("alfred.ico"))))
        self.tray = Tray(self) if self.has_tray else None
        if self.tray:
            self.tray.show()
        self._update_gesture_chip()

        # IPC ------------------------------------------------------------------------
        self.server = single_instance.PrimaryServer(self)
        self.server.listen()
        self.server.files_batch.connect(lambda files: self.open_wheel([Path(f) for f in files], QCursor.pos(), "click"))
        self.server.message.connect(self._on_message)

        # lifecycle --------------------------------------------------------------------
        qapp.commitDataRequest.connect(self._on_session_end)
        qapp.aboutToQuit.connect(self._cleanup)
        threading.Thread(target=self._detect_engines, daemon=True, name="alfred-engines").start()
        if not s.first_run_done or fresh_install:
            integration.apply(s)
            self.settings.update(first_run_done=True)
        if not background or not self.has_tray:
            self.window.show()

    # -- engines ---------------------------------------------------------------------------
    def _detect_engines(self, refresh: bool = False):
        try:
            eng = engines_mod.get(refresh=refresh)
        except Exception:  # noqa: BLE001
            log.exception("Falha ao detectar motores")
            eng = engines_mod.Engines()
        self._engines_from_thread.emit(eng)

    def _on_engines(self, eng):
        self.engines = eng
        self.wheel.ffmpeg_path = eng.infos["ffmpeg"].path if eng.has("ffmpeg") else None
        self.engines_ready.emit(eng)

    def redetect_engines(self):
        threading.Thread(target=self._detect_engines, args=(True,), daemon=True).start()

    # -- settings --------------------------------------------------------------------------
    def _options(self) -> Options:
        return Options.from_settings(self.settings.value)

    def update_setting(self, **changes):
        self.settings.update(**changes)
        s = self.settings.value
        if "sounds_enabled" in changes:
            self.sounds.set_enabled(s.sounds_enabled)
        if "volume" in changes:
            self.sounds.set_volume(s.volume)
        if "explorer_gesture" in changes:
            self.gesture.set_enabled(s.explorer_gesture)
        if "gesture_modifier" in changes:
            self.gesture.set_modifier(s.gesture_modifier)
        if "reduce_motion" in changes:
            self.wheel.reduce_motion = s.reduce_motion
        if "context_menu" in changes or "start_with_windows" in changes:
            integration.apply(s, force=True)
        self._update_gesture_chip()
        if self.tray:
            self.tray.sync()
        self.settings_changed.emit()

    def _update_gesture_chip(self):
        if not self.gesture_supported:
            self.window.sidebar.set_gesture_state("Gesto: só no Windows", "muted")
        elif self.settings.value.explorer_gesture:
            label = {"shift": "Shift", "shift+ctrl": "Shift+Ctrl", "shift+alt": "Shift+Alt"}[
                self.settings.value.gesture_modifier]
            self.window.sidebar.set_gesture_state(f"{label} + arrastar ativo", "ok")
        else:
            self.window.sidebar.set_gesture_state("Gesto desativado", "muted")

    # -- window -------------------------------------------------------------------------------
    def show_page(self, key: str | None):
        self.window.bring_to_front()
        if key:
            self.window.show_page(key)

    def window_hidden_to_tray(self):
        if not self.settings.value.tray_hint_shown:
            self.toasts.info("O Alfred continua na bandeja",
                             "Ele segue pronto para o gesto. Para encerrar, use “Sair” no ícone da bandeja.",
                             "sparkle", 7000)
            self.settings.update(tray_hint_shown=True)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self.window, "Escolha os arquivos para o Alfred")
        if files:
            self.open_wheel([Path(f) for f in files], QCursor.pos(), "click")

    def open_path(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def reveal(self, path):
        path = Path(path)
        if sys.platform == "win32" and path.exists():
            subprocess.Popen(["explorer.exe", f"/select,{path}"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            self.open_path(path.parent if path.is_file() else path)

    # -- wheel ------------------------------------------------------------------------------------
    def _engines_now(self) -> engines_mod.Engines:
        if self.engines is None:
            self._on_engines(engines_mod.get())
        return self.engines

    def build_items(self, files: list[Path]) -> list[WheelItem]:
        items = []
        for ch in routes.choices_for(files, self._engines_now()):
            note = ""
            for f in ch.files[:1]:
                plan = routes.pick_plan(f, ch.target.key, self._engines_now()) if not ch.target.batch else None
                note = plan.note if plan else ""
            items.append(WheelItem(ch.target.key, ch.target.label, ch.target.sublabel, ch.target.icon,
                                   ch.status == routes.EXPERIMENTAL, note, ch))
        return items

    def open_wheel(self, files: list[Path], pos: QPoint, mode: str = "click") -> bool:
        files = [Path(f) for f in files if Path(f).exists()]
        if not files:
            return False
        items = self.build_items(files)
        if not items:
            self.sounds.play("error")
            self.toasts.info("Nada para converter", f"O Alfred ainda não sabe converter “{files[0].name}”.",
                             "alert", 5000, "error")
            return False
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        self.overlay.arm(screen)
        self.wheel.open_at(pos, items, files, mode)
        self.gesture.set_watch_escape(True)
        self.sounds.play("open")
        return True

    def _cancel_wheel(self, reason: str):
        self._drag_session = False
        if self.wheel.isVisible():
            self.wheel.dismiss(reason)
        else:
            self.overlay.disarm()

    def _on_wheel_chosen(self, choice: routes.Choice, files: list):
        self.overlay.disarm()
        self.gesture.set_watch_escape(False)
        self._drag_session = False
        self.sounds.play("select")
        if choice is None:
            return
        self.runner.submit(list(choice.files), choice)

    def _on_wheel_cancelled(self, reason: str):
        self.overlay.disarm()
        self.gesture.set_watch_escape(False)
        self._drag_session = False
        self.sounds.play("close")

    # -- gesture ------------------------------------------------------------------------------------
    def _on_gesture_armed(self, pos: QPoint):
        if self.wheel.isVisible():
            return
        self._drag_session = True
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        self.overlay.arm(screen)
        self._overlay_timeout.start(8000)

    def _on_overlay_drag(self, files: list, pos: QPoint):
        self._overlay_timeout.stop()
        if not self._drag_session or self.wheel.isVisible():
            return
        if not self.open_wheel(files, pos, "drag"):
            self.overlay.disarm()
            self._drag_session = False

    def _end_drag_session(self):
        self._overlay_timeout.stop()
        if self.wheel.isVisible() and self.wheel.state.mode == "drag" and self.wheel.is_open():
            self.wheel.dismiss("released")
        elif not self.wheel.isVisible():
            self.overlay.disarm()
        self._drag_session = False

    def _overlay_expired(self):
        if not self.wheel.isVisible():
            self.overlay.disarm()
            self._drag_session = False

    # -- jobs ------------------------------------------------------------------------------------------
    def cancel_job(self, job_id: str):
        self.runner.cancel(job_id)

    def _on_job(self, job: J.Job):
        self.job_updated.emit(job)
        toast = self.toasts.by_job.get(job.id)
        if toast is None and job.state not in J.FINAL_STATES:
            toast = Toast("info")
            toast.job_id = job.id
            toast.set_icon(job.target.icon, T.GOLD)
            toast.set_text(job.title, f"Convertendo para {job.target.label}…")
            toast.progress.show()
            toast.set_actions([("Cancelar", "stop", lambda _c=False, jid=job.id: self.cancel_job(jid))])
            self.toasts.by_job[job.id] = toast
            self.toasts.show(toast)
        if toast is not None and job.state not in J.FINAL_STATES:
            toast.progress.setValue(job.progress if job.state == J.RUNNING else None)
            pct = f" · {int(job.progress * 100)}%" if job.progress is not None and job.state == J.RUNNING else ""
            toast.body.setText(f"{job.message or 'Convertendo'} → {job.target.label}{pct}")
        if job.state in J.FINAL_STATES:
            self._job_finished(job, toast)

    def _job_finished(self, job: J.Job, toast: Toast | None):
        self.history_changed.emit()
        s = self.settings.value
        if job.state in (J.DONE, J.PARTIAL):
            self.sounds.play("success")
            if s.open_folder_when_done and job.outputs:
                self.reveal(job.outputs[0])
        elif job.state == J.FAILED:
            self.sounds.play("error")
        if toast is None:
            if job.state == J.CANCELLED or (not s.notify_when_done and job.state != J.FAILED):
                return
            toast = Toast()
            self.toasts.show(toast)
        if job.state == J.CANCELLED:
            toast.kind = "info"
            toast.set_icon("stop", T.MUTED)
            toast.set_text(job.title, "Conversão cancelada. Nenhum arquivo foi criado.")
            toast.progress.hide()
            toast.set_actions([])
            toast.auto_hide(3000)
            return
        if job.state in (J.DONE, J.PARTIAL):
            if not s.notify_when_done:
                toast.dismiss()
                return
            n = len(job.outputs)
            toast.kind = "success"
            toast.set_icon("check", T.SUCCESS)
            body = f"{n} {'arquivo criado' if n == 1 else 'arquivos criados'} em {job.target.label}"
            if job.errors:
                body += f" · {len(job.errors)} com erro"
            if job.notes:
                body += f"\n{job.notes[0]}"
            toast.set_text("Pronto, senhor." if job.state == J.DONE else "Concluído com avisos", body)
            toast.progress.hide()
            first = job.outputs[0]
            toast.set_actions([("Abrir", "external", lambda: self.open_path(first)),
                               ("Mostrar na pasta", "folder", lambda: self.reveal(first))])
            toast.auto_hide(7000)
        else:
            toast.kind = "error"
            toast.set_icon("alert", T.DANGER)
            toast.set_text("Não foi possível converter", job.errors[0] if job.errors else "Erro desconhecido.")
            toast.progress.hide()
            toast.set_actions([("Detalhes", "history", lambda: self.show_page("history"))])
            toast.auto_hide(12000)
        toast.update()

    # -- IPC -------------------------------------------------------------------------------------------------
    def _on_message(self, msg: dict):
        cmd = msg.get("cmd")
        if cmd == "show":
            self.show_page("home")
        elif cmd == "settings":
            self.show_page("settings")
        elif cmd == "quit":
            self.quit(confirm=False)

    def handle_initial(self, message: dict):
        if message.get("cmd") == "open":
            QTimer.singleShot(150, lambda: self.open_wheel([Path(f) for f in message["files"]], QCursor.pos(), "click"))
        elif message.get("cmd") == "settings":
            self.show_page("settings")

    # -- shutdown ---------------------------------------------------------------------------------------------
    def _on_session_end(self, manager):
        """Windows is logging off / shutting down: never block it."""
        self._session_ending = True
        self.window.allow_close()

    def quit(self, confirm: bool = True):
        if self._quitting:
            return
        if confirm and self.runner.busy and self.window.isVisible():
            box = QMessageBox(self.window)
            box.setWindowTitle("Sair do Alfred")
            box.setText("Há conversões em andamento. Cancelar e sair?")
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if box.exec() != QMessageBox.StandardButton.Yes:
                return
        self._quitting = True
        self.window.allow_close()
        self.qapp.quit()

    def _cleanup(self):
        log.info("Encerrando o Alfred")
        self.gesture.stop()
        self.wheel.hide()
        self.overlay.hide()
        self.toasts.clear()
        if self.tray:
            self.tray.hide()
        self.server.close()
        self.runner.shutdown(timeout=4.0)


def _initial_message(args) -> dict:
    files = [str(Path(f).resolve()) for f in (list(args.files) + list(args.open_files or [])) if Path(f).exists()]
    if args.quit:
        return {"cmd": "quit"}
    if files:
        return {"cmd": "open", "files": files}
    if args.settings:
        return {"cmd": "settings"}
    if args.background:
        return {"cmd": "noop"}
    return {"cmd": "show"}


def run_gui(args) -> int:
    win32.set_app_user_model_id(APP_ID)
    if sys.platform != "win32" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    qapp = QApplication(sys.argv[:1])
    qapp.setApplicationName(APP_NAME)
    qapp.setApplicationVersion(__version__)
    qapp.setOrganizationName("ilgn3r")
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setWindowIcon(QIcon(str(paths.asset_path("alfred.ico"))))
    message = _initial_message(args)

    for _attempt in range(30):
        win32.allow_foreground_for_any()
        if single_instance.send_to_primary(message):
            log.info("Pedido enviado à instância principal: %s", message.get("cmd"))
            return 0
        if args.quit:
            return 0  # nothing is running
        if single_instance.acquire_primary_lock():
            break
        time.sleep(0.1)  # another process is becoming the primary right now
    else:
        log.error("Não foi possível falar com a instância principal")
        return 1

    theme.apply(qapp)
    win32.create_named_mutex("AlfredAppMutex")
    log.info("Alfred %s iniciado (edição %s)", __version__, paths.edition())
    controller = AlfredApp(qapp, background=args.background and message.get("cmd") != "open")
    controller.handle_initial(message)
    return qapp.exec()
