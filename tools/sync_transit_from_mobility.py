#!/usr/bin/env python3
"""Merge MobilityData SA feed URLs into transit_feeds.yaml (manual review recommended)."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.ingest.mobility_catalog import lookup_gtfs_rt_alerts_url, refresh_sa_index
from pulsegrid.metros import list_metros

FEEDS_PATH = ROOT / "datasets" / "reference" / "transit_feeds.yaml"


def main() -> int:
    if "--force" in sys.argv:
        refresh_sa_index(force=True)
    doc = yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8")) or {}
    metros = doc.setdefault("metros", {})
    added = 0
    for metro in list_metros():
        if metro.slug in metros:
            continue
        if metro.transit_adapter in ("cta", "mbta", "transit_json"):
            continue
        url = lookup_gtfs_rt_alerts_url(metro)
        if url:
            metros[metro.slug] = {"adapter": "gtfs_rt", "gtfs_rt_url": url}
            added += 1
            print(f"  + {metro.slug}: {url[:80]}…")
    FEEDS_PATH.write_text(
        yaml.safe_dump(doc, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"Wrote {added} new entries to {FEEDS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
