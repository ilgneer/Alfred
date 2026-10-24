"""Copies the license files of every installed Python distribution.

    python tools/collect_licenses.py <pasta_destino>

Also writes INDEX.md with name, version and declared license of each package
that ends up inside the build (inventory of dependencies).
"""
from __future__ import annotations

import shutil
import sys
from importlib import metadata
from pathlib import Path

SKIP = {"pip", "setuptools", "wheel", "pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile",
        "pywin32-ctypes", "macholib", "packaging", "pytest", "pytest-qt", "ruff", "iniconfig", "pluggy",
        "pygments"}
LICENSE_HINTS = ("LICEN", "COPYING", "NOTICE", "AUTHORS", "COPYRIGHT")


def declared_license(dist: metadata.Distribution) -> str:
    md = dist.metadata
    expr = md.get("License-Expression")
    if expr:
        return expr
    lic = (md.get("License") or "").strip()
    if lic and len(lic) < 80 and "\n" not in lic:
        return lic
    classifiers = [c.split("::")[-1].strip() for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    return ", ".join(classifiers) or (lic[:60] + "…" if lic else "ver arquivos")


def main(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    for dist in sorted(metadata.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name = dist.metadata["Name"]
        if not name or name.lower() in SKIP:
            continue
        folder = dest / f"{name}-{dist.version}"
        copied = 0
        for f in dist.files or []:
            fname = Path(str(f)).name.upper()
            if any(h in fname for h in LICENSE_HINTS):
                src = Path(dist.locate_file(f))
                if src.is_file():
                    folder.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, folder / Path(str(f)).name)
                    copied += 1
        rows.append((name, dist.version, declared_license(dist), copied))
    lines = ["# Pacotes Python incluídos\n", "| Pacote | Versão | Licença declarada | Arquivos de licença |",
             "|---|---|---|---|"]
    lines += [f"| {n} | {v} | {lic} | {c} |" for n, v, lic, c in rows]
    (dest / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} pacotes inventariados em {dest}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "build/licenses-python"))
