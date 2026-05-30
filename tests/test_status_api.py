"""Tests for PulseGrid ops FastAPI data + ML routes."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_sample_csvs(data_dir)
    monkeypatch.setenv("PULSEGRID_DATA_DIR", str(data_dir))
    monkeypatch.setenv("PULSEGRID_CITY", "chicago")
    monkeypatch.setenv("PULSEGRID_MIN_METRO_COUNT", "1")

    import pulsegrid.web.csv_store as csv_store

    csv_store.DATA_DIR = data_dir
    csv_store.DEFAULT_METRO = "chicago"

    from pulsegrid.web.status_app import app

    return TestClient(app)


def _write_sample_csvs(data_dir: Path) -> None:
    dim = [
        {"city": "chicago", "display_name": "Chicago", "metro_name": "Chicago, IL"},
        {"city": "boston", "display_name": "Boston", "metro_name": "Boston, MA"},
    ]
    pulse = [
        {
            "city": "chicago",
            "snapshot_at": "2026-05-24T12:00:00+00:00",
            "city_stress_index": "42.5",
            "transit_load_score": "10.0",
            "weather_risk_score": "8.0",
            "precip_risk_score": "5.0",
            "disruption_ratio_score": "3.0",
            "active_transit_alerts": "12",
            "active_noaa_alerts": "1",
            "data_refreshed_at": "2026-05-24T11:55:00+00:00",
            "last_weather_ingest_at": "2026-05-24T11:50:00+00:00",
            "last_transit_ingest_at": "2026-05-24T11:52:00+00:00",
        },
        {
            "city": "boston",
            "snapshot_at": "2026-05-24T12:00:00+00:00",
            "city_stress_index": "18.0",
            "transit_load_score": "4.0",
            "weather_risk_score": "2.0",
            "precip_risk_score": "1.0",
            "disruption_ratio_score": "1.0",
            "active_transit_alerts": "2",
            "active_noaa_alerts": "0",
        },
    ]
    anomalies = [
        {
            "city": "chicago",
            "snapshot_at": "2026-05-24T12:00:00+00:00",
            "signal_type": "transit_alert_spike",
            "metric": "active_transit_alerts",
            "observed": "12",
            "baseline": "5",
            "z_score": "2.5",
            "severity": "medium",
            "message": "Transit spike",
        },
        {
            "city": "chicago",
            "snapshot_at": "2026-05-24T11:00:00+00:00",
            "signal_type": "weather_alert_spike",
            "metric": "active_noaa_alerts",
            "observed": "3",
            "baseline": "1",
            "z_score": "3.1",
            "severity": "high",
            "message": "Weather spike",
        },
    ]
    weather = [
        {
            "city": "chicago",
            "snapshot_at": "2026-05-24T12:00:00+00:00",
            "period_name": "Tonight",
            "precip_pct": "40",
        }
    ]
    history = [
        {
            "city": "chicago",
            "snapshot_at": "2026-05-23T12:00:00+00:00",
            "city_stress_index": "35.0",
            "active_transit_alerts": "8",
        },
        {
            "city": "chicago",
            "snapshot_at": "2026-05-24T12:00:00+00:00",
            "city_stress_index": "42.5",
            "active_transit_alerts": "12",
        },
    ]
    _write_csv(data_dir / "DimMetro.csv", dim)
    _write_csv(data_dir / "CityPulseSnapshot.csv", pulse)
    _write_csv(data_dir / "AnomalySignals.csv", anomalies)
    _write_csv(data_dir / "WeatherForecastPeriods.csv", weather)
    _write_csv(data_dir / "PulseHistory.csv", history)
    _write_csv(data_dir / "TransitAlertSummary.csv", [])


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_api_data_catalog(api_client: TestClient) -> None:
    res = api_client.get("/api/data")
    assert res.status_code == 200
    tables = {t["table"] for t in res.json()["tables"]}
    assert "CityPulseSnapshot" in tables
    assert "PulseHistory" in tables


def test_api_data_table_slug(api_client: TestClient) -> None:
    res = api_client.get("/api/data/city-pulse-snapshot?metro=chicago&limit=5")
    assert res.status_code == 200
    body = res.json()
    assert body["metro"] == "chicago"
    assert body["total"] == 1
    assert body["rows"][0]["city_stress_index"] == "42.5"


def test_api_data_unknown_table(api_client: TestClient) -> None:
    res = api_client.get("/api/data/not-a-table")
    assert res.status_code == 404


def test_api_weather_domain(api_client: TestClient) -> None:
    res = api_client.get("/api/weather?metro=chicago")
    assert res.status_code == 200
    body = res.json()
    assert body["domain"] == "weather"
    assert len(body["tables"]["WeatherForecastPeriods"]) == 1


def test_api_ml_stress(api_client: TestClient) -> None:
    res = api_client.get("/api/ml/stress?metro=chicago")
    assert res.status_code == 200
    body = res.json()
    assert body["stressIndex"] == "42.5"
    assert body["components"]["transit_load_score"] == "10.0"
    assert body["freshness"]["data_refreshed_at"] == "2026-05-24T11:55:00+00:00"


def test_api_ml_anomalies_severity_filter(api_client: TestClient) -> None:
    res = api_client.get("/api/ml/anomalies?metro=chicago&severity=high")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
    assert body["anomalies"][0]["severity"] == "high"


def test_api_ml_history(api_client: TestClient) -> None:
    res = api_client.get("/api/ml/history?metro=chicago&days=30")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 2
    assert body["history"][-1]["city_stress_index"] == "42.5"


def test_api_pulse_enriched(api_client: TestClient) -> None:
    res = api_client.get("/api/pulse?metro=chicago")
    assert res.status_code == 200
    body = res.json()
    assert body["snapshot"]["city_stress_index"] == "42.5"
    assert body["stressComponents"]["transit_load_score"] == "10.0"
    assert "links" in body
    assert body["links"]["stress"].startswith("/api/ml/stress")


def test_openapi_docs(api_client: TestClient) -> None:
    res = api_client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]
    assert "/api/data/{table_slug}" in paths
    assert "/api/ml/stress" in paths
