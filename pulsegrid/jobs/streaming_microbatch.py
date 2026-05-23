"""Micro-batch streaming bronze ingest (poll APIs → append Delta)."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from pulsegrid.config import DELTA, get_city
from pulsegrid.ingest.cta import ingest_cta
from pulsegrid.ingest.noaa import ingest_noaa
from pulsegrid.io.delta_writer import append_delta_table, read_delta_table


def _event_row(city: str, source: str, path: str) -> dict:
    return {
        "city": city,
        "source": source,
        "bronze_path": str(path),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


def run_microbatch(
    city_slug: str,
    *,
    batches: int = 3,
    interval_sec: float = 5.0,
) -> None:
    """Poll NOAA + CTA N times and append ingest events to Delta (streaming bronze log)."""
    city = get_city(city_slug)
    log_path = DELTA / "bronze" / "ingest_events"
    print(f"Micro-batch streaming: {batches} batches, {interval_sec}s interval")
    for i in range(batches):
        print(f"  batch {i + 1}/{batches}")
        rows: list[dict] = []
        for source, paths in (
            ("noaa", ingest_noaa(city)),
            ("cta", ingest_cta(city)),
        ):
            for p in paths:
                rows.append(_event_row(city.slug, source, p))
                print(f"    {source} -> {p.name}")
        append_delta_table(rows, log_path)
        if i + 1 < batches:
            time.sleep(interval_sec)
    total = len(read_delta_table(log_path))
    print(f"  bronze.ingest_events rows: {total} at {log_path}")
