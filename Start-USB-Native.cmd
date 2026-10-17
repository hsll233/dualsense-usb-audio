@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
if exist "DualSense-USB-Audio.exe" (
  "DualSense-USB-Audio.exe" %*
) else if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" usb-system-audio.py %*
) else (
  python usb-system-audio.py %*
)
if errorlevel 1 pause
