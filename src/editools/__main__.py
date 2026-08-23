"""So that ``python -m editools`` works wherever the command is not on PATH."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
