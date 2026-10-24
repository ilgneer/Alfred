"""File categories and extension helpers."""
from __future__ import annotations

from pathlib import Path

IMAGE = "image"
AUDIO = "audio"
VIDEO = "video"
PDF = "pdf"
DOCUMENT = "document"
PRESENTATION = "presentation"
SPREADSHEET = "spreadsheet"
SUBTITLE = "subtitle"
ARCHIVE = "archive"
FOLDER = "folder"
UNKNOWN = "unknown"

CATEGORY_LABELS = {
    IMAGE: "Imagem",
    AUDIO: "Áudio",
    VIDEO: "Vídeo",
    PDF: "PDF",
    DOCUMENT: "Documento",
    PRESENTATION: "Apresentação",
    SPREADSHEET: "Planilha",
    SUBTITLE: "Legenda",
    ARCHIVE: "Compactado",
    FOLDER: "Pasta",
    UNKNOWN: "Arquivo",
}

EXTENSIONS: dict[str, set[str]] = {
    IMAGE: {"jpg", "jpeg", "jpe", "jfif", "png", "webp", "heic", "heif", "tif", "tiff", "avif", "bmp", "svg"},
    AUDIO: {"mp3", "m4a", "aac", "wav", "flac", "ogg", "oga", "opus", "aif", "aiff", "wma"},
    VIDEO: {"mp4", "m4v", "mov", "mkv", "webm", "avi", "wmv", "gif"},
    PDF: {"pdf"},
    DOCUMENT: {"doc", "docx", "odt", "rtf", "txt", "md", "markdown", "html", "htm", "epub"},
    PRESENTATION: {"ppt", "pptx", "odp"},
    SPREADSHEET: {"xls", "xlsx", "xlsm", "ods", "csv", "tsv"},
    SUBTITLE: {"srt", "vtt"},
    ARCHIVE: {"zip", "tar", "gz", "tgz", "bz2", "tbz2", "xz", "txz", "rar", "7z"},
}

_EXT_TO_CATEGORY = {ext: cat for cat, exts in EXTENSIONS.items() for ext in exts}

# Canonical name for aliases (used to decide "already in this format").
CANONICAL = {
    "jpeg": "jpg", "jpe": "jpg", "jfif": "jpg", "tif": "tiff", "heif": "heic",
    "aif": "aiff", "oga": "ogg", "m4v": "mp4", "htm": "html", "markdown": "md",
    "tgz": "tar.gz", "tbz2": "tar.bz2", "txz": "tar.xz", "xlsm": "xlsx",
}

COMPOUND_SUFFIXES = (".tar.gz", ".tar.bz2", ".tar.xz")


def extension(path: str | Path) -> str:
    """Lower-case extension without dot; understands .tar.gz and friends."""
    name = Path(path).name.lower()
    for suffix in COMPOUND_SUFFIXES:
        if name.endswith(suffix):
            return suffix[1:]
    return Path(name).suffix.lstrip(".")


def canonical(ext: str) -> str:
    ext = ext.lower().lstrip(".")
    return CANONICAL.get(ext, ext)


def stem(path: str | Path) -> str:
    """File name without (compound) extension."""
    p = Path(path)
    name = p.name
    lower = name.lower()
    for suffix in COMPOUND_SUFFIXES:
        if lower.endswith(suffix):
            return name[: -len(suffix)]
    return p.stem


def category(path: str | Path) -> str:
    p = Path(path)
    if p.is_dir():
        return FOLDER
    ext = extension(p)
    if ext.startswith("tar."):
        return ARCHIVE
    return _EXT_TO_CATEGORY.get(ext, UNKNOWN)


def category_label(cat: str) -> str:
    return CATEGORY_LABELS.get(cat, "Arquivo")
