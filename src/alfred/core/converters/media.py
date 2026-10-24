"""Audio and video conversions through the bundled FFmpeg."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from alfred.core import formats as F
from alfred.core import procs
from alfred.core.context import ConvertContext
from alfred.core.routes import Plan, Target


@dataclass
class Probe:
    duration: float = 0.0
    video_codecs: list[str] = field(default_factory=list)
    audio_codecs: list[str] = field(default_factory=list)
    width: int = 0
    height: int = 0

    @property
    def has_video(self) -> bool:
        # cover art ("attached pic") is reported as mjpeg/png video streams
        return any(c not in ("mjpeg", "png", "bmp") for c in self.video_codecs)

    @property
    def has_audio(self) -> bool:
        return bool(self.audio_codecs)


def probe(ffmpeg: str, src: Path) -> Probe:
    """Parse ``ffmpeg -i`` output (FFmpeg exits with 1 because no output is given)."""
    import subprocess

    try:
        proc = subprocess.run([ffmpeg, "-hide_banner", "-nostdin", "-i", str(src)], capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              creationflags=procs.NO_WINDOW, timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"Não foi possível executar o FFmpeg: {exc}") from exc
    out = proc.stderr or ""
    info = Probe()
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out)
    if m:
        h, mi, s = m.groups()
        info.duration = int(h) * 3600 + int(mi) * 60 + float(s)
    for line in out.splitlines():
        sm = re.search(r"Stream #\S+.*?: (Video|Audio): (\w+)", line)
        if not sm:
            continue
        kind, codec = sm.groups()
        if kind == "Video":
            if "attached pic" in line:
                continue
            info.video_codecs.append(codec)
            dm = re.search(r", (\d{2,5})x(\d{2,5})", line)
            if dm and not info.width:
                info.width, info.height = int(dm.group(1)), int(dm.group(2))
        else:
            info.audio_codecs.append(codec)
    if "Invalid data found" in out or (not info.video_codecs and not info.audio_codecs):
        raise RuntimeError("O FFmpeg não reconheceu este arquivo de mídia (pode estar corrompido).")
    return info


EVEN = "scale=trunc(iw/2)*2:trunc(ih/2)*2"


def audio_args(target: str, ctx: ConvertContext) -> list[str]:
    enc = ctx.engines.ffmpeg_encoders
    if target in ("mp3", "audio_mp3"):
        return ["-c:a", "libmp3lame", "-q:a", "2"]
    if target == "m4a":
        return ["-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart"]
    if target == "wav":
        return ["-c:a", "pcm_s16le"]
    if target == "aiff":
        return ["-c:a", "pcm_s16be", "-write_id3v2", "1"]
    if target == "flac":
        return ["-c:a", "flac", "-compression_level", "5"]
    if target == "ogg":
        if "libvorbis" in enc:
            return ["-c:a", "libvorbis", "-q:a", "6"]
        return ["-c:a", "vorbis", "-strict", "-2", "-ac", "2", "-b:a", "192k"]
    if target == "opus":
        if "libopus" in enc:
            return ["-c:a", "libopus", "-b:a", "160k", "-vbr", "on"]
        return ["-c:a", "opus", "-strict", "-2", "-ar", "48000", "-b:a", "160k"]
    if target == "wma":
        return ["-c:a", "wmav2", "-b:a", "192k"]
    raise RuntimeError(f"Formato de áudio desconhecido: {target}")


def video_args(target: str, ctx: ConvertContext, info: Probe) -> list[str]:
    enc = ctx.engines.ffmpeg_encoders
    crf = str(ctx.options.crf)
    a_map = ["-map", "0:a:0?"]
    if target in ("mp4", "mov", "mkv"):
        args = ["-map", "0:v:0", *a_map, "-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
                "-pix_fmt", "yuv420p", "-vf", EVEN, "-c:a", "aac", "-b:a", "192k"]
        if target in ("mp4", "mov"):
            args += ["-movflags", "+faststart"]
        return args
    if target == "webm":
        audio = ["-c:a", "libopus", "-b:a", "128k"] if "libopus" in enc else ["-c:a", "libvorbis", "-q:a", "5"]
        return ["-map", "0:v:0", *a_map, "-c:v", "libvpx-vp9", "-crf", str(ctx.options.crf_vp9), "-b:v", "0",
                "-row-mt", "1", "-deadline", "good", "-cpu-used", "4", "-pix_fmt", "yuv420p", "-vf", EVEN, *audio]
    if target == "avi":
        return ["-map", "0:v:0", *a_map, "-c:v", "mpeg4", "-q:v", "3", "-vtag", "xvid", "-vf", EVEN,
                "-c:a", "libmp3lame", "-b:a", "192k"]
    if target == "wmv":
        return ["-map", "0:v:0", *a_map, "-c:v", "wmv2", "-q:v", "3", "-vf", EVEN, "-c:a", "wmav2", "-b:a", "192k"]
    if target == "gif":
        width = min(720, info.width or 720)
        vf = (f"[0:v:0]fps=12,scale={width}:-1:flags=lanczos,split[a][b];"
              "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4[out]")
        return ["-filter_complex", vf, "-map", "[out]", "-loop", "0"]
    raise RuntimeError(f"Formato de vídeo desconhecido: {target}")


def _remux_ok(target: str, src_ext: str, info: Probe) -> bool:
    """Can we copy streams without re-encoding (lossless and fast)?"""
    if src_ext == "gif" or not info.has_video:
        return False
    v = info.video_codecs[0]
    a = info.audio_codecs[0] if info.audio_codecs else None
    if target == "mkv":
        return v in ("h264", "hevc", "vp9", "av1", "mpeg4", "vp8") and a in (None, "aac", "mp3", "opus", "vorbis", "flac", "ac3")
    if target in ("mp4", "mov"):
        return v == "h264" and a in (None, "aac", "mp3")
    return False


def convert(ctx: ConvertContext, src: Path, target: Target, plan: Plan) -> None:
    ffmpeg = ctx.engines.path("ffmpeg")
    info = probe(ffmpeg, src)
    key = target.key
    stem = F.stem(src)
    ext = "mp3" if key == "audio_mp3" else target.ext
    dst = ctx.stage(f"{stem}.{ext}")
    is_audio_target = key in ("mp3", "m4a", "wav", "flac", "ogg", "opus", "aiff", "wma", "audio_mp3")

    if is_audio_target:
        if not info.has_audio:
            raise RuntimeError("Este arquivo não possui faixa de áudio.")
        body = ["-map", "0:a:0", "-vn", "-map_metadata", "0", *audio_args(key, ctx)]
    else:
        if not info.has_video:
            raise RuntimeError("Este arquivo não possui faixa de vídeo.")
        body = video_args(key, ctx, info)

    duration = info.duration

    def on_line(line: str) -> None:
        if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
            try:
                us = int(line.split("=", 1)[1])
            except ValueError:
                return
            if duration > 0:
                ctx.progress(min(0.99, us / 1_000_000 / duration), "Convertendo")
        elif line == "progress=end":
            ctx.progress(1.0, "Finalizando")

    head = [ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-progress", "pipe:1", "-nostats"]
    ctx.progress(0.0 if duration else None, "Convertendo")

    if not is_audio_target and _remux_ok(key, F.extension(src), info):
        copy = ["-map", "0:v:0", "-map", "0:a:0?", "-c", "copy"]
        if key in ("mp4", "mov"):
            copy += ["-movflags", "+faststart"]
        try:
            ctx.run([*head, "-i", src, *copy, dst], on_stdout_line=on_line)
            return
        except procs.ProcessError:
            dst.unlink(missing_ok=True)  # fall back to re-encoding
    ctx.run([*head, "-i", src, *body, dst], on_stdout_line=on_line, timeout=6 * 3600)


def thumbnail(ffmpeg: str, src: Path, dst: Path, size: int = 256) -> bool:
    """Grab a representative frame for the wheel preview."""
    try:
        procs.run([ffmpeg, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", "-ss", "1", "-i", src,
                   "-frames:v", "1", "-vf", f"scale={size}:-2", dst], timeout=15)
        return dst.exists() and dst.stat().st_size > 0
    except Exception:  # noqa: BLE001
        return False
