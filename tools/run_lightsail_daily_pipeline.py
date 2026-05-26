#!/usr/bin/env python3
"""Lightsail daily job: tier-full extended ingest, then refresh all metros for platform export."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "tools" / "run_scheduled_pipeline.py"


def _call(argv: list[str]) -> int:
    cmd = [sys.executable, str(RUN), *argv]
    print("Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    code = _call(
        [
            "--extended-ingest",
            "--ingest-delay",
            "1.5",
            "--tier",
            "full",
        ]
    )
    if code != 0:
        return code
    # Refresh weather-only metros (platform CSV union needs all tiers).
    return _call(
        [
            "--step",
            "ingest,transform,ml,export",
            "--tier",
            "weather_only",
            "--ingest-delay",
            "0.35",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
