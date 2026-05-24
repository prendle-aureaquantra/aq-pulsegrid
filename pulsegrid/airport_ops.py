"""Airport operations stress scoring and multi-station gold rollups."""

from __future__ import annotations

from typing import Any

import pandas as pd

FLIGHT_CATEGORY_RANK = {"LIFR": 4, "IFR": 3, "MVFR": 2, "VFR": 1}


def ops_stress_from_observation(
    flight_category: str | None, visibility_sm: float | None
) -> float:
    stress = 0.0
    if visibility_sm is not None:
        try:
            if float(visibility_sm) < 3:
                stress += 5.0
        except (TypeError, ValueError):
            pass
    flt = str(flight_category or "").upper()
    if flt in ("IFR", "LIFR"):
        stress += 8.0
    elif flt == "MVFR":
        stress += 3.0
    return round(stress, 2)


def _worst_flight_category(categories: list[str]) -> str:
    best = ""
    rank = 0
    for cat in categories:
        c = str(cat or "").upper()
        r = FLIGHT_CATEGORY_RANK.get(c, 0)
        if r > rank:
            rank = r
            best = c
    return best or (categories[0] if categories else "")


def latest_airport_ops_rows(
    airport: pd.DataFrame | None,
    city: str,
    snapshot_at: str,
    *,
    station_names: dict[str, str] | None = None,
) -> list[dict]:
    """One gold row per METAR station (latest observation each)."""
    if airport is None or airport.empty:
        return []
    ac = airport[airport["city"] == city].copy()
    if ac.empty:
        return []
    ac = ac.sort_values("ingested_at", ascending=False)
    names = station_names or {}
    rows: list[dict] = []
    for station, grp in ac.groupby("station", dropna=False):
        st = str(station or "").strip().upper()
        if not st:
            continue
        row = grp.iloc[0]
        flt = str(row.get("flight_category") or "")
        vis = row.get("visibility_sm")
        stress = ops_stress_from_observation(flt, vis)
        label = names.get(st) or st
        rows.append(
            {
                "city": city,
                "snapshot_at": snapshot_at,
                "station": st,
                "station_label": label,
                "flight_category": flt,
                "visibility_sm": vis,
                "wind_speed_kt": row.get("wind_speed_kt"),
                "temperature_c": row.get("temperature_c"),
                "airport_ops_stress": stress,
            }
        )
    return rows


def rollup_airport_for_city_pulse(station_rows: list[dict]) -> dict[str, Any]:
    """Aggregate multi-airport ops into CityPulseSnapshot airport fields."""
    if not station_rows:
        return {
            "airport_flight_category": "",
            "airport_visibility_sm": None,
            "airport_ops_stress": 0.0,
            "active_airport_stations": 0,
            "airport_stations_summary": "",
        }
    categories = [str(r.get("flight_category") or "") for r in station_rows]
    visibilities = []
    for r in station_rows:
        v = r.get("visibility_sm")
        if v is not None and str(v).strip() != "":
            try:
                visibilities.append(float(v))
            except (TypeError, ValueError):
                pass
    stresses = [float(r.get("airport_ops_stress") or 0) for r in station_rows]
    labels = [
        f"{r.get('station_label') or r.get('station')}: {r.get('flight_category') or '—'}"
        for r in station_rows
    ]
    return {
        "airport_flight_category": _worst_flight_category(categories),
        "airport_visibility_sm": min(visibilities) if visibilities else None,
        "airport_ops_stress": max(stresses) if stresses else 0.0,
        "active_airport_stations": len(station_rows),
        "airport_stations_summary": "; ".join(labels[:6]),
    }
