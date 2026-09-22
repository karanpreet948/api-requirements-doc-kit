"""Allows the package to be run as ``python -m apidoc ...``."""

import sys

from apidoc.cli import main

if __name__ == "__main__":
    sys.exit(main())
