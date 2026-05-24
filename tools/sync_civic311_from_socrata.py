#!/usr/bin/env python3
"""Discover and merge Socrata 311 endpoints into civic311.yaml."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.ingest.socrata_311_discovery import (
    CURATED_311,
    discover_311_config,
)
from pulsegrid.metro_feeds import civic311_config
from pulsegrid.metros import list_metros

CIVIC_PATH = ROOT / "datasets" / "reference" / "civic311.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Socrata 311 URLs into civic311.yaml")
    parser.add_argument(
        "--country",
        default="US",
        help="Only metros with this country code (default US)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing metro entries when discovery finds a valid URL",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print discoveries without writing YAML",
    )
    args = parser.parse_args()

    doc = yaml.safe_load(CIVIC_PATH.read_text(encoding="utf-8")) or {}
    metros = doc.setdefault("metros", {})
    added = 0
    updated = 0
    skipped = 0

    for slug, cfg in CURATED_311.items():
        if slug in metros and not args.overwrite:
            continue
        existed = slug in metros
        if not args.dry_run:
            metros[slug] = dict(cfg)
        print(
            f"  curated {slug}: {cfg.get('adapter', 'socrata')} "
            f"{str(cfg.get('url', ''))[:70]}"
        )
        if existed:
            updated += 1
        else:
            added += 1

    for metro in list_metros():
        if metro.country.upper() != args.country.upper():
            continue
        if metro.slug in metros and not args.overwrite:
            skipped += 1
            continue
        if metro.slug in metros and civic311_config(metro.slug) and not args.overwrite:
            skipped += 1
            continue
        print(f"  Discovering 311 for {metro.slug}…")
        cfg = discover_311_config(metro)
        if not cfg:
            print("    — no Socrata 311 found")
            continue
        cfg.pop("_discovery_score", None)
        if metro.slug in metros:
            updated += 1
            action = "update"
        else:
            added += 1
            action = "add"
        print(f"    + {action}: {cfg['url'][:90]}")
        if not args.dry_run:
            metros[metro.slug] = cfg

    if not args.dry_run:
        CIVIC_PATH.write_text(
            yaml.safe_dump(doc, sort_keys=False, default_flow_style=False),
            encoding="utf-8",
        )
    print(f"Done: added={added} updated={updated} skipped={skipped} -> {CIVIC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
