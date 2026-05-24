"""Smoke tests for tools/run_scheduled_pipeline.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_scheduled_pipeline.py"


def test_scheduled_pipeline_help() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "ingest" in r.stdout


def test_scheduled_pipeline_unknown_step() -> None:
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--step", "train", "--city", "chicago"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
