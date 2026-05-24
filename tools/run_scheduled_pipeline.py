"""Run the daily PulseGrid pipeline locally (cron / Task Scheduler / systemd).

Mirrors the Databricks job ``pulsegrid_daily_global``:
ingest → transform → ml → platform export.

Examples::

    python tools/run_scheduled_pipeline.py
    python tools/run_scheduled_pipeline.py --step ml --tier full
    python tools/run_scheduled_pipeline.py --step transform,ml --city chicago
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = ("ingest", "transform", "ml", "export")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in (ROOT.parent / ".env", ROOT / ".env"):
        if p.is_file():
            load_dotenv(p)
            break


def _base_cmd(
    *,
    all_metros: bool,
    city: str | None,
    metros: str | None,
    tier: str,
) -> list[str]:
    cmd = [sys.executable, str(ROOT / "generate_city.py")]
    if all_metros:
        cmd.extend(["--all-metros", "--tier", tier])
    elif metros:
        cmd.extend(["--metros", metros])
    else:
        cmd.extend(["--city", city or "chicago"])
    return cmd


def _run_step(
    step: str,
    base: list[str],
    *,
    extended_ingest: bool,
    ingest_delay: float,
    with_visuals: bool,
) -> int:
    flag_map = {
        "ingest": "--ingest-only",
        "transform": "--transform-only",
        "ml": "--ml-only",
        "export": "--platform-only",
    }
    cmd = base + [flag_map[step]]
    if step == "ingest" and extended_ingest:
        cmd.append("--extended-ingest")
    if step == "ingest" and ingest_delay > 0:
        cmd.extend(["--ingest-delay", str(ingest_delay)])
    if step == "export" and with_visuals:
        cmd.append("--with-visuals")
    print("Running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run scheduled PulseGrid pipeline steps (local/cron)"
    )
    parser.add_argument(
        "--step",
        default="all",
        help="Step(s): ingest, transform, ml, export, or all (comma-separated)",
    )
    parser.add_argument("--tier", default="full", help="Metro tier when --all-metros")
    parser.add_argument("--city", default=None, help="Single metro slug")
    parser.add_argument("--metros", default=None, help="Comma-separated metro slugs")
    parser.add_argument(
        "--all-metros",
        action="store_true",
        help="All metros in tier (default when no --city/--metros)",
    )
    parser.add_argument(
        "--extended-ingest",
        action="store_true",
        help="Pass --extended-ingest to ingest step",
    )
    parser.add_argument(
        "--ingest-delay",
        type=float,
        default=float(os.getenv("PULSEGRID_INGEST_DELAY", "0")),
        help="Seconds between metro ingests",
    )
    parser.add_argument(
        "--with-visuals",
        action="store_true",
        help="Include programmatic visuals on platform export (slower)",
    )
    args = parser.parse_args()
    _load_env()

    all_metros = args.all_metros or (not args.city and not args.metros)
    raw = args.step.strip().lower()
    if raw == "all":
        steps = list(STEPS)
    else:
        steps = [s.strip() for s in raw.split(",") if s.strip()]
        bad = [s for s in steps if s not in STEPS]
        if bad:
            print(f"Unknown step(s): {bad}. Use: {', '.join(STEPS)}", file=sys.stderr)
            return 2

    base = _base_cmd(
        all_metros=all_metros,
        city=args.city,
        metros=args.metros,
        tier=args.tier,
    )

    failed_steps: list[str] = []
    for step in steps:
        code = _run_step(
            step,
            base,
            extended_ingest=args.extended_ingest,
            ingest_delay=args.ingest_delay,
            with_visuals=args.with_visuals,
        )
        if code != 0:
            failed_steps.append(step)
            print(f"WARN: step '{step}' exited {code}", file=sys.stderr)

    try:
        from pulsegrid.pipeline_status import write_pipeline_status

        scope = "all-metros" if all_metros else (args.metros or args.city or "chicago")
        write_pipeline_status(
            job="scheduled-pipeline",
            metros_ok=len(steps) - len(failed_steps),
            metros_failed=len(failed_steps),
            detail=f"steps={','.join(steps)} tier={args.tier} scope={scope}",
            extra={"failed_steps": failed_steps},
        )
    except Exception as exc:
        print(f"WARN: could not write pipeline status: {exc}", file=sys.stderr)

    return 1 if failed_steps else 0


if __name__ == "__main__":
    raise SystemExit(main())
