#!/usr/bin/env python3
"""Merge MobilityData SA feed URLs into transit_feeds.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.ingest.mobility_catalog import lookup_gtfs_rt_alerts_url, refresh_sa_index
from pulsegrid.metros import list_metros

FEEDS_PATH = ROOT / "datasets" / "reference" / "transit_feeds.yaml"

_REJECT_URL_SUBSTRINGS = (
    "data.texas.gov/download",
    "passio3.com/uga/passiotransit",
)


def _mobility_url_ok(url: str) -> bool:
    low = url.lower()
    return not any(bad in low for bad in _REJECT_URL_SUBSTRINGS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync GTFS-RT URLs from MobilityData catalog")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh MobilityData SA filename index from GitHub",
    )
    parser.add_argument(
        "--fill-empty-urls",
        action="store_true",
        help="Update existing gtfs_rt metros that have no gtfs_rt_url",
    )
    args = parser.parse_args()

    if args.force:
        refresh_sa_index(force=True)

    doc = yaml.safe_load(FEEDS_PATH.read_text(encoding="utf-8")) or {}
    metros = doc.setdefault("metros", {})
    added = 0
    updated = 0

    for metro in list_metros():
        if metro.transit_adapter in ("cta", "mbta", "transit_json"):
            continue
        existing = metros.get(metro.slug)
        if existing:
            adapter = str(existing.get("adapter", "")).strip()
            url = str(existing.get("gtfs_rt_url", "")).strip()
            if adapter not in ("gtfs_rt", "", "none") and not args.fill_empty_urls:
                continue
            if url and not args.fill_empty_urls:
                continue
        url = lookup_gtfs_rt_alerts_url(metro)
        if not url or not _mobility_url_ok(url):
            continue
        entry = {"adapter": "gtfs_rt", "gtfs_rt_url": url}
        if metro.slug not in metros:
            added += 1
            print(f"  + {metro.slug}: {url[:80]}…")
        else:
            updated += 1
            print(f"  ~ {metro.slug}: {url[:80]}…")
        metros[metro.slug] = {**metros.get(metro.slug, {}), **entry}

    FEEDS_PATH.write_text(
        yaml.safe_dump(doc, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    print(f"Wrote transit_feeds.yaml (+{added} new, ~{updated} updated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
