#!/usr/bin/env python3
"""Phase 2 deploy orchestrator: Databricks, Fabric embed, Lightsail."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


def _run(cmd: list[str], *, cwd: Path | None = None) -> int:
    print("\n>>>", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(cwd or ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-databricks", action="store_true")
    ap.add_argument("--skip-fabric", action="store_true")
    ap.add_argument("--skip-lightsail", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    rc = 0

    if not args.skip_databricks:
        cmd = [sys.executable, str(ROOT / "tools" / "deploy_databricks_job.py")]
        if args.dry_run:
            cmd.append("--validate-only")
        rc = _run(cmd) or rc

    if not args.skip_fabric:
        cmd = [sys.executable, str(ROOT / "tools" / "publish_pulsegrid_fabric.py")]
        if args.dry_run:
            cmd.append("--dry-run")
        rc = _run(cmd) or rc

    if not args.skip_lightsail:
        cmd = [
            sys.executable,
            str(REPO_ROOT / "deploy_pulsegrid.py"),
            "--from-dotenv",
        ]
        if args.dry_run:
            cmd.append("--dry-run")
        rc = _run(cmd, cwd=REPO_ROOT) or rc

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
