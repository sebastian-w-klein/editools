"""Allow `python -m indexcheck`.

The launchers call the package this way rather than the installed console
script, because a console script bakes in the path of the environment that
built it and the launchers deliberately keep that environment somewhere else.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
