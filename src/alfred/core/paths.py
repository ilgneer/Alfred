"""Locations used by Alfred (assets, bundled engines, user data).

Everything that depends on whether we run from source or from a PyInstaller
bundle lives here, so the rest of the code never guesses paths.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from alfred import APP_NAME


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path:
    """Folder that contains Alfred.exe (frozen) or the repository root (source)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    # src/alfred/core/paths.py -> repository root
    return Path(__file__).resolve().parents[3]


def bundle_dir() -> Path:
    """Folder with bundled read-only data (PyInstaller _internal or repo root)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", install_dir()))
    return install_dir()


def asset_path(*parts: str) -> Path:
    return bundle_dir().joinpath("assets", *parts)


def engines_dir() -> Path:
    """Bundled third-party engines (FFmpeg, Pandoc, 7-Zip, LibreOffice).

    Can be overridden with ``ALFRED_ENGINES_DIR`` (used by CI and tests).
    """
    override = os.environ.get("ALFRED_ENGINES_DIR")
    if override:
        return Path(override)
    candidates = [install_dir() / "engines", install_dir() / "vendor" / "engines"]
    for c in candidates:
        if c.is_dir():
            return c
    return candidates[0]


def _base_dir(env: str, fallback: Path) -> Path:
    value = os.environ.get(env)
    return Path(value) if value else fallback


def config_dir() -> Path:
    """Roaming settings: %APPDATA%\\Alfred (or ~/.config/Alfred)."""
    override = os.environ.get("ALFRED_CONFIG_DIR")
    if override:
        p = Path(override)
    elif sys.platform == "win32":
        p = _base_dir("APPDATA", Path.home() / "AppData" / "Roaming") / APP_NAME
    else:
        p = _base_dir("XDG_CONFIG_HOME", Path.home() / ".config") / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_dir() -> Path:
    """Local data (history, logs, caches): %LOCALAPPDATA%\\Alfred."""
    override = os.environ.get("ALFRED_DATA_DIR")
    if override:
        p = Path(override)
    elif sys.platform == "win32":
        p = _base_dir("LOCALAPPDATA", Path.home() / "AppData" / "Local") / APP_NAME
    else:
        p = _base_dir("XDG_DATA_HOME", Path.home() / ".local" / "share") / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = data_dir() / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p


def documents_fallback_dir() -> Path:
    """Used when the source folder is read-only (CD, Program Files, etc.)."""
    home = Path.home()
    docs = home / "Documents"
    if not docs.is_dir():
        docs = home
    p = docs / "Alfred"
    p.mkdir(parents=True, exist_ok=True)
    return p


def edition() -> str:
    """'completa', 'leve' or 'desenvolvimento' (read from engines/edition.txt)."""
    marker = engines_dir() / "edition.txt"
    try:
        value = marker.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "desenvolvimento" if not is_frozen() else "leve"
    return {"full": "completa", "lite": "leve"}.get(value, value or "leve")


def app_command(*args: str) -> list[str]:
    """Command line that starts Alfred again (for registry entries, workers)."""
    if is_frozen():
        return [sys.executable, *args]
    exe = Path(sys.executable)
    if sys.platform == "win32":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            exe = pythonw
    return [str(exe), "-m", "alfred", *args]
