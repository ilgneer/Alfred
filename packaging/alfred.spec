# PyInstaller spec — Alfred (Windows x64, sem console).
#   pyinstaller packaging/alfred.spec --noconfirm --clean
# Normalmente chamado por tools/build.py, que também copia os motores (engines/).
# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 - SPECPATH is injected by PyInstaller
SRC = ROOT / "src"
IS_WIN = sys.platform == "win32"
VERSION_FILE = ROOT / "build" / "version_info.txt"

datas = [
    (str(ROOT / "assets" / "alfred.png"), "assets"),
    (str(ROOT / "assets" / "alfred.ico"), "assets"),
    (str(ROOT / "assets" / "alfred_tray.png"), "assets"),
    (str(ROOT / "assets" / "sounds"), "assets/sounds"),
    (str(ROOT / "assets" / "fonts"), "assets/fonts"),
]

hiddenimports = [
    "alfred.core.converters.images",
    "alfred.core.converters.media",
    "alfred.core.converters.pdf",
    "alfred.core.converters.documents",
    "alfred.core.converters.subtitles",
    "alfred.core.converters.archives",
    "alfred.selftest",
    "pillow_heif",
    "PIL.AvifImagePlugin",
    "pymupdf",
    "pdf2docx",
    "docx",
    "pptx",
    "openpyxl",
    "xlrd",
    "PySide6.QtSvg",
    "PySide6.QtNetwork",
]

excludes = [
    # Engines are copied as standalone executables to engines/, not bundled twice.
    "imageio_ffmpeg", "pypandoc",
    # Qt modules Alfred never uses (keeps the installer small).
    "PySide6.QtMultimedia", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtQml",
    "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.Qt3DCore", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtDesigner",
    "PySide6.QtHelp", "PySide6.QtSql", "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtLocation",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtTextToSpeech", "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets",
    # Development / unrelated
    "tkinter", "pytest", "IPython", "matplotlib", "pandas", "scipy", "onnxruntime",
]

a = Analysis(  # noqa: F821
    [str(SRC / "alfred" / "__main__.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Alfred",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,              # nunca abre CMD
    disable_windowed_traceback=False,
    icon=str(ROOT / "assets" / "alfred.ico") if IS_WIN else None,
    version=str(VERSION_FILE) if IS_WIN and VERSION_FILE.exists() else None,
    uac_admin=False,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Alfred",
)
