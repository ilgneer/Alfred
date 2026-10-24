"""Safety: no overwrite, no partial files, cancellation, malicious archives."""
from __future__ import annotations

import io
import shutil
import tarfile
import threading
import time
import zipfile
from pathlib import Path

import pytest

from alfred.core import naming, routes
from alfred.core.context import ConvertContext, Options
from alfred.core.converters import convert_one
from alfred.core.jobs import CANCELLED, DONE, FAILED, PARTIAL, Job, run_job
from tests.conftest import FIXTURES, MARKER


def opts(d):
    return Options(output_mode="custom", custom_output_dir=str(d))


def test_unique_path_never_overwrites(tmp_path):
    (tmp_path / "foto.png").write_bytes(b"x")
    (tmp_path / "foto (2).png").write_bytes(b"x")
    assert naming.unique_path(tmp_path, "foto.png").name == "foto (3).png"
    (tmp_path / "a.tar.gz").write_bytes(b"x")
    assert naming.unique_path(tmp_path, "a.tar.gz").name == "a (2).tar.gz"


def test_sanitize_windows_names():
    assert naming.sanitize('a<b>:c?.txt') == "a_b__c_.txt"
    assert naming.sanitize("CON.txt") == "_CON.txt"
    assert naming.sanitize("nome. ") == "nome"


def test_conversion_does_not_overwrite_existing_output(samples, engines, tmp_path):
    src = samples.get("png")
    existing = tmp_path / "Relatório de teste.jpg"
    existing.write_bytes(b"conteudo do usuario")
    job = Job(files=[src], target=routes.T["jpg"])
    run_job(job, engines, opts(tmp_path))
    assert job.state == DONE
    assert existing.read_bytes() == b"conteudo do usuario"
    assert job.outputs[0].name == "Relatório de teste (2).jpg"


def test_same_folder_default_keeps_original(samples, engines, tmp_path):
    src = tmp_path / "Minha Foto Ação.png"
    shutil.copy2(samples.get("png"), src)
    before = src.read_bytes()
    job = run_job(Job(files=[src], target=routes.T["webp"]), engines, Options())
    assert job.state == DONE and job.outputs[0].parent == tmp_path
    assert src.read_bytes() == before


def test_failure_leaves_no_partial_file(engines, tmp_path):
    bad = tmp_path / "corrompido.mp4"
    bad.write_bytes(b"isto nao e um video" * 100)
    job = run_job(Job(files=[bad], target=routes.T["mov"]), engines, opts(tmp_path / "out"))
    assert job.state == FAILED and job.errors
    out = tmp_path / "out"
    assert not out.exists() or not any(out.iterdir())


def test_partial_batch(samples, engines, tmp_path):
    bad = tmp_path / "ruim.png"
    bad.write_bytes(b"nope")
    job = run_job(Job(files=[samples.get("png"), bad], target=routes.T["jpg"]), engines, opts(tmp_path / "o"))
    assert job.state == PARTIAL and len(job.outputs) == 1 and len(job.errors) == 1


