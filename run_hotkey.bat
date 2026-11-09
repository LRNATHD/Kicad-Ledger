@echo off
setlocal

REM KiCad-StockCheck Background Hotkey Daemon
set "KICAD_PYTHON=C:\Program Files\KiCad\10.0\bin\python.exe"

if exist "%KICAD_PYTHON%" (
    "%KICAD_PYTHON%" "%~dp0run_hotkey_daemon.py" %*
) else (
    python "%~dp0run_hotkey_daemon.py" %*
)

endlocal
