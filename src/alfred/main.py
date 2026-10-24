"""Command-line entry point.

    Alfred.exe [arquivos...]          abre a roda para os arquivos
    Alfred.exe --open arquivos...     idem (usado pelo menu de contexto / Enviar para)
    Alfred.exe --background           inicia oculto na bandeja (inicialização com o Windows)
    Alfred.exe --settings             abre as configurações
    Alfred.exe --quit                 encerra a instância em execução (desinstalador)
    Alfred.exe --unregister           remove integrações do Explorer (desinstalador)
    Alfred.exe --self-test saida.json executa verificações sem interface (CI)
"""
from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys


def _ensure_streams() -> None:
    """Windowed builds have no console: give print()/logging a sink."""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115


def setup_logging(verbose: bool = False) -> None:
    from alfred.core import paths

    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    try:
        fh = logging.handlers.RotatingFileHandler(paths.logs_dir() / "alfred.log", maxBytes=2_000_000,
                                                  backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError:
        pass
    if verbose or not getattr(sys, "frozen", False):
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fmt)
        root.addHandler(sh)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="Alfred", add_help=True)
    p.add_argument("files", nargs="*")
    p.add_argument("--open", nargs="*", default=None, dest="open_files")
    p.add_argument("--background", action="store_true")
    p.add_argument("--settings", action="store_true")
    p.add_argument("--quit", action="store_true")
    p.add_argument("--unregister", action="store_true")
    p.add_argument("--self-test", dest="self_test", metavar="RELATORIO")
    p.add_argument("--verbose", action="store_true")
    args, _unknown = p.parse_known_args(argv)
    return args


def run_worker(argv: list[str]) -> int:
    """Child-process workers (cancellable heavy Python conversions)."""
    i = argv.index("--worker")
    name, rest = argv[i + 1], argv[i + 2:]
    if name == "pdf2docx":
        from alfred.core.converters.pdf import worker_pdf2docx

        return worker_pdf2docx(rest[0], rest[1])
    return 64


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _ensure_streams()
    if "--worker" in argv:
        return run_worker(argv)
    args = parse_args(argv)
    setup_logging(args.verbose)
    if args.self_test:
        from alfred.selftest import run_self_test

        return run_self_test(args.self_test)
    if args.unregister:
        from alfred.platform import integration

        integration.unregister_all()
        return 0
    from alfred.app import run_gui

    return run_gui(args)


if __name__ == "__main__":
    raise SystemExit(main())
