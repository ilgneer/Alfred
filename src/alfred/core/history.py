"""Conversion history stored as JSON lines (most recent last)."""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from alfred.core import paths

log = logging.getLogger(__name__)
MAX_ENTRIES = 500


@dataclass
class HistoryEntry:
    id: str
    started: float
    finished: float
    target: str            # rótulo exibido, ex.: "PNG"
    status: str            # done | partial | failed | cancelled
    sources: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max(0.0, self.finished - self.started)


class History:
    def __init__(self, path: Path | None = None):
        self.path = path or (paths.data_dir() / "history.jsonl")
        self._lock = threading.Lock()

    def add(self, entry: HistoryEntry) -> None:
        with self._lock:
            entries = self._read()
            entries.append(entry)
            entries = entries[-MAX_ENTRIES:]
            self._write(entries)

    def entries(self) -> list[HistoryEntry]:
        with self._lock:
            return list(reversed(self._read()))

    def clear(self) -> None:
        with self._lock:
            self._write([])

    def count_since(self, timestamp: float) -> int:
        return sum(1 for e in self.entries() if e.finished >= timestamp and e.status in ("done", "partial"))

    def count_today(self) -> int:
        lt = time.localtime()
        midnight = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
        return self.count_since(midnight)

    # -- storage -----------------------------------------------------------
    def _read(self) -> list[HistoryEntry]:
        if not self.path.exists():
            return []
        out: list[HistoryEntry] = []
        try:
            with self.path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        out.append(HistoryEntry(**json.loads(line)))
                    except (ValueError, TypeError):
                        continue
        except OSError as exc:
            log.warning("Não foi possível ler o histórico: %s", exc)
        return out

    def _write(self, entries: list[HistoryEntry]) -> None:
        tmp = self.path.with_suffix(".tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                for e in entries:
                    fh.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
            tmp.replace(self.path)
        except OSError as exc:
            log.warning("Não foi possível gravar o histórico: %s", exc)
