@echo off
REM Atalho para o build local (veja build_windows.ps1 e docs\BUILD.md)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1" %*
exit /b %ERRORLEVEL%