def test_cancel_long_ffmpeg_job(engines, tmp_path):
    if not engines.has("ffmpeg"):
        pytest.skip("FFmpeg ausente")
    import subprocess

    src = tmp_path / "longo.mp4"
    subprocess.run([engines.path("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=size=1280x720:rate=30:duration=60", "-c:v", "libx264", "-preset", "ultrafast",
                    str(src)], check=True, stdin=subprocess.DEVNULL)
    job = Job(files=[src], target=routes.T["webm"])
    out = tmp_path / "out"
    t = threading.Thread(target=run_job, args=(job, engines, opts(out)))
    t.start()
    deadline = time.time() + 30
    while job.state != "running" and time.time() < deadline:
        time.sleep(0.05)
    time.sleep(1.5)
    started_cancel = time.time()
    job.token.cancel()
    t.join(30)
    assert not t.is_alive()
    assert time.time() - started_cancel < 10
    assert job.state == CANCELLED
    assert not out.exists() or not any(out.iterdir()), "arquivos parciais deixados para trás"


def test_zip_slip_rejected(engines, tmp_path):
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../../fora.txt", "x")
    job = run_job(Job(files=[evil], target=routes.T["extract"]), engines, opts(tmp_path / "o"))
    assert job.state == FAILED and "inseguro" in job.errors[0]
    assert not (tmp_path / "fora.txt").exists()


def test_tar_symlink_rejected(engines, tmp_path):
    evil = tmp_path / "evil.tar"
    with tarfile.open(evil, "w") as t:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        t.addfile(info)
        data = b"ok"
        f = tarfile.TarInfo("ok.txt")
        f.size = len(data)
        t.addfile(f, io.BytesIO(data))
    job = run_job(Job(files=[evil], target=routes.T["extract"]), engines, opts(tmp_path / "o"))
    assert job.state == FAILED


def test_rar_symlink_traversal_contained(engines, tmp_path):
    if not engines.has("sevenzip:rar"):
        pytest.skip("7-Zip com RAR ausente")
    src = tmp_path / "evil.rar"
    shutil.copy2(FIXTURES / "rar5-evil-symlink-traversal.rar", src)
    before = set(tmp_path.parent.iterdir())
    run_job(Job(files=[src], target=routes.T["extract"]), engines, opts(tmp_path / "o"))
    assert set(tmp_path.parent.iterdir()) == before
    for p in (tmp_path / "o").rglob("*") if (tmp_path / "o").exists() else []:
        assert not p.is_symlink()


def test_password_rar_fails_cleanly(engines, tmp_path):
    if not engines.has("sevenzip:rar"):
        pytest.skip("7-Zip com RAR ausente")
    src = tmp_path / "senha.rar"
    shutil.copy2(FIXTURES / "rar5-psw.rar", src)
    t0 = time.time()
    job = run_job(Job(files=[src], target=routes.T["extract"]), engines, opts(tmp_path / "o"))
    assert time.time() - t0 < 30, "não pode travar esperando senha"
    assert job.state == FAILED
    assert not (tmp_path / "o").exists() or not any((tmp_path / "o").iterdir())


def test_readonly_destination_falls_back(samples, engines, tmp_path, monkeypatch):
    from alfred.core import context, paths

    ro = tmp_path / "somente_leitura"
    ro.mkdir()
    fallback = tmp_path / "Documentos" / "Alfred"
    fallback.mkdir(parents=True)
    real = context._writable
    monkeypatch.setattr(context, "_writable", lambda d: False if Path(d) == ro else real(d))
    monkeypatch.setattr(paths, "documents_fallback_dir", lambda: fallback)
    job = run_job(Job(files=[samples.get("png")], target=routes.T["jpg"]), engines, opts(ro))
    assert job.state == DONE and job.notes
    assert job.outputs[0].parent == fallback
    assert not any(ro.iterdir())


def test_staging_hidden_and_removed(samples, engines, tmp_path):
    ctx = ConvertContext(engines, opts(tmp_path))
    ctx.begin(samples.get("txt"))
    staging = ctx.staging_dir
    assert staging.name.startswith(".alfred-")
    convert_one(ctx, samples.get("txt"), routes.T["html"], routes.pick_plan(samples.get("txt"), "html", engines))
    ctx.commit()
    assert not staging.exists()


def test_large_image_guard(engines, tmp_path):
    from PIL import Image

    big = tmp_path / "grande.png"
    Image.new("L", (12000, 9000), 128).save(big, optimize=False, compress_level=1)  # 108 MP: allowed
    job = run_job(Job(files=[big], target=routes.T["jpg"]), engines, opts(tmp_path / "o"))
    assert job.state == DONE


def test_many_files_at_once(samples, engines, tmp_path):
    files = []
    for i in range(25):
        f = tmp_path / f"lote ç {i}.png"
        shutil.copy2(samples.get("png"), f)
        files.append(f)
    progress = []
    job = run_job(Job(files=files, target=routes.T["webp"]), engines, opts(tmp_path / "o"),
                  notify=lambda j: progress.append(j.progress))
    assert job.state == DONE and len(job.outputs) == 25
    nums = [p for p in progress if p is not None]
    assert nums == sorted(nums)


def test_engine_missing_hides_routes(samples, engines):
    from dataclasses import replace

    no_lo = replace(engines, tokens=frozenset(t for t in engines.tokens if t != "libreoffice"))
    keys = [c.target.key for c in routes.choices_for([samples.get("doc")], no_lo)]
    assert "pdf" not in keys and "docx" not in keys
    keys = [c.target.key for c in routes.choices_for([samples.get("pptx")], no_lo)]
    assert keys == ["zip_pack"]
    nothing = replace(engines, tokens=frozenset({"pillow", "builtin"}))
    keys = [c.target.key for c in routes.choices_for([samples.get("mp4")], nothing)]
    assert keys == ["zip_pack"]


def test_choices_mixed_selection(samples, engines):
    ch = routes.choices_for([samples.get("png"), samples.get("jpg")], engines)
    keys = [c.target.key for c in ch]
    assert keys[:2] == ["jpg", "png"] and "pdf_merge" in keys
    jpg = next(c for c in ch if c.target.key == "jpg")
    assert [p.suffix for p in jpg.files] == [".png"] and [p.suffix for p in jpg.skipped] == [".jpg"]
    mixed = [c.target.key for c in routes.choices_for([samples.get("docx"), samples.get("png")], engines)]
    assert "pdf" in mixed and "jpg" not in mixed


def test_never_offers_same_format(samples, engines):
    for ext in ("png", "mp3", "mp4", "pdf", "docx", "xlsx", "srt", "zip"):
        src = samples.get(ext)
        for c in routes.choices_for([src], engines):
            assert not routes.already_in_format(src, c.target.key) or c.target.batch, (ext, c.target.key)


def test_marker_constant():
    assert "ç" in MARKER and Path(__file__).exists()
