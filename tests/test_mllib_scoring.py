"""Tests for multivariate MLlib / pandas anomaly scoring."""

from __future__ import annotations

import pandas as pd

from pulsegrid.ml.anomaly import detect_anomalies
from pulsegrid.ml.spark_mllib import (
    build_feature_matrix,
    enrich_metrics_with_mllib,
    pandas_multivariate_score,
)


def test_pandas_multivariate_score_detects_spike():
    baseline = [
        [10.0, 1.0, 5.0, 30.0],
        [12.0, 1.0, 6.0, 32.0],
        [11.0, 2.0, 4.0, 28.0],
    ]
    normal = baseline + [[11.0, 1.5, 5.0, 31.0]]
    spike = baseline + [[200.0, 15.0, 80.0, 95.0]]
    normal_score = pandas_multivariate_score(normal)
    spike_score = pandas_multivariate_score(spike)
    assert normal_score is not None
    assert spike_score is not None
    assert spike_score > normal_score


def test_enrich_metrics_with_history():
    history = pd.DataFrame(
        [
            {
                "city": "chicago",
                "active_transit_alerts": 10,
                "active_noaa_alerts": 1,
                "avg_precip_pct_next_periods": 5,
                "city_stress_index": 25,
            },
            {
                "city": "chicago",
                "active_transit_alerts": 12,
                "active_noaa_alerts": 2,
                "avg_precip_pct_next_periods": 8,
                "city_stress_index": 30,
            },
            {
                "city": "chicago",
                "active_transit_alerts": 11,
                "active_noaa_alerts": 1,
                "avg_precip_pct_next_periods": 6,
                "city_stress_index": 28,
            },
        ]
    )
    metrics = {
        "city": "chicago",
        "active_transit_alerts": 150,
        "active_noaa_alerts": 10,
        "avg_precip_pct_next_periods": 40,
        "city_stress_index": 90,
    }
    enriched = enrich_metrics_with_mllib(metrics, history=history)
    assert "mllib_z_score" in enriched
    assert float(enriched["mllib_z_score"]) > 2.0


def test_mllib_spike_emits_anomaly_signal():
    metrics = {
        "active_transit_alerts": 150,
        "active_noaa_alerts": 10,
        "avg_precip_pct_next_periods": 40,
        "city_stress_index": 90,
        "mllib_z_score": 8.5,
        "reroute_count": 0,
    }
    signals = detect_anomalies(
        city="chicago",
        snapshot_at="2026-05-30T12:00:00+00:00",
        metrics=metrics,
        history=None,
    )
    types = {s.signal_type for s in signals}
    assert "mllib_multivariate_spike" in types


def test_build_feature_matrix_orders_history():
    history = pd.DataFrame(
        [
            {
                "city": "boston",
                "snapshot_at": "2026-05-01T00:00:00+00:00",
                "active_transit_alerts": 1,
                "active_noaa_alerts": 0,
                "avg_precip_pct_next_periods": 0,
                "city_stress_index": 5,
            },
            {
                "city": "chicago",
                "snapshot_at": "2026-05-01T00:00:00+00:00",
                "active_transit_alerts": 2,
                "active_noaa_alerts": 0,
                "avg_precip_pct_next_periods": 0,
                "city_stress_index": 6,
            },
        ]
    )
    metrics = {
        "city": "chicago",
        "active_transit_alerts": 20,
        "active_noaa_alerts": 1,
        "avg_precip_pct_next_periods": 3,
        "city_stress_index": 40,
    }
    matrix = build_feature_matrix(metrics, history)
    assert len(matrix) == 2
    assert matrix[-1][0] == 20.0
