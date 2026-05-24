"""PulseGrid CLI."""

from __future__ import annotations

import argparse

from pulsegrid.config import ensure_dirs, get_city, load_dotenv
from pulsegrid.ingest.cta import ingest_cta
from pulsegrid.ingest.noaa import ingest_noaa
from pulsegrid.jobs.gold import run_gold
from pulsegrid.jobs.ml import run_ml
from pulsegrid.jobs.silver import run_silver


def cmd_ingest(args: argparse.Namespace) -> int:
    city = get_city(args.city)
    for p in ingest_noaa(city):
        print(p)
    for p in ingest_cta(city):
        print(p)
    return 0


def cmd_transform(args: argparse.Namespace) -> int:
    for name, path in run_silver(args.city).items():
        print(f"silver.{name} -> {path}")
    for name, path in run_gold(args.city).items():
        print(f"gold.{name} -> {path}")
    return 0


def cmd_ml(args: argparse.Namespace) -> int:
    for name, path in run_ml(args.city).items():
        print(f"ml.{name} -> {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    ensure_dirs()
    parser = argparse.ArgumentParser(prog="pulsegrid")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Bronze ingest for a city")
    p_ingest.add_argument("--city", default="chicago")
    p_ingest.set_defaults(func=cmd_ingest)

    p_transform = sub.add_parser("transform", help="Silver + Gold Delta transforms")
    p_transform.add_argument("--city", default="chicago")
    p_transform.set_defaults(func=cmd_transform)

    p_ml = sub.add_parser("ml", help="ML scoring + anomaly detection")
    p_ml.add_argument("--city", default="chicago")
    p_ml.set_defaults(func=cmd_ml)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
