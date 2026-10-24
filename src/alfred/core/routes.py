"""Declarative registry of every conversion Alfred offers.

This table is the single source of truth:

* the radial wheel only shows targets whose plan has all engines available;
* ``tools/gen_matrix.py`` renders ``docs/COMPATIBILIDADE.md`` from it;
* ``tests/test_routes_all.py`` executes every (source, target, plan) with a
  real fixture and validates the produced file.

A target is never offered without a real converter behind it.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from alfred.core import formats as F
from alfred.core.engines import Engines

STABLE = "estavel"
EXPERIMENTAL = "experimental"


@dataclass(frozen=True)
class Target:
    key: str
    label: str
    ext: str               # extension of the produced file ("" for folders)
    icon: str
    sublabel: str = ""
    batch: bool = False    # one output for the whole selection


@dataclass(frozen=True)
class Plan:
    requires: tuple[str, ...]
    method: str
    status: str = STABLE
    note: str = ""


@dataclass(frozen=True)
class Route:
    category: str
    target: str
    sources: frozenset[str]
    plans: tuple[Plan, ...]


@dataclass
class Choice:
    """A target offered for a concrete selection of files."""

    target: Target
    status: str
    files: list[Path] = field(default_factory=list)      # files that will be converted
    skipped: list[Path] = field(default_factory=list)    # already in that format


# ---------------------------------------------------------------------------
# targets
# ---------------------------------------------------------------------------
T: dict[str, Target] = {}


def _t(key, label, ext, icon, sublabel="", batch=False):
    T[key] = Target(key, label, ext, icon, sublabel, batch)


for _k, _sub in (("jpg", ""), ("png", ""), ("webp", ""), ("heic", ""), ("avif", ""),
                 ("tiff", ""), ("bmp", "")):
    _t(_k, _k.upper(), _k, "image", _sub)
_t("pdf", "PDF", "pdf", "pdf")
_t("pdf_merge", "PDF", "pdf", "merge", "único", batch=True)
for _k in ("mp3", "m4a", "wav", "flac", "ogg", "opus", "aiff", "wma"):
    _t(_k, _k.upper(), _k, "audio")
for _k in ("mp4", "mov", "mkv", "webm", "avi", "wmv"):
    _t(_k, _k.upper(), _k, "video")
_t("gif", "GIF", "gif", "gif")
_t("audio_mp3", "MP3", "mp3", "extract_audio", "só áudio")
_t("docx", "DOCX", "docx", "doc")
_t("doc", "DOC", "doc", "doc")
_t("odt", "ODT", "odt", "doc")
_t("rtf", "RTF", "rtf", "doc")
_t("txt", "TXT", "txt", "text")
_t("md", "MD", "md", "markdown", "Markdown")
_t("html", "HTML", "html", "code")
_t("epub", "EPUB", "epub", "book")
_t("pptx", "PPTX", "pptx", "slides")
_t("ppt", "PPT", "ppt", "slides")
_t("odp", "ODP", "odp", "slides")
_t("xlsx", "XLSX", "xlsx", "sheet")
_t("xls", "XLS", "xls", "sheet")
_t("ods", "ODS", "ods", "sheet")
_t("csv", "CSV", "csv", "table")
_t("tsv", "TSV", "tsv", "table")
_t("png_pages", "PNG", "", "pages", "páginas")
_t("jpg_pages", "JPG", "", "pages", "páginas")
_t("srt", "SRT", "srt", "subtitle")
_t("vtt", "VTT", "vtt", "subtitle")
_t("extract", "Extrair", "", "extract", "aqui")
_t("zip", "ZIP", "zip", "archive", "converter")
_t("zip_pack", "ZIP", "zip", "archive", "compactar", batch=True)

# canonical output format of each target (to skip "already in format")
TARGET_FORMAT = {k: F.canonical(t.ext) for k, t in T.items() if t.ext and not t.batch}
TARGET_FORMAT.update({"audio_mp3": "", "png_pages": "", "jpg_pages": ""})

# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------
ROUTES: list[Route] = []

# Extra engines needed just to *read* some inputs.
INPUT_REQUIRES: dict[str, tuple[str, ...]] = {
    "heic": ("heif",), "heif": ("heif",), "avif": ("avif",), "svg": ("qtsvg",),
}


def _r(category: str, target: str, sources: Iterable[str], *plans: Plan) -> None:
    ROUTES.append(Route(category, target, frozenset(sources), tuple(plans)))


def P(*requires: str, method: str, status: str = STABLE, note: str = "") -> Plan:
    return Plan(tuple(requires), method, status, note)


# Images ------------------------------------------------------------------
RASTER = F.EXTENSIONS[F.IMAGE] - {"svg"}
ALL_IMAGES = F.EXTENSIONS[F.IMAGE]
for key in ("jpg", "png", "webp", "tiff", "bmp"):
    _r(F.IMAGE, key, ALL_IMAGES, P("pillow", method="pillow"))
_r(F.IMAGE, "heic", ALL_IMAGES, P("pillow", "heif_enc", method="pillow"))
_r(F.IMAGE, "avif", ALL_IMAGES, P("pillow", "avif_enc", method="pillow"))
_r(F.IMAGE, "pdf", RASTER, P("pillow", method="pillow"))
_r(F.IMAGE, "pdf", {"svg"}, P("qtsvg", "qtpdf", method="svg_vector", note="PDF vetorial (SVG Tiny 1.2)"))
_r(F.IMAGE, "pdf_merge", ALL_IMAGES, P("pillow", method="merge"))

# Audio -------------------------------------------------------------------
AUD = F.EXTENSIONS[F.AUDIO]
_r(F.AUDIO, "mp3", AUD, P("ffmpeg:libmp3lame", method="ffmpeg"))
_r(F.AUDIO, "m4a", AUD, P("ffmpeg:aac", method="ffmpeg"))
_r(F.AUDIO, "wav", AUD, P("ffmpeg:pcm_s16le", method="ffmpeg"))
_r(F.AUDIO, "flac", AUD, P("ffmpeg:flac", method="ffmpeg"))
_r(F.AUDIO, "ogg", AUD, P("ffmpeg:libvorbis", method="ffmpeg"),
   P("ffmpeg:vorbis", method="ffmpeg", status=EXPERIMENTAL, note="codificador Vorbis nativo"))
_r(F.AUDIO, "opus", AUD, P("ffmpeg:libopus", method="ffmpeg"),
   P("ffmpeg:opus", method="ffmpeg", status=EXPERIMENTAL, note="codificador Opus nativo"))
_r(F.AUDIO, "aiff", AUD, P("ffmpeg:pcm_s16be", method="ffmpeg"))
_r(F.AUDIO, "wma", AUD, P("ffmpeg:wmav2", method="ffmpeg"))

# Video -------------------------------------------------------------------
VID = F.EXTENSIONS[F.VIDEO]
_r(F.VIDEO, "mp4", VID, P("ffmpeg:libx264", "ffmpeg:aac", method="ffmpeg", note="H.264 + AAC; cópia sem perdas quando possível"))
_r(F.VIDEO, "mov", VID, P("ffmpeg:libx264", "ffmpeg:aac", method="ffmpeg", note="H.264 + AAC"))
_r(F.VIDEO, "mkv", VID, P("ffmpeg:libx264", "ffmpeg:aac", method="ffmpeg", note="remux sem perdas quando possível"))
_r(F.VIDEO, "webm", VID, P("ffmpeg:libvpx-vp9", "ffmpeg:libopus", method="ffmpeg", note="VP9 + Opus"),
   P("ffmpeg:libvpx-vp9", "ffmpeg:libvorbis", method="ffmpeg", note="VP9 + Vorbis"))
_r(F.VIDEO, "avi", VID, P("ffmpeg:mpeg4", "ffmpeg:libmp3lame", method="ffmpeg", note="MPEG-4 Part 2 + MP3"))
_r(F.VIDEO, "wmv", VID, P("ffmpeg:wmv2", "ffmpeg:wmav2", method="ffmpeg", note="WMV8 + WMA"))
_r(F.VIDEO, "gif", VID - {"gif"}, P("ffmpeg:gif", method="ffmpeg", note="paleta otimizada, 12 fps, até 720 px"))
_r(F.VIDEO, "audio_mp3", VID - {"gif"}, P("ffmpeg:libmp3lame", method="ffmpeg"))

# PDF ---------------------------------------------------------------------
_PDF = {"pdf"}
_r(F.PDF, "docx", _PDF, P("pdf2docx", "pymupdf", method="pdf2docx", note="layouts complexos podem variar"))
_r(F.PDF, "pptx", _PDF, P("pymupdf", "pptx", method="pptx", note="cada página vira um slide (imagem) com o texto nas notas"))
_r(F.PDF, "xlsx", _PDF, P("pymupdf", "openpyxl", method="tables", status=EXPERIMENTAL, note="detecção automática de tabelas"))
_r(F.PDF, "jpg_pages", _PDF, P("pymupdf", method="render", note="todas as páginas, 300 DPI"))
_r(F.PDF, "png_pages", _PDF, P("pymupdf", method="render", note="todas as páginas, 300 DPI"))
_r(F.PDF, "epub", _PDF, P("pymupdf", "pandoc", method="pdf_epub", status=EXPERIMENTAL, note="texto, títulos e imagens; sem layout fixo"))
_r(F.PDF, "txt", _PDF, P("pymupdf", method="text"))
_r(F.PDF, "md", _PDF, P("pymupdf", method="markdown", status=EXPERIMENTAL, note="títulos detectados pelo tamanho da fonte"))

# Documents -----------------------------------------------------------------
LO = "libreoffice"
PD = "pandoc"
OFFICE_IN = {"doc", "docx", "odt", "rtf"}
PANDOC_IN = {"docx", "odt", "rtf", "md", "markdown", "html", "htm", "epub", "txt"}

# PDF
_r(F.DOCUMENT, "pdf", {"doc"}, P(LO, method="lo"))
_r(F.DOCUMENT, "pdf", {"docx", "odt", "rtf"}, P(LO, method="lo"),
   P(PD, "qtpdf", method="pandoc_qtpdf", status=EXPERIMENTAL, note="sem LibreOffice: layout simplificado"))
_r(F.DOCUMENT, "pdf", {"html", "htm"}, P(LO, method="lo"),
   P("qtpdf", method="html_qtpdf", status=EXPERIMENTAL, note="HTML/CSS básico"))
_r(F.DOCUMENT, "pdf", {"md", "markdown"}, P(PD, "qtpdf", method="pandoc_qtpdf"))
_r(F.DOCUMENT, "pdf", {"txt"}, P("qtpdf", method="text_qtpdf"))
_r(F.DOCUMENT, "pdf", {"epub"}, P(PD, "qtpdf", method="pandoc_qtpdf", status=EXPERIMENTAL, note="sem paginação original"))
# Word / ODF / RTF
for key in ("docx", "odt", "rtf"):
    _r(F.DOCUMENT, key, {"doc"}, P(LO, method="lo"))
    _r(F.DOCUMENT, key, OFFICE_IN - {"doc"}, P(LO, method="lo"), P(PD, method="pandoc"))
    _r(F.DOCUMENT, key, PANDOC_IN - OFFICE_IN, P(PD, method="pandoc"))
_r(F.DOCUMENT, "doc", {"docx", "odt", "rtf", "txt", "html", "htm"}, P(LO, method="lo"))
_r(F.DOCUMENT, "doc", {"md", "markdown", "epub"}, P(PD, LO, method="pandoc_lo"))
# Text formats
for key in ("txt", "md", "html", "epub"):
    _r(F.DOCUMENT, key, PANDOC_IN, P(PD, method="pandoc"))
    _r(F.DOCUMENT, key, {"doc"}, P(LO, PD, method="lo_pandoc"))

# Presentations -------------------------------------------------------------
PRES = F.EXTENSIONS[F.PRESENTATION]
for key in ("pdf", "pptx", "ppt", "odp"):
    _r(F.PRESENTATION, key, PRES, P(LO, method="lo"))
_r(F.PRESENTATION, "png_pages", PRES, P(LO, "pymupdf", method="lo_render", note="um arquivo por slide"))
_r(F.PRESENTATION, "jpg_pages", PRES, P(LO, "pymupdf", method="lo_render", note="um arquivo por slide"))

# Spreadsheets --------------------------------------------------------------
_r(F.SPREADSHEET, "xlsx", {"csv", "tsv"}, P("openpyxl", method="csv_xlsx"), P(LO, method="lo"))
_r(F.SPREADSHEET, "xlsx", {"xls"}, P(LO, method="lo"),
   P("xlrd", "openpyxl", method="xls_xlsx", status=EXPERIMENTAL, note="somente valores, sem formatação"))
_r(F.SPREADSHEET, "xlsx", {"ods"}, P(LO, method="lo"))
for key in ("csv", "tsv"):
    _r(F.SPREADSHEET, key, {"xlsx", "xlsm"}, P("openpyxl", method="xlsx_csv", note="uma saída por aba"), P(LO, method="lo"))
    _r(F.SPREADSHEET, key, {"xls"}, P("xlrd", method="xls_csv", note="uma saída por aba"), P(LO, method="lo"))
    _r(F.SPREADSHEET, key, {"ods"}, P(LO, method="lo"))
    _r(F.SPREADSHEET, key, {"csv", "tsv"}, P("builtin", method="delimited"))
for key in ("xls", "ods", "pdf"):
    _r(F.SPREADSHEET, key, F.EXTENSIONS[F.SPREADSHEET], P(LO, method="lo"))

# Subtitles -----------------------------------------------------------------
for key in ("srt", "vtt", "txt"):
    _r(F.SUBTITLE, key, {"srt", "vtt"}, P("builtin", method="subtitle"))

# Archives ------------------------------------------------------------------
NATIVE_ARCHIVES = {"zip", "tar", "tar.gz", "tgz", "tar.bz2", "tbz2", "tar.xz", "txz", "gz", "bz2", "xz"}
_r(F.ARCHIVE, "extract", NATIVE_ARCHIVES, P("builtin", method="extract"))
_r(F.ARCHIVE, "extract", {"rar"}, P("sevenzip:rar", method="extract7z"))
_r(F.ARCHIVE, "extract", {"7z"}, P("sevenzip", method="extract7z"))
_r(F.ARCHIVE, "zip", NATIVE_ARCHIVES - {"zip", "gz", "bz2", "xz"}, P("builtin", method="repack"))
_r(F.ARCHIVE, "zip", {"rar"}, P("sevenzip:rar", method="repack"))
_r(F.ARCHIVE, "zip", {"7z"}, P("sevenzip", method="repack"))

# Order in which targets appear on the wheel, per category.
ORDER = {
    F.IMAGE: ["jpg", "png", "webp", "avif", "heic", "tiff", "bmp", "pdf", "pdf_merge"],
    F.AUDIO: ["mp3", "m4a", "wav", "flac", "ogg", "opus", "aiff", "wma"],
    F.VIDEO: ["mp4", "mov", "mkv", "webm", "avi", "wmv", "gif", "audio_mp3"],
    F.PDF: ["docx", "pptx", "xlsx", "png_pages", "jpg_pages", "epub", "txt", "md"],
    F.DOCUMENT: ["pdf", "docx", "doc", "odt", "rtf", "txt", "md", "html", "epub"],
    F.PRESENTATION: ["pdf", "pptx", "ppt", "odp", "png_pages", "jpg_pages"],
    F.SPREADSHEET: ["xlsx", "xls", "ods", "csv", "tsv", "pdf"],
    F.SUBTITLE: ["srt", "vtt", "txt"],
    F.ARCHIVE: ["extract", "zip"],
}
MAX_WHEEL_ITEMS = 12


# ---------------------------------------------------------------------------
# queries
# ---------------------------------------------------------------------------

def _ext(path: Path) -> str:
    return F.extension(path)


def routes_for(category: str, ext: str, target: str) -> list[Route]:
    return [r for r in ROUTES if r.category == category and r.target == target and ext in r.sources]


def input_ok(ext: str, engines: Engines) -> bool:
    return engines.has_all(INPUT_REQUIRES.get(ext, ()))


def pick_plan(path: Path, target: str, engines: Engines) -> Plan | None:
    """First plan (in priority order) whose engines are all available."""
    cat = F.category(path)
    ext = _ext(path)
    if not input_ok(ext, engines):
        return None
    for route in routes_for(cat, ext, target):
        for plan in route.plans:
            if engines.has_all(plan.requires):
                return plan
    return None


def already_in_format(path: Path, target: str) -> bool:
    fmt = TARGET_FORMAT.get(target, "")
    return bool(fmt) and F.canonical(_ext(path)) == fmt


def choices_for(files: Sequence[Path], engines: Engines) -> list[Choice]:
    """Targets offered for a selection, in wheel order."""
    files = [Path(f) for f in files]
    if not files:
        return []
    cats = [F.category(f) for f in files]
    out: list[Choice] = []

    def order_keys() -> list[str]:
        keys: list[str] = []
        for c in dict.fromkeys(cats):
            for k in ORDER.get(c, []):
                if k not in keys:
                    keys.append(k)
        return keys

    for key in order_keys():
        target = T[key]
        if key == "pdf_merge":
            if len(files) >= 2 and all(c == F.IMAGE for c in cats):
                plans = [pick_plan(f, key, engines) for f in files]
                if all(plans):
                    out.append(Choice(target, _worst(plans), list(files), []))
            continue
        convert, skipped, plans, ok = [], [], [], True
        for f in files:
            if already_in_format(f, key):
                skipped.append(f)
                continue
            plan = pick_plan(f, key, engines)
            if plan is None:
                ok = False
                break
            convert.append(f)
            plans.append(plan)
        if ok and convert:
            out.append(Choice(target, _worst(plans), convert, skipped))

    # Universal "compactar em ZIP"
    if not all(c == F.ARCHIVE for c in cats) and all(Path(f).exists() for f in files):
        out.append(Choice(T["zip_pack"], STABLE, list(files), []))
    return out[:MAX_WHEEL_ITEMS]


def _worst(plans) -> str:
    return EXPERIMENTAL if any(p.status == EXPERIMENTAL for p in plans) else STABLE


def all_route_cases():
    """Every (category, source ext, target, plan) tuple — used by tests/docs."""
    for route in ROUTES:
        for ext in sorted(route.sources):
            for plan in route.plans:
                yield route.category, ext, route.target, plan
