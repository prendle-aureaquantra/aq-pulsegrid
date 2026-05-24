"""Transit alert → neighborhood resolution."""

from __future__ import annotations

import json
from pathlib import Path

from pulsegrid.geo.transit_neighborhood import resolve_transit_alert_neighborhood
from pulsegrid.transforms.bronze_parsers import parse_cta_bronze


def test_clark_lake_stop_change():
    hood = resolve_transit_alert_neighborhood(
        city="chicago",
        headline="Temporary Bus Stop Change",
        short_description="SB #22 bus stop on Clark/Lake discontinued.",
    )
    assert hood == "Loop"


def test_red_line_subway_reroute():
    hood = resolve_transit_alert_neighborhood(
        city="chicago",
        headline="Temporary Reroute",
        short_description="Red Line subway trains rerouted between Cermak-Chinatown and Fullerton.",
    )
    assert hood in ("South Loop", "Lakeview", "Loop")


def test_bus_route_number():
    hood = resolve_transit_alert_neighborhood(
        city="chicago",
        headline="Temporary Reroute",
        short_description="EB #73 via Cortland, Elston, North, Kingsbury.",
    )
    assert hood == "Lincoln Park"


def test_brown_line_station():
    hood = resolve_transit_alert_neighborhood(
        city="chicago",
        headline="Elevator",
        short_description="Kimball-bound platform elevator at Western Brown Line stn out of service.",
    )
    assert hood in ("Logan Square", "Albany Park")


def test_parse_cta_bronze_uses_resolver(tmp_path: Path):
    doc = {
        "fetched_at": "2026-05-23T12:00:00+00:00",
        "alerts": [
            {
                "alert_id": "1",
                "headline": "Temporary Bus Stop Change",
                "short_description": "Stop at Clark/Lake discontinued.",
                "severity": "",
                "service": "",
            }
        ],
    }
    p = tmp_path / "alerts.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rows = parse_cta_bronze([p])
    assert rows[0]["neighborhood_hint"] == "Loop"


def test_london_tfl_headline_line():
    hood = resolve_transit_alert_neighborhood(
        city="london",
        headline="Bakerloo: Part Suspended",
        short_description="",
    )
    assert hood == "Westminster"


def test_tokyo_synthetic_district():
    hood = resolve_transit_alert_neighborhood(
        city="tokyo",
        headline="Delay",
        short_description="Service disruption near Shinjuku station.",
    )
    assert hood == "Central Tokyo"


def test_all_metros_have_geo_config():
    from pulsegrid.metros import list_metros
    from pulsegrid.geo.transit_neighborhood import load_transit_geo_config

    for metro in list_metros():
        cfg = load_transit_geo_config(metro.slug)
        assert cfg is not None, metro.slug
        assert len(cfg.keywords) >= 3, metro.slug


def test_chicago_bronze_coverage_sample():
    """Smoke: majority of live CTA alerts should resolve beyond citywide."""
    sample = (
        Path(__file__).resolve().parents[1]
        / "datasets"
        / "bronze"
        / "chicago"
        / "transit"
    )
    files = sorted(sample.glob("alerts_*.json"))
    if not files:
        return
    rows = parse_cta_bronze([files[-1]])
    assert len(rows) >= 10
    resolved = sum(1 for r in rows if r.get("neighborhood_hint"))
    assert resolved / len(rows) >= 0.55
