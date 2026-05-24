"""MobilityData catalog lookup tests."""

from __future__ import annotations

from unittest.mock import patch

from pulsegrid.ingest.mobility_catalog import lookup_gtfs_rt_alerts_url
from pulsegrid.metros import load_metro


def test_lookup_mbta_from_cached_index(tmp_path, monkeypatch):
    index = {
        "feeds": [
            {
                "filename": "us-massachusetts-mbta-gtfs-rt-sa-1603.json",
                "country": "us",
                "provider": "Massachusetts Bay Transportation Authority (MBTA)",
                "url": "https://cdn.mbta.com/realtime/Alerts.pb",
            },
            {
                "filename": "us-california-la-metro-gtfs-rt-sa-99.json",
                "country": "us",
                "provider": "LA Metro",
                "url": "https://example.com/la.pb",
            },
        ]
    }
    cache = tmp_path / "mobility_sa_filenames.json"
    cache.write_text(
        __import__("json").dumps({"filenames": [f["filename"] for f in index["feeds"]]}),
        encoding="utf-8",
    )
    monkeypatch.setattr("pulsegrid.ingest.mobility_catalog.BUNDLED_LIST", cache)
    monkeypatch.setattr("pulsegrid.ingest.mobility_catalog.LIST_CACHE", cache)
    monkeypatch.setattr("pulsegrid.ingest.mobility_catalog._filename_list", lambda: [f["filename"] for f in index["feeds"]])
    monkeypatch.setattr(
        "pulsegrid.ingest.mobility_catalog._fetch_download_url",
        lambda fn: next(
            (f["url"] for f in index["feeds"] if f["filename"] == fn),
            None,
        ),
    )
    boston = load_metro("boston")
    url = lookup_gtfs_rt_alerts_url(boston)
    assert url and "mbta.com" in url


def test_resolve_transit_metro_uses_catalog():
    from pulsegrid.ingest.transit_resolve import resolve_transit_metro as _resolve_transit_metro

    berlin = load_metro("berlin")
    with patch(
        "pulsegrid.ingest.mobility_catalog.lookup_gtfs_rt_alerts_url",
        return_value="https://example.com/berlin.pb",
    ):
        resolved = _resolve_transit_metro(berlin)
    assert resolved.transit_adapter == "gtfs_rt"
    assert resolved.gtfs_rt_url == "https://example.com/berlin.pb"
    assert "transit" in resolved.modules
