"""Metadata-driven ingest feed framework tests."""

from __future__ import annotations

from pulsegrid.ingest.feed_framework import (
    CORE_FEED_IDS,
    coverage_report,
    list_metro_feeds,
    resolve_feed,
)
from pulsegrid.metros import load_metro


def test_core_feed_ids_catalog():
    assert set(CORE_FEED_IDS) == {
        "nws_weather",
        "gtfs_rt",
        "opensky_aviation",
        "civic311",
    }


def test_chicago_all_four_feeds_enabled():
    metro = load_metro("chicago")
    by_id = {f.feed_id: f for f in list_metro_feeds(metro)}
    assert by_id["nws_weather"].enabled
    assert by_id["gtfs_rt"].enabled
    assert by_id["opensky_aviation"].enabled
    assert by_id["civic311"].enabled


def test_london_nws_disabled_open_meteo_weather():
    metro = load_metro("london")
    nws = resolve_feed(metro, "nws_weather")
    assert not nws.enabled
    assert "US" in nws.reason or "noaa" in nws.reason.lower()


def test_berlin_civic311_disabled():
    metro = load_metro("berlin")
    civic = resolve_feed(metro, "civic311")
    assert not civic.enabled


def test_boston_gtfs_rt_via_mbta_adapter():
    metro = load_metro("boston")
    transit = resolve_feed(metro, "gtfs_rt")
    assert transit.enabled
    assert transit.config.get("transit_adapter") == "mbta"


def test_coverage_report_has_metro_rows():
    rows = coverage_report([load_metro("chicago"), load_metro("london")])
    assert len(rows) == 2
    assert rows[0]["metro"] == "chicago"
    assert "nws_weather" in rows[0]
