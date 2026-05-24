"""Gold KPI tables from silver Delta (all metros — legacy module name)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pulsegrid.airport_ops import (
    latest_airport_ops_rows,
    rollup_airport_for_city_pulse,
)
from pulsegrid.config import DELTA, get_city
from pulsegrid.geo.hex_grid import aggregate_transit_by_hex
from pulsegrid.metro_feeds import airport_station_labels
from pulsegrid.io.delta_writer import (
    merge_delta_table,
    read_delta_table,
    use_spark_engine,
)
from pulsegrid.jobs.gold_platform import (
    event_detail_rows,
    event_heatmap_rows,
    osm_amenity_summary_rows,
    streaming_telemetry_rows,
    transit_alert_detail_rows,
)
from pulsegrid.ingest.bronze_freshness import latest_bronze_times
from pulsegrid.infrastructure_risk import (
    infrastructure_detail_rows,
    infrastructure_risk_rollup,
    infrastructure_summary_by_asset,
)

GOLD_ROOT = DELTA / "gold"
SILVER_ROOT = DELTA / "silver"


def _read_silver_pandas(table: str) -> pd.DataFrame | None:
    path = SILVER_ROOT / table
    if not path.exists():
        return None
    return read_delta_table(path)


def _fred_macro_rows(
    fred: pd.DataFrame | None, city: str, snapshot_at: str
) -> list[dict]:
    if fred is None or fred.empty:
        return []
    fc = fred[fred["city"] == city]
    rows: list[dict] = []
    for series_id, grp in fc.groupby("series_id"):
        latest = grp.sort_values("observation_date", ascending=False).iloc[0]
        rows.append(
            {
                "city": city,
                "series_id": series_id,
                "series_label": latest.get("series_label") or series_id,
                "latest_value": float(latest["value"]),
                "observation_date": latest["observation_date"],
                "snapshot_at": snapshot_at,
            }
        )
    return rows


def _trend_summary_rows(
    trends: pd.DataFrame | None, city: str, snapshot_at: str
) -> list[dict]:
    if trends is None or trends.empty:
        return []
    tc = trends[trends["city"] == city]
    rows: list[dict] = []
    for keyword, grp in tc.groupby("keyword"):
        rows.append(
            {
                "city": city,
                "keyword": keyword,
                "avg_interest": round(float(grp["interest_index"].mean()), 2),
                "max_interest": int(grp["interest_index"].max()),
                "observation_count": len(grp),
                "snapshot_at": snapshot_at,
            }
        )
    return rows


def run_gold(city_slug: str = "chicago") -> dict[str, Path]:
    city = get_city(city_slug)
    snapshot_at = datetime.now(timezone.utc).isoformat()
    written: dict[str, Path] = {}

    if use_spark_engine():
        from pulsegrid.jobs import gold_chicago_spark

        return gold_chicago_spark.run_gold_spark(city_slug)

    transit = _read_silver_pandas("transit_alerts")
    weather_alerts = _read_silver_pandas("weather_alerts")
    forecast = _read_silver_pandas("weather_forecast_periods")
    airport = _read_silver_pandas("airport_observations")
    fred = _read_silver_pandas("fred_observations")
    trends = _read_silver_pandas("trend_interest")
    events = _read_silver_pandas("city_events")
    osm = _read_silver_pandas("osm_pois")
    civic311 = _read_silver_pandas("civic311_requests")

    active_transit = 0
    if transit is not None and not transit.empty:
        tc = transit[transit["city"] == city.slug]
        active_transit = len(tc)
        summary = (
            tc.groupby(["city", "alert_category"], as_index=False)
            .size()
            .rename(columns={"size": "alert_count"})
        )
        summary["snapshot_at"] = snapshot_at
        written["transit_alert_summary"] = merge_delta_table(
            summary.to_dict("records"), GOLD_ROOT / "transit_alert_summary"
        )
        hex_rows = aggregate_transit_by_hex(tc.to_dict("records"))
        for row in hex_rows:
            row["city"] = city.slug
            row["snapshot_at"] = snapshot_at
        if hex_rows:
            written["hex_pulse_grid"] = merge_delta_table(
                hex_rows, GOLD_ROOT / "hex_pulse_grid"
            )
        detail_rows = transit_alert_detail_rows(transit, city.slug, snapshot_at)
        if detail_rows:
            written["transit_alert_detail"] = merge_delta_table(
                detail_rows, GOLD_ROOT / "transit_alert_detail"
            )

    active_noaa = 0
    if weather_alerts is not None and not weather_alerts.empty:
        active_noaa = len(weather_alerts[weather_alerts["city"] == city.slug])

    avg_precip = 0.0
    if forecast is not None and not forecast.empty:
        fc = forecast[forecast["city"] == city.slug]
        if not fc.empty:
            avg_precip = float(
                pd.to_numeric(fc["precip_pct"], errors="coerce").mean() or 0.0
            )

    airport_station_rows = latest_airport_ops_rows(
        airport,
        city.slug,
        snapshot_at,
        station_names=airport_station_labels(city.slug),
    )
    airport_rollup = rollup_airport_for_city_pulse(airport_station_rows)
    if airport_station_rows:
        written["airport_ops_snapshot"] = merge_delta_table(
            airport_station_rows,
            GOLD_ROOT / "airport_ops_snapshot",
        )

    fred_rows = _fred_macro_rows(fred, city.slug, snapshot_at)
    if fred_rows:
        written["fred_macro_snapshot"] = merge_delta_table(
            fred_rows, GOLD_ROOT / "fred_macro_snapshot"
        )

    trend_rows = _trend_summary_rows(trends, city.slug, snapshot_at)
    if trend_rows:
        written["trend_interest_summary"] = merge_delta_table(
            trend_rows, GOLD_ROOT / "trend_interest_summary"
        )

    event_rows = event_heatmap_rows(events, city.slug, snapshot_at)
    if event_rows:
        written["event_heatmap"] = merge_delta_table(
            event_rows, GOLD_ROOT / "event_heatmap"
        )
    detail_rows = event_detail_rows(events, city.slug, snapshot_at)
    if detail_rows:
        written["event_detail"] = merge_delta_table(
            detail_rows, GOLD_ROOT / "event_detail"
        )

    osm_rows = osm_amenity_summary_rows(osm, city.slug, snapshot_at)
    if osm_rows:
        written["osm_amenity_summary"] = merge_delta_table(
            osm_rows, GOLD_ROOT / "osm_amenity_summary"
        )

    civic311_count = 0
    infra_rollup: dict = {}
    if civic311 is not None and not civic311.empty:
        cc = civic311[civic311["city"] == city.slug]
        civic311_count = len(cc)
        if not cc.empty:
            summary = (
                cc.groupby(["city", "request_type"], as_index=False)
                .size()
                .rename(columns={"size": "request_count"})
            )
            summary["snapshot_at"] = snapshot_at
            written["civic311_summary"] = merge_delta_table(
                summary.to_dict("records"), GOLD_ROOT / "civic311_summary"
            )
        infra_rollup = infrastructure_risk_rollup(
            civic311, city.slug, snapshot_at, avg_precip_pct=avg_precip
        )
        written["infrastructure_risk_snapshot"] = merge_delta_table(
            [infra_rollup], GOLD_ROOT / "infrastructure_risk_snapshot"
        )
        asset_rows = infrastructure_summary_by_asset(
            civic311, city.slug, snapshot_at
        )
        if asset_rows:
            written["infrastructure_asset_summary"] = merge_delta_table(
                asset_rows, GOLD_ROOT / "infrastructure_asset_summary"
            )
        detail = infrastructure_detail_rows(civic311, city.slug, snapshot_at)
        if detail:
            written["infrastructure_request_detail"] = merge_delta_table(
                detail, GOLD_ROOT / "infrastructure_request_detail"
            )

    stream_rows = streaming_telemetry_rows(city.slug, snapshot_at)
    if stream_rows:
        written["streaming_telemetry"] = merge_delta_table(
            stream_rows, GOLD_ROOT / "streaming_telemetry"
        )

    event_count = (
        len(events[events["city"] == city.slug])
        if events is not None and not events.empty
        else 0
    )
    trend_avg = (
        round(sum(r["avg_interest"] for r in trend_rows) / len(trend_rows), 2)
        if trend_rows
        else 0.0
    )
    airport_stress = float(airport_rollup.get("airport_ops_stress") or 0.0)
    infra_failure = float(infra_rollup.get("infrastructure_failure_risk") or 0.0)
    infra_fatigue = float(infra_rollup.get("infrastructure_fatigue_risk") or 0.0)
    infra_stress = round(min(20.0, infra_failure * 0.12 + infra_fatigue * 0.06), 2)
    event_stress = min(10.0, event_count * 0.5)
    stress = round(
        active_transit * 0.05
        + active_noaa * 2.0
        + avg_precip * 0.1
        + airport_stress
        + infra_stress
        + event_stress,
        2,
    )
    freshness = latest_bronze_times(city.slug)
    pulse = [
        {
            "city": city.slug,
            "snapshot_at": snapshot_at,
            "data_refreshed_at": freshness.get("data_refreshed_at", snapshot_at),
            "last_weather_ingest_at": freshness.get("weather", ""),
            "last_transit_ingest_at": freshness.get("transit", ""),
            "last_civic311_ingest_at": freshness.get("civic311", ""),
            "last_airport_ingest_at": freshness.get("airport", ""),
            "active_transit_alerts": active_transit,
            "active_noaa_alerts": active_noaa,
            "avg_precip_pct_next_periods": avg_precip,
            "city_stress_score": stress,
            "airport_flight_category": airport_rollup.get("airport_flight_category", ""),
            "airport_visibility_sm": airport_rollup.get("airport_visibility_sm"),
            "airport_ops_stress": airport_stress,
            "active_airport_stations": airport_rollup.get("active_airport_stations", 0),
            "airport_stations_summary": airport_rollup.get("airport_stations_summary", ""),
            "trend_avg_interest": trend_avg,
            "fred_series_count": len(fred_rows),
            "active_events": event_count,
            "active_civic311_requests": civic311_count,
            "infrastructure_failure_risk": infra_failure,
            "infrastructure_fatigue_risk": infra_fatigue,
            "bridge_risk_score": float(infra_rollup.get("bridge_risk_score") or 0),
            "road_surface_risk_score": float(
                infra_rollup.get("road_surface_risk_score") or 0
            ),
            "open_infrastructure_requests": int(
                infra_rollup.get("open_infrastructure_requests") or 0
            ),
            "infrastructure_summary": infra_rollup.get("infrastructure_summary", ""),
        }
    ]
    written["city_pulse_snapshot"] = merge_delta_table(
        pulse, GOLD_ROOT / "city_pulse_snapshot"
    )
    return written


def main() -> int:
    paths = run_gold("chicago")
    for name, path in paths.items():
        print(f"  gold.{name} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
