#!/usr/bin/env python3
"""
AQ PulseGrid city pipeline entrypoint.

Examples:
  python generate_city.py --city chicago --ingest-only
  python generate_city.py --city chicago --extended-ingest
  python generate_city.py --city chicago --stream
  python generate_city.py --city chicago --with-visuals
"""

from __future__ import annotations

import argparse
import sys

from pulsegrid.config import ensure_dirs, get_city, load_dotenv
from pulsegrid.ingest.airport import ingest_airport
from pulsegrid.ingest.cta import ingest_cta
from pulsegrid.ingest.events import ingest_events
from pulsegrid.geo.osm_enrich import ingest_osm_pois
from pulsegrid.ingest.fred import ingest_fred
from pulsegrid.ingest.google_trends import ingest_google_trends
from pulsegrid.ingest.noaa import ingest_noaa
from pulsegrid.jobs.gold_chicago import run_gold
from pulsegrid.jobs.ml_chicago import run_ml as run_ml_job
from pulsegrid.jobs.silver_chicago import run_silver
from pulsegrid.jobs.streaming_microbatch import run_microbatch
from pulsegrid.jobs.streaming_spark import run_structured_stream
from pbip_generator.generate import generate_pbip


def run_ingest(city_slug: str, *, extended: bool = False) -> None:
    city = get_city(city_slug)
    print(f"Ingesting public feeds for {city.name}...")
    for label, paths in (
        ("NOAA", ingest_noaa(city)),
        ("CTA", ingest_cta(city)),
    ):
        for p in paths:
            print(f"  {label:5} -> {p}")

    if not extended:
        return

    print("Extended ingest (airport, trends, FRED, events, OSM)...")
    for p in ingest_airport(city):
        print(f"  AIRP  -> {p}")
    try:
        for p in ingest_events(city):
            print(f"  EVENT -> {p}")
    except Exception as exc:
        print(f"  EVENT -> skip ({exc})")
    try:
        for p in ingest_osm_pois(city):
            print(f"  OSM   -> {p}")
    except Exception as exc:
        print(f"  OSM   -> skip ({exc})")
    try:
        for p in ingest_google_trends(city):
            print(f"  TREND -> {p}")
    except RuntimeError as exc:
        print(f"  TREND -> skip ({exc})")
    try:
        for p in ingest_fred(city):
            print(f"  FRED  -> {p}")
    except RuntimeError as exc:
        print(f"  FRED  -> skip ({exc})")


def run_transform(city_slug: str) -> None:
    print(f"Silver transforms for {city_slug}...")
    silver = run_silver(city_slug)
    for name, path in silver.items():
        print(f"  silver.{name} -> {path}")
    print(f"Gold KPIs for {city_slug}...")
    gold = run_gold(city_slug)
    for name, path in gold.items():
        print(f"  gold.{name} -> {path}")


def run_ml(city_slug: str) -> None:
    print(f"ML scoring + anomalies for {city_slug}...")
    outputs = run_ml_job(city_slug)
    for name, path in outputs.items():
        print(f"  ml.{name} -> {path}")


def run_full(
    city_slug: str, *, with_visuals: bool = False, extended: bool = False
) -> None:
    run_ingest(city_slug, extended=extended)
    run_transform(city_slug)
    run_ml(city_slug)
    print("\nPBIP generation")
    pbip = generate_pbip(city_slug, include_visuals=with_visuals)
    mode = "with visuals" if with_visuals else "blank pages"
    print(f"  PBIP ({mode}) -> {pbip}")


def main() -> int:
    load_dotenv()
    ensure_dirs()
    parser = argparse.ArgumentParser(description="AQ PulseGrid city pipeline")
    parser.add_argument(
        "--city", default="chicago", help="City slug (default: chicago)"
    )
    parser.add_argument("--ingest-only", action="store_true", help="Bronze ingest only")
    parser.add_argument(
        "--extended-ingest",
        action="store_true",
        help="Also ingest airport METAR, Google Trends, FRED (needs keys/deps)",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Micro-batch poll NOAA+CTA into bronze ingest_events Delta log",
    )
    parser.add_argument(
        "--stream-spark",
        action="store_true",
        help="PySpark Structured Streaming ingest (requires PULSEGRID_ENGINE=spark)",
    )
    parser.add_argument(
        "--transform-only",
        action="store_true",
        help="Silver + Gold Delta transforms only",
    )
    parser.add_argument(
        "--ml-only",
        action="store_true",
        help="ML scoring + anomaly detection (requires silver/gold)",
    )
    parser.add_argument(
        "--pbip-only",
        action="store_true",
        help="Export CSV + build PBIP (requires gold tables)",
    )
    parser.add_argument(
        "--pbip-blank",
        action="store_true",
        help="Build PBIP with blank pages only",
    )
    parser.add_argument(
        "--with-visuals",
        action="store_true",
        help="Styled Aurea Quantra PBIP visuals (full pipeline or --pbip-only)",
    )
    parser.add_argument("--stream-batches", type=int, default=3)
    parser.add_argument("--stream-interval", type=float, default=5.0)
    args = parser.parse_args()
    try:
        if args.stream_spark:
            run_structured_stream(
                args.city,
                max_batches=args.stream_batches,
                trigger_interval=f"{int(args.stream_interval)} seconds",
            )
        elif args.stream:
            run_microbatch(
                args.city,
                batches=args.stream_batches,
                interval_sec=args.stream_interval,
            )
        elif args.ingest_only:
            run_ingest(args.city, extended=args.extended_ingest)
        elif args.transform_only:
            run_transform(args.city)
        elif args.ml_only:
            run_ml(args.city)
        elif args.pbip_only or args.pbip_blank:
            include_visuals = args.with_visuals and not args.pbip_blank
            pbip = generate_pbip(args.city, include_visuals=include_visuals)
            mode = "with visuals" if include_visuals else "blank pages"
            print(f"  PBIP ({mode}) -> {pbip}")
        else:
            run_full(
                args.city,
                with_visuals=args.with_visuals,
                extended=args.extended_ingest,
            )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
