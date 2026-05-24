"""Feed coverage orchestration smoke tests."""

from __future__ import annotations

from pulsegrid.ingest.socrata_311_discovery import CURATED_311, curated_311_config


def test_curated_houston_philadelphia():
    assert curated_311_config("houston")["adapter"] == "arcgis"
    assert curated_311_config("philadelphia")["adapter"] == "carto"
    assert "houston" in CURATED_311
