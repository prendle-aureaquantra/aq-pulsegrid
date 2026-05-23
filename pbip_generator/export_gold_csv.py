"""Export gold/silver Delta tables to CSV for Power BI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pulsegrid.config import DELTA, GENERATED
from pulsegrid.io.delta_writer import read_delta_table

SILVER = DELTA / "silver"
GOLD = DELTA / "gold"

# PBIP table name -> delta path relative to DELTA
CORE_EXPORT_MAP = {
    "CityPulseSnapshot": GOLD / "city_stress_index",
    "TransitAlertSummary": GOLD / "transit_alert_summary",
    "AnomalySignals": GOLD / "anomaly_signals",
    "WeatherForecastPeriods": SILVER / "weather_forecast_periods",
}

OPTIONAL_EXPORT_MAP = {
    "AirportOpsSnapshot": GOLD / "airport_ops_snapshot",
    "FredMacroSnapshot": GOLD / "fred_macro_snapshot",
    "TrendInterestSummary": GOLD / "trend_interest_summary",
    "HexPulseGrid": GOLD / "hex_pulse_grid",
    "EventHeatmap": GOLD / "event_heatmap",
    "StreamingTelemetry": GOLD / "streaming_telemetry",
    "OsmAmenitySummary": GOLD / "osm_amenity_summary",
}

PULSE_EXTENDED_COLUMNS = (
    "airport_flight_category",
    "airport_visibility_sm",
    "trend_avg_interest",
    "fred_series_count",
)


def _merge_pulse_extensions(df: pd.DataFrame, city_slug: str) -> pd.DataFrame:
    """Join ML stress index with extended gold fields from city_pulse_snapshot."""
    pulse_path = GOLD / "city_pulse_snapshot"
    if not pulse_path.exists():
        for col in PULSE_EXTENDED_COLUMNS:
            if col not in df.columns:
                df[col] = None
        return df
    pulse = read_delta_table(pulse_path)
    if pulse.empty or "city" not in pulse.columns:
        return df
    pulse = pulse[pulse["city"] == city_slug]
    if pulse.empty:
        return df
    latest = pulse.sort_values("snapshot_at", ascending=False).iloc[0]
    for col in PULSE_EXTENDED_COLUMNS:
        df[col] = latest.get(col)
    return df


def export_city_csv(city_slug: str) -> Path:
    data_dir = GENERATED / city_slug / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    for table, delta_path in {**CORE_EXPORT_MAP, **OPTIONAL_EXPORT_MAP}.items():
        if not delta_path.exists():
            continue
        df = read_delta_table(delta_path)
        if df.empty:
            continue
        if "city" in df.columns:
            df = df[df["city"] == city_slug]
        if table == "CityPulseSnapshot":
            df = _merge_pulse_extensions(df, city_slug)
        out = data_dir / f"{table}.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")
    from pbip_generator.studio_catalog import write_studio_catalog_csv

    write_studio_catalog_csv(city_slug)
    return data_dir
