"""DimAirport — one row per metro airport station (from metro_airports.yaml)."""

from __future__ import annotations

from pathlib import Path

from pulsegrid.config import DELTA, list_metros
from pulsegrid.metro_feeds import airport_station_labels
from pulsegrid.io.delta_writer import write_delta_table

GOLD_ROOT = DELTA / "gold"


def build_dim_airport_rows() -> list[dict]:
    rows: list[dict] = []
    for metro in list_metros():
        labels = airport_station_labels(metro.slug)
        if not labels:
            continue
        for idx, (icao, name) in enumerate(labels.items()):
            rows.append(
                {
                    "city": metro.slug,
                    "icao": icao,
                    "station_label": name,
                    "sort_order": idx,
                }
            )
    return rows


def write_dim_airport() -> Path:
    return write_delta_table(build_dim_airport_rows(), GOLD_ROOT / "dim_airport")
