"""Gold KPI tables — city-generic (Phase 2)."""

from __future__ import annotations

from pathlib import Path

from pulsegrid.jobs.dim_metro import write_dim_metro
from pulsegrid.jobs.gold_chicago import run_gold as _run_gold_metro


def run_gold(city_slug: str = "chicago") -> dict[str, Path]:
    """Gold layer for any metro (311/infrastructure when civic311 bronze exists)."""
    written = _run_gold_metro(city_slug)
    write_dim_metro(active_cities={city_slug})
    return written


__all__ = ["run_gold"]
