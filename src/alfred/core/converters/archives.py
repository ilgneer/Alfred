"""Safe extraction (ZIP, TAR, GZ/BZ2/XZ, RAR/7Z via 7-Zip) and ZIP packing."""
from __future__ import annotations

import bz2
import gzip
import lzma
import os
import re
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

from alfred.core import formats as F
from alfred.core.context import ConvertContext
from alfred.core.routes import Plan, Target

SINGLE_STREAM = {"gz": gzip.open, "bz2": bz2.open, "xz": lzma.open}
MAX_RATIO_BYTES = 200 * 1024**3  # refuse absurd archives (zip bombs)


def _oem_encoding() -> str:
    if os.name == "nt":
        try:
            import ctypes

            return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
        except Exception:  # noqa: BLE001
            pass
    return "cp437"


def _safe_member(root: Path, name: str) -> Path:
    name = name.replace("\\", "/")
    pp = PurePosixPath(name)
    if pp.is_absolute() or ".." in pp.parts or re.match(r"^[A-Za-z]:", name):
        raise RuntimeError(f"O arquivo compactado contém um caminho inseguro: {name}")
    target = (root / Path(*[p for p in pp.parts if p not in ("", ".")])).resolve()
    if not target.is_relative_to(root.resolve()):
        raise RuntimeError(f"O arquivo compactado contém um caminho inseguro: {name}")
    return target


def _check_space(directory: Path, needed: int) -> None:
    if needed > MAX_RATIO_BYTES:
        raise RuntimeError("O conteúdo descompactado é grande demais (possível arquivo malicioso).")
    try:
        free = shutil.disk_usage(directory).free
    except OSError:
        return
    if needed > free * 0.95:
        raise RuntimeError("Espaço em disco insuficiente para extrair este arquivo.")


def extract_zip(ctx: ConvertContext, src: Path, out: Path) -> None:
    try:
        zf = zipfile.ZipFile(src, metadata_encoding=_oem_encoding())
    except TypeError:  # Python < 3.11
        zf = zipfile.ZipFile(src)
    except zipfile.BadZipFile as exc:
        raise RuntimeError("ZIP corrompido ou inválido.") from exc
    with zf:
        infos = zf.infolist()
        if any(i.flag_bits & 0x1 for i in infos):
            raise RuntimeError("ZIP protegido por senha não é suportado.")
        _check_space(out, sum(i.file_size for i in infos))
        total = len(infos) or 1
        for n, info in enumerate(infos):
            if n % 20 == 0:
                ctx.progress(n / total, f"Extraindo {n} de {total}")
            dest = _safe_member(out, info.filename)
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as fin, open(dest, "wb") as fout:
                shutil.copyfileobj(fin, fout, 1024 * 1024)


def extract_tar(ctx: ConvertContext, src: Path, out: Path) -> None:
    try:
        tf = tarfile.open(src)  # noqa: SIM115 - closed by the with-block below
    except tarfile.TarError as exc:
        raise RuntimeError("TAR corrompido ou inválido.") from exc
    with tf:
        members = tf.getmembers()
        _check_space(out, sum(m.size for m in members if m.isfile()))
        for m in members:
            _safe_member(out, m.name)
            if m.issym() or m.islnk():
                raise RuntimeError("O TAR contém links simbólicos; extração recusada por segurança.")
        ctx.progress(0.3, "Extraindo")
        if sys.version_info >= (3, 12) or hasattr(tarfile, "data_filter"):
            tf.extractall(out, filter="data")
        else:  # pragma: no cover
            tf.extractall(out)


def extract_single(ctx: ConvertContext, src: Path, out: Path, kind: str) -> None:
    opener = SINGLE_STREAM[kind]
    name = src.name[: -len(src.suffix)] if src.suffix else src.name + ".out"
    dest = out / name
    ctx.progress(None, "Descompactando")
    try:
        with opener(src, "rb") as fin, open(dest, "wb") as fout:
            while True:
                chunk = fin.read(1024 * 1024)
                if not chunk:
                    break
                ctx.check()
                fout.write(chunk)
    except (OSError, EOFError, lzma.LZMAError) as exc:
        raise RuntimeError(f"Arquivo {kind.upper()} corrompido ou inválido: {exc}") from exc


