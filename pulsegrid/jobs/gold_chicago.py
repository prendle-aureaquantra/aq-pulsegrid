"""Gold KPI tables from silver Delta."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from pulsegrid.config import DELTA, get_city
from pulsegrid.geo.hex_grid import aggregate_transit_by_hex
from pulsegrid.io.delta_writer import read_delta_table, use_spark_engine, write_delta_table

GOLD_ROOT = DELTA / "gold"
SILVER_ROOT = DELTA / "silver"


def _read_silver_pandas(table: str) -> pd.DataFrame | None:
    path = SILVER_ROOT / table
    if not path.exists():
        return None
    return read_delta_table(path)


def _latest_airport_snapshot(airport: pd.DataFrame | None, city: str) -> dict:
    if airport is None or airport.empty:
        return {}
    ac = airport[airport["city"] == city].sort_values("ingested_at", ascending=False)
    if ac.empty:
        return {}
    row = ac.iloc[0]
    vis = row.get("visibility_sm")
    flt = str(row.get("flight_category") or "")
    airport_stress = 0.0
    if vis is not None and float(vis) < 3:
        airport_stress += 5.0
    if flt.upper() in ("IFR", "LIFR"):
        airport_stress += 8.0
    return {
        "station": row.get("station"),
        "flight_category": flt,
        "visibility_sm": vis,
        "wind_speed_kt": row.get("wind_speed_kt"),
        "temperature_c": row.get("temperature_c"),
        "airport_ops_stress": round(airport_stress, 2),
    }


def _fred_macro_rows(fred: pd.DataFrame | None, city: str, snapshot_at: str) -> list[dict]:
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


def _trend_summary_rows(trends: pd.DataFrame | None, city: str, snapshot_at: str) -> list[dict]:
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

    active_cta = 0
    if transit is not None and not transit.empty:
        tc = transit[transit["city"] == city.slug]
        active_cta = len(tc)
        summary = (
            tc.groupby(["city", "alert_category"], as_index=False)
            .size()
            .rename(columns={"size": "alert_count"})
        )
        summary["snapshot_at"] = snapshot_at
        written["transit_alert_summary"] = write_delta_table(
            summary.to_dict("records"), GOLD_ROOT / "transit_alert_summary"
        )
        hex_rows = aggregate_transit_by_hex(tc.to_dict("records"))
        for row in hex_rows:
            row["city"] = city.slug
            row["snapshot_at"] = snapshot_at
        if hex_rows:
            written["hex_pulse_grid"] = write_delta_table(
                hex_rows, GOLD_ROOT / "hex_pulse_grid"
            )

    active_noaa = 0
    if weather_alerts is not None and not weather_alerts.empty:
        active_noaa = len(weather_alerts[weather_alerts["city"] == city.slug])

    avg_precip = 0.0
    if forecast is not None and not forecast.empty:
        fc = forecast[forecast["city"] == city.slug]
        if not fc.empty:
            avg_precip = float(fc["precip_pct"].mean())

    airport_snap = _latest_airport_snapshot(airport, city.slug)
    if airport_snap:
        written["airport_ops_snapshot"] = write_delta_table(
            [{"city": city.slug, "snapshot_at": snapshot_at, **airport_snap}],
            GOLD_ROOT / "airport_ops_snapshot",
        )

    fred_rows = _fred_macro_rows(fred, city.slug, snapshot_at)
    if fred_rows:
        written["fred_macro_snapshot"] = write_delta_table(
            fred_rows, GOLD_ROOT / "fred_macro_snapshot"
        )

    trend_rows = _trend_summary_rows(trends, city.slug, snapshot_at)
    if trend_rows:
        written["trend_interest_summary"] = write_delta_table(
            trend_rows, GOLD_ROOT / "trend_interest_summary"
        )

    trend_avg = (
        round(sum(r["avg_interest"] for r in trend_rows) / len(trend_rows), 2)
        if trend_rows
        else 0.0
    )
    airport_stress = airport_snap.get("airport_ops_stress", 0.0)
    stress = round(
        active_cta * 0.05 + active_noaa * 2.0 + avg_precip * 0.1 + airport_stress, 2
    )
    pulse = [
        {
            "city": city.slug,
            "snapshot_at": snapshot_at,
            "active_cta_alerts": active_cta,
            "active_noaa_alerts": active_noaa,
            "avg_precip_pct_next_periods": avg_precip,
            "city_stress_score": stress,
            "airport_flight_category": airport_snap.get("flight_category", ""),
            "airport_visibility_sm": airport_snap.get("visibility_sm"),
            "trend_avg_interest": trend_avg,
            "fred_series_count": len(fred_rows),
        }
    ]
    written["city_pulse_snapshot"] = write_delta_table(pulse, GOLD_ROOT / "city_pulse_snapshot")
    return written


def main() -> int:
    paths = run_gold("chicago")
    for name, path in paths.items():
        print(f"  gold.{name} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
