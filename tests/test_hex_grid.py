"""Hex grid assignment tests."""

from __future__ import annotations

from pulsegrid.geo.hex_grid import aggregate_transit_by_hex, neighborhood_to_hex


def test_neighborhood_to_hex():
    assert neighborhood_to_hex("Loop") == "hex_837_941"
    assert neighborhood_to_hex("unknown area") is None


def test_aggregate_transit_by_hex():
    rows = [
        {"neighborhood_hint": "Loop", "alert_category": "reroute"},
        {"neighborhood_hint": "Loop", "alert_category": "delay"},
        {"neighborhood_hint": "Hyde Park", "alert_category": "info"},
    ]
    agg = aggregate_transit_by_hex(rows)
    by_hex = {r["hex_id"]: r for r in agg}
    assert by_hex["hex_837_941"]["alert_count"] == 2
    assert by_hex["hex_837_941"]["reroute_count"] == 1
    assert by_hex["hex_833_938"]["alert_count"] == 1
