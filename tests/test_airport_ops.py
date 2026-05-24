"""Multi-station airport ops rollup tests."""

from __future__ import annotations

import pandas as pd

from pulsegrid.airport_ops import latest_airport_ops_rows, rollup_airport_for_city_pulse


def test_latest_airport_ops_rows_one_per_station():
    airport = pd.DataFrame(
        [
            {
                "city": "chicago",
                "station": "KORD",
                "ingested_at": "2026-01-02T12:00:00Z",
                "flight_category": "VFR",
                "visibility_sm": 10.0,
            },
            {
                "city": "chicago",
                "station": "KORD",
                "ingested_at": "2026-01-02T11:00:00Z",
                "flight_category": "IFR",
                "visibility_sm": 1.0,
            },
            {
                "city": "chicago",
                "station": "KMDW",
                "ingested_at": "2026-01-02T12:00:00Z",
                "flight_category": "MVFR",
                "visibility_sm": 4.0,
            },
        ]
    )
    rows = latest_airport_ops_rows(
        airport,
        "chicago",
        "2026-01-02T12:30:00Z",
        station_names={"KORD": "O'Hare", "KMDW": "Midway"},
    )
    assert len(rows) == 2
    ord_row = next(r for r in rows if r["station"] == "KORD")
    assert ord_row["flight_category"] == "VFR"
    assert ord_row["station_label"] == "O'Hare"
    mdw = next(r for r in rows if r["station"] == "KMDW")
    assert mdw["airport_ops_stress"] == 3.0


def test_rollup_worst_category_and_max_stress():
    rows = [
        {
            "station": "KORD",
            "station_label": "O'Hare",
            "flight_category": "VFR",
            "visibility_sm": 10.0,
            "airport_ops_stress": 0.0,
        },
        {
            "station": "KMDW",
            "station_label": "Midway",
            "flight_category": "IFR",
            "visibility_sm": 2.0,
            "airport_ops_stress": 13.0,
        },
    ]
    rollup = rollup_airport_for_city_pulse(rows)
    assert rollup["airport_flight_category"] == "IFR"
    assert rollup["airport_visibility_sm"] == 2.0
    assert rollup["airport_ops_stress"] == 13.0
    assert rollup["active_airport_stations"] == 2
    assert "Midway" in rollup["airport_stations_summary"]
