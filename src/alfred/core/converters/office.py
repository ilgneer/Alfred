"""Thin wrappers around LibreOffice, Pandoc and Qt's PDF writer."""
from __future__ import annotations

import html
import logging
import shutil
import uuid
from pathlib import Path

from alfred.core import paths, procs
from alfred.core.context import ConvertContext

log = logging.getLogger(__name__)

LO_FILTERS = {
    "docx": "docx:MS Word 2007 XML",
    "doc": "doc:MS Word 97",
    "odt": "odt",
    "rtf": "rtf:Rich Text Format",
    "pdf": "pdf",
    "txt": "txt:Text (encoded):UTF8",
    "pptx": "pptx:Impress MS PowerPoint 2007 XML",
    "ppt": "ppt:MS PowerPoint 97",
    "odp": "odp",
    "xlsx": "xlsx:Calc MS Excel 2007 XML",
    "xls": "xls:MS Excel 97",
    "ods": "ods",
    # UTF-8, all sheets (one file per sheet), values as shown
    "csv": "csv:Text - txt - csv (StarCalc):44,34,76,1,,0,false,true,true,false,false,-1",
    "tsv": "csv:Text - txt - csv (StarCalc):9,34,76,1,,0,false,true,true,false,false,-1",
}


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------

def read_text(path: Path) -> str:
    """Decode a text file trying UTF-8 (with/without BOM), UTF-16 and Windows-1252."""
    data = Path(path).read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def text_to_html(text: str, title: str) -> str:
    paragraphs = [p for p in text.replace("\r\n", "\n").replace("\r", "\n").split("\n\n")]
    body = "\n".join(
        "<p>" + "<br/>".join(html.escape(line) for line in p.split("\n")) + "</p>"
        for p in paragraphs if p.strip()
    )
    return (f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title>"
            f"</head><body>{body}</body></html>")


# ---------------------------------------------------------------------------
# LibreOffice
# ---------------------------------------------------------------------------

def _lo_profile() -> Path:
    p = paths.data_dir() / "libreoffice-profile"
    p.mkdir(parents=True, exist_ok=True)
    return p


def lo_convert(ctx: ConvertContext, src: Path, fmt: str, infilter: str | None = None) -> list[Path]:
    """Convert with LibreOffice; returns produced files inside ``ctx.scratch``."""
    exe = ctx.engines.path("libreoffice")
    out_filter = LO_FILTERS[fmt]
    # Work on a copy with a simple name: avoids issues with exotic characters
    # in URLs and never lets LibreOffice touch the original file.
    work = ctx.scratch / f"lo-{uuid.uuid4().hex[:8]}"
    work.mkdir()
    local = work / ("entrada" + src.suffix.lower())
    shutil.copy2(src, local)
    outdir = work / "saida"
    outdir.mkdir()

    def attempt(profile: Path) -> list[Path]:
        args = [exe, f"-env:UserInstallation={profile.as_uri()}", "--headless", "--invisible",
                "--nologo", "--norestore", "--nodefault", "--nolockcheck"]
        if infilter:
            args.append(f"--infilter={infilter}")
        args += ["--convert-to", out_filter, "--outdir", outdir, local]
        ctx.run(args, timeout=900)
        return sorted(p for p in outdir.iterdir() if p.is_file())

    ctx.progress(None, "LibreOffice convertendo")
    try:
        produced = attempt(_lo_profile())
    except procs.ProcessError as exc:
        log.warning("LibreOffice falhou com o perfil persistente: %s", exc)
        produced = []
    if not produced:
        # stale/locked profile: retry once with a throw-away profile
        produced = attempt(ctx.scratch / f"lo-profile-{uuid.uuid4().hex[:6]}")
    if not produced:
        raise RuntimeError("O LibreOffice não conseguiu converter este arquivo.")
    return produced


