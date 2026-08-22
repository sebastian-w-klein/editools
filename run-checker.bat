@echo off
REM Windows: double-click this file to open the Hyphenation Checker.
cd /d "%~dp0"
if not exist .venv (
    echo Setting up for the first time. This takes a minute...
    python -m venv .venv
    .venv\Scripts\pip install --quiet --upgrade pip
    .venv\Scripts\pip install --quiet -e .
)
.venv\Scripts\hyphencheck ui
pause
