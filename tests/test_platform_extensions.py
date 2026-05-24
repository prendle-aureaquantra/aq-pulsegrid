"""Tests for events parser and platform gold helpers."""

from __future__ import annotations

import json
from pathlib import Path

from pulsegrid.jobs.gold_platform import (
    event_detail_rows,
    event_heatmap_rows,
    transit_alert_detail_rows,
)
from pulsegrid.geo.hex_grid import resolve_transit_neighborhood
from pulsegrid.transforms.bronze_parsers import parse_events_bronze


def test_parse_events_bronze(tmp_path: Path):
    doc = {
        "fetched_at": "2026-05-23T12:00:00+00:00",
        "records": [
            {
                "id": "1",
                "event_name": "Jazz Festival",
                "event_type": "music",
                "community_area": "Loop",
                "start_date": "2026-06-01",
            }
        ],
    }
    p = tmp_path / "events_test.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rows = parse_events_bronze([p])
    assert rows[0]["event_name"] == "Jazz Festival"
    assert rows[0]["event_category"] == "music"


def test_event_heatmap_rows():
    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "city": "chicago",
                "event_category": "music",
                "neighborhood_hint": "Loop",
            },
            {
                "city": "chicago",
                "event_category": "music",
                "neighborhood_hint": "Loop",
            },
        ]
    )
    rows = event_heatmap_rows(df, "chicago", "2026-05-23T12:00:00+00:00")
    assert rows[0]["event_count"] == 2
    assert rows[0]["neighborhood"] == "Loop"


def test_event_detail_rows():
    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "city": "chicago",
                "event_id": "e1",
                "event_name": "Jazz Fest",
                "event_category": "music",
                "neighborhood_hint": "Loop",
                "location": "Grant Park",
                "start_date": "2026-06-01",
                "end_date": "2026-06-03",
            },
        ]
    )
    rows = event_detail_rows(df, "chicago", "2026-05-23T12:00:00+00:00")
    assert len(rows) == 1
    assert rows[0]["event_name"] == "Jazz Fest"
    assert rows[0]["neighborhood"] == "Loop"


def test_resolve_transit_neighborhood_citywide():
    hex_id, label = resolve_transit_neighborhood("")
    assert hex_id == "citywide"
    assert label == "citywide"


def test_transit_alert_detail_rows():
    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "city": "chicago",
                "alert_id": "a1",
                "headline": "Reroute on Red Line",
                "short_description": "Due to construction",
                "severity": "minor",
                "service": "Red Line",
                "alert_category": "reroute",
                "neighborhood_hint": "Hyde Park",
            },
            {
                "city": "chicago",
                "alert_id": "a2",
                "headline": "Bus stop change",
                "short_description": "",
                "severity": "",
                "service": "Bus 22",
                "alert_category": "stop_change",
                "neighborhood_hint": "",
            },
        ]
    )
    rows = transit_alert_detail_rows(df, "chicago", "2026-05-23T12:00:00+00:00")
    assert len(rows) == 2
    assert rows[0]["neighborhood"] == "Hyde Park"
    assert rows[1]["neighborhood"] == "citywide"
