"""Builds the distributable folder dist/Alfred (PyInstaller + engines + licenses).

    python tools/build.py --edition full --engines vendor/engines
    python tools/build.py --edition lite --engines vendor/engines

Steps
  1. writes src/alfred/_build_info.py (repository URL, edition, commit)
  2. writes build/version_info.txt (Windows file properties of Alfred.exe)
  3. runs PyInstaller with packaging/alfred.spec (windowed: no console)
  4. copies the engines prepared by tools/fetch_engines.py into dist/Alfred/engines
  5. copies LICENSE, third-party licenses and notices
  6. verifies the result
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from alfred import __version__  # noqa: E402

EXE = ".exe" if os.name == "nt" else ""
ENGINE_FILES = {
    "ffmpeg": [f"ffmpeg/ffmpeg{EXE}"],
    "pandoc": [f"pandoc/pandoc{EXE}"],
    "7zip": [f"7zip/7z{EXE}"],
    "libreoffice": [f"libreoffice/program/soffice{EXE}"],
}


def run(cmd: list[str], **kw) -> None:
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kw)


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "local"


def write_build_info(edition: str, repo_url: str) -> None:
    (ROOT / "src" / "alfred" / "_build_info.py").write_text(
        "# Gerado por tools/build.py — não editar.\n"
        f"REPO_URL = {repo_url!r}\nEDITION = {edition!r}\nCOMMIT = {git_commit()!r}\n", encoding="utf-8")


def write_version_info(version: str) -> None:
    parts = [int(p) for p in (version.split("-")[0].split(".") + ["0", "0", "0"])[:4]]
    t = tuple(parts)
    text = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
                    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041604B0', [
      StringStruct('CompanyName', '@ilgn3r'),
      StringStruct('FileDescription', 'Alfred — conversor universal de arquivos'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'Alfred'),
      StringStruct('LegalCopyright', 'Código: AGPL-3.0-or-later. Arte: todos os direitos reservados a @ilgn3r.'),
      StringStruct('OriginalFilename', 'Alfred.exe'),
      StringStruct('ProductName', 'Alfred'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1046, 1200])])
  ]
)
"""
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "version_info.txt").write_text(text, encoding="utf-8")


def copy_engines(engines_src: Path, dist: Path, edition: str) -> None:
    dest = dist / "engines"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    wanted = ["ffmpeg", "pandoc", "7zip"] + (["libreoffice"] if edition == "full" else [])
    for name in wanted:
        src = engines_src / name
        if not src.is_dir():
            raise SystemExit(f"Motor ausente em {src}. Rode tools/fetch_engines.py primeiro.")
        print(f"  copiando motor {name}…", flush=True)
        shutil.copytree(src, dest / name)
    (dest / "edition.txt").write_text(edition, encoding="utf-8")


def copy_licenses(dist: Path) -> None:
    lic = dist / "licenses"
    if lic.exists():
        shutil.rmtree(lic)
    shutil.copytree(ROOT / "licenses", lic)
    shutil.copy2(ROOT / "LICENSE", dist / "LICENSE.txt")
    for doc in ("THIRD_PARTY_NOTICES.md", "docs/ASSETS_E_DIREITOS.md", "docs/COMPATIBILIDADE.md"):
        f = ROOT / doc
        if f.exists():
            shutil.copy2(f, lic / f.name)
    # Python packages: copy every license file shipped in the installed distributions
    run([sys.executable, str(ROOT / "tools" / "collect_licenses.py"), str(lic / "python")])


def verify(dist: Path, edition: str) -> None:
    required = [dist / f"Alfred{EXE}", dist / "LICENSE.txt"]
    for name, files in ENGINE_FILES.items():
        if name == "libreoffice" and edition != "full":
            continue
        required += [dist / "engines" / f for f in files]
    missing = [str(p) for p in required if not p.exists()]
    internal = dist / "_internal" / "assets"
    if not (internal / "sounds" / "select.wav").exists() or not (internal / "fonts").is_dir():
        missing.append(str(internal))
    if missing:
        raise SystemExit("Build incompleto:\n  " + "\n  ".join(missing))
    size = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    print(f"OK — {dist} ({size / 1024 / 1024:.0f} MB)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--edition", choices=("full", "lite"), default="full")
    p.add_argument("--engines", default=str(ROOT / "vendor" / "engines"))
    p.add_argument("--repo-url", default=os.environ.get("ALFRED_REPO_URL", "https://github.com/ilgn3r/alfred"))
    p.add_argument("--version", default=__version__)
    p.add_argument("--skip-pyinstaller", action="store_true")
    a = p.parse_args()

    write_build_info(a.edition, a.repo_url)
    write_version_info(a.version)
    dist = ROOT / "dist" / "Alfred"
    if not a.skip_pyinstaller:
        run([sys.executable, "-m", "PyInstaller", str(ROOT / "packaging" / "alfred.spec"), "--noconfirm", "--clean",
             "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build" / "pyinstaller")])
    copy_engines(Path(a.engines), dist, a.edition)
    copy_licenses(dist)
    verify(dist, a.edition)


if __name__ == "__main__":
    main()
