"""Per-conversion context: staging of outputs, progress, cancellation.

Converters never write to the final destination directly. They write into a
hidden staging folder created *inside* the destination folder (same volume),
and only after the converter returns successfully the files are renamed to
their final, never-overwriting names. A failure or a cancellation therefore
leaves no partial file behind and the original is never touched.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from alfred.core import naming, paths, procs
from alfred.core.engines import Engines
from alfred.core.settings import SUBFOLDER_NAME, Settings

log = logging.getLogger(__name__)

CRF = {"compact": 28, "balanced": 23, "high": 18}
CRF_VP9 = {"compact": 38, "balanced": 32, "high": 26}


@dataclass
class Options:
    jpg_quality: int = 92
    pdf_dpi: int = 300
    video_quality: str = "balanced"
    output_mode: str = "same"
    custom_output_dir: str = ""

    @classmethod
    def from_settings(cls, s: Settings) -> Options:
        return cls(s.jpg_quality, s.pdf_dpi, s.video_quality, s.output_mode, s.custom_output_dir)

    @property
    def crf(self) -> int:
        return CRF.get(self.video_quality, 23)

    @property
    def crf_vp9(self) -> int:
        return CRF_VP9.get(self.video_quality, 32)


def resolve_output_dir(src: Path, options: Options) -> Path:
    src = Path(src)
    if options.output_mode == "custom" and options.custom_output_dir:
        return Path(options.custom_output_dir)
    base = src.parent
    if options.output_mode == "subfolder":
        return base / SUBFOLDER_NAME
    return base


def _writable(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".alfred-probe-", dir=directory)
        os.close(fd)
        os.unlink(tmp)
        return True
    except OSError:
        return False


def _hide(path: Path) -> None:
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02)  # HIDDEN
        except Exception:  # noqa: BLE001
            pass


class ConvertContext:
    def __init__(
        self,
        engines: Engines,
        options: Options,
        token: procs.CancelToken | None = None,
        progress: Callable[[float | None, str], None] | None = None,
    ):
        self.engines = engines
        self.options = options
        self.token = token or procs.CancelToken()
        self._progress = progress
        self._staging: Path | None = None
        self._final_dir: Path | None = None
        self._scratch: tempfile.TemporaryDirectory | None = None
        self.notes: list[str] = []

    # -- progress / cancel ----------------------------------------------------
    def progress(self, fraction: float | None, text: str = "") -> None:
        self.token.check()
        if self._progress:
            self._progress(None if fraction is None else max(0.0, min(1.0, fraction)), text)

    def check(self) -> None:
        self.token.check()

    def run(self, args, **kw) -> str:
        return procs.run(args, token=self.token, **kw)

    # -- staging ----------------------------------------------------------------
    def begin(self, src: Path) -> Path:
        """Prepare staging for one source file; returns the final directory."""
        final_dir = resolve_output_dir(src, self.options)
        if not _writable(final_dir):
            fallback = paths.documents_fallback_dir()
            self.notes.append(f"Sem permissão em “{final_dir}”. Salvo em “{fallback}”.")
            final_dir = fallback
        staging = final_dir / f".alfred-{uuid.uuid4().hex[:10]}"
        staging.mkdir(parents=True)
        _hide(staging)
        self._final_dir = final_dir
        self._staging = staging
        return final_dir

    def stage(self, name: str) -> Path:
        """Path (inside staging) where a converter writes an output named ``name``."""
        if self._staging is None:
            raise RuntimeError("begin() não foi chamado")
        return self._staging / naming.sanitize(name)

    @property
    def staging_dir(self) -> Path:
        if self._staging is None:
            raise RuntimeError("begin() não foi chamado")
        return self._staging

    def stage_dir(self, name: str) -> Path:
        p = self.stage(name)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def scratch(self) -> Path:
        """Private temporary folder (outside the destination) for intermediates."""
        if self._scratch is None:
            self._scratch = tempfile.TemporaryDirectory(prefix="alfred-")
        return Path(self._scratch.name)

    def commit(self) -> list[Path]:
        """Move staged outputs to their final names; never overwrites."""
        assert self._staging is not None and self._final_dir is not None
        results = []
        for item in sorted(self._staging.iterdir()):
            if item.is_file() and item.stat().st_size == 0:
                raise RuntimeError(f"O conversor gerou um arquivo vazio: {item.name}")
            results.append(naming.move_without_overwrite(item, self._final_dir, item.name))
        if not results:
            raise RuntimeError("O conversor terminou sem gerar nenhum arquivo.")
        self.discard()
        return results

    def discard(self) -> None:
        if self._staging is not None:
            shutil.rmtree(self._staging, ignore_errors=True)
            self._staging = None
        if self._scratch is not None:
            self._scratch.cleanup()
            self._scratch = None
