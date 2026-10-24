"""Executes EVERY route of the registry with a real sample file.

A route that cannot run here (engine missing on this machine) is reported as
SKIPPED with the reason — never as passed. The Windows release workflow runs
this same suite against the bundled engines before packaging.
"""
from __future__ import annotations

import pytest

from alfred.core import routes
from alfred.core.context import ConvertContext, Options
from alfred.core.converters import convert_batch, convert_one
from tests.validators import check_output

CASES = sorted(set(routes.all_route_cases()), key=lambda c: (c[0], c[1], c[2], c[3].method, c[3].requires))


def _id(case):
    cat, ext, target, plan = case
    return f"{ext}->{target}[{plan.method}{'+' + '+'.join(plan.requires) if plan.requires else ''}]"


@pytest.mark.parametrize("case", CASES, ids=[_id(c) for c in CASES])
def test_route(case, samples, engines, tmp_path):
    category, ext, target_key, plan = case
    missing = [r for r in (*plan.requires, *routes.INPUT_REQUIRES.get(ext, ())) if not engines.has(r)]
    if missing:
        pytest.skip(f"motor ausente nesta máquina: {', '.join(missing)}")
    src = samples.get(ext)
    target = routes.T[target_key]
    out_dir = tmp_path / "saída com espaço"
    ctx = ConvertContext(engines, Options(output_mode="custom", custom_output_dir=str(out_dir), pdf_dpi=110))
    ctx.begin(src)
    try:
        convert_one(ctx, src, target, plan)
        outputs = ctx.commit()
    except Exception:
        ctx.discard()
        raise
    assert outputs, "nenhuma saída"
    ffmpeg = engines.infos["ffmpeg"].path if engines.has("ffmpeg") else None
    for out in outputs:
        if out.is_dir():
            files = sorted(p for p in out.rglob("*") if p.is_file())
            assert files
            if target_key in ("png_pages", "jpg_pages"):
                for f in files:
                    check_output(f, target_key.split("_")[0])
            continue
        if out.suffix == "" or out.name.endswith("_midia"):
            continue
        expected = target.ext or out.suffix.lstrip(".")
        if out.suffix.lstrip(".") != expected:
            continue  # auxiliary file (e.g. media folder)
        check_output(out, expected, ffmpeg)
    # never overwrite / never touch the source
    assert src.exists()
    assert not any(p.name.startswith(".alfred-") for p in out_dir.iterdir()), "staging não foi limpo"


def test_no_route_without_validator():
    """Every target that produces a file has an output validator."""
    validated = {"jpg", "png", "webp", "tiff", "bmp", "heic", "avif", "pdf", "mp3", "m4a", "wav", "flac", "ogg",
                 "opus", "aiff", "wma", "mp4", "mov", "mkv", "webm", "avi", "wmv", "gif", "docx", "pptx", "xlsx",
                 "epub", "odt", "ods", "odp", "doc", "xls", "ppt", "rtf", "txt", "md", "html", "csv", "tsv",
                 "srt", "vtt", "zip", ""}
    for t in routes.T.values():
        assert t.ext in validated, t.key


@pytest.mark.parametrize("key", ["pdf_merge", "zip_pack"])
def test_batch_targets(key, samples, engines, tmp_path):
    files = [samples.get("png"), samples.get("jpg"), samples.get("svg")] if key == "pdf_merge" else \
        [samples.get("txt"), samples.get("png"), samples._payload()]
    out_dir = tmp_path / "lote"
    ctx = ConvertContext(engines, Options(output_mode="custom", custom_output_dir=str(out_dir)))
    ctx.begin(files[0])
    convert_batch(ctx, files, routes.T[key])
    outs = ctx.commit()
    assert len(outs) == 1
    if key == "pdf_merge":
        import pymupdf

        with pymupdf.open(str(outs[0])) as d:
            assert d.page_count == 3
    else:
        import zipfile

        with zipfile.ZipFile(outs[0]) as z:
            names = z.namelist()
            assert any(n.endswith("olá.txt") for n in names)
            assert any("sub pasta/" in n for n in names)
