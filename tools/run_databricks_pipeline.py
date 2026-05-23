"""Run Chicago pipeline on Databricks via SQL warehouse (SQL steps) or local fallback."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _has_databricks() -> bool:
    return bool(os.getenv("DATABRICKS_HOST") and os.getenv("DATABRICKS_TOKEN"))


def run_local(city: str, *, with_visuals: bool) -> int:
    cmd = [sys.executable, str(ROOT / "generate_city.py"), "--city", city]
    if with_visuals:
        cmd.extend(["--pbip-only", "--with-visuals"])
    else:
        cmd.append("--pbip-only")
    # Full pipeline
    full = [sys.executable, str(ROOT / "generate_city.py"), "--city", city]
    if with_visuals:
        # run steps then pbip with visuals
        for flag in ("--ingest-only", "--transform-only", "--ml-only"):
            r = subprocess.run([sys.executable, str(ROOT / "generate_city.py"), "--city", city, flag], cwd=ROOT)
            if r.returncode:
                return r.returncode
        r = subprocess.run(cmd, cwd=ROOT)
        return r.returncode
    r = subprocess.run(full, cwd=ROOT)
    return r.returncode


def run_databricks_notebook(city: str) -> int:
    """Submit repo notebook if databricks CLI is configured."""
    cli = "databricks"
    profile = os.getenv("DATABRICKS_CONFIG_PROFILE", "aureaquantra")
    nb = ROOT / "databricks" / "chicago_daily.py"
    if not nb.is_file():
        print(f"Notebook not found: {nb}", file=sys.stderr)
        return 1
    cmd = [
        cli,
        "workspace",
        "import",
        str(nb),
        f"/Users/pulsegrid/chicago_daily",
        "--language",
        "PYTHON",
        "--format",
        "SOURCE",
        "--overwrite",
        "--profile",
        profile,
    ]
    print("Import notebook:", " ".join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode:
        return r.returncode
    print(
        "Schedule in Databricks UI: Jobs → chicago_daily → daily trigger.\n"
        "Or use Databricks Asset Bundles (see databricks/README.md)."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PulseGrid on Databricks or locally")
    parser.add_argument("--city", default="chicago")
    parser.add_argument("--with-visuals", action="store_true")
    parser.add_argument("--local-only", action="store_true")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        for p in (ROOT.parent / ".env", ROOT / ".env"):
            if p.is_file():
                load_dotenv(p)
                break
    except ImportError:
        pass

    if args.local_only or not _has_databricks():
        if not _has_databricks():
            print("DATABRICKS_* not set — running local pipeline.")
        return run_local(args.city, with_visuals=args.with_visuals)
    return run_databricks_notebook(args.city)


if __name__ == "__main__":
    raise SystemExit(main())
