"""PyCharm-friendly launcher for the local trading dashboard.

Right-click this file in PyCharm and choose Run. It starts the Python HTTP
server and opens the dashboard in Edge or your default browser.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
DB_PATH = PROJECT_ROOT / "data" / "market_data.sqlite"
HOST = "127.0.0.1"
PREFERRED_PORT = 8770

os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(SRC_DIR))

from futures_trading.web import run_dashboard  # noqa: E402


def find_free_port(host: str, preferred_port: int, attempts: int = 20) -> int:
    for port in range(preferred_port, preferred_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(
        f"No free dashboard port found from {preferred_port} to {preferred_port + attempts - 1}"
    )


if __name__ == "__main__":
    port = find_free_port(HOST, PREFERRED_PORT)
    run_dashboard(
        host=HOST,
        port=port,
        db_path=DB_PATH,
        open_browser=True,
    )
