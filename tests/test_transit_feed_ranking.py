"""MobilityData ranking and curated transit config."""

from __future__ import annotations

from pulsegrid.ingest.mobility_catalog import _rank_filenames, lookup_gtfs_rt_alerts_url
from pulsegrid.metro_feeds import transit_feed_config
from pulsegrid.metros import load_metro


def test_curated_phoenix_transit_url():
    cfg = transit_feed_config("phoenix")
    assert cfg is not None
    assert cfg["adapter"] == "gtfs_rt"
    assert "valleymetro" in cfg["gtfs_rt_url"]


def test_philadelphia_mobility_prefers_septa_not_california():
    metro = load_metro("philadelphia")
    ranked = _rank_filenames(metro)
    assert ranked
    top = ranked[0][1].lower()
    assert "septa" in top or "pennsylvania" in top
    assert "california" not in top


def test_phoenix_mobility_lookup():
    metro = load_metro("phoenix")
    url = lookup_gtfs_rt_alerts_url(metro)
    assert url
    assert "valleymetro" in url.lower()
