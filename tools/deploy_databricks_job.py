"""Deploy scheduled Databricks job via Asset Bundles."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in (ROOT.parent / ".env", ROOT / ".env"):
        if p.is_file():
            load_dotenv(p)
            break


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy aq-pulsegrid Databricks bundle")
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run databricks bundle validate without deploy",
    )
    parser.add_argument(
        "--repo-path",
        default=os.getenv("DATABRICKS_REPO_PATH", "/Repos/pulsegrid/aq-pulsegrid"),
        help="Workspace Repos mount path",
    )
    args = parser.parse_args()
    _load_env()

    host = os.getenv("DATABRICKS_HOST", "").strip()
    token = os.getenv("DATABRICKS_TOKEN", "").strip()
    if not host or not token:
        print(
            "Set DATABRICKS_HOST and DATABRICKS_TOKEN in .env, then retry.",
            file=sys.stderr,
        )
        return 1

    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "DEFAULT")
    env = os.environ.copy()
    env.setdefault("DATABRICKS_HOST", host)
    env.setdefault("DATABRICKS_TOKEN", token)

    bundle_vars = [
        f"--var=databricks_host={host}",
        f"--var=repo_path={args.repo_path}",
    ]
    cmd = ["databricks", "bundle", "validate", *bundle_vars, "--profile", profile]
    if not args.validate_only:
        cmd = ["databricks", "bundle", "deploy", *bundle_vars, "--profile", profile]

    print("Running:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT, env=env)
    if r.returncode == 0 and not args.validate_only:
        print(
            "\nJob deployed. Open Databricks → Workflows → aq-pulsegrid-chicago-daily.\n"
            "Ensure Repos path matches --repo-path before first run."
        )
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
