"""Parse bronze JSON into row dicts for Spark silver tables."""

from __future__ import annotations

import json
from pathlib import Path

from pulsegrid.config import BRONZE, ROOT

REF_DIR = ROOT / "datasets" / "reference"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _headline_category(headline: str) -> str:
    h = headline.lower()
    if "reroute" in h:
        return "reroute"
    if "bus stop" in h or "stop change" in h:
        return "stop_change"
    if "delay" in h or "slow" in h:
        return "delay"
    if "elevator" in h or "escalator" in h:
        return "accessibility"
    if "station" in h:
        return "station"
    return "other"


def load_neighborhood_keywords() -> list[tuple[str, str]]:
    from pulsegrid.geo.transit_neighborhood import _read_keywords_csv

    path = REF_DIR / "chicago_neighborhood_keywords.csv"
    return list(_read_keywords_csv(path))


def parse_cta_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    return parse_transit_bronze(paths, city)


def parse_transit_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    from pulsegrid.geo.transit_neighborhood import resolve_transit_alert_neighborhood

    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        for alert in doc.get("alerts", []):
            headline = alert.get("headline") or ""
            desc = alert.get("short_description") or ""
            service = alert.get("service") or ""
            rows.append(
                {
                    "city": city,
                    "alert_id": str(alert.get("alert_id", "")),
                    "headline": headline,
                    "short_description": desc,
                    "severity": alert.get("severity") or "",
                    "service": service,
                    "alert_category": _headline_category(headline),
                    "neighborhood_hint": resolve_transit_alert_neighborhood(
                        city=city,
                        headline=headline,
                        short_description=desc,
                        service=service,
                    ),
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_noaa_alerts_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        if doc.get("source") == "meteoalarm_cap":
            continue
        ingested_at = doc.get("fetched_at", "")
        for feature in doc.get("raw", {}).get("features", []):
            props = feature.get("properties") or {}
            rows.append(
                {
                    "city": city,
                    "alert_id": str(props.get("id") or feature.get("id") or ""),
                    "event": props.get("event") or "",
                    "severity": props.get("severity") or "",
                    "urgency": props.get("urgency") or "",
                    "headline": props.get("headline") or "",
                    "area_desc": props.get("areaDesc") or "",
                    "effective": props.get("effective") or "",
                    "expires": props.get("expires") or "",
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_meteoalarm_alerts_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        if doc.get("source") != "meteoalarm_cap":
            continue
        ingested_at = doc.get("fetched_at", "")
        for warn in doc.get("warnings") or []:
            rows.append(
                {
                    "city": city,
                    "alert_id": str(warn.get("alert_id") or ""),
                    "event": warn.get("event") or "",
                    "severity": warn.get("severity") or "",
                    "urgency": warn.get("urgency") or "",
                    "headline": warn.get("headline") or "",
                    "area_desc": warn.get("area_desc") or "",
                    "effective": warn.get("effective") or "",
                    "expires": warn.get("expires") or "",
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_noaa_forecast_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        periods = doc.get("forecast", {}).get("properties", {}).get("periods", [])
        for period in periods:
            pop = period.get("probabilityOfPrecipitation") or {}
            pop_val = pop.get("value") if isinstance(pop, dict) else 0
            rows.append(
                {
                    "city": city,
                    "period_number": int(period.get("number") or 0),
                    "period_name": period.get("name") or "",
                    "start_time": period.get("startTime") or "",
                    "end_time": period.get("endTime") or "",
                    "is_daytime": bool(period.get("isDaytime")),
                    "temperature_f": int(period.get("temperature") or 0),
                    "precip_pct": int(pop_val or 0),
                    "short_forecast": period.get("shortForecast") or "",
                    "wind_speed": period.get("windSpeed") or "",
                    "wind_direction": period.get("windDirection") or "",
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def bronze_glob(city: str, source: str, pattern: str) -> list[Path]:
    base = BRONZE / city / source
    if not base.is_dir():
        return []
    return sorted(base.glob(pattern))


def parse_events_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        for rec in doc.get("records") or []:
            name = (
                rec.get("event_name")
                or rec.get("application_name")
                or rec.get("name")
                or rec.get("eventtype")
                or "Event"
            )
            start = (
                rec.get("start_date")
                or rec.get("starttime")
                or rec.get("startdatetime")
                or ""
            )
            end = (
                rec.get("end_date")
                or rec.get("endtime")
                or rec.get("enddatetime")
                or ""
            )
            loc = (
                rec.get("street_address")
                or rec.get("location")
                or rec.get("address")
                or ""
            )
            category = (
                rec.get("event_type")
                or rec.get("eventtype")
                or rec.get("category")
                or "general"
            )
            neighborhood = (
                rec.get("community_area")
                or rec.get("neighborhood")
                or rec.get("borough")
                or ""
            )
            rows.append(
                {
                    "city": city,
                    "event_id": str(
                        rec.get("id")
                        or rec.get("eventid")
                        or rec.get("permit_")
                        or f"{name}-{start}"
                    ),
                    "event_name": str(name),
                    "event_category": str(category),
                    "neighborhood_hint": str(neighborhood),
                    "location": str(loc),
                    "start_date": str(start),
                    "end_date": str(end),
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_civic311_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        if doc.get("source") not in ("socrata_311", "arcgis_311", "carto_311"):
            continue
        ingested_at = doc.get("fetched_at", "")
        field_map = doc.get("field_map") or {}
        type_field = field_map.get("type_field") or "sr_type"
        status_field = field_map.get("status_field") or "status"
        date_field = field_map.get("date_field") or "created_date"
        for rec in doc.get("records") or []:
            req_type = (
                rec.get(type_field)
                or rec.get("complaint_type")
                or rec.get("requesttype")
                or rec.get("sr_type")
                or "other"
            )
            descriptor = str(
                rec.get("descriptor")
                or rec.get("description")
                or rec.get("short_description")
                or rec.get("subject")
                or ""
            )
            rows.append(
                {
                    "city": city,
                    "request_id": str(
                        rec.get("sr_number")
                        or rec.get("unique_key")
                        or rec.get("case_enquiry_id")
                        or rec.get("srnumber")
                        or rec.get("CaseNumber")
                        or rec.get("CaseNumber365")
                        or rec.get("service_request_id")
                        or rec.get("id")
                        or f"{req_type}-{rec.get(date_field, '')}"
                    ),
                    "request_type": str(req_type),
                    "descriptor": descriptor,
                    "status": str(rec.get(status_field) or rec.get("status") or ""),
                    "created_date": str(rec.get(date_field) or ""),
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    from pulsegrid.infrastructure_risk import enrich_civic311_rows

    return enrich_civic311_rows(rows)


def parse_osm_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        for poi in doc.get("pois") or []:
            rows.append(
                {
                    "city": city,
                    "osm_id": str(poi.get("osm_id") or ""),
                    "amenity": str(poi.get("amenity") or ""),
                    "name": str(poi.get("name") or ""),
                    "lat": poi.get("lat"),
                    "lon": poi.get("lon"),
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_airport_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        raw = doc.get("raw") or {}
        ingested_at = doc.get("fetched_at", "")
        temp_c = raw.get("temp") or raw.get("tempC")
        if temp_c is None and raw.get("tempF") is not None:
            temp_c = (float(raw["tempF"]) - 32) * 5 / 9
        rows.append(
            {
                "city": city,
                "station": doc.get("station") or raw.get("icaoId") or "",
                "observation_time": raw.get("obsTime") or raw.get("reportTime") or "",
                "flight_category": raw.get("fltCat") or raw.get("flightCategory") or "",
                "visibility_sm": _safe_float(raw.get("visib") or raw.get("visibility")),
                "wind_speed_kt": _safe_float(raw.get("wspd") or raw.get("windSpeedKt")),
                "temperature_c": _safe_float(temp_c),
                "altimeter_inhg": _safe_float(raw.get("altim") or raw.get("altimeter")),
                "raw_ob": raw.get("rawOb") or raw.get("rawText") or "",
                "ingested_at": ingested_at,
                "bronze_file": path.name,
            }
        )
    return rows


def parse_fred_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        series_id = doc.get("series_id", "")
        for obs in doc.get("raw", {}).get("observations", []):
            val = obs.get("value")
            if val in (".", None, ""):
                continue
            rows.append(
                {
                    "city": city,
                    "series_id": series_id,
                    "series_label": doc.get("series_label") or series_id,
                    "observation_date": obs.get("date") or "",
                    "value": float(val),
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_trends_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        keywords = doc.get("keywords") or []
        for rec in doc.get("interest_over_time") or []:
            if rec.get("isPartial"):
                continue
            for kw in keywords:
                if kw not in rec:
                    continue
                rows.append(
                    {
                        "city": city,
                        "keyword": kw,
                        "observation_date": str(rec.get("date", "")),
                        "interest_index": int(rec.get(kw) or 0),
                        "ingested_at": ingested_at,
                        "bronze_file": path.name,
                    }
                )
    return rows


def _safe_float(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def parse_open_meteo_forecast_bronze(
    paths: list[Path], city: str = "chicago"
) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        hourly = doc.get("forecast", {}).get("hourly") or {}
        times = hourly.get("time") or []
        temps = hourly.get("temperature_2m") or []
        precips = hourly.get("precipitation_probability") or []
        for i, start in enumerate(times[:24]):
            rows.append(
                {
                    "city": city,
                    "period_number": i + 1,
                    "period_name": f"H+{i + 1}",
                    "start_time": start,
                    "end_time": start,
                    "is_daytime": True,
                    "temperature_f": int((temps[i] if i < len(temps) else 0) * 9 / 5 + 32),
                    "precip_pct": int(precips[i] if i < len(precips) else 0),
                    "short_forecast": "Open-Meteo hourly",
                    "wind_speed": "",
                    "wind_direction": "",
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_opensky_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        rows.append(
            {
                "city": city,
                "snapshot_at": doc.get("fetched_at", ""),
                "aircraft_count": int(doc.get("aircraft_count") or 0),
                "ingested_at": doc.get("fetched_at", ""),
                "bronze_file": path.name,
            }
        )
    return rows


def parse_usgs_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        for feature in doc.get("raw", {}).get("features", []):
            props = feature.get("properties") or {}
            rows.append(
                {
                    "city": city,
                    "event_id": feature.get("id", ""),
                    "magnitude": _safe_float(props.get("mag")),
                    "place": props.get("place") or "",
                    "event_time": props.get("time"),
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_air_quality_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        rows.append(
            {
                "city": city,
                "snapshot_at": doc.get("fetched_at", ""),
                "us_aqi": _safe_float(doc.get("latest_us_aqi")),
                "pm25": _safe_float(doc.get("latest_pm25")),
                "ingested_at": doc.get("fetched_at", ""),
                "bronze_file": path.name,
            }
        )
    return rows

