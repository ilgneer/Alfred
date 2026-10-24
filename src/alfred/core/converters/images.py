"""Image conversions (Pillow, pillow-heif, AVIF, QtSvg for SVG)."""
from __future__ import annotations

import io
from pathlib import Path

from alfred.core import formats as F
from alfred.core.context import ConvertContext
from alfred.core.routes import Plan, Target

MAX_PIXELS = 400_000_000  # ~20000 x 20000
_heif_registered = False

PIL_FORMAT = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP", "tiff": "TIFF", "bmp": "BMP",
              "heic": "HEIF", "avif": "AVIF", "pdf": "PDF"}
ALPHA_OK = {"png", "webp", "tiff", "heic", "avif"}


def _register_plugins() -> None:
    global _heif_registered
    if _heif_registered:
        return
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except Exception:  # noqa: BLE001
        pass
    try:
        from PIL import features

        if not features.check("avif"):
            import pillow_avif  # noqa: F401
    except Exception:  # noqa: BLE001
        pass
    _heif_registered = True


def render_svg(src: Path, min_side: int = 1600, max_side: int = 8192):
    """Rasterise an SVG with QtSvg and return a PIL RGBA image."""
    from PIL import Image
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, QSize, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    _ensure_qt_app()
    renderer = QSvgRenderer(str(src))
    if not renderer.isValid():
        raise RuntimeError("SVG inválido ou com recursos não suportados (QtSvg usa SVG Tiny 1.2).")
    size = renderer.defaultSize()
    if size.isEmpty():
        vb = renderer.viewBoxF()
        size = QSize(max(1, int(vb.width())), max(1, int(vb.height())))
    if size.isEmpty():
        size = QSize(1024, 1024)
    longest = max(size.width(), size.height())
    scale = 1.0
    if longest < min_side:
        scale = min_side / longest
    if longest * scale > max_side:
        scale = max_side / longest
    w, h = max(1, round(size.width() * scale)), max(1, round(size.height() * scale))
    image = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, w, h))
    painter.end()
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buf, "PNG")
    buf.close()
    return Image.open(io.BytesIO(bytes(data))).convert("RGBA")


def svg_to_pdf(src: Path, dst: Path) -> None:
    """Vector SVG -> PDF using QPdfWriter (keeps shapes and text as vectors)."""
    from PySide6.QtCore import QMarginsF, QRectF, QSizeF
    from PySide6.QtGui import QPageLayout, QPageSize, QPainter, QPdfWriter
    from PySide6.QtSvg import QSvgRenderer

    _ensure_qt_app()
    renderer = QSvgRenderer(str(src))
    if not renderer.isValid():
        raise RuntimeError("SVG inválido ou com recursos não suportados.")
    size = renderer.defaultSize()
    w_px, h_px = (size.width(), size.height()) if not size.isEmpty() else (800, 600)
    # SVG user unit = 1/96 in ; PDF point = 1/72 in
    w_pt, h_pt = w_px * 72 / 96, h_px * 72 / 96
    writer = QPdfWriter(str(dst))
    writer.setResolution(300)
    writer.setPageSize(QPageSize(QSizeF(w_pt, h_pt), QPageSize.Unit.Point, "SVG"))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Point)
    writer.setTitle(src.stem)
    writer.setCreator("Alfred")
    painter = QPainter(writer)
    if not painter.isActive():
        raise RuntimeError("Não foi possível criar o PDF.")
    rect = writer.pageLayout().paintRectPixels(writer.resolution())
    renderer.render(painter, QRectF(rect))
    painter.end()


def _ensure_qt_app():
    from PySide6.QtGui import QGuiApplication

    if QGuiApplication.instance() is None:
        import os
        import sys

        if sys.platform != "win32" and not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        _ensure_qt_app.app = QGuiApplication(sys.argv[:1])  # keep a reference


def open_image(src: Path):
    """Open any supported input as a PIL image with EXIF orientation applied."""
    from PIL import Image, ImageOps

    _register_plugins()
    if F.extension(src) == "svg":
        return render_svg(src)
    try:
        im = Image.open(src)
        im.load()
    except Image.DecompressionBombError as exc:
        raise RuntimeError("Imagem grande demais (acima de 400 megapixels).") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Não foi possível abrir a imagem: {exc}") from exc
    try:
        return ImageOps.exif_transpose(im)
    except Exception:  # noqa: BLE001
        return im


def _flatten(im, background=(255, 255, 255)):
    from PIL import Image

    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, background)
        bg.paste(rgba, mask=rgba.getchannel("A"))
        return bg
    return im.convert("RGB") if im.mode != "RGB" else im


def _has_alpha(im) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)