# ---------------------------------------------------------------------------
# Pandoc
# ---------------------------------------------------------------------------
PANDOC_FROM = {
    "docx": "docx", "odt": "odt", "rtf": "rtf", "epub": "epub",
    "md": "markdown", "markdown": "markdown", "html": "html", "htm": "html",
}
PANDOC_TO = {
    "docx": "docx", "odt": "odt", "rtf": "rtf", "epub": "epub",
    "txt": "plain", "md": "gfm", "html": "html5",
}


def prepare_pandoc_input(ctx: ConvertContext, src: Path, ext: str) -> tuple[Path, str]:
    """Return (file, pandoc reader); normalises text encodings to UTF-8."""
    if ext == "txt":
        f = ctx.scratch / "entrada.html"
        f.write_text(text_to_html(read_text(src), src.stem), encoding="utf-8")
        return f, "html"
    if ext in ("md", "markdown", "html", "htm"):
        f = ctx.scratch / f"entrada-{uuid.uuid4().hex[:6]}.{ext}"
        f.write_text(read_text(src), encoding="utf-8")
        return f, PANDOC_FROM[ext]
    return src, PANDOC_FROM[ext]


def pandoc(ctx: ConvertContext, src: Path, ext: str, dst: Path, to: str, title: str,
           extract_media: str | None = None, cwd: Path | None = None) -> None:
    exe = ctx.engines.path("pandoc")
    inp, reader = prepare_pandoc_input(ctx, src, ext)
    writer = PANDOC_TO[to]
    args = [exe, inp, "-f", reader, "-t", writer, "-o", dst, f"--resource-path={src.parent}"]
    if to in ("html", "rtf"):
        args.append("--standalone")
    if to == "html":
        args += ["--embed-resources", "--metadata", f"pagetitle={title}"]
    if to == "epub":
        args += ["--metadata", f"title={title}"]
    if to in ("txt", "md"):
        args.append("--wrap=none")
    if extract_media:
        args.append(f"--extract-media={extract_media}")
    ctx.progress(None, "Pandoc convertendo")
    ctx.run(args, timeout=900, cwd=cwd)
    if not dst.exists() or dst.stat().st_size == 0:
        raise RuntimeError("O Pandoc não gerou o arquivo de saída.")


# ---------------------------------------------------------------------------
# Qt PDF (HTML / text -> PDF without LibreOffice)
# ---------------------------------------------------------------------------
PDF_CSS = """
body { font-family: 'Segoe UI', 'Noto Sans', 'DejaVu Sans', sans-serif; font-size: 11pt; color: #111; }
h1 { font-size: 20pt; } h2 { font-size: 16pt; } h3 { font-size: 13pt; }
pre, code { font-family: 'Cascadia Mono', 'Consolas', 'DejaVu Sans Mono', monospace; font-size: 9.5pt; }
table { border-collapse: collapse; } td, th { border: 1px solid #999; padding: 3px; }
img { max-width: 100%; }
"""


def html_to_pdf(html_text: str, dst: Path, base_dir: Path | None = None, title: str = "") -> None:
    from PySide6.QtCore import QMarginsF, QUrl
    from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument

    from alfred.core.converters.images import _ensure_qt_app

    _ensure_qt_app()
    writer = QPdfWriter(str(dst))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(18, 18, 18, 18), QPageLayout.Unit.Millimeter)
    writer.setResolution(300)
    writer.setTitle(title)
    writer.setCreator("Alfred")
    doc = QTextDocument()
    if base_dir:
        doc.setBaseUrl(QUrl.fromLocalFile(str(base_dir) + "/"))
    doc.setDefaultStyleSheet(PDF_CSS)
    doc.setHtml(html_text)
    doc.print_(writer)
    if not dst.exists() or dst.stat().st_size == 0:
        raise RuntimeError("Não foi possível gerar o PDF.")


def text_to_pdf(text: str, dst: Path, title: str) -> None:
    body = html.escape(text.replace("\r\n", "\n"))
    html_text = (f"<html><head><meta charset='utf-8'><title>{html.escape(title)}</title></head>"
                 f"<body><div style='white-space: pre-wrap;'>{body}</div></body></html>")
    html_to_pdf(html_text, dst, title=title)
