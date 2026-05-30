"""CSV-backed data access for PulseGrid ops APIs."""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path

DATA_DIR = Path(os.getenv("PULSEGRID_DATA_DIR", "data"))
DEFAULT_METRO = (os.getenv("PULSEGRID_CITY") or "chicago").strip().lower()
MAX_PAGE_SIZE = 500
DEFAULT_PAGE_SIZE = 100

# PBIP export table name -> CSV filename (see pbip_generator/export_gold_csv.py)
TABLE_FILES: dict[str, str] = {
    "CityPulseSnapshot": "CityPulseSnapshot.csv",
    "TransitAlertSummary": "TransitAlertSummary.csv",
    "TransitAlertDetail": "TransitAlertDetail.csv",
    "AnomalySignals": "AnomalySignals.csv",
    "WeatherForecastPeriods": "WeatherForecastPeriods.csv",
    "AirportOpsSnapshot": "AirportOpsSnapshot.csv",
    "FredMacroSnapshot": "FredMacroSnapshot.csv",
    "TrendInterestSummary": "TrendInterestSummary.csv",
    "HexPulseGrid": "HexPulseGrid.csv",
    "EventHeatmap": "EventHeatmap.csv",
    "CityEventDetail": "CityEventDetail.csv",
    "StreamingTelemetry": "StreamingTelemetry.csv",
    "OsmAmenitySummary": "OsmAmenitySummary.csv",
    "InfrastructureRiskSnapshot": "InfrastructureRiskSnapshot.csv",
    "InfrastructureAssetSummary": "InfrastructureAssetSummary.csv",
    "InfrastructureRequestDetail": "InfrastructureRequestDetail.csv",
    "PulseHistory": "PulseHistory.csv",
    "DimMetro": "DimMetro.csv",
    "DimAirport": "DimAirport.csv",
}

DOMAIN_TABLES: dict[str, list[str]] = {
    "weather": ["WeatherForecastPeriods"],
    "infrastructure": [
        "InfrastructureRiskSnapshot",
        "InfrastructureAssetSummary",
        "InfrastructureRequestDetail",
    ],
    "events": ["EventHeatmap", "CityEventDetail"],
    "airport": ["AirportOpsSnapshot"],
}

STRESS_COMPONENT_FIELDS = (
    "city_stress_index",
    "transit_load_score",
    "weather_risk_score",
    "precip_risk_score",
    "disruption_ratio_score",
    "active_transit_alerts",
    "active_noaa_alerts",
    "active_civic311_requests",
    "avg_precip_pct_next_periods",
    "reroute_count",
    "delay_count",
    "infrastructure_failure_risk",
    "infrastructure_fatigue_risk",
    "bridge_risk_score",
    "road_surface_risk_score",
    "open_infrastructure_requests",
    "mllib_z_score",
)

FRESHNESS_FIELDS = (
    "data_refreshed_at",
    "last_weather_ingest_at",
    "last_transit_ingest_at",
    "last_civic311_ingest_at",
    "last_airport_ingest_at",
)


def table_slug(table_name: str) -> str:
    """CityPulseSnapshot -> city-pulse-snapshot."""
    return re.sub(r"(?<!^)(?=[A-Z])", "-", table_name).lower()


_SLUG_TO_TABLE = {table_slug(name): name for name in TABLE_FILES}


def resolve_table(slug: str) -> str | None:
    key = slug.strip().lower().replace("_", "-")
    if key in _SLUG_TO_TABLE:
        return _SLUG_TO_TABLE[key]
    for name in TABLE_FILES:
        if name.lower() == key.replace("-", ""):
            return name
    return None


def list_tables(*, available_only: bool = True) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for name, filename in sorted(TABLE_FILES.items()):
        path = DATA_DIR / filename
        if available_only and not path.is_file():
            continue
        rows.append(
            {
                "table": name,
                "slug": table_slug(name),
                "file": filename,
                "endpoint": f"/api/data/{table_slug(name)}",
            }
        )
    return rows


def read_csv_rows(filename: str) -> list[dict[str, str]]:
    path = DATA_DIR / filename
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def filter_city(rows: list[dict[str, str]], metro: str) -> list[dict[str, str]]:
    if not rows:
        return rows
    if "city" not in rows[0]:
        return rows
    slug = metro.strip().lower()
    return [r for r in rows if r.get("city", "").lower() == slug]


def paginate(
    rows: list[dict[str, str]], *, limit: int, offset: int
) -> tuple[list[dict[str, str]], int]:
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    offset = max(0, offset)
    total = len(rows)
    return rows[offset : offset + limit], total


def query_table(
    table_name: str,
    *,
    metro: str = "",
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict[str, object]:
    filename = TABLE_FILES.get(table_name)
    if not filename:
        return {"error": f"Unknown table: {table_name}"}
    rows = read_csv_rows(filename)
    slug = (metro or DEFAULT_METRO).strip().lower()
    filtered = filter_city(rows, slug) if slug else rows
    page, total = paginate(filtered, limit=limit, offset=offset)
    return {
        "table": table_name,
        "slug": table_slug(table_name),
        "metro": slug or None,
        "total": total,
        "limit": min(max(1, limit), MAX_PAGE_SIZE),
        "offset": max(0, offset),
        "rows": page,
    }


def query_domain(domain: str, *, metro: str = "", limit: int = DEFAULT_PAGE_SIZE) -> dict:
    tables = DOMAIN_TABLES.get(domain)
    if not tables:
        return {"error": f"Unknown domain: {domain}"}
    slug = (metro or DEFAULT_METRO).strip().lower()
    payload: dict[str, object] = {"domain": domain, "metro": slug, "tables": {}}
    for table in tables:
        result = query_table(table, metro=slug, limit=limit, offset=0)
        payload["tables"][table] = result.get("rows", [])
    return payload


def latest_snapshot(metro: str) -> dict[str, str] | None:
    rows = filter_city(read_csv_rows("CityPulseSnapshot.csv"), metro)
    return rows[-1] if rows else None


def pick_fields(row: dict[str, str] | None, fields: tuple[str, ...]) -> dict[str, str | None]:
    if not row:
        return {f: None for f in fields}
    return {f: row.get(f) for f in fields}
