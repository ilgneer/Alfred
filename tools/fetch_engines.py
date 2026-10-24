"""Prepares vendor/engines/ with the third-party engines bundled in Alfred.

    python tools/fetch_engines.py --edition full   # FFmpeg, Pandoc, 7-Zip, LibreOffice
    python tools/fetch_engines.py --edition lite   # FFmpeg, Pandoc, 7-Zip

Sources (all official, all redistributable — see THIRD_PARTY_NOTICES.md):
  FFmpeg       binary shipped in the `imageio-ffmpeg` wheel (pip)
  Pandoc       binary shipped in the `pypandoc_binary` wheel (pip)
  7-Zip        existing installation (GitHub runners have it) or `choco install 7zip`
  LibreOffice  existing installation or `choco install libreoffice-still`

Each engine folder also receives its license and a SOURCE.txt describing the
exact version and where its source code can be obtained.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IS_WIN = os.name == "nt"
EXE = ".exe" if IS_WIN else ""


def log(msg: str) -> None:
    print(f"[engines] {msg}", flush=True)


def _version_line(exe: Path, *args: str) -> str:
    try:
        out = subprocess.run([str(exe), *args], capture_output=True, text=True, timeout=60,
                             encoding="utf-8", errors="replace")
        return (out.stdout or out.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return f"(versão indisponível: {exc})"


def ffmpeg(out: Path) -> None:
    import imageio_ffmpeg

    bins = Path(imageio_ffmpeg.__file__).parent / "binaries"
    cands = [p for p in bins.glob("ffmpeg*") if p.is_file() and p.suffix.lower() not in (".md", ".py", ".txt", ".pyc")]
    if not cands:
        raise SystemExit("imageio-ffmpeg sem binário para esta plataforma")
    dest = out / "ffmpeg"
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"ffmpeg{EXE}"
    shutil.copy2(cands[0], target)
    target.chmod(0o755)
    shutil.copy2(ROOT / "licenses" / "GPL-3.0.txt", dest / "LICENSE-GPL-3.0.txt")
    info = _version_line(target, "-hide_banner", "-version")
    (dest / "SOURCE.txt").write_text(
        "FFmpeg — https://ffmpeg.org\n"
        "Binário distribuído pelo projeto imageio-ffmpeg (https://github.com/imageio/imageio-ffmpeg),\n"
        "compilado com --enable-gpl --enable-version3: licença GPL-3.0-or-later.\n"
        "Código-fonte correspondente: https://ffmpeg.org/releases/ (mesma versão abaixo) e o\n"
        "arquivo third-party-sources anexado a cada Release do Alfred no GitHub.\n\n" + info + "\n",
        encoding="utf-8")
    log(f"FFmpeg: {info.splitlines()[0] if info else '?'}")


def pandoc(out: Path) -> None:
    spec = importlib.util.find_spec("pypandoc")
    if not spec or not spec.origin:
        raise SystemExit("pypandoc_binary não instalado")
    src = Path(spec.origin).parent / "files" / f"pandoc{EXE}"
    if not src.exists():
        raise SystemExit(f"Pandoc não encontrado em {src}")
    dest = out / "pandoc"
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"pandoc{EXE}"
    shutil.copy2(src, target)
    target.chmod(0o755)
    shutil.copy2(ROOT / "licenses" / "GPL-2.0.txt", dest / "LICENSE-GPL-2.0.txt")
    info = _version_line(target, "--version")
    version = info.split()[1] if info.startswith("pandoc") and len(info.split()) > 1 else "?"
    (dest / "SOURCE.txt").write_text(
        "Pandoc — https://pandoc.org — © John MacFarlane, GPL-2.0-or-later\n"
        f"Código-fonte: https://github.com/jgm/pandoc/releases/tag/{version}\n\n" + info + "\n", encoding="utf-8")
    log(f"Pandoc {version}")


def _program_files() -> list[Path]:
    return [Path(os.environ[v]) for v in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)") if os.environ.get(v)]


def _choco(package: str) -> None:
    log(f"instalando {package} via Chocolatey…")
    subprocess.run(["choco", "install", package, "-y", "--no-progress", "--limit-output"], check=True)


def sevenzip(out: Path) -> None:
    dest = out / "7zip"
    dest.mkdir(parents=True, exist_ok=True)
    if IS_WIN:
        home = next((p / "7-Zip" for p in _program_files() if (p / "7-Zip" / "7z.exe").exists()), None)
        if home is None:
            _choco("7zip")
            home = next(p / "7-Zip" for p in _program_files() if (p / "7-Zip" / "7z.exe").exists())
        for name in ("7z.exe", "7z.dll", "License.txt", "readme.txt"):
            if (home / name).exists():
                shutil.copy2(home / name, dest / name)
    else:  # development builds on Linux
        exe = shutil.which("7z") or shutil.which("7zz")
        if not exe:
            raise SystemExit("7-Zip não encontrado")
        real = Path(exe).resolve()
        shutil.copy2(real, dest / "7z")
        (dest / "7z").chmod(0o755)
    shutil.copy2(ROOT / "licenses" / "LGPL-2.1.txt", dest / "LICENSE-LGPL-2.1.txt")
    (dest / "SOURCE.txt").write_text(
        "7-Zip — https://www.7-zip.org — © Igor Pavlov. GNU LGPL-2.1 + BSD-3 + restrição unRAR\n"
        "(o código unRAR não pode ser usado para recriar o algoritmo de compressão RAR).\n"
        "Código-fonte: https://www.7-zip.org/download.html\n", encoding="utf-8")
    log("7-Zip copiado")


def libreoffice(out: Path) -> None:
    dest = out / "libreoffice"
    if dest.exists():
        shutil.rmtree(dest)
    if IS_WIN:
        home = next((p / "LibreOffice" for p in _program_files()
                     if (p / "LibreOffice" / "program" / "soffice.exe").exists()), None)
        if home is None:
            _choco("libreoffice-still")
            home = next(p / "LibreOffice" for p in _program_files()
                        if (p / "LibreOffice" / "program" / "soffice.exe").exists())
        log(f"copiando LibreOffice de {home} (pode levar alguns minutos)…")
        shutil.copytree(home, dest, ignore=shutil.ignore_patterns("help", "*.log"))
    else:
        raise SystemExit("A edição completa (com LibreOffice) é montada apenas no Windows.")
    shutil.copy2(ROOT / "licenses" / "MPL-2.0.txt", dest / "LICENSE-MPL-2.0.txt")
    ver = ""
    ini = dest / "program" / "version.ini"
    if ini.exists():
        for line in ini.read_text(errors="ignore").splitlines():
            if line.startswith("MsiProductVersion="):
                ver = line.split("=", 1)[1]
    (dest / "SOURCE.txt").write_text(
        f"LibreOffice {ver} — https://www.libreoffice.org — Mozilla Public License 2.0\n"
        "Avisos completos de licença: LICENSE.html e NOTICE nesta pasta.\n"
        "Código-fonte: https://download.documentfoundation.org/libreoffice/src/\n", encoding="utf-8")
    log(f"LibreOffice {ver} copiado")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--edition", choices=("full", "lite"), default="full")
    p.add_argument("--out", default=str(ROOT / "vendor" / "engines"))
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ffmpeg(out)
    pandoc(out)
    sevenzip(out)
    if a.edition == "full":
        libreoffice(out)
    (out / "edition.txt").write_text(a.edition, encoding="utf-8")
    log(f"pronto em {out}")


if __name__ == "__main__":
    sys.exit(main())
