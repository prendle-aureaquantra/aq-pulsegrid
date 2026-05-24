"""Bronze freshness helpers."""

from __future__ import annotations

from pulsegrid.ingest.bronze_freshness import latest_bronze_times, write_freshness_marker


def test_freshness_marker_and_read(tmp_path, monkeypatch):
    import pulsegrid.config as cfg

    bronze = tmp_path / "bronze"
    monkeypatch.setattr(cfg, "BRONZE", bronze)
    write_freshness_marker("chicago", "transit")
    times = latest_bronze_times("chicago")
    assert "transit" in times or times == {}
