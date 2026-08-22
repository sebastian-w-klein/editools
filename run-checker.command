#!/bin/bash
# macOS: double-click this file to open the Index Checker.
cd "$(dirname "$0")" || exit 1
if [ ! -d .venv ]; then
    echo "Setting up for the first time. This takes a minute…"
    python3 -m venv .venv && .venv/bin/pip install --quiet --upgrade pip && .venv/bin/pip install --quiet -e .
fi
exec .venv/bin/indexcheck ui
