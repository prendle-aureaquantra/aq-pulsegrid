"""Gold tables for streaming telemetry, events, OSM — platform layer."""

from __future__ import annotations

from collections import Counter

import pandas as pd

from pulsegrid.config import DELTA
from pulsegrid.geo.hex_grid import neighborhood_to_hex
from pulsegrid.io.delta_writer import read_delta_table

GOLD_ROOT = DELTA / "gold"
SILVER_ROOT = DELTA / "silver"
BRONZE_INGEST_LOG = DELTA / "bronze" / "ingest_events"


def streaming_telemetry_rows(city: str, snapshot_at: str) -> list[dict]:
    if not BRONZE_INGEST_LOG.exists():
        return []
    df = read_delta_table(BRONZE_INGEST_LOG)
    if df.empty or "city" not in df.columns:
        return []
    dc = df[df["city"] == city]
    if dc.empty:
        return []
    rows: list[dict] = []
    for source, grp in dc.groupby("source"):
        rows.append(
            {
                "city": city,
                "snapshot_at": snapshot_at,
                "source": source,
                "batch_count": len(grp),
                "last_ingested_at": str(grp["ingested_at"].max()),
            }
        )
    return rows


def event_heatmap_rows(
    events: pd.DataFrame | None, city: str, snapshot_at: str
) -> list[dict]:
    if events is None or events.empty:
        return []
    ec = events[events["city"] == city]
    if ec.empty:
        return []
    buckets: Counter = Counter()
    meta: dict[str, dict] = {}
    for _, row in ec.iterrows():
        cat = row.get("event_category") or "general"
        hint = (row.get("neighborhood_hint") or "").strip()
        hex_id = neighborhood_to_hex(hint) if hint else "citywide"
        key = (hex_id, hint or "Chicago", cat)
        buckets[key] += 1
        meta[key] = {
            "hex_id": hex_id,
            "neighborhood": hint or "Chicago",
            "event_category": cat,
        }
    return [
        {
            "city": city,
            "snapshot_at": snapshot_at,
            "hex_id": meta[k]["hex_id"],
            "neighborhood": meta[k]["neighborhood"],
            "event_category": meta[k]["event_category"],
            "event_count": count,
        }
        for k, count in buckets.items()
    ]


def osm_amenity_summary_rows(
    osm: pd.DataFrame | None, city: str, snapshot_at: str
) -> list[dict]:
    if osm is None or osm.empty:
        return []
    oc = osm[osm["city"] == city]
    if oc.empty:
        return []
    rows: list[dict] = []
    for amenity, grp in oc.groupby("amenity"):
        if not str(amenity).strip():
            continue
        rows.append(
            {
                "city": city,
                "snapshot_at": snapshot_at,
                "amenity": amenity,
                "poi_count": len(grp),
            }
        )
    return rows
