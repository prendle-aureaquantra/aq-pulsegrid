"""Phase 2 ingest adapter dispatch tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pulsegrid.ingest.registry import ingest_transit, ingest_weather
from pulsegrid.metros import load_metro


def test_transit_none_skips():
    metro = load_metro("berlin")
    assert ingest_transit(metro) == []


def test_weather_open_meteo_adapter(tmp_path, monkeypatch):
    metro = load_metro("london")
    monkeypatch.setattr("pulsegrid.config.BRONZE", tmp_path)
    with patch("pulsegrid.ingest.open_meteo.fetch_open_meteo") as mock_fetch:
        mock_fetch.return_value = {
            "hourly": {
                "time": ["2026-01-01T00:00"],
                "temperature_2m": [5.0],
                "precipitation_probability": [10],
            }
        }
        paths = ingest_weather(metro)
    assert len(paths) >= 1


def test_mbta_adapter_writes_bronze(tmp_path, monkeypatch):
    metro = load_metro("boston")
    from pulsegrid.config import BRONZE

    monkeypatch.setattr("pulsegrid.config.BRONZE", tmp_path)
    fake = {"data": [{"id": "a1", "attributes": {"header": "Test", "description": "Delay", "severity": "minor"}}]}
    with patch("pulsegrid.ingest.mbta.fetch_mbta_alerts", return_value=fake):
        paths = ingest_transit(metro)
    assert len(paths) == 1
    assert paths[0].name.startswith("alerts_")
