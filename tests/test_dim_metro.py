"""DimMetro and platform export tests."""

from __future__ import annotations

from pulsegrid.jobs.dim_metro import build_dim_metro_rows


def test_dim_metro_rows_include_all_registry_metros():
    rows = build_dim_metro_rows(active_cities={"chicago", "london"})
    slugs = {r["city"] for r in rows}
    assert "chicago" in slugs
    assert "london" in slugs
    assert len(rows) >= 60
    chicago = next(r for r in rows if r["city"] == "chicago")
    assert chicago["display_name"] == "Chicago, US"
    assert chicago["last_snapshot_at"]
