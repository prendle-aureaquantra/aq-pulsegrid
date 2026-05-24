#!/usr/bin/env python3
"""Print per-metro enablement for NWS, GTFS-RT, OpenSky, and civic 311."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.ingest.feed_framework import CORE_FEED_IDS, coverage_report
from pulsegrid.metros import list_metros


def main() -> int:
    rows = coverage_report(list_metros())
    if not rows:
        print("No metros in registry.")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
