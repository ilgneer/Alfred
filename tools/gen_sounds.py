"""Synthesises Alfred's original UI sounds (no samples from other apps).

    python tools/gen_sounds.py            -> assets/sounds/*.wav (48 kHz, 16-bit, stereo)

Every sound is built from sine partials, filtered noise and a tiny synthetic
room reverb, so the result is original and reproducible. Released as CC0.
"""
from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

SR = 48_000
OUT = Path(__file__).resolve().parents[1] / "assets" / "sounds"
rng = np.random.default_rng(1234)


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(SR * dur)) / SR


def db(x: float) -> float:
    return 10 ** (x / 20)


def fade(sig: np.ndarray, fin: float = 0.002, fout: float = 0.02) -> np.ndarray:
    sig = sig.copy()
    a, b = int(SR * fin), int(SR * fout)
    if a:
        sig[:a] *= np.linspace(0, 1, a) ** 2
    if b:
        sig[-b:] *= np.linspace(1, 0, b) ** 2
    return sig


def bell(freq: float, dur: float, tau: float, bright: float = 1.0, attack: float = 0.003) -> np.ndarray:
    """Soft bell: slightly inharmonic partials with independent decays."""
    t = t_axis(dur)
    partials = [(1.0, 1.0, 1.0), (2.002, 0.32 * bright, 0.55), (3.011, 0.14 * bright, 0.38),
                (4.17, 0.05 * bright, 0.25), (0.5, 0.10, 1.2)]
    sig = np.zeros_like(t)
    for ratio, amp, tmul in partials:
        f = freq * ratio
        if f > SR / 2.2:
            continue
        sig += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 0.3)) * np.exp(-t / (tau * tmul))
    env = np.minimum(1.0, t / attack)
    return sig * env


