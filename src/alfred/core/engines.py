"""Detection of conversion engines (bundled first, then system).

Nothing here assumes the user configured PATH: bundled engines live in
``<install>/engines/<name>/`` and are found by absolute path. System
installations are only a fallback (useful for the "leve" edition and for
developers).
"""
from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from alfred.core import paths

log = logging.getLogger(__name__)

EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass
class EngineInfo:
    key: str
    name: str
    available: bool
    path: str = ""
    version: str = ""
    source: str = ""  # "incluído", "sistema", "biblioteca"
    license: str = ""
    detail: str = ""


@dataclass
class Engines:
    """Snapshot of what is available on this machine."""

    infos: dict[str, EngineInfo] = field(default_factory=dict)
    ffmpeg_encoders: frozenset[str] = frozenset()
    tokens: frozenset[str] = frozenset()

    def has(self, token: str) -> bool:
        return token in self.tokens

    def has_all(self, tokens) -> bool:
        return all(t in self.tokens for t in tokens)

    def path(self, key: str) -> str:
        info = self.infos.get(key)
        if not info or not info.available:
            raise EngineMissing(key)
        return info.path


class EngineMissing(RuntimeError):
    LABELS = {
        "ffmpeg": "FFmpeg",
        "pandoc": "Pandoc",
        "libreoffice": "LibreOffice",
        "sevenzip": "7-Zip",
    }

    def __init__(self, key: str):
        self.key = key
        label = self.LABELS.get(key, key)
        super().__init__(
            f"O motor {label} não está disponível nesta instalação. "
            "Reinstale o Alfred (edição completa) ou veja Configurações › Motores."
        )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _run(args: list[str], timeout: float = 15) -> str:
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            creationflags=NO_WINDOW, stdin=subprocess.DEVNULL,
            encoding="utf-8", errors="replace",
        )
        return (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        log.debug("Falha ao executar %s: %s", args, exc)
        return ""


def _first_existing(candidates) -> Path | None:
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    return None


def _program_files() -> list[Path]:
    out = []
    for env in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)", "LOCALAPPDATA"):
        v = os.environ.get(env)
        if v:
            out.append(Path(v))
    return out


# ---------------------------------------------------------------------------
# individual engines
# ---------------------------------------------------------------------------

def find_ffmpeg() -> tuple[Path | None, str]:
    env = os.environ.get("ALFRED_FFMPEG")
    if env and Path(env).is_file():
        return Path(env), "configurado"
    bundled = paths.engines_dir() / "ffmpeg" / f"ffmpeg{EXE}"
    if bundled.is_file():
        return bundled, "incluído"
    try:
        import imageio_ffmpeg

        bin_dir = Path(imageio_ffmpeg.__file__).parent / "binaries"
        for f in sorted(bin_dir.glob("ffmpeg*")):
            if f.is_file() and f.suffix.lower() not in (".md", ".py", ".txt", ".pyc"):
                return f, "incluído"
    except Exception:  # noqa: BLE001 - optional package
        pass
    which = shutil.which("ffmpeg")
    return (Path(which), "sistema") if which else (None, "")


def find_pandoc() -> tuple[Path | None, str]:
    env = os.environ.get("ALFRED_PANDOC")
    if env and Path(env).is_file():
        return Path(env), "configurado"
    bundled = paths.engines_dir() / "pandoc" / f"pandoc{EXE}"
    if bundled.is_file():
        return bundled, "incluído"
    try:
        spec = importlib.util.find_spec("pypandoc")
        if spec and spec.origin:
            f = Path(spec.origin).parent / "files" / f"pandoc{EXE}"
            if f.is_file():
                return f, "incluído"
    except Exception:  # noqa: BLE001
        pass
    which = shutil.which("pandoc")
    return (Path(which), "sistema") if which else (None, "")


