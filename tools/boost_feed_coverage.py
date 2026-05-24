#!/usr/bin/env python3
"""Boost transit (MobilityData) and civic 311 (Socrata) feed coverage programmatically."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.ingest.feed_framework import CORE_FEED_IDS, coverage_report
from pulsegrid.metros import list_metros


def _counts() -> dict[str, int]:
    rows = coverage_report(list_metros())
    return {fid: sum(1 for r in rows if r.get(fid) == "yes") for fid in CORE_FEED_IDS}


def main() -> int:
    parser = argparse.ArgumentParser(description="Boost ingest feed coverage")
    parser.add_argument(
        "--skip-transit",
        action="store_true",
        help="Skip MobilityData GTFS-RT sync",
    )
    parser.add_argument(
        "--skip-311",
        action="store_true",
        help="Skip Socrata 311 discovery",
    )
    parser.add_argument(
        "--force-mobility",
        action="store_true",
        help="Pass --force to mobility index refresh",
    )
    parser.add_argument(
        "--fill-empty-transit-urls",
        action="store_true",
        help="Update gtfs_rt entries missing URLs in transit_feeds.yaml",
    )
    parser.add_argument(
        "--overwrite-311",
        action="store_true",
        help="Replace existing civic311.yaml entries when rediscovered",
    )
    args = parser.parse_args()

    before = _counts()
    print("Coverage before:", before)

    py = sys.executable
    if not args.skip_transit:
        cmd = [py, str(ROOT / "tools" / "sync_transit_from_mobility.py")]
        if args.force_mobility:
            cmd.append("--force")
        if args.fill_empty_transit_urls:
            cmd.append("--fill-empty-urls")
        print("\n== MobilityData transit sync ==")
        subprocess.check_call(cmd, cwd=str(ROOT))

    if not args.skip_311:
        cmd = [py, str(ROOT / "tools" / "sync_civic311_from_socrata.py")]
        if args.overwrite_311:
            cmd.append("--overwrite")
        print("\n== Socrata 311 discovery ==")
        subprocess.check_call(cmd, cwd=str(ROOT))

    after = _counts()
    print("\nCoverage after:", after)
    for fid in CORE_FEED_IDS:
        delta = after.get(fid, 0) - before.get(fid, 0)
        if delta:
            print(f"  {fid}: +{delta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
