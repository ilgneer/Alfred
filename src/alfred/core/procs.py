"""Cancellable execution of external engines, without console windows.

On Windows every child process is attached to a Job Object configured with
``KILL_ON_JOB_CLOSE``: if Alfred exits (or crashes) no FFmpeg/LibreOffice
process is left running in the background.
"""
from __future__ import annotations

import logging
import os
import queue
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

log = logging.getLogger(__name__)

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Cancelled(Exception):
    """Raised when the user cancels a job."""


class CancelToken:
    def __init__(self):
        self._event = threading.Event()
        self._procs: set[subprocess.Popen] = set()
        self._lock = threading.Lock()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        self._event.set()
        with self._lock:
            procs = list(self._procs)
        for p in procs:
            kill_tree(p)

    def check(self) -> None:
        if self._event.is_set():
            raise Cancelled()

    def register(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._procs.add(proc)
        if self._event.is_set():
            kill_tree(proc)

    def unregister(self, proc: subprocess.Popen) -> None:
        with self._lock:
            self._procs.discard(proc)


# ---------------------------------------------------------------------------
# Windows Job Object
# ---------------------------------------------------------------------------
_job_handle = None


def _windows_job():
    global _job_handle
    if os.name != "nt":
        return None
    if _job_handle is not None:
        return _job_handle
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class BASIC(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_longlong),
                ("PerJobUserTimeLimit", ctypes.c_longlong),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class EXTENDED(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", BASIC),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        job = kernel32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = EXTENDED()
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        JobObjectExtendedLimitInformation = 9
        ok = kernel32.SetInformationJobObject(
            wintypes.HANDLE(job), JobObjectExtendedLimitInformation,
            ctypes.byref(info), ctypes.sizeof(info))
        if not ok:
            return None
        _job_handle = job
        return job
    except Exception as exc:  # noqa: BLE001
        log.debug("Job Object indisponível: %s", exc)
        return None


def _assign_to_job(proc: subprocess.Popen) -> None:
    job = _windows_job()
    if not job:
        return
    try:
        import ctypes
        from ctypes import wintypes

        handle = getattr(proc, "_handle", None)
        if handle:
            ctypes.windll.kernel32.AssignProcessToJobObject(wintypes.HANDLE(job), wintypes.HANDLE(int(handle)))
    except Exception as exc:  # noqa: BLE001
        log.debug("AssignProcessToJobObject falhou: %s", exc)


def kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, creationflags=NO_WINDOW, timeout=10)
        else:
            proc.kill()
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

class ProcessError(RuntimeError):
    pass


def run(
    args: list,
    token: CancelToken | None = None,
    timeout: float = 3600,
    on_stdout_line: Callable[[str], None] | None = None,
    cwd: str | Path | None = None,
    env: dict | None = None,
) -> str:
    """Run a process, stream stdout lines to ``on_stdout_line``, return stderr.

    Raises :class:`Cancelled` if the token is cancelled, :class:`ProcessError`
    on non-zero exit codes and on timeouts.
    """
    args = [str(a) for a in args]
    log.debug("Executando: %s", " ".join(args))
    proc = subprocess.Popen(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
        env=env,
        creationflags=NO_WINDOW,
    )
    _assign_to_job(proc)
    if token:
        token.register(proc)
    stderr_chunks: list[bytes] = []

    def read_stderr():
        assert proc.stderr is not None
        for chunk in iter(lambda: proc.stderr.read(4096), b""):
            stderr_chunks.append(chunk)
            if sum(len(c) for c in stderr_chunks) > 2_000_000:
                del stderr_chunks[: len(stderr_chunks) // 2]

    lines: queue.Queue[str | None] = queue.Queue()

    def read_stdout():
        assert proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            lines.put(raw.decode("utf-8", "replace").rstrip("\r\n"))
        lines.put(None)

    t_err = threading.Thread(target=read_stderr, daemon=True)
    t_out = threading.Thread(target=read_stdout, daemon=True)
    t_err.start()
    t_out.start()
    started = time.monotonic()
    try:
        stdout_open = True
        while True:
            if token and token.cancelled:
                kill_tree(proc)
                raise Cancelled()
            if time.monotonic() - started > timeout:
                kill_tree(proc)
                raise ProcessError("O conversor excedeu o tempo limite.")
            if stdout_open:
                try:
                    line = lines.get(timeout=0.2)
                except queue.Empty:
                    continue
                if line is None:
                    stdout_open = False
                    continue
                if on_stdout_line:
                    try:
                        on_stdout_line(line)
                    except Cancelled:
                        kill_tree(proc)
                        raise
                continue
            try:
                proc.wait(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                continue
        t_err.join(timeout=2)
    finally:
        if token:
            token.unregister(proc)
        if proc.poll() is None:
            kill_tree(proc)
    stderr = b"".join(stderr_chunks).decode("utf-8", "replace")
    if token and token.cancelled:
        raise Cancelled()
    if proc.returncode != 0:
        tail = "\n".join(line for line in stderr.strip().splitlines()[-8:])
        raise ProcessError(tail or f"O conversor terminou com código {proc.returncode}.")
    return stderr
