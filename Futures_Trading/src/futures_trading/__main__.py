"""Allow ``python -m futures_trading ...`` (same CLI as the ``futures-trading`` console script)."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
