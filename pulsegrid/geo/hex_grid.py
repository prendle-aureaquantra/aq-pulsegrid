"""H3-style hex grid assignment for Chicago (Sedona-ready geospatial layer)."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from pulsegrid.config import ROOT

REF_HEX = ROOT / "datasets" / "reference" / "chicago_hex_grid.csv"


def _load_hex_centroids() -> list[dict]:
    if not REF_HEX.is_file():
        return []
    with REF_HEX.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def lat_lon_to_hex(lat: float, lon: float, *, precision: float = 0.05) -> str:
    """Simple grid hex id (~5km cells) when H3/Sedona unavailable."""
    lat_bin = int(math.floor(lat / precision))
    lon_bin = int(math.floor(lon / precision))
    return f"hex_{lat_bin}_{lon_bin}"


def neighborhood_to_hex(neighborhood: str) -> str | None:
    """Map neighborhood label to nearest reference hex."""
    if not neighborhood:
        return None
    key = neighborhood.strip().lower()
    for row in _load_hex_centroids():
        if row.get("neighborhood", "").lower() == key:
            return row.get("hex_id")
        if key in row.get("neighborhood", "").lower():
            return row.get("hex_id")
    return None


def chicago_default_hex() -> str:
    rows = _load_hex_centroids()
    return rows[0]["hex_id"] if rows else "hex_837_941"


def aggregate_transit_by_hex(transit_rows: list[dict]) -> list[dict]:
    """Roll up transit alerts to hex cells via neighborhood_hint."""
    buckets: dict[str, dict] = {}
    for row in transit_rows:
        hint = (row.get("neighborhood_hint") or "").strip()
        hex_id = neighborhood_to_hex(hint) if hint else chicago_default_hex()
        if not hex_id:
            hex_id = chicago_default_hex()
        b = buckets.setdefault(
            hex_id,
            {
                "hex_id": hex_id,
                "neighborhood": hint or "Chicago (citywide)",
                "alert_count": 0,
                "reroute_count": 0,
                "delay_count": 0,
            },
        )
        b["alert_count"] += 1
        cat = row.get("alert_category") or ""
        if cat == "reroute":
            b["reroute_count"] += 1
        if cat == "delay":
            b["delay_count"] += 1
    return list(buckets.values())
