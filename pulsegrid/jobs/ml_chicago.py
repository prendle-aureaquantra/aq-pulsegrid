"""ML scoring + anomaly detection — Chicago."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pulsegrid.config import DELTA, get_city
from pulsegrid.io.delta_writer import (
    append_delta_table,
    merge_delta_table,
    read_delta_table,
    write_delta_table,
)
from pulsegrid.ml.anomaly import detect_anomalies, detect_neighborhood_spikes
from pulsegrid.ml.city_stress import stress_from_frames
from pulsegrid.ml.spark_mllib import enrich_metrics_with_mllib
from pulsegrid.ml.semantic_metadata import write_semantic_metadata

GOLD_ROOT = DELTA / "gold"
SILVER_ROOT = DELTA / "silver"
ML_ROOT = DELTA / "ml"


def _read_silver(table: str) -> pd.DataFrame | None:
    path = SILVER_ROOT / table
    if not path.exists():
        return None
    return read_delta_table(path)


def _read_history() -> pd.DataFrame | None:
    path = ML_ROOT / "pulse_history"
    if not path.exists():
        return None
    return read_delta_table(path)


def run_ml(city_slug: str = "chicago") -> dict[str, Path]:
    from pulsegrid.io.delta_writer import use_spark_engine

    if use_spark_engine():
        from pulsegrid.jobs.ml_spark import run_ml_spark

        return run_ml_spark(city_slug)

    city = get_city(city_slug)
    snapshot_at = datetime.now(timezone.utc).isoformat()
    written: dict[str, Path] = {}

    transit = _read_silver("transit_alerts")
    weather = _read_silver("weather_alerts")
    forecast = _read_silver("weather_forecast_periods")
    civic311 = _read_silver("civic311_requests")
    history = _read_history()

    from pulsegrid.infrastructure_risk import infrastructure_risk_rollup

    avg_precip = 0.0
    if forecast is not None and not forecast.empty:
        fc = forecast[forecast["city"] == city.slug]
        if not fc.empty and "precip_pct" in fc.columns:
            avg_precip = float(fc["precip_pct"].mean())
    infra = infrastructure_risk_rollup(
        civic311, city.slug, snapshot_at, avg_precip_pct=avg_precip
    )
    metrics = stress_from_frames(
        transit,
        weather,
        forecast,
        city.slug,
        civic311,
        infrastructure_rollup=infra,
    )
    metrics = enrich_metrics_with_mllib(metrics)
    metrics["city"] = city.slug
    metrics["snapshot_at"] = snapshot_at

    written["city_stress_index"] = merge_delta_table(
        [metrics], GOLD_ROOT / "city_stress_index"
    )

    # Keep legacy snapshot table aligned for downstream consumers
    legacy = {
        "city": city.slug,
        "snapshot_at": snapshot_at,
        "active_transit_alerts": metrics["active_transit_alerts"],
        "active_noaa_alerts": metrics["active_noaa_alerts"],
        "avg_precip_pct_next_periods": metrics["avg_precip_pct_next_periods"],
        "city_stress_score": metrics["city_stress_index"],
    }
    pulse_path = GOLD_ROOT / "city_pulse_snapshot"
    if pulse_path.exists():
        pulse_df = read_delta_table(pulse_path)
        if pulse_df is not None and not pulse_df.empty:
            pc = pulse_df[pulse_df["city"] == city.slug]
            if not pc.empty:
                latest = pc.sort_values("snapshot_at", ascending=False).iloc[0]
                for key in (
                    "airport_flight_category",
                    "airport_visibility_sm",
                    "airport_ops_stress",
                    "active_airport_stations",
                    "airport_stations_summary",
                    "infrastructure_failure_risk",
                    "infrastructure_fatigue_risk",
                    "bridge_risk_score",
                    "road_surface_risk_score",
                    "open_infrastructure_requests",
                    "infrastructure_summary",
                    "trend_avg_interest",
                    "fred_series_count",
                ):
                    if key in latest.index and pd.notna(latest[key]):
                        legacy[key] = latest[key]
    written["city_pulse_snapshot"] = merge_delta_table(
        [legacy], GOLD_ROOT / "city_pulse_snapshot"
    )

    anomaly_rows = [
        s.to_row(city.slug, snapshot_at)
        for s in detect_anomalies(
            city=city.slug,
            snapshot_at=snapshot_at,
            metrics=metrics,
            history=history,
        )
    ]
    anomaly_rows.extend(detect_neighborhood_spikes(transit, city.slug, snapshot_at))
    if anomaly_rows:
        written["anomaly_signals"] = merge_delta_table(
            anomaly_rows,
            GOLD_ROOT / "anomaly_signals",
        )

    history_row = {k: metrics[k] for k in metrics if k not in ("city", "snapshot_at")}
    history_row.update({"city": city.slug, "snapshot_at": snapshot_at})
    written["pulse_history"] = append_delta_table(
        [history_row], ML_ROOT / "pulse_history"
    )

    written["semantic_model_metadata"] = write_semantic_metadata(city_slug)
    return written


def main() -> int:
    paths = run_ml("chicago")
    for name, path in paths.items():
        print(f"  ml.{name} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
