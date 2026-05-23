"""Tests for airport METAR bronze ingest."""

from __future__ import annotations

from unittest.mock import patch

from pulsegrid.config import get_city
from pulsegrid.ingest.airport import ingest_airport


def test_ingest_airport_writes_json(tmp_path, monkeypatch):
    import pulsegrid.config as cfg

    monkeypatch.setattr(cfg, "BRONZE", tmp_path / "bronze")
    city = get_city("chicago")
    sample = {
        "icaoId": "KORD",
        "rawOb": "METAR KORD 251100Z 00000KT 10SM CLR 05/M02 A3012",
    }

    with patch("pulsegrid.ingest.airport.fetch_metar", return_value=sample):
        paths = ingest_airport(city)

    assert len(paths) == 1
    assert paths[0].is_file()
    assert "KORD" in paths[0].read_text()
