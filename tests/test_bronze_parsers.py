"""Tests for bronze -> silver parsers."""

from __future__ import annotations

import json
from pathlib import Path

from pulsegrid.transforms.bronze_parsers import (
    parse_airport_bronze,
    parse_cta_bronze,
    parse_fred_bronze,
    parse_noaa_forecast_bronze,
    parse_trends_bronze,
)


def test_parse_cta_bronze(tmp_path: Path):
    doc = {
        "fetched_at": "2026-05-23T12:00:00+00:00",
        "alerts": [
            {
                "alert_id": "1",
                "headline": "Temporary Reroute",
                "short_description": "NB #146 via Michigan and Loop",
                "severity": "",
                "service": "",
            }
        ],
    }
    p = tmp_path / "alerts_test.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rows = parse_cta_bronze([p])
    assert len(rows) == 1
    assert rows[0]["alert_category"] == "reroute"
    assert rows[0]["neighborhood_hint"] == "Loop"


def test_parse_noaa_forecast_bronze(tmp_path: Path):
    doc = {
        "fetched_at": "2026-05-23T12:00:00+00:00",
        "forecast": {
            "properties": {
                "periods": [
                    {
                        "number": 1,
                        "name": "Today",
                        "startTime": "2026-05-23T09:00:00-05:00",
                        "endTime": "2026-05-23T18:00:00-05:00",
                        "isDaytime": True,
                        "temperature": 61,
                        "probabilityOfPrecipitation": {"value": 8},
                        "shortForecast": "Fog",
                        "windSpeed": "5 mph",
                        "windDirection": "N",
                    }
                ]
            }
        },
    }
    p = tmp_path / "forecast_test.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rows = parse_noaa_forecast_bronze([p])
    assert rows[0]["temperature_f"] == 61
    assert rows[0]["precip_pct"] == 8


def test_parse_airport_bronze(tmp_path: Path):
    doc = {
        "fetched_at": "2026-05-23T12:00:00+00:00",
        "station": "KORD",
        "raw": {
            "icaoId": "KORD",
            "obsTime": "2026-05-23T11:54:00Z",
            "fltCat": "VFR",
            "visib": 10.0,
            "wspd": 12,
            "tempC": 18.3,
        },
    }
    p = tmp_path / "metar_test.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rows = parse_airport_bronze([p])
    assert rows[0]["flight_category"] == "VFR"
    assert rows[0]["visibility_sm"] == 10.0


def test_parse_fred_bronze(tmp_path: Path):
    doc = {
        "fetched_at": "2026-05-23T12:00:00+00:00",
        "series_id": "UNRATE",
        "series_label": "Unemployment rate",
        "raw": {
            "observations": [
                {"date": "2026-04-01", "value": "4.2"},
                {"date": "2026-03-01", "value": "."},
            ]
        },
    }
    p = tmp_path / "fred_test.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rows = parse_fred_bronze([p])
    assert len(rows) == 1
    assert rows[0]["value"] == 4.2


def test_parse_trends_bronze(tmp_path: Path):
    doc = {
        "fetched_at": "2026-05-23T12:00:00+00:00",
        "keywords": ["Chicago transit", "CTA delay"],
        "interest_over_time": [
            {
                "date": "2026-05-18",
                "Chicago transit": 42,
                "CTA delay": 18,
                "isPartial": False,
            },
        ],
    }
    p = tmp_path / "trends_test.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rows = parse_trends_bronze([p])
    assert len(rows) == 2
    assert {r["keyword"] for r in rows} == {"Chicago transit", "CTA delay"}
