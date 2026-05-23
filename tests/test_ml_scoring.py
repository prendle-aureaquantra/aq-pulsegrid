"""Tests for City Stress Index and anomaly detection."""

from __future__ import annotations

import pandas as pd

from pulsegrid.ml.anomaly import detect_anomalies
from pulsegrid.ml.city_stress import compute_stress_index


def test_stress_index_bounded():
    score, parts = compute_stress_index(
        active_cta=200,
        active_noaa=5,
        avg_precip=80,
        severe_weather_count=2,
        category_counts={"reroute": 100, "delay": 20},
    )
    assert score <= 100
    assert parts.transit_load > 0


def test_anomaly_detects_transit_spike():
    metrics = {
        "active_cta_alerts": 200,
        "active_noaa_alerts": 1,
        "avg_precip_pct_next_periods": 10,
        "reroute_count": 110,
    }
    history = pd.DataFrame(
        [
            {"active_cta_alerts": 90, "active_noaa_alerts": 1, "avg_precip_pct_next_periods": 10},
            {"active_cta_alerts": 95, "active_noaa_alerts": 2, "avg_precip_pct_next_periods": 12},
        ]
    )
    signals = detect_anomalies(
        city="chicago",
        snapshot_at="2026-05-23T12:00:00+00:00",
        metrics=metrics,
        history=history,
    )
    types = {s.signal_type for s in signals}
    assert "transit_alert_spike" in types
