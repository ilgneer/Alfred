"""Low-latency UI sounds.

Windows: WAV data kept in memory and played with ``PlaySoundW`` (SND_MEMORY |
SND_ASYNC) through ctypes — no extra multimedia stack, no latency on first
play. The volume is applied by scaling the PCM samples, so 0–100 % works the
same on every machine. Other platforms (development) use QtMultimedia when
available and ``ALFRED_QT_SOUND=1`` is set, otherwise stay silent.
"""
from __future__ import annotations

import array
import io
import logging
import sys
import wave

from alfred.core import paths

log = logging.getLogger(__name__)

NAMES = ("hover", "select", "open", "close", "success", "error")
LABELS = {"hover": "Passar o mouse", "select": "Seleção", "open": "Abrir a roda", "close": "Cancelar",
          "success": "Conversão concluída", "error": "Erro"}


def _gain(volume: int) -> float:
    v = max(0, min(100, volume)) / 100
    return v ** 1.6  # perceptual curve


def scaled_wav(raw: bytes, gain: float) -> bytes:
    with wave.open(io.BytesIO(raw)) as w:
        params = w.getparams()
        frames = w.readframes(w.getnframes())
    if params.sampwidth != 2:
        return raw
    samples = array.array("h")
    samples.frombytes(frames)
    if sys.byteorder == "big":
        samples.byteswap()
    for i, s in enumerate(samples):
        samples[i] = int(max(-32768, min(32767, s * gain)))
    if sys.byteorder == "big":
        samples.byteswap()
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        w.writeframes(samples.tobytes())
    return out.getvalue()


class SoundPlayer:
    def __init__(self, enabled: bool = True, volume: int = 80):
        self.enabled = enabled
        self.volume = volume
        self._raw: dict[str, bytes] = {}
        self._scaled: dict[tuple[str, int], object] = {}
        self._keep = None  # buffer currently playing (must stay alive)
        self._qt_effects: dict = {}
        for name in NAMES:
            f = paths.asset_path("sounds", f"{name}.wav")
            try:
                self._raw[name] = f.read_bytes()
            except OSError:
                log.warning("Som ausente: %s", f)
        self._win = None
        if sys.platform == "win32":
            try:
                import ctypes

                self._win = ctypes.WinDLL("winmm")
                self._win.PlaySoundW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
            except OSError:
                self._win = None

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, int(volume)))

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not enabled:
            self.stop()

    def play(self, name: str, force: bool = False) -> None:
        if (not self.enabled and not force) or self.volume <= 0 or name not in self._raw:
            return
        try:
            if self._win is not None:
                self._play_windows(name)
            else:
                self._play_qt(name)
        except Exception as exc:  # noqa: BLE001 - sound must never break the UI
            log.debug("Falha ao tocar %s: %s", name, exc)

    def stop(self) -> None:
        if self._win is not None:
            try:
                self._win.PlaySoundW(None, None, 0)
            except Exception:  # noqa: BLE001
                pass

    # -- backends ------------------------------------------------------------
    def _play_windows(self, name: str) -> None:
        import ctypes

        key = (name, self.volume)
        buf = self._scaled.get(key)
        if buf is None:
            data = scaled_wav(self._raw[name], _gain(self.volume))
            buf = ctypes.create_string_buffer(data, len(data))
            if len(self._scaled) > 40:
                self._scaled.clear()
            self._scaled[key] = buf
        SND_ASYNC, SND_NODEFAULT, SND_MEMORY = 0x0001, 0x0002, 0x0004
        self._win.PlaySoundW(ctypes.cast(buf, ctypes.c_void_p), None, SND_ASYNC | SND_NODEFAULT | SND_MEMORY)
        self._keep = buf  # the previous buffer is released only after the new call returned

    def _play_qt(self, name: str) -> None:
        # Development fallback only (Linux/macOS): opt-in, because QtMultimedia
        # crashes on machines without an audio device.
        import os

        if os.environ.get("ALFRED_QT_SOUND") != "1":
            return
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QSoundEffect
        except Exception:  # noqa: BLE001
            return
        eff = self._qt_effects.get(name)
        if eff is None:
            eff = QSoundEffect()
            eff.setSource(QUrl.fromLocalFile(str(paths.asset_path("sounds", f"{name}.wav"))))
            self._qt_effects[name] = eff
        eff.setVolume(_gain(self.volume))
        eff.play()
