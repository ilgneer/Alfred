"""Headless self-test of a built/installed Alfred (used by CI and support).

    Alfred.exe --self-test relatorio.json

Generates small sample files, runs representative conversions through the
real engines bundled with this build and writes a JSON report. Exit code 0
means every check that this edition promises passed.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback
import zipfile
from pathlib import Path

from alfred import __version__
from alfred.core import engines as engines_mod
from alfred.core import paths, routes
from alfred.core.context import Options
from alfred.core.jobs import DONE, Job, run_job


def _samples(root: Path) -> dict[str, Path]:
    from PIL import Image, ImageDraw

    out = {}
    img = Image.new("RGB", (200, 120), (8, 9, 13))
    ImageDraw.Draw(img).ellipse((20, 10, 120, 110), fill=(212, 175, 55))
    out["png"] = root / "Imagem de teste ção.png"
    img.save(out["png"])
    out["svg"] = root / "vetor.svg"
    out["svg"].write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="60">'
                          '<rect width="100" height="60" fill="#D4AF37"/></svg>', encoding="utf-8")
    out["txt"] = root / "Texto ação.txt"
    out["txt"].write_text("Alfred Conversão\n\nSegundo parágrafo.\n", encoding="utf-8")
    out["md"] = root / "Notas.md"
    out["md"].write_text("# Título\n\nAlfred **Conversão**\n", encoding="utf-8")
    out["srt"] = root / "legenda.srt"
    out["srt"].write_text("1\n00:00:01,000 --> 00:00:02,000\nOlá\n", encoding="utf-8")
    out["csv"] = root / "dados.csv"
    out["csv"].write_bytes("a;b\nCafé;1,5\n".encode("cp1252"))
    out["zip"] = root / "pacote.zip"
    with zipfile.ZipFile(out["zip"], "w") as z:
        z.writestr("pasta/olá.txt", "ok")
    from docx import Document

    d = Document()
    d.add_paragraph("Alfred Conversão")
    out["docx"] = root / "Documento.docx"
    d.save(out["docx"])
    import pymupdf

    pdf = pymupdf.open()
    pdf.new_page().insert_text((72, 72), "Alfred Conversao")
    out["pdf"] = root / "Arquivo.pdf"
    pdf.save(str(out["pdf"]))
    return out


def _wav(root: Path, eng) -> Path | None:
    if not eng.has("ffmpeg"):
        return None
    import subprocess

    f = root / "som.wav"
    subprocess.run([eng.path("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "sine=duration=1", str(f)],
                   check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), stdin=subprocess.DEVNULL)
    return f


CHECKS = [
    # (sample, target, engines required, required in edition)
    ("png", "jpg", ("pillow",), "all"),
    ("png", "webp", ("pillow",), "all"),
    ("png", "heic", ("heif_enc",), "all"),
    ("png", "avif", ("avif_enc",), "all"),
    ("svg", "png", ("qtsvg",), "all"),
    ("svg", "pdf", ("qtsvg", "qtpdf"), "all"),
    ("txt", "pdf", ("qtpdf",), "all"),
    ("md", "docx", ("pandoc",), "all"),
    ("md", "html", ("pandoc",), "all"),
    ("docx", "md", ("pandoc",), "all"),
    ("srt", "vtt", ("builtin",), "all"),
    ("csv", "xlsx", ("openpyxl",), "all"),
    ("zip", "extract", ("builtin",), "all"),
    ("pdf", "png_pages", ("pymupdf",), "all"),
    ("pdf", "docx", ("pdf2docx",), "all"),
    ("wav", "mp3", ("ffmpeg:libmp3lame",), "all"),
    ("wav", "opus", ("ffmpeg:libopus",), "all"),
    ("docx", "pdf", ("libreoffice",), "completa"),
    ("csv", "ods", ("libreoffice",), "completa"),
]


def run_self_test(report_path: str) -> int:
    started = time.time()
    if sys.platform != "win32" and not os.environ.get("DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])  # noqa: F841 - needed by QtSvg/QPdfWriter
    edition = paths.edition()
    report: dict = {"version": __version__, "edition": edition, "frozen": paths.is_frozen(),
                    "install_dir": str(paths.install_dir()), "checks": [], "engines": {}}
    ok = True
    try:
        eng = engines_mod.get(refresh=True)
        report["engines"] = {k: {"available": v.available, "version": v.version, "source": v.source, "path": v.path}
                             for k, v in eng.infos.items()}
        report["tokens"] = sorted(t for t in eng.tokens if not t.startswith("ffmpeg:"))
        with tempfile.TemporaryDirectory(prefix="alfred-selftest-") as td:
            root = Path(td)
            samples = _samples(root)
            wav = _wav(root, eng)
            if wav:
                samples["wav"] = wav
            out_dir = root / "saida"
            for sample, target, needs, required_in in CHECKS:
                required = required_in == "all" or required_in == edition
                entry = {"sample": sample, "target": target, "required": required}
                if sample not in samples or not eng.has_all(needs):
                    entry["result"] = "missing-engine"
                    entry["missing"] = [n for n in needs if not eng.has(n)]
                    ok = ok and not required
                    report["checks"].append(entry)
                    continue
                src = samples[sample]
                choice = next((c for c in routes.choices_for([src], eng) if c.target.key == target), None)
                if choice is None:
                    entry["result"] = "not-offered"
                    ok = ok and not required
                    report["checks"].append(entry)
                    continue
                t0 = time.time()
                job = run_job(Job(files=[src], target=choice.target), eng,
                              Options(output_mode="custom", custom_output_dir=str(out_dir), pdf_dpi=100))
                entry.update(result=job.state, seconds=round(time.time() - t0, 2), errors=job.errors,
                             outputs=[Path(o).name for o in job.outputs])
                if job.state != DONE:
                    ok = ok and not required
                report["checks"].append(entry)
    except Exception:  # noqa: BLE001
        ok = False
        report["exception"] = traceback.format_exc()
    report["ok"] = ok
    report["seconds"] = round(time.time() - started, 2)
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if ok else 1
