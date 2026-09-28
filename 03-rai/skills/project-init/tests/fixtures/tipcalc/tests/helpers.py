"""Run tipcalc's entrypoint in a subprocess.

A real project spawns the installed `tipcalc` console script. This fixture runs the same
`main()` from src/ with the current interpreter, so the suite needs no install.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
ENTRY = "import sys; from tipcalc import main; sys.argv[0] = 'tipcalc'; main()"


def tipcalc(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full = {k: v for k, v in os.environ.items() if k != "TIPCALC_DEFAULT_PERCENT"}
    full["PYTHONPATH"] = str(SRC)
    full.update(env or {})
    return subprocess.run(
        [sys.executable, "-c", ENTRY, *args],
        capture_output=True,
        text=True,
        check=False,
        env=full,
    )