def prepare_for(im, fmt: str):
    """Convert mode to something the target format can store."""
    if fmt in ("jpg", "bmp", "pdf"):
        return _flatten(im)
    if fmt in ALPHA_OK:
        if fmt == "tiff" and im.mode in ("RGB", "RGBA", "L", "LA", "CMYK", "I;16", "1"):
            return im
        if fmt == "png" and im.mode in ("RGB", "RGBA", "L", "LA", "P", "I;16", "1"):
            return im
        return im.convert("RGBA" if _has_alpha(im) else "RGB")
    return im.convert("RGB")


def save_image(im, dst: Path, fmt: str, ctx: ConvertContext, exif: bytes | None, icc: bytes | None) -> None:
    im = prepare_for(im, fmt)
    kw: dict = {}
    if icc and fmt in ("jpg", "png", "webp", "tiff", "heic", "avif", "pdf"):
        kw["icc_profile"] = icc
    if exif and fmt in ("jpg", "webp", "png", "heic", "avif", "tiff"):
        kw["exif"] = exif
    if fmt == "jpg":
        kw.update(quality=ctx.options.jpg_quality, optimize=True, progressive=True)
    elif fmt == "webp":
        kw.update(quality=90, method=4)
    elif fmt == "avif":
        kw.update(quality=80, speed=6)
    elif fmt == "heic":
        kw.update(quality=90)
    elif fmt == "tiff":
        kw.update(compression="tiff_lzw")
    elif fmt == "png":
        kw.update(optimize=False, compress_level=6)
    elif fmt == "pdf":
        kw.update(resolution=float(ctx.options.pdf_dpi) if ctx.options.pdf_dpi else 300.0)
    try:
        im.save(dst, format=PIL_FORMAT[fmt], **kw)
    except (KeyError, OSError, ValueError) as exc:
        raise RuntimeError(f"O codec {fmt.upper()} não conseguiu gravar a imagem: {exc}") from exc


def _metadata(im) -> tuple[bytes | None, bytes | None]:
    icc = im.info.get("icc_profile")
    exif_bytes = None
    try:
        exif = im.getexif()
        if exif:
            exif[0x0112] = 1  # orientation already applied
            exif_bytes = exif.tobytes()
    except Exception:  # noqa: BLE001
        exif_bytes = None
    return exif_bytes, icc


def convert(ctx: ConvertContext, src: Path, target: Target, plan: Plan) -> None:
    fmt = target.ext
    stem = F.stem(src)
    ctx.progress(0.05, "Lendo imagem")
    if plan.method == "svg_vector":
        svg_to_pdf(src, ctx.stage(f"{stem}.pdf"))
        return
    _register_plugins()
    n_frames = _frame_count(src)
    im = open_image(src)
    exif, icc = _metadata(im)
    ctx.progress(0.4, "Convertendo")
    dst = ctx.stage(f"{stem}.{fmt}")
    if fmt in ("pdf", "tiff") and n_frames > 1 and F.extension(src) in ("tif", "tiff"):
        frames = _all_frames(src)
        first, rest = prepare_for(frames[0], fmt), [prepare_for(f, fmt) for f in frames[1:]]
        kw = {"save_all": True, "append_images": rest}
        if fmt == "pdf":
            kw["resolution"] = float(ctx.options.pdf_dpi)
        else:
            kw["compression"] = "tiff_lzw"
        first.save(dst, format=PIL_FORMAT[fmt], **kw)
    else:
        if n_frames > 1:
            ctx.notes.append(f"{src.name}: imagem com vários quadros — convertido o primeiro.")
        save_image(im, dst, fmt, ctx, exif, icc)
    ctx.progress(1.0, "Pronto")


def _frame_count(src: Path) -> int:
    if F.extension(src) == "svg":
        return 1
    from PIL import Image

    try:
        with Image.open(src) as raw:
            return int(getattr(raw, "n_frames", 1) or 1)
    except Exception:  # noqa: BLE001
        return 1


def _all_frames(src: Path):
    from PIL import Image, ImageOps, ImageSequence

    with Image.open(src) as raw:
        return [ImageOps.exif_transpose(f.copy()) for f in ImageSequence.Iterator(raw)]


def merge_to_pdf(ctx: ConvertContext, files: list[Path]) -> None:
    """Combine several images into a single PDF (natural name order)."""
    import re

    def natural(p: Path):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]

    files = sorted(files, key=natural)
    pages = []
    for i, f in enumerate(files):
        ctx.progress(i / max(1, len(files)), f"Lendo {f.name}")
        pages.append(_flatten(open_image(f)))
    name = f"{F.stem(files[0])} e mais {len(files) - 1}.pdf" if len(files) > 1 else f"{F.stem(files[0])}.pdf"
    dst = ctx.stage(name)
    pages[0].save(dst, format="PDF", save_all=True, append_images=pages[1:],
                  resolution=float(ctx.options.pdf_dpi))
    ctx.progress(1.0, "Pronto")
