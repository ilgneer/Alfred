"""SRT <-> WebVTT <-> plain text, with a real cue parser."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from alfred.core import formats as F
from alfred.core.context import ConvertContext
from alfred.core.converters.office import read_text
from alfred.core.routes import Plan, Target

_TS = re.compile(
    r"(?P<a>(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})\s*-->\s*(?P<b>(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3})(?P<rest>.*)$"
)
_TAG = re.compile(r"</?(?:c|v|i|b|u|ruby|rt|lang)(?:[.\s][^>]*)?>|<\d{1,2}:\d{2}[^>]*>")
_VOICE = re.compile(r"<v(?:\.[^\s>]+)?\s+([^>]+)>")


@dataclass
class Cue:
    start: int  # ms
    end: int
    text: str


def parse_time(s: str) -> int:
    s = s.replace(",", ".")
    parts = s.split(":")
    if len(parts) == 2:
        h, m, rest = 0, parts[0], parts[1]
    else:
        h, m, rest = parts[0], parts[1], parts[2]
    sec, _, frac = rest.partition(".")
    frac = (frac + "000")[:3]
    return ((int(h) * 60 + int(m)) * 60 + int(sec)) * 1000 + int(frac)


def fmt_time(ms: int, sep: str) -> str:
    ms = max(0, ms)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def parse(text: str) -> list[Cue]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").lstrip("﻿")
    blocks = re.split(r"\n\s*\n", text.strip())
    cues: list[Cue] = []
    for block in blocks:
        lines = block.split("\n")
        if lines[0].startswith(("NOTE", "STYLE", "REGION")):
            continue
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        m = _TS.search(lines[idx])
        if not m:
            continue
        body = "\n".join(lines[idx + 1:]).strip("\n")
        cues.append(Cue(parse_time(m.group("a")), parse_time(m.group("b")), body))
    if not cues:
        raise RuntimeError("Nenhuma legenda válida foi encontrada no arquivo.")
    return cues


def _clean_for_srt(text: str) -> str:
    text = _VOICE.sub(lambda m: f"{m.group(1).strip()}: ", text)
    text = re.sub(r"</?(?:c|v|ruby|rt|lang)(?:[.\s][^>]*)?>|<\d{1,2}:\d{2}[^>]*>", "", text)
    return text


def _plain(text: str) -> str:
    text = _VOICE.sub(lambda m: f"{m.group(1).strip()}: ", text)
    text = _TAG.sub("", text)
    text = re.sub(r"</?font[^>]*>|\{\\an?\d+\}", "", text)
    return text.strip()


def to_srt(cues: list[Cue]) -> str:
    out = []
    for i, c in enumerate(cues, 1):
        out.append(f"{i}\n{fmt_time(c.start, ',')} --> {fmt_time(c.end, ',')}\n{_clean_for_srt(c.text)}")
    return "\n\n".join(out) + "\n"


def to_vtt(cues: list[Cue]) -> str:
    out = ["WEBVTT", ""]
    for c in cues:
        text = re.sub(r"</?font[^>]*>|\{\\an?\d+\}", "", c.text)
        out.append(f"{fmt_time(c.start, '.')} --> {fmt_time(c.end, '.')}\n{text}\n")
    return "\n".join(out)


def to_txt(cues: list[Cue]) -> str:
    lines: list[str] = []
    for c in cues:
        for line in _plain(c.text).split("\n"):
            line = line.strip()
            if line and (not lines or lines[-1] != line):
                lines.append(line)
    return "\n".join(lines) + "\n"


def convert(ctx: ConvertContext, src: Path, target: Target, plan: Plan) -> None:
    cues = parse(read_text(src))
    stem = F.stem(src)
    writer = {"srt": to_srt, "vtt": to_vtt, "txt": to_txt}[target.key]
    ctx.stage(f"{stem}.{target.ext}").write_text(writer(cues), encoding="utf-8")
    ctx.progress(1.0, "Pronto")
