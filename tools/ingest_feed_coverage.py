#!/usr/bin/env python3
"""Print per-metro enablement for NWS, GTFS-RT, OpenSky, and civic 311."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.ingest.feed_framework import CORE_FEED_IDS, coverage_report
from pulsegrid.metros import list_metros


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest feed coverage report")
    parser.add_argument(
        "--check-min",
        action="store_true",
        help="Exit 1 if any feed count is below --min-* thresholds",
    )
    parser.add_argument("--min-transit", type=int, default=20)
    parser.add_argument("--min-nws", type=int, default=12)
    parser.add_argument("--min-civic311", type=int, default=10)
    args = parser.parse_args()

    rows = coverage_report(list_metros())
    if not rows:
        print("No metros in registry.", file=sys.stderr)
        return 1
    fields = ["metro", "country", *CORE_FEED_IDS]
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    enabled = {fid: sum(1 for r in rows if r.get(fid) == "yes") for fid in CORE_FEED_IDS}
    print("\n# enabled counts", file=sys.stderr)
    for fid, count in enabled.items():
        print(f"  {fid}: {count}/{len(rows)}", file=sys.stderr)
    if args.check_min:
        floors = {
            "gtfs_rt": args.min_transit,
            "nws_weather": args.min_nws,
            "civic311": args.min_civic311,
        }
        for fid, floor in floors.items():
            if enabled.get(fid, 0) < floor:
                print(
                    f"FAIL: {fid} enabled {enabled.get(fid, 0)} < min {floor}",
                    file=sys.stderr,
                )
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
