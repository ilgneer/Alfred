"""Background job queue (pure Python; the UI wraps it with Qt signals)."""
from __future__ import annotations

import itertools
import logging
import queue
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from alfred.core import engines as engines_mod
from alfred.core import routes
from alfred.core.context import ConvertContext, Options
from alfred.core.converters import convert_batch, convert_one
from alfred.core.history import History, HistoryEntry
from alfred.core.procs import Cancelled, CancelToken, ProcessError

log = logging.getLogger(__name__)

QUEUED, RUNNING, DONE, PARTIAL, FAILED, CANCELLED = (
    "queued", "running", "done", "partial", "failed", "cancelled")
FINAL_STATES = (DONE, PARTIAL, FAILED, CANCELLED)
_ids = itertools.count(1)


@dataclass
class Job:
    files: list[Path]
    target: routes.Target
    skipped: list[Path] = field(default_factory=list)
    id: str = field(default_factory=lambda: f"{int(time.time())}-{next(_ids)}")
    state: str = QUEUED
    progress: float | None = 0.0
    message: str = "Na fila"
    current: str = ""
    outputs: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    started: float = 0.0
    finished: float = 0.0
    token: CancelToken = field(default_factory=CancelToken, repr=False)

    @property
    def title(self) -> str:
        n = len(self.files)
        first = self.files[0].name if self.files else ""
        return first if n == 1 else f"{first} + {n - 1}"

    @property
    def finished_ok(self) -> bool:
        return self.state in (DONE, PARTIAL)


def friendly_error(exc: BaseException) -> str:
    if isinstance(exc, ProcessError):
        detail = str(exc).strip().splitlines()[-1:] or [""]
        return f"O motor de conversão falhou: {detail[0][:300]}"
    if isinstance(exc, MemoryError):
        return "Memória insuficiente para converter este arquivo."
    if isinstance(exc, PermissionError):
        return "Sem permissão para ler o arquivo ou gravar na pasta de destino."
    if isinstance(exc, FileNotFoundError):
        return f"Arquivo não encontrado: {getattr(exc, 'filename', '') or exc}"
    msg = str(exc).strip()
    return msg or exc.__class__.__name__


def run_job(job: Job, engines: engines_mod.Engines, options: Options,
            notify: Callable[[Job], None] | None = None) -> Job:
    """Execute a job synchronously (used by the worker thread, tests and self-test)."""
    notify = notify or (lambda j: None)
    job.state, job.started = RUNNING, time.time()
    job.message = "Convertendo"
    notify(job)
    n = len(job.files)

    def make_progress(index: int, name: str):
        last = [0.0]

        def cb(fraction: float | None, text: str):
            now = time.monotonic()
            if fraction is not None and now - last[0] < 0.08 and fraction < 1.0:
                return
            last[0] = now
            if job.target.batch or n == 1:
                job.progress = fraction
            else:
                job.progress = (index + (fraction or 0.0)) / n
            job.message = text
            job.current = name
            notify(job)
        return cb

    try:
        if job.target.batch:
            ctx = ConvertContext(engines, options, job.token, make_progress(0, job.title))
            try:
                ctx.begin(job.files[0])
                convert_batch(ctx, job.files, job.target)
                job.token.check()
                job.outputs.extend(ctx.commit())
                job.notes.extend(ctx.notes)
            except Cancelled:
                ctx.discard()
                raise
            except Exception as exc:  # noqa: BLE001
                ctx.discard()
                log.error("Falha em %s: %s", job.target.key, traceback.format_exc())
                job.errors.append(friendly_error(exc))
        else:
            for i, src in enumerate(job.files):
                job.token.check()
                job.current = src.name
                plan = routes.pick_plan(src, job.target.key, engines)
                if plan is None:
                    job.errors.append(f"{src.name}: conversão para {job.target.label} indisponível.")
                    continue
                if not src.exists():
                    job.errors.append(f"{src.name}: o arquivo não existe mais.")
                    continue
                ctx = ConvertContext(engines, options, job.token, make_progress(i, src.name))
                try:
                    ctx.begin(src)
                    convert_one(ctx, src, job.target, plan)
                    job.token.check()
                    job.outputs.extend(ctx.commit())
                    job.notes.extend(ctx.notes)
                except Cancelled:
                    ctx.discard()
                    raise
                except Exception as exc:  # noqa: BLE001
                    ctx.discard()
                    log.error("Falha convertendo %s para %s:\n%s", src, job.target.key, traceback.format_exc())
                    job.errors.append(f"{src.name}: {friendly_error(exc)}")
        if job.outputs and job.errors:
            job.state = PARTIAL
        elif job.outputs:
            job.state = DONE
        else:
            job.state = FAILED
    except Cancelled:
        job.state = CANCELLED
    job.finished = time.time()
    job.progress = 1.0 if job.state in (DONE, PARTIAL) else job.progress
    job.message = {DONE: "Concluído", PARTIAL: "Concluído com avisos", FAILED: "Falhou",
                   CANCELLED: "Cancelado"}[job.state]
    notify(job)
    return job


class JobRunner:
    """Sequential queue running on one daemon thread."""

    def __init__(self, options_provider: Callable[[], Options], history: History | None,
                 on_update: Callable[[Job], None]):
        self._options = options_provider
        self._history = history
        self._on_update = on_update
        self._queue: queue.Queue[Job | None] = queue.Queue()
        self.jobs: dict[str, Job] = {}
        self._current: Job | None = None
        self._thread = threading.Thread(target=self._loop, name="alfred-jobs", daemon=True)
        self._thread.start()

    def submit(self, files: list[Path], choice: routes.Choice) -> Job:
        job = Job(files=list(choice.files) or list(files), target=choice.target, skipped=list(choice.skipped))
        if job.skipped:
            job.notes.append(f"{len(job.skipped)} arquivo(s) já estavam em {choice.target.label}.")
        self.jobs[job.id] = job
        self._on_update(job)
        self._queue.put(job)
        return job

    def cancel(self, job_id: str) -> None:
        job = self.jobs.get(job_id)
        if job and job.state not in FINAL_STATES:
            job.token.cancel()
            if job.state == QUEUED:
                job.state, job.message = CANCELLED, "Cancelado"
                self._on_update(job)

    def cancel_all(self) -> None:
        for job_id in list(self.jobs):
            self.cancel(job_id)

    @property
    def busy(self) -> bool:
        return any(j.state in (QUEUED, RUNNING) for j in self.jobs.values())

    def shutdown(self, timeout: float = 5.0) -> None:
        self.cancel_all()
        self._queue.put(None)
        self._thread.join(timeout)

    def _loop(self) -> None:
        while True:
            job = self._queue.get()
            if job is None:
                return
            if job.state == CANCELLED:
                continue
            self._current = job
            try:
                run_job(job, engines_mod.get(), self._options(), self._on_update)
            except Exception:  # noqa: BLE001 - never kill the worker thread
                log.exception("Erro inesperado no job %s", job.id)
                job.state, job.message = FAILED, "Falhou"
                job.errors.append("Erro inesperado. Veja o log em Configurações › Avançado.")
                self._on_update(job)
            finally:
                self._current = None
            if self._history is not None:
                try:
                    self._history.add(HistoryEntry(
                        id=job.id, started=job.started, finished=job.finished or time.time(),
                        target=job.target.label + (f" {job.target.sublabel}" if job.target.sublabel else ""),
                        status=job.state, sources=[str(f) for f in job.files],
                        outputs=[str(o) for o in job.outputs], errors=job.errors[:20]))
                except Exception:  # noqa: BLE001
                    log.exception("Falha ao gravar histórico")
