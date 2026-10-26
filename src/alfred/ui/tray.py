"""System tray icon and menu."""
from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from alfred.core import paths
from alfred.ui import icons
from alfred.ui import theme as T


class Tray:
    def __init__(self, app):
        self.app = app
        icon = QIcon(str(paths.asset_path("alfred_tray.png")))
        self.icon = QSystemTrayIcon(icon)
        self.icon.setToolTip("Alfred — algumas tarefas é melhor deixar para o Alfred")
        menu = QMenu()
        self.menu = menu
        a_open = QAction(icons.icon("home", T.GOLD_LIGHT), "Abrir Alfred", menu)
        a_open.triggered.connect(lambda: app.show_page("home"))
        f = a_open.font()
        f.setBold(True)
        a_open.setFont(f)
        menu.addAction(a_open)
        a_settings = QAction(icons.icon("settings", T.MUTED), "Configurações", menu)
        a_settings.triggered.connect(lambda: app.show_page("settings"))
        menu.addAction(a_settings)
        menu.addSeparator()
        self.a_gesture = QAction("Integração com o Explorer", menu)
        self.a_gesture.setCheckable(True)
        self.a_gesture.toggled.connect(lambda v: app.update_setting(explorer_gesture=v))
        menu.addAction(self.a_gesture)
        self.a_sounds = QAction("Sons", menu)
        self.a_sounds.setCheckable(True)
        self.a_sounds.toggled.connect(lambda v: app.update_setting(sounds_enabled=v))
        menu.addAction(self.a_sounds)
        menu.addSeparator()
        a_support = QAction(icons.icon("heart", T.GOLD_LIGHT), "Apoie o projeto (Pix)", menu)
        a_support.triggered.connect(lambda: app.show_support())
        menu.addAction(a_support)
        a_about = QAction(icons.icon("info", T.MUTED), "Sobre o Alfred", menu)
        a_about.triggered.connect(lambda: app.show_page("about"))
        menu.addAction(a_about)
        menu.addSeparator()
        a_quit = QAction(icons.icon("power", T.DANGER), "Sair", menu)
        a_quit.triggered.connect(lambda: app.quit())
        menu.addAction(a_quit)
        self.icon.setContextMenu(menu)
        self.icon.activated.connect(self._activated)
        self.sync()

    def _activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.app.show_page(None)

    def sync(self):
        s = self.app.settings.value
        for action, value in ((self.a_gesture, s.explorer_gesture), (self.a_sounds, s.sounds_enabled)):
            action.blockSignals(True)
            action.setChecked(value)
            action.blockSignals(False)
        self.a_gesture.setEnabled(self.app.gesture_supported)

    def show(self):
        self.icon.show()

    def hide(self):
        self.icon.hide()
