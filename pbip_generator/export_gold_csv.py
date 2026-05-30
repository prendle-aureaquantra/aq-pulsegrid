"""Export gold/silver Delta tables to CSV for Power BI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pulsegrid.config import DELTA, GENERATED
from pulsegrid.io.delta_writer import read_delta_table


def _gold_root() -> Path:
    return DELTA / "gold"


def _silver_root() -> Path:
    return DELTA / "silver"


def core_export_map() -> dict[str, Path]:
    gold = _gold_root()
    silver = _silver_root()
    return {
        "CityPulseSnapshot": gold / "city_stress_index",
        "TransitAlertSummary": gold / "transit_alert_summary",
        "TransitAlertDetail": gold / "transit_alert_detail",
        "AnomalySignals": gold / "anomaly_signals",
        "WeatherForecastPeriods": silver / "weather_forecast_periods",
    }


def optional_export_map() -> dict[str, Path]:
    gold = _gold_root()
    ml = DELTA / "ml"
    return {
        "PulseHistory": ml / "pulse_history",
        "AirportOpsSnapshot": gold / "airport_ops_snapshot",
        "FredMacroSnapshot": gold / "fred_macro_snapshot",
        "TrendInterestSummary": gold / "trend_interest_summary",
        "HexPulseGrid": gold / "hex_pulse_grid",
        "EventHeatmap": gold / "event_heatmap",
        "CityEventDetail": gold / "event_detail",
        "StreamingTelemetry": gold / "streaming_telemetry",
        "OsmAmenitySummary": gold / "osm_amenity_summary",
        "InfrastructureRiskSnapshot": gold / "infrastructure_risk_snapshot",
        "InfrastructureAssetSummary": gold / "infrastructure_asset_summary",
        "InfrastructureRequestDetail": gold / "infrastructure_request_detail",
    }


PULSE_FRESHNESS_COLUMNS = (
    "data_refreshed_at",
    "last_weather_ingest_at",
    "last_transit_ingest_at",
    "last_civic311_ingest_at",
    "last_airport_ingest_at",
)

PULSE_EXTENDED_COLUMNS = (
    *PULSE_FRESHNESS_COLUMNS,
    "airport_flight_category",
    "airport_visibility_sm",
    "airport_ops_stress",
    "active_airport_stations",
    "airport_stations_summary",
    "trend_avg_interest",
    "fred_series_count",
    "infrastructure_failure_risk",
    "infrastructure_fatigue_risk",
    "bridge_risk_score",
    "road_surface_risk_score",
    "open_infrastructure_requests",
    "infrastructure_summary",
)


def _merge_pulse_extensions(df: pd.DataFrame, city_slug: str) -> pd.DataFrame:
    """Join ML stress index with extended gold fields from city_pulse_snapshot."""
    pulse_path = _gold_root() / "city_pulse_snapshot"
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
    for table, delta_path in {**core_export_map(), **optional_export_map()}.items():
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
