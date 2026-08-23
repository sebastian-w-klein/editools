#!/bin/bash
# macOS: double-click this file to update the Hyphenation Checker.
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/hyphencheck ]; then
    echo "The checker does not look installed yet. Follow Step 3 in the README first."
    read -r -p "Press Return to close."
    exit 1
fi
.venv/bin/hyphencheck update
echo
read -r -p "Press Return to close."
