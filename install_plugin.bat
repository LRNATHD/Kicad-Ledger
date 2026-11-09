@echo off
setlocal

REM KiCad Action Plugin Installer
set "KICAD_PYTHON=C:\Program Files\KiCad\10.0\bin\python.exe"

if exist "%KICAD_PYTHON%" (
    "%KICAD_PYTHON%" "%~dp0install_kicad_plugin.py"
) else (
    python "%~dp0install_kicad_plugin.py"
)

pause
endlocal
