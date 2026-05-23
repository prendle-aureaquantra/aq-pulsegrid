"""Historical replay — filter bronze snapshots by date and re-run transforms."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pulsegrid.config as cfg
from pulsegrid.config import BRONZE, DATA_ROOT, ensure_dirs, get_city, load_dotenv
from pulsegrid.jobs.gold_chicago import run_gold
from pulsegrid.jobs.ml_chicago import run_ml
from pulsegrid.jobs.silver_chicago import run_silver

SOURCES = ("noaa", "cta", "airport", "fred", "google_trends", "events", "osm")


def _file_matches_date(path: Path, date_str: str) -> bool:
    if date_str in path.name:
        return True
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    fetched = str(doc.get("fetched_at", ""))
    return fetched.startswith(date_str)


def _collect_replay_files(city: str, date_str: str) -> dict[str, list[Path]]:
    selected: dict[str, list[Path]] = {}
    for source in SOURCES:
        base = BRONZE / city / source
        if not base.is_dir():
            continue
        matches = [
            p for p in sorted(base.glob("*.json")) if _file_matches_date(p, date_str)
        ]
        if matches:
            selected[source] = matches
    return selected


def run_replay(city_slug: str, date_str: str, *, dry_run: bool = False) -> None:
    get_city(city_slug)
    selected = _collect_replay_files(city_slug, date_str)
    if not selected:
        raise FileNotFoundError(
            f"No bronze files for {city_slug} matching date {date_str!r}. "
            f"Run ingest first or use YYYY-MM-DD from fetched_at."
        )
    print(
        f"Replay {city_slug} @ {date_str}: {sum(len(v) for v in selected.values())} bronze files"
    )
    for source, paths in selected.items():
        for p in paths:
            print(f"  {source:14} -> {p.name}")

    if dry_run:
        return

    original_bronze = cfg.BRONZE
    with tempfile.TemporaryDirectory(prefix="pulsegrid-replay-", dir=DATA_ROOT) as tmp:
        replay_root = Path(tmp) / city_slug
        for source, paths in selected.items():
            dest = replay_root / source
            dest.mkdir(parents=True, exist_ok=True)
            for p in paths:
                shutil.copy2(p, dest / p.name)
        cfg.BRONZE = replay_root.parent
        try:
            print("Silver replay...")
            for name, path in run_silver(city_slug).items():
                print(f"  silver.{name} -> {path}")
            print("Gold replay...")
            for name, path in run_gold(city_slug).items():
                print(f"  gold.{name} -> {path}")
            print("ML replay...")
            for name, path in run_ml(city_slug).items():
                print(f"  ml.{name} -> {path}")
        finally:
            cfg.BRONZE = original_bronze


def main() -> int:
    load_dotenv()
    ensure_dirs()
    parser = argparse.ArgumentParser(
        description="Replay historical city bronze through Spark/ML pipeline"
    )
    parser.add_argument("--city", default="chicago")
    parser.add_argument(
        "--date", required=True, help="YYYY-MM-DD (matches filename or fetched_at)"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("ERROR: --date must be YYYY-MM-DD", file=sys.stderr)
        return 1
    try:
        run_replay(args.city, args.date, dry_run=args.dry_run)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
