"""Dispatch a (file, target, plan) to the right converter module."""
from __future__ import annotations

from pathlib import Path

from alfred.core import formats as F
from alfred.core.context import ConvertContext
from alfred.core.routes import Plan, Target


def convert_one(ctx: ConvertContext, src: Path, target: Target, plan: Plan) -> None:
    cat = F.category(src)
    if cat == F.IMAGE:
        from alfred.core.converters import images as mod

        return mod.convert(ctx, src, target, plan)
    if cat in (F.AUDIO, F.VIDEO):
        from alfred.core.converters import media as mod

        return mod.convert(ctx, src, target, plan)
    if cat == F.PDF:
        from alfred.core.converters import pdf as mod

        return mod.convert(ctx, src, target, plan)
    if cat == F.DOCUMENT:
        from alfred.core.converters import documents as mod

        return mod.convert_document(ctx, src, target, plan)
    if cat == F.PRESENTATION:
        from alfred.core.converters import documents as mod

        return mod.convert_presentation(ctx, src, target, plan)
    if cat == F.SPREADSHEET:
        from alfred.core.converters import documents as mod

        return mod.convert_spreadsheet(ctx, src, target, plan)
    if cat == F.SUBTITLE:
        from alfred.core.converters import subtitles as mod

        return mod.convert(ctx, src, target, plan)
    if cat == F.ARCHIVE:
        from alfred.core.converters import archives as mod

        return mod.convert(ctx, src, target, plan)
    raise RuntimeError(f"Não há conversor para {src.name}.")


def convert_batch(ctx: ConvertContext, files: list[Path], target: Target) -> None:
    if target.key == "pdf_merge":
        from alfred.core.converters import images

        return images.merge_to_pdf(ctx, files)
    if target.key == "zip_pack":
        from alfred.core.converters import archives

        return archives.pack_zip(ctx, files)
    raise RuntimeError(f"Ação em lote desconhecida: {target.key}")
