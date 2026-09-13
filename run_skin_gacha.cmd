@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
cd /d "%~dp0"
set "PYTHONPATH="
set "PYTHONHOME="
set "TCL_LIBRARY="
set "TK_LIBRARY="
rem Optional existing Codex development environment (not shipped in the archive).
set "GACHA_DEV=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python"
if exist ".runtime\customtkinter\__init__.py" if exist "%GACHA_DEV%\python.exe" (
  set "PYTHONPATH=%~dp0.runtime"
  set "TCL_LIBRARY=%GACHA_DEV%\tcl\tcl8.6"
  set "TK_LIBRARY=%GACHA_DEV%\tcl\tk8.6"
  "%GACHA_DEV%\python.exe" "%~dp0main.py"
  if errorlevel 1 pause
  exit /b
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0ensure_python.ps1" --run
if errorlevel 1 pause
