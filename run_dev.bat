@echo off
REM Executa o Alfred a partir do codigo-fonte (desenvolvimento)
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
  py -3.12 -m venv .venv || exit /b 1
  .venv\Scripts\python -m pip install -r requirements-dev.txt || exit /b 1
)
set PYTHONPATH=%~dp0src
start "" .venv\Scripts\pythonw.exe -m alfred %*