def extract_7z(ctx: ConvertContext, src: Path, out: Path) -> None:
    exe = ctx.engines.path("sevenzip")

    def on_line(line: str):
        m = re.search(r"(\d{1,3})%", line)
        if m:
            ctx.progress(int(m.group(1)) / 100, "Extraindo")

    # -p with a dummy password: never blocks waiting for input on protected files
    try:
        ctx.run([exe, "x", "-y", "-bso0", "-bsp1", "-pALFRED-SEM-SENHA", f"-o{out}", src], on_stdout_line=on_line,
                timeout=6 * 3600)
    except Exception as exc:
        text = str(exc)
        if "Wrong password" in text or "password" in text.lower():
            raise RuntimeError("Arquivo protegido por senha não é suportado.") from exc
        raise RuntimeError(f"O 7-Zip não conseguiu extrair: {text}") from exc
    # 7-Zip already blocks absolute/".." paths; double-check nothing escaped
    for p in out.rglob("*"):
        if p.is_symlink():
            p.unlink()


def _extract_into(ctx: ConvertContext, src: Path, out: Path, plan_method: str) -> None:
    ext = F.extension(src)
    if plan_method == "extract7z" or ext in ("rar", "7z"):
        extract_7z(ctx, src, out)
    elif ext == "zip":
        extract_zip(ctx, src, out)
    elif ext in ("tar", "tar.gz", "tgz", "tar.bz2", "tbz2", "tar.xz", "txz"):
        extract_tar(ctx, src, out)
    elif ext in SINGLE_STREAM:
        if tarfile.is_tarfile(src):
            extract_tar(ctx, src, out)
        else:
            extract_single(ctx, src, out, ext)
    else:
        raise RuntimeError("Tipo de arquivo compactado não suportado.")


def convert(ctx: ConvertContext, src: Path, target: Target, plan: Plan) -> None:
    stem = F.stem(src)
    if target.key == "extract":
        out = ctx.stage_dir(stem)
        _extract_into(ctx, src, out, plan.method)
        if not any(out.iterdir()):
            raise RuntimeError("O arquivo compactado está vazio.")
    elif target.key == "zip":  # repack (TAR/RAR/7Z -> ZIP)
        work = ctx.scratch / "conteudo"
        work.mkdir()
        _extract_into(ctx, src, work, "extract7z" if F.extension(src) in ("rar", "7z") else "extract")
        _zip_paths(ctx, [p for p in sorted(work.iterdir())], ctx.stage(f"{stem}.zip"), base=work)
    else:
        raise RuntimeError(f"Ação desconhecida: {target.key}")
    ctx.progress(1.0, "Pronto")


def _zip_paths(ctx: ConvertContext, items: list[Path], dst: Path, base: Path | None = None) -> None:
    files: list[tuple[Path, str]] = []
    staging = ctx.staging_dir.resolve()
    for item in items:
        root = base if base is not None else item.parent
        if item.is_dir():
            for f in sorted(item.rglob("*")):
                if f.is_file() and not f.is_symlink() and not f.resolve().is_relative_to(staging):
                    files.append((f, f.relative_to(root).as_posix()))
        elif item.is_file():
            files.append((item, item.relative_to(root).as_posix() if base else item.name))
    if not files:
        raise RuntimeError("Nada para compactar.")
    total = len(files)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        seen: set[str] = set()
        for n, (f, arc) in enumerate(files):
            if n % 10 == 0:
                ctx.progress(n / total, f"Compactando {n} de {total}")
            base_arc, i = arc, 2
            while arc.lower() in seen:
                stem, dot, ext = base_arc.rpartition(".")
                arc = f"{stem} ({i}).{ext}" if dot else f"{base_arc} ({i})"
                i += 1
            seen.add(arc.lower())
            zf.write(f, arc)


def pack_zip(ctx: ConvertContext, files: list[Path]) -> None:
    files = [Path(f) for f in files]
    name = f"{F.stem(files[0]) if files[0].is_file() else files[0].name}.zip"
    if len(files) > 1:
        name = f"{files[0].parent.name or 'Arquivos'} ({len(files)} itens).zip"
    _zip_paths(ctx, files, ctx.stage(name))
    ctx.progress(1.0, "Pronto")
