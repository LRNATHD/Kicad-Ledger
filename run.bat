@echo off
setlocal

REM KiCad-StockCheck Launcher
set "KICAD_PYTHON=C:\Program Files\KiCad\10.0\bin\python.exe"

if exist "%KICAD_PYTHON%" (
    "%KICAD_PYTHON%" "%~dp0run_gui.py" %*
) else (
    python "%~dp0run_gui.py" %*
)

endlocal
