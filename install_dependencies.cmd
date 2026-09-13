@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0ensure_python.ps1" --install
pause
