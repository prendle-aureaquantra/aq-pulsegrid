"""Tests for events parser and platform gold helpers."""

from __future__ import annotations

import json
from pathlib import Path

from pulsegrid.jobs.gold_platform import event_heatmap_rows
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