def find_libreoffice() -> tuple[Path | None, str]:
    env = os.environ.get("ALFRED_SOFFICE")
    if env and Path(env).is_file():
        return Path(env), "configurado"
    if os.environ.get("ALFRED_DISABLE_SYSTEM_LIBREOFFICE") == "1":
        system_allowed = False
    else:
        system_allowed = True
    bundled = paths.engines_dir() / "libreoffice" / "program" / f"soffice{EXE}"
    if bundled.is_file():
        return bundled, "incluído"
    if not system_allowed:
        return None, ""
    if os.name == "nt":
        found = _first_existing(base / "LibreOffice" / "program" / "soffice.exe" for base in _program_files())
        if found:
            return found, "sistema"
    which = shutil.which("soffice") or shutil.which("libreoffice")
    return (Path(which), "sistema") if which else (None, "")


def find_sevenzip() -> tuple[Path | None, str]:
    env = os.environ.get("ALFRED_7Z")
    if env and Path(env).is_file():
        return Path(env), "configurado"
    bundled = paths.engines_dir() / "7zip" / f"7z{EXE}"
    if bundled.is_file():
        return bundled, "incluído"
    if os.name == "nt":
        found = _first_existing(base / "7-Zip" / "7z.exe" for base in _program_files())
        if found:
            return found, "sistema"
    for name in ("7z", "7zz"):
        which = shutil.which(name)
        if which:
            return Path(which), "sistema"
    return None, ""


def _sevenzip_supports_rar(exe: Path) -> bool:
    out = _run([str(exe), "i"], timeout=10)
    return bool(re.search(r"\bRar5?\b", out))


def _ffmpeg_encoders(exe: Path) -> frozenset[str]:
    out = _run([str(exe), "-hide_banner", "-encoders"], timeout=20)
    names = set()
    for line in out.splitlines():
        m = re.match(r"^\s*[VAS][\.FXSBD]{5}\s+(\S+)", line)
        if m:
            names.add(m.group(1))
    return frozenset(names)


def _module_ok(name: str) -> bool:
    try:
        importlib.import_module(name)
        return True
    except Exception:  # noqa: BLE001 - any import failure means "not available"
        return False


# ---------------------------------------------------------------------------
# full detection
# ---------------------------------------------------------------------------

