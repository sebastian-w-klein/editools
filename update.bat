@echo off
REM Windows: double-click this file to update the Hyphenation Checker.
cd /d "%~dp0"
if not exist .venv\Scripts\hyphencheck.exe (
    echo The checker does not look installed yet. Follow Step 3 in the README first.
    pause
    exit /b 1
)
.venv\Scripts\hyphencheck update
echo.
pause
