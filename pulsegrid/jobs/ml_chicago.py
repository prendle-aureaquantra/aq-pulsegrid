"""ML scoring + anomaly detection — Chicago."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pulsegrid.config import DELTA, get_city
from pulsegrid.io.delta_writer import (
    append_delta_table,
    read_delta_table,
    write_delta_table,
)
from pulsegrid.ml.anomaly import detect_anomalies, detect_neighborhood_spikes
from pulsegrid.ml.city_stress import stress_from_frames
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
    city = get_city(city_slug)
    snapshot_at = datetime.now(timezone.utc).isoformat()
    written: dict[str, Path] = {}

    transit = _read_silver("transit_alerts")
    weather = _read_silver("weather_alerts")
    forecast = _read_silver("weather_forecast_periods")
    history = _read_history()

    metrics = stress_from_frames(transit, weather, forecast, city.slug)
    metrics["city"] = city.slug
    metrics["snapshot_at"] = snapshot_at

    written["city_stress_index"] = write_delta_table(
        [metrics], GOLD_ROOT / "city_stress_index"
    )

    # Keep legacy snapshot table aligned for downstream consumers
    legacy = {
        "city": city.slug,
        "snapshot_at": snapshot_at,
        "active_cta_alerts": metrics["active_cta_alerts"],
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
                    "trend_avg_interest",
                    "fred_series_count",
                ):
                    if key in latest.index and pd.notna(latest[key]):
                        legacy[key] = latest[key]
    written["city_pulse_snapshot"] = write_delta_table(
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
    if not anomaly_rows:
        anomaly_rows = [
            {
                "city": city.slug,
                "snapshot_at": snapshot_at,
                "signal_type": "none",
                "metric": "n/a",
                "observed": 0,
                "baseline": 0,
                "z_score": 0,
                "severity": "low",
                "message": "No anomalies detected",
            }
        ]
    written["anomaly_signals"] = write_delta_table(
        anomaly_rows,
        GOLD_ROOT / "anomaly_signals",
    )

    history_row = {k: metrics[k] for k in metrics if k not in ("city", "snapshot_at")}
    history_row.update({"city": city.slug, "snapshot_at": snapshot_at})
    written["pulse_history"] = append_delta_table([history_row], ML_ROOT / "pulse_history")

    written["semantic_model_metadata"] = write_semantic_metadata(city_slug)
    return written


def main() -> int:
    paths = run_ml("chicago")
    for name, path in paths.items():
        print(f"  ml.{name} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
