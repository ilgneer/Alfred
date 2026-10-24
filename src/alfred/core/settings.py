"""Persistent user preferences (JSON, written atomically)."""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from alfred.core import paths

log = logging.getLogger(__name__)

OUTPUT_MODES = ("same", "subfolder", "custom")
GESTURE_MODIFIERS = ("shift", "shift+ctrl", "shift+alt")
VIDEO_QUALITIES = ("compact", "balanced", "high")
SUBFOLDER_NAME = "Convertidos pelo Alfred"


@dataclass
class Settings:
    # Sons
    sounds_enabled: bool = True
    volume: int = 80  # 0..100
    # Integração
    explorer_gesture: bool = True
    gesture_modifier: str = "shift"
    context_menu: bool = True
    start_with_windows: bool = True
    # Saída
    output_mode: str = "same"
    custom_output_dir: str = ""
    open_folder_when_done: bool = False
    notify_when_done: bool = True
    # Qualidade
    video_quality: str = "balanced"
    jpg_quality: int = 92
    pdf_dpi: int = 300
    # Interface
    reduce_motion: bool = False
    tray_hint_shown: bool = False
    first_run_done: bool = False
    # Interno
    schema: int = 2
    extra: dict = field(default_factory=dict)

    def normalized(self) -> Settings:
        """Return a copy with every value clamped to a valid range."""
        s = Settings(**asdict(self))
        s.volume = max(0, min(100, int(s.volume)))
        s.jpg_quality = max(40, min(100, int(s.jpg_quality)))
        s.pdf_dpi = max(72, min(600, int(s.pdf_dpi)))
        if s.output_mode not in OUTPUT_MODES:
            s.output_mode = "same"
        if s.output_mode == "custom" and not s.custom_output_dir:
            s.output_mode = "same"
        if s.gesture_modifier not in GESTURE_MODIFIERS:
            s.gesture_modifier = "shift"
        if s.video_quality not in VIDEO_QUALITIES:
            s.video_quality = "balanced"
        return s


def settings_file() -> Path:
    return paths.config_dir() / "settings.json"


def _installer_defaults() -> dict:
    """First run on Windows: honour choices made in the installer wizard."""
    if os.name != "nt":
        return {}
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Alfred\InstallerDefaults") as key:
            out = {}
            for name, attr in (("ExplorerGesture", "explorer_gesture"),
                               ("ContextMenu", "context_menu"),
                               ("StartWithWindows", "start_with_windows")):
                try:
                    value, _ = winreg.QueryValueEx(key, name)
                    out[attr] = bool(int(value))
                except OSError:
                    pass
            return out
    except OSError:
        return {}


def consume_installer_defaults(store: SettingsStore) -> bool:
    """Apply the choices of a (re)installation once, then mark them consumed.

    The installer writes ``HKCU\\Software\\Alfred\\InstallerDefaults`` with
    ``Pending=1``; the next start of Alfred copies the choices into the user's
    settings so reinstalling with different options takes effect.
    """
    if os.name != "nt":
        return False
    try:
        import winreg

        path = r"Software\Alfred\InstallerDefaults"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            try:
                pending, _ = winreg.QueryValueEx(key, "Pending")
            except OSError:
                return False
            if not int(pending):
                return False
            values = _installer_defaults()
            if values:
                store.update(**values)
            winreg.SetValueEx(key, "Pending", 0, winreg.REG_DWORD, 0)
            return True
    except OSError:
        return False


class SettingsStore:
    """Thread-safe load/save of :class:`Settings`."""

    def __init__(self, path: Path | None = None):
        self.path = path or settings_file()
        self._lock = threading.Lock()
        self.value = self.load()

    def load(self) -> Settings:
        known = {f.name for f in fields(Settings)}
        data: dict = {}
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    data = {k: v for k, v in raw.items() if k in known}
            except (OSError, ValueError) as exc:
                log.warning("Configurações corrompidas, usando padrão: %s", exc)
                try:
                    self.path.replace(self.path.with_suffix(".json.bak"))
                except OSError:
                    pass
        else:
            data.update(_installer_defaults())
        try:
            return Settings(**data).normalized()
        except TypeError:
            return Settings()

    def save(self) -> None:
        with self._lock:
            self.value = self.value.normalized()
            payload = json.dumps(asdict(self.value), ensure_ascii=False, indent=2)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".settings-", suffix=".json", dir=self.path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(payload)
                    fh.flush()
                    os.fsync(fh.fileno())
                os.replace(tmp, self.path)
            except OSError:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise

    def update(self, **changes) -> Settings:
        for key, value in changes.items():
            if not hasattr(self.value, key):
                raise AttributeError(key)
            setattr(self.value, key, value)
        self.save()
        return self.value