def detect() -> Engines:
    infos: dict[str, EngineInfo] = {}
    tokens: set[str] = {"pillow", "builtin"}
    encoders: frozenset[str] = frozenset()

    # FFmpeg ---------------------------------------------------------------
    exe, src = find_ffmpeg()
    if exe:
        encoders = _ffmpeg_encoders(exe)
        version_out = _run([str(exe), "-hide_banner", "-version"], timeout=10)
        m = re.search(r"ffmpeg version (\S+)", version_out)
        ok = bool(encoders)
        infos["ffmpeg"] = EngineInfo("ffmpeg", "FFmpeg", ok, str(exe), m.group(1) if m else "",
                                     src, "GPL-3.0 (build incluída)",
                                     f"{len(encoders)} codificadores")
        if ok:
            tokens.add("ffmpeg")
            tokens.update(f"ffmpeg:{e}" for e in encoders)
    else:
        infos["ffmpeg"] = EngineInfo("ffmpeg", "FFmpeg", False, detail="Áudio e vídeo")

    # Pandoc ---------------------------------------------------------------
    exe, src = find_pandoc()
    if exe:
        out = _run([str(exe), "--version"], timeout=15)
        m = re.search(r"pandoc(?:\.exe)? (\d[\d.]*)", out)
        ok = bool(m)
        infos["pandoc"] = EngineInfo("pandoc", "Pandoc", ok, str(exe), m.group(1) if m else "",
                                     src, "GPL-2.0-or-later", "Documentos e e-books")
        if ok:
            tokens.add("pandoc")
    else:
        infos["pandoc"] = EngineInfo("pandoc", "Pandoc", False, detail="Documentos e e-books")

    # LibreOffice ----------------------------------------------------------
    exe, src = find_libreoffice()
    if exe:
        version = ""
        ini = exe.parent / "version.ini"
        if ini.is_file():
            m = re.search(r"MsiProductVersion=(\S+)", ini.read_text(errors="ignore"))
            version = m.group(1) if m else ""
        infos["libreoffice"] = EngineInfo("libreoffice", "LibreOffice", True, str(exe), version,
                                          src, "MPL-2.0", "Office: DOC, PPT, XLS, ODF, PDF")
        tokens.add("libreoffice")
    else:
        infos["libreoffice"] = EngineInfo("libreoffice", "LibreOffice", False,
                                          detail="Incluído apenas na edição completa")

    # 7-Zip ----------------------------------------------------------------
    exe, src = find_sevenzip()
    if exe:
        rar = _sevenzip_supports_rar(exe)
        infos["sevenzip"] = EngineInfo("sevenzip", "7-Zip", True, str(exe), "", src,
                                       "LGPL-2.1 + restrição unRAR",
                                       "RAR e 7Z" if rar else "7Z (sem RAR)")
        tokens.add("sevenzip")
        if rar:
            tokens.add("sevenzip:rar")
    else:
        infos["sevenzip"] = EngineInfo("sevenzip", "7-Zip", False, detail="Extração de RAR e 7Z")

    # Python libraries ----------------------------------------------------
    libs = [
        ("pymupdf", "pymupdf", "PyMuPDF", "AGPL-3.0"),
        ("pdf2docx", "pdf2docx", "pdf2docx", "MIT"),
        ("docx", "docx", "python-docx", "MIT"),
        ("pptx", "pptx", "python-pptx", "MIT"),
        ("openpyxl", "openpyxl", "openpyxl", "MIT"),
        ("xlrd", "xlrd", "xlrd", "BSD-3-Clause"),
    ]
    for token, module, name, lic in libs:
        ok = _module_ok(module)
        infos[token] = EngineInfo(token, name, ok, source="biblioteca", license=lic)
        if ok:
            tokens.add(token)

    # Pillow plugins ------------------------------------------------------
    try:
        import pillow_heif

        info = pillow_heif.libheif_info()
        tokens.add("heif")
        if info.get("HEIF") or any("hevc" in str(v).lower() or "x265" in str(v).lower()
                                   for v in (info.get("encoders") or {}).values()):
            tokens.add("heif_enc")
        infos["heif"] = EngineInfo("heif", "pillow-heif (libheif)", True, source="biblioteca",
                                   version=str(info.get("libheif", "")),
                                   license="BSD-3 / LGPL-3 / GPL-2 (x265)")
    except Exception:  # noqa: BLE001
        infos["heif"] = EngineInfo("heif", "pillow-heif (libheif)", False, detail="HEIC")
    try:
        from PIL import features

        if features.check("avif"):
            tokens.update({"avif", "avif_enc"})
    except Exception:  # noqa: BLE001
        pass
    if "avif" not in tokens and _module_ok("pillow_avif"):
        tokens.update({"avif", "avif_enc"})

    # Qt helpers -----------------------------------------------------------
    if _module_ok("PySide6.QtSvg"):
        tokens.add("qtsvg")
    if _module_ok("PySide6.QtGui"):
        tokens.add("qtpdf")

    return Engines(infos=infos, ffmpeg_encoders=encoders, tokens=frozenset(tokens))


_cache: Engines | None = None
_lock = threading.Lock()


def get(refresh: bool = False) -> Engines:
    """Cached detection (thread-safe)."""
    global _cache
    with _lock:
        if _cache is None or refresh:
            _cache = detect()
            log.info("Motores: %s", ", ".join(sorted(t for t in _cache.tokens if ":" not in t)))
        return _cache


def python_runtime() -> str:
    return f"Python {sys.version.split()[0]}"
