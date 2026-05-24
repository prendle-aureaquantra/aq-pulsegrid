#!/usr/bin/env python3
"""
AQ PulseGrid city pipeline entrypoint.

Examples:
  python generate_city.py --city chicago --ingest-only
  python generate_city.py --metros chicago,boston --extended-ingest
  python generate_city.py --all-metros --tier full --with-visuals
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from pulsegrid.config import ensure_dirs, get_metro, list_metros, load_dotenv
from pulsegrid.ingest.registry import run_metro_ingest
from pulsegrid.jobs.gold import run_gold
from pulsegrid.jobs.ml import run_ml
from pulsegrid.jobs.silver import run_silver
from pulsegrid.jobs.streaming_microbatch import run_microbatch
from pulsegrid.jobs.streaming_spark import run_structured_stream
from pbip_generator.generate import generate_pbip
from pbip_generator.platform import export_platform_csv, generate_platform_pbip


def resolve_metros(
    *,
    city: str | None,
    metros: str | None,
    all_metros: bool,
    tier: str | None,
) -> list[str]:
    if all_metros:
        return [m.slug for m in list_metros(tier=tier or None)]  # type: ignore[arg-type]
    if metros:
        return [s.strip().lower() for s in metros.split(",") if s.strip()]
    return [city or "chicago"]


def run_ingest(metro_slug: str, *, extended: bool = False) -> None:
    metro = get_metro(metro_slug)
    print(f"Ingesting public feeds for {metro.display_name}...")
    paths = run_metro_ingest(metro_slug, extended=extended)
    for p in paths:
        print(f"  -> {p}")


def run_transform(metro_slug: str) -> None:
    print(f"Silver transforms for {metro_slug}...")
    silver = run_silver(metro_slug)
    for name, path in silver.items():
        print(f"  silver.{name} -> {path}")
    print(f"Gold KPIs for {metro_slug}...")
    gold = run_gold(metro_slug)
    for name, path in gold.items():
        print(f"  gold.{name} -> {path}")


def run_ml_pipeline(metro_slug: str) -> None:
    print(f"ML scoring + anomalies for {metro_slug}...")
    outputs = run_ml(metro_slug)
    for name, path in outputs.items():
        print(f"  ml.{name} -> {path}")


def run_full(
    metro_slug: str, *, with_visuals: bool = False, extended: bool = False
) -> None:
    run_ingest(metro_slug, extended=extended)
    run_transform(metro_slug)
    run_ml_pipeline(metro_slug)
    print("\nPBIP generation")
    pbip = generate_pbip(metro_slug, include_visuals=with_visuals)
    mode = "with visuals" if with_visuals else "blank pages"
    print(f"  PBIP ({mode}) -> {pbip}")


def run_platform(*, with_visuals: bool = False, tier: str | None = "full") -> None:
    slugs = [m.slug for m in list_metros(tier=tier or None)]  # type: ignore[arg-type]
    if tier is None:
        slugs = [m.slug for m in list_metros()]
    print(f"Platform export for {len(slugs)} metros (tier={tier or 'all'})...")
    data_dir = export_platform_csv(None if tier is None else slugs)
    print(f"  platform CSV -> {data_dir}")
    pbip = generate_platform_pbip(include_visuals=with_visuals)
    print(f"  platform PBIP -> {pbip}")


def main() -> int:
    load_dotenv()
    ensure_dirs()
    parser = argparse.ArgumentParser(description="AQ PulseGrid city pipeline")
    parser.add_argument("--city", default="chicago", help="Metro slug (default: chicago)")
    parser.add_argument(
        "--metros",
        help="Comma-separated metro slugs (e.g. chicago,boston,london)",
    )
    parser.add_argument(
        "--all-metros",
        action="store_true",
        help="Run for all metros in registry (optional --tier filter)",
    )
    parser.add_argument(
        "--tier",
        choices=("full", "weather_only"),
        help="Filter metros by tier when using --all-metros",
    )
    parser.add_argument("--ingest-only", action="store_true", help="Bronze ingest only")
    parser.add_argument(
        "--extended-ingest",
        action="store_true",
        help="Also ingest airport, OpenSky, USGS, AQI, trends, FRED, events, OSM",
    )
    parser.add_argument(
        "--boost-feeds",
        action="store_true",
        help="Run MobilityData + Socrata discovery to expand transit_feeds.yaml and civic311.yaml",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Micro-batch poll NOAA+transit into bronze ingest_events Delta log",
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
        "--platform-only",
        action="store_true",
        help="Union multi-metro CSVs + build platform PulseGrid.pbip",
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
    parser.add_argument(
        "--ingest-delay",
        type=float,
        default=0.25,
        help="Seconds to wait between metros during ingest (rate limits)",
    )
    args = parser.parse_args()

    metro_slugs = resolve_metros(
        city=args.city,
        metros=args.metros,
        all_metros=args.all_metros,
        tier=args.tier,
    )

    try:
        if args.boost_feeds:
            import subprocess

            cmd = [
                sys.executable,
                str(Path(__file__).resolve().parent / "tools" / "boost_feed_coverage.py"),
                "--force-mobility",
                "--fill-empty-urls",
            ]
            print("Boosting feed coverage (transit + 311 catalogs)…")
            subprocess.check_call(cmd)
            return 0

        if args.platform_only:
            run_platform(with_visuals=args.with_visuals, tier=args.tier)
            from pulsegrid.pipeline_status import write_pipeline_status

            write_pipeline_status(
                job="platform-only",
                metros_ok=len(metro_slugs),
                metros_failed=0,
                detail=f"visuals={args.with_visuals}",
            )
            return 0

        if args.stream_spark:
            for slug in metro_slugs:
                run_structured_stream(
                    slug,
                    max_batches=args.stream_batches,
                    trigger_interval=f"{int(args.stream_interval)} seconds",
                )
        elif args.stream:
            for slug in metro_slugs:
                run_microbatch(
                    slug,
                    batches=args.stream_batches,
                    interval_sec=args.stream_interval,
                )
        elif args.ingest_only:
            failed = 0
            for i, slug in enumerate(metro_slugs):
                try:
                    run_ingest(slug, extended=args.extended_ingest)
                except Exception as exc:
                    failed += 1
                    print(f"WARN: ingest failed for {slug}: {exc}", file=sys.stderr)
                if i + 1 < len(metro_slugs) and args.ingest_delay > 0:
                    time.sleep(args.ingest_delay)
            if len(metro_slugs) > 1:
                from pulsegrid.pipeline_status import write_pipeline_status

                write_pipeline_status(
                    job="ingest-only",
                    metros_ok=len(metro_slugs) - failed,
                    metros_failed=failed,
                    detail=f"tier={args.tier or 'all'} extended={args.extended_ingest}",
                )
            if failed == len(metro_slugs):
                return 1
        elif args.transform_only:
            failed = 0
            for slug in metro_slugs:
                try:
                    run_transform(slug)
                except Exception as exc:
                    failed += 1
                    print(f"WARN: transform failed for {slug}: {exc}", file=sys.stderr)
            if len(metro_slugs) > 1:
                from pulsegrid.pipeline_status import write_pipeline_status

                write_pipeline_status(
                    job="transform-only",
                    metros_ok=len(metro_slugs) - failed,
                    metros_failed=failed,
                    detail=f"tier={args.tier or 'all'}",
                )
            if failed == len(metro_slugs):
                return 1
        elif args.ml_only:
            failed = 0
            for slug in metro_slugs:
                try:
                    run_ml_pipeline(slug)
                except Exception as exc:
                    failed += 1
                    print(f"WARN: ML failed for {slug}: {exc}", file=sys.stderr)
            if len(metro_slugs) > 1:
                from pulsegrid.pipeline_status import write_pipeline_status

                write_pipeline_status(
                    job="ml-only",
                    metros_ok=len(metro_slugs) - failed,
                    metros_failed=failed,
                    detail=f"tier={args.tier or 'all'}",
                )
            if failed == len(metro_slugs):
                return 1
        elif args.pbip_only or args.pbip_blank:
            include_visuals = args.with_visuals and not args.pbip_blank
            for slug in metro_slugs:
                pbip = generate_pbip(slug, include_visuals=include_visuals)
                mode = "with visuals" if include_visuals else "blank pages"
                print(f"  PBIP ({mode}) -> {pbip}")
            if len(metro_slugs) > 1 or args.all_metros:
                run_platform(with_visuals=include_visuals, tier=args.tier)
        else:
            for slug in metro_slugs:
                run_full(
                    slug,
                    with_visuals=args.with_visuals,
                    extended=args.extended_ingest,
                )
            if len(metro_slugs) > 1 or args.all_metros:
                run_platform(with_visuals=args.with_visuals, tier=args.tier)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
