@echo off
rem Meowcana: Swap. Chain. Pounce.  Double-click to play on this PC (window, mouse, sound).
setlocal
cd /d "%~dp0.."
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
%PY% -c "import pygame, PIL" >nul 2>&1 || (
  echo Installing pygame-ce and Pillow, one moment...
  %PY% -m pip install --quiet pygame-ce pillow || (echo Could not install the game's Python packages. & pause & exit /b 1)
)
where pythonw >nul 2>&1 && (
  start "" pythonw pc\play.py %*
  exit /b 0
)
%PY% pc\play.py %*
if errorlevel 1 pause
