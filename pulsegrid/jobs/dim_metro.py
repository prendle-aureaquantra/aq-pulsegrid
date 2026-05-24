"""Gold dim_metro dimension table for worldwide metro slicer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pulsegrid.config import DELTA, list_metros
from pulsegrid.io.delta_writer import read_delta_table, write_delta_table

GOLD_ROOT = DELTA / "gold"


def build_dim_metro_rows(
    *,
    active_cities: set[str] | None = None,
    snapshot_at: str | None = None,
) -> list[dict]:
    ts = snapshot_at or datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    for metro in list_metros():
        tier_label = "Tier 1" if metro.tier == "full" else "Tier 2"
        rows.append(
            {
                "city": metro.slug,
                "display_name": metro.display_name,
                "metro_label": f"{metro.display_name} · {tier_label}",
                "metro_name": metro.name,
                "country": metro.country,
                "tier": metro.tier,
                "lat": metro.lat,
                "lon": metro.lon,
                "timezone": metro.timezone,
                "modules": ",".join(metro.modules),
                "last_snapshot_at": ts if active_cities and metro.slug in active_cities else "",
            }
        )
    return rows


def write_dim_metro(
    *,
    active_cities: set[str] | None = None,
    snapshot_at: str | None = None,
) -> Path:
    rows = build_dim_metro_rows(active_cities=active_cities, snapshot_at=snapshot_at)
    return write_delta_table(rows, GOLD_ROOT / "dim_metro")


def read_dim_metro_csv_rows() -> list[dict]:
    path = GOLD_ROOT / "dim_metro"
    if not path.exists():
        return build_dim_metro_rows()
    df = read_delta_table(path)
    if df is None or df.empty:
        return build_dim_metro_rows()
    return df.to_dict("records")