def onepole_lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    a = math.exp(-2 * math.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def sweep_bandpass(noise: np.ndarray, f0: float, f1: float, q: float = 4.0) -> np.ndarray:
    """Resonant band-pass whose centre moves exponentially from f0 to f1."""
    n = len(noise)
    out = np.zeros(n)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(n):
        f = f0 * (f1 / f0) ** (i / max(1, n - 1))
        w = 2 * math.pi * f / SR
        alpha = math.sin(w) / (2 * q)
        b0, b2 = alpha, -alpha
        a0, a1, a2 = 1 + alpha, -2 * math.cos(w), 1 - alpha
        x = noise[i]
        y = (b0 * x + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1 = x1, x
        y2, y1 = y1, y
        out[i] = y
    return out


def room(sig: np.ndarray, mix: float = 0.14, decay: float = 0.22, tail: float = 0.35) -> np.ndarray:
    """Tiny synthetic room: exponentially decaying, low-passed noise impulse response."""
    t = t_axis(tail)
    ir = rng.standard_normal(len(t)) * np.exp(-t / (decay / 3))
    ir = onepole_lowpass(ir, 4200)
    ir /= np.sqrt(np.sum(ir**2)) + 1e-9
    wet = np.convolve(np.concatenate([sig, np.zeros(len(t))]), ir)[: len(sig) + len(t)]
    dry = np.concatenate([sig, np.zeros(len(t))])
    return dry * (1 - mix) + wet * mix


def place(total: float, *parts: tuple[float, np.ndarray]) -> np.ndarray:
    out = np.zeros(int(SR * total))
    for start, sig in parts:
        i = int(SR * start)
        j = min(len(out), i + len(sig))
        out[i:j] += sig[: j - i]
    return out


def normalize(sig: np.ndarray, peak_db: float) -> np.ndarray:
    peak = np.max(np.abs(sig)) or 1.0
    return sig / peak * db(peak_db)


def stereo(sig: np.ndarray, width: float = 0.0, delay_ms: float = 0.0) -> np.ndarray:
    d = int(SR * delay_ms / 1000)
    right = np.concatenate([np.zeros(d), sig])[: len(sig)] if d else sig
    left = sig * (1 - width * 0.3) + right * width * 0.3
    return np.stack([left, right * (1 - width * 0.3) + sig * width * 0.3], axis=1)


def write(name: str, sig: np.ndarray) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if sig.ndim == 1:
        sig = stereo(sig)
    # trim inaudible tail (< -60 dBFS) and fade the cut point
    level = np.max(np.abs(sig), axis=1)
    loud = np.nonzero(level > db(-60))[0]
    if len(loud):
        end = min(len(sig), loud[-1] + int(SR * 0.01))
        sig = sig[:end].copy()
        n = min(len(sig), int(SR * 0.015))
        sig[-n:] *= np.linspace(1, 0, n)[:, None]
    pcm = np.clip(sig, -1, 1)
    pcm = (pcm * 32767).astype("<i2")
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{name}.wav  {len(sig) / SR * 1000:.0f} ms  pico {20 * np.log10(np.max(np.abs(sig))):.1f} dBFS")


# ---------------------------------------------------------------------------
# the sounds
# ---------------------------------------------------------------------------

def hover() -> np.ndarray:
    """Discreet digital glass tick (~45 ms)."""
    t = t_axis(0.045)
    body = (np.sin(2 * np.pi * 2100 * t) * np.exp(-t / 0.008)
            + 0.40 * np.sin(2 * np.pi * 3150 * t) * np.exp(-t / 0.0045)
            + 0.25 * np.sin(2 * np.pi * 1050 * t) * np.exp(-t / 0.006))
    click = rng.standard_normal(len(t)) * np.exp(-t / 0.0006) * 0.12
    click = onepole_lowpass(click - onepole_lowpass(click, 1800), 6500)  # band-limited transient
    sig = fade(body + click, 0.0004, 0.01)
    return stereo(normalize(sig, -7.5), width=0.2, delay_ms=0.25)


def select() -> np.ndarray:
    """Short, satisfying two-note confirmation (~260 ms + tail)."""
    thump_t = t_axis(0.06)
    thump = np.sin(2 * np.pi * 170 * thump_t) * np.exp(-thump_t / 0.018) * 0.5
    sig = place(0.32, (0.0, thump), (0.0, bell(1318.5, 0.28, 0.07)), (0.05, 0.85 * bell(1975.5, 0.27, 0.08)))
    sig = room(fade(sig, 0.001, 0.04), mix=0.12)
    return stereo(normalize(sig, -2.0), width=0.35, delay_ms=0.4)


def open_() -> np.ndarray:
    """Smooth rising whoosh with a soft shimmer when the wheel opens."""
    dur = 0.30
    t = t_axis(dur)
    noise = rng.standard_normal(len(t))
    whoosh = sweep_bandpass(noise, 320, 2200, q=3.0)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 1.6
    whoosh *= env
    glide_f = 210 * (2 ** (t / dur))
    glide = 0.22 * np.sin(2 * np.pi * np.cumsum(glide_f) / SR) * env
    shimmer = place(dur, (0.17, 0.10 * bell(2637.0, 0.13, 0.05, bright=0.4)))
    sig = room(fade(whoosh / (np.max(np.abs(whoosh)) + 1e-9) + glide + shimmer, 0.01, 0.05), mix=0.1)
    return stereo(normalize(sig, -6.0), width=0.6, delay_ms=0.6)


def close() -> np.ndarray:
    """Quiet falling whoosh used on cancel / ESC."""
    dur = 0.18
    t = t_axis(dur)
    whoosh = onepole_lowpass(sweep_bandpass(rng.standard_normal(len(t)), 1800, 360, q=2.5), 5000)
    whoosh *= np.exp(-t / 0.07) * np.minimum(1, t / 0.01)
    sig = fade(whoosh, 0.002, 0.04)
    return stereo(normalize(sig, -11.0), width=0.5, delay_ms=0.5)


def success() -> np.ndarray:
    """Elegant rising major arpeggio (E–G#–B–E) with a warm tail."""
    notes = [(0.00, 659.25, 0.20, 0.9), (0.07, 830.61, 0.22, 0.85), (0.14, 987.77, 0.26, 0.8),
             (0.23, 1318.51, 0.40, 0.95)]
    parts = [(start, amp * bell(f, 0.9, tau, bright=0.8)) for start, f, tau, amp in notes]
    pad_t = t_axis(0.8)
    pad = 0.12 * (np.sin(2 * np.pi * 329.63 * pad_t) + 0.5 * np.sin(2 * np.pi * 493.88 * pad_t))
    pad *= np.minimum(1, pad_t / 0.12) * np.exp(-pad_t / 0.35)
    sig = place(1.0, *parts, (0.0, pad))
    sig = room(fade(sig, 0.001, 0.12), mix=0.18, decay=0.35, tail=0.45)
    return stereo(normalize(sig, -2.0), width=0.45, delay_ms=0.7)


def error() -> np.ndarray:
    """Discreet two-tone descending signal (never harsh)."""
    def tone(f, dur):
        t = t_axis(dur)
        s = (np.sin(2 * np.pi * f * t) + 0.22 * np.sin(2 * np.pi * 2 * f * t) + 0.06 * np.sin(2 * np.pi * 3 * f * t))
        env = np.minimum(1, t / 0.012) * np.exp(-t / 0.09)
        return s * env

    sig = place(0.42, (0.0, tone(440.0, 0.16)), (0.15, tone(349.23, 0.24)))
    sig = onepole_lowpass(sig, 3000)
    sig = room(fade(sig, 0.002, 0.05), mix=0.1)
    return stereo(normalize(sig, -5.0), width=0.2, delay_ms=0.3)


SOUNDS = {"hover": hover, "select": select, "open": open_, "close": close, "success": success, "error": error}

if __name__ == "__main__":
    for name, fn in SOUNDS.items():
        write(name, fn())
