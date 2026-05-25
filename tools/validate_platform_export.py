#!/usr/bin/env python3
"""Fail deploy/publish if platform CSV export is below expected metro coverage."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def pulsegrid_root() -> Path:
    return Path(__file__).resolve().parent.parent


def count_csv_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def validate_platform_data(
    data_dir: Path,
    *,
    min_metros: int = 70,
    min_snapshots: int = 70,
) -> list[str]:
    errors: list[str] = []
    dim = data_dir / "DimMetro.csv"
    snap = data_dir / "CityPulseSnapshot.csv"
    if not dim.is_file():
        errors.append(f"Missing {dim}")
        return errors
    metro_rows = count_csv_rows(dim)
    snap_rows = count_csv_rows(snap) if snap.is_file() else 0
    if metro_rows < min_metros:
        errors.append(
            f"DimMetro.csv has {metro_rows} rows (need >= {min_metros}). "
            "Run: python generate_city.py --all-metros --platform-csv-only"
        )
    if snap_rows < min_snapshots:
        errors.append(
            f"CityPulseSnapshot.csv has {snap_rows} rows (need >= {min_snapshots}). "
            "Re-run platform export after transform+ML."
        )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=pulsegrid_root() / "generated_reports/platform/data")
    ap.add_argument("--min-metros", type=int, default=70)
    ap.add_argument("--min-snapshots", type=int, default=70)
    args = ap.parse_args()
    errs = validate_platform_data(
        args.data_dir,
        min_metros=args.min_metros,
        min_snapshots=args.min_snapshots,
    )
    if errs:
        for e in errs:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(
        f"OK: platform export ({args.data_dir}) "
        f"metros={count_csv_rows(args.data_dir / 'DimMetro.csv')} "
        f"snapshots={count_csv_rows(args.data_dir / 'CityPulseSnapshot.csv')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
