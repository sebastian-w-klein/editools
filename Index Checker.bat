@echo off
setlocal EnableDelayedExpansion
title Index Checker

REM Windows: double-click this file to open the Index Checker.

REM The Python environment goes on the local disk, never beside this file.
REM Editorial folders usually live on a network drive, and a virtual
REM environment cannot be created on one: Windows resolves the mapped letter
REM to its UNC form (I:\... becomes \\SERVER\share\...) and the environment
REM records a path it cannot use afterwards.
set "SOURCE=%~dp0"
set "HOME_DIR=%LOCALAPPDATA%\EditorialTools"
set "VENV=%HOME_DIR%\venv"
set "PY=%VENV%\Scripts\python.exe"
set "STAMP=%HOME_DIR%\installed-from.txt"

if not exist "%PY%" (
    echo Setting up for the first time. This takes a minute...
    if not exist "%HOME_DIR%" mkdir "%HOME_DIR%"
    py -3 -m venv "%VENV%" 2>nul
    if not exist "%PY%" python -m venv "%VENV%" 2>nul
    if not exist "%PY%" goto :nopython
    "%PY%" -m pip install --quiet --upgrade pip
)

REM Point the environment at this folder, and again if the folder ever moves.
set "SAVED="
if exist "%STAMP%" set /p SAVED=<"%STAMP%"
if not "!SAVED!"=="!SOURCE!" (
    echo Getting the tools ready...
    "%PY%" -m pip install --quiet -e "%SOURCE%."
    if errorlevel 1 goto :noinstall
    > "%STAMP%" echo !SOURCE!
)

REM Install a new version if there is one. Checked once a day at most, silent
REM when there is nothing to do, and never a reason not to start.
"%PY%" -m editools update --auto 2>nul

"%PY%" -m editools index ui
pause
exit /b 0

:nopython
echo.
echo Could not find Python.
echo.
echo Install Python 3.9 or newer from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" at the bottom of the installer,
echo then close this window and double-click this file again.
echo.
pause
exit /b 1

:noinstall
echo.
echo Could not get the tools ready.
echo.
echo Try copying this whole folder to your Desktop and running it there.
echo.
pause
exit /b 1
