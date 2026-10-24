"""Safe, never-overwriting output names."""
from __future__ import annotations

import os
import re
from pathlib import Path

from alfred.core.formats import COMPOUND_SUFFIXES

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def sanitize(name: str, fallback: str = "arquivo") -> str:
    """Make a single path component valid on Windows."""
    name = _INVALID.sub("_", name).strip().rstrip(". ")
    if not name:
        name = fallback
    base = name.split(".")[0].lower()
    if base in _RESERVED:
        name = "_" + name
    return name[:200]


def split_name(name: str) -> tuple[str, str]:
    lower = name.lower()
    for suffix in COMPOUND_SUFFIXES:
        if lower.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)], name[-len(suffix):]
    p = Path(name)
    if p.suffix and p.stem:
        return p.stem, p.suffix
    return name, ""


def unique_path(directory: Path, name: str) -> Path:
    """``directory/name`` or ``directory/name (2)`` … — never an existing path."""
    directory = Path(directory)
    candidate = directory / name
    if not os.path.lexists(candidate):
        return candidate
    base, ext = split_name(name)
    for n in range(2, 100000):
        candidate = directory / f"{base} ({n}){ext}"
        if not os.path.lexists(candidate):
            return candidate
    raise RuntimeError("Não foi possível escolher um nome livre para o arquivo de saída.")


def move_without_overwrite(src: Path, directory: Path, name: str) -> Path:
    """Move ``src`` into ``directory`` under ``name`` (or a free variant)."""
    for _ in range(50):
        dest = unique_path(directory, name)
        try:
            if os.name == "nt":
                os.rename(src, dest)  # fails if dest exists: never overwrites
            else:
                if os.path.lexists(dest):
                    continue
                os.rename(src, dest)
            return dest
        except FileExistsError:
            continue
        except OSError as exc:
            # Different volume (should not happen: staging lives in the same folder)
            if getattr(exc, "errno", None) == 18 or getattr(exc, "winerror", None) == 17:
                import shutil

                if os.path.lexists(dest):
                    continue
                shutil.move(str(src), str(dest))
                return dest
            raise
    raise RuntimeError("Não foi possível gravar o arquivo de saída sem sobrescrever outro.")
