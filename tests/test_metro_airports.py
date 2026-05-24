"""Metro airport catalog coverage."""

from __future__ import annotations

from pulsegrid.config import get_metro
from pulsegrid.metro_feeds import airport_station_codes, airport_station_labels
from pulsegrid.metros import list_metros


def test_all_metros_have_airport_stations():
    for metro in list_metros():
        codes = airport_station_codes(metro.slug)
        assert len(codes) >= 1, metro.slug


def test_chicago_includes_regional_airports():
    codes = airport_station_codes("chicago")
    assert "KORD" in codes
    assert "KMDW" in codes
    assert "KGYY" in codes
    labels = airport_station_labels("chicago")
    assert labels["KGYY"] == "Gary/Chicago International"
    assert len(codes) >= 5


def test_nyc_multi_airport():
    codes = airport_station_codes("nyc")
    assert len(codes) >= 5
    assert "KJFK" in codes and "KEWR" in codes


def test_metro_modules_include_airports():
    chicago = get_metro("chicago")
    assert "airports" in chicago.modules
    assert len(chicago.airports) >= 5
