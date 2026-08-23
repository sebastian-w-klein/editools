#!/bin/bash
# macOS: double-click this file to open the Editorial Tools.
#
# One icon opens both checkers. Which one you want is a click on the page
# that appears — there is nothing else to start.

# The Python environment goes in your home folder, never beside this file, so
# that the tools still work when they are kept on a shared network volume.
SOURCE="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="$HOME/Library/Application Support/EditorialTools"
VENV="$HOME_DIR/venv"
PY="$VENV/bin/python"
STAMP="$HOME_DIR/installed-from.txt"

fail() {
    echo
    echo "$1"
    echo
    read -r -p "Press Return to close this window."
    exit 1
}

if [ ! -x "$PY" ]; then
    echo "Setting up for the first time. This takes a minute…"
    mkdir -p "$HOME_DIR"
    python3 -m venv "$VENV" 2>/dev/null
    [ -x "$PY" ] || fail "Could not find Python.

Install Python 3.9 or newer from https://www.python.org/downloads/
then close this window and double-click this file again."
    "$PY" -m pip install --quiet --upgrade pip
fi

# Point the environment at this folder, and again if the folder ever moves.
if [ "$(cat "$STAMP" 2>/dev/null)" != "$SOURCE" ]; then
    echo "Getting the tools ready…"
    "$PY" -m pip install --quiet -e "$SOURCE" \
        || fail "Could not get the tools ready.

Try copying this whole folder to your Desktop and running it there."
    printf '%s' "$SOURCE" > "$STAMP"
fi

# Install a new version if there is one. Checked once a day at most, silent
# when there is nothing to do, and never a reason not to start.
"$PY" -m editools update --auto 2>/dev/null

exec "$PY" -m editools ui
