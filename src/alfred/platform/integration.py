"""Explorer context menu and start-with-Windows (per-user, HKCU only).

No administrator rights are needed and nothing outside the current user's
registry hive is touched. ``unregister_all`` is called by the uninstaller.
"""
from __future__ import annotations

import logging
import subprocess
import sys

from alfred.core import paths

log = logging.getLogger(__name__)
IS_WINDOWS = sys.platform == "win32"

MENU_KEYS = (r"Software\Classes\*\shell\Alfred", r"Software\Classes\Directory\shell\Alfred")
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "Alfred"
MENU_LABEL = "Converter com Alfred"


def _cmdline(*args: str) -> str:
    return subprocess.list2cmdline(paths.app_command(*args))


def _icon_ref() -> str:
    if paths.is_frozen():
        return f"{sys.executable},0"
    return str(paths.asset_path("alfred.ico"))


def set_context_menu(enabled: bool) -> None:
    if not IS_WINDOWS:
        return
    import winreg

    if not enabled:
        for key in MENU_KEYS:
            _delete_tree(winreg.HKEY_CURRENT_USER, key)
        return
    command = _cmdline("--open") + ' "%1"'
    for key in MENU_KEYS:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, MENU_LABEL)
            winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, _icon_ref())
            winreg.SetValueEx(k, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key + r"\command") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, command)


def context_menu_installed() -> bool:
    if not IS_WINDOWS:
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU_KEYS[0] + r"\command"):
            return True
    except OSError:
        return False


def set_autostart(enabled: bool) -> None:
    if not IS_WINDOWS:
        return
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        if enabled:
            winreg.SetValueEx(k, RUN_VALUE, 0, winreg.REG_SZ, _cmdline("--background"))
        else:
            try:
                winreg.DeleteValue(k, RUN_VALUE)
            except FileNotFoundError:
                pass


def autostart_enabled() -> bool:
    if not IS_WINDOWS:
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_VALUE)
            return True
    except OSError:
        return False


def _delete_tree(root, key: str) -> None:
    import winreg

    try:
        with winreg.OpenKey(root, key, 0, winreg.KEY_ALL_ACCESS) as k:
            while True:
                try:
                    sub = winreg.EnumKey(k, 0)
                except OSError:
                    break
                _delete_tree(root, key + "\\" + sub)
        winreg.DeleteKey(root, key)
    except FileNotFoundError:
        pass
    except OSError as exc:
        log.warning("Não foi possível remover %s: %s", key, exc)


def unregister_all() -> None:
    """Remove every registry entry Alfred may have created (uninstaller)."""
    if not IS_WINDOWS:
        return
    import winreg

    set_context_menu(False)
    set_autostart(False)
    _delete_tree(winreg.HKEY_CURRENT_USER, r"Software\Alfred")


def is_installed() -> bool:
    """True when running from the Inno Setup installation (not a portable copy)."""
    return paths.is_frozen() and any(paths.install_dir().glob("unins*.exe"))


def apply(settings, force: bool = False) -> None:
    """Make the registry match the user's preferences.

    Automatic calls (first run) only touch the registry for installed copies;
    ``force=True`` is used when the user flips a switch in Configurações.
    """
    if not IS_WINDOWS or not paths.is_frozen():
        return
    if not force and not is_installed():
        return
    try:
        set_context_menu(settings.context_menu)
        set_autostart(settings.start_with_windows)
    except OSError as exc:
        log.warning("Falha ao aplicar integração com o Windows: %s", exc)
