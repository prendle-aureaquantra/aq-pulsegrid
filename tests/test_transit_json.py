"""Agency JSON transit adapter tests."""

from __future__ import annotations

from unittest.mock import patch

from pulsegrid.ingest.transit_json import ingest_transit_json
from pulsegrid.metros import load_metro


def test_tfl_adapter_writes_bronze(tmp_path, monkeypatch):
    from pulsegrid.config import BRONZE

    monkeypatch.setattr("pulsegrid.config.BRONZE", tmp_path)
    metro = load_metro("london")
    city = __import__("pulsegrid.config", fromlist=["metro_to_city"]).metro_to_city(metro)
    fake = [
        {
            "alert_id": "tfl-bakerloo-1",
            "headline": "Bakerloo: Minor Delays",
            "short_description": "signal failure",
            "severity": "6",
            "service": "tfl",
        }
    ]
    with patch.dict(
        "pulsegrid.ingest.transit_json._JSON_ADAPTERS",
        {"tfl": lambda: fake},
    ):
        paths = ingest_transit_json(metro, city, json_adapter="tfl")
    assert len(paths) == 1
    doc = __import__("json").loads(paths[0].read_text(encoding="utf-8"))
    assert doc["source"] == "transit_alerts"
    assert doc["alert_count"] == 1
