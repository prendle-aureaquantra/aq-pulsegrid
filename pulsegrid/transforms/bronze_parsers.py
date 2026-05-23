"""Parse bronze JSON into row dicts for Spark silver tables."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pulsegrid.config import ROOT

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


def _neighborhood_hint(text: str, keywords: list[tuple[str, str]]) -> str | None:
    lower = text.lower()
    for neighborhood, keyword in keywords:
        if keyword.lower() in lower:
            return neighborhood
    return None


def load_neighborhood_keywords() -> list[tuple[str, str]]:
    path = REF_DIR / "chicago_neighborhood_keywords.csv"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    out: list[tuple[str, str]] = []
    for line in lines[1:]:
        if "," in line:
            n, k = line.split(",", 1)
            out.append((n.strip(), k.strip()))
    return out


def parse_cta_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    keywords = load_neighborhood_keywords()
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
        ingested_at = doc.get("fetched_at", "")
        for alert in doc.get("alerts", []):
            headline = alert.get("headline") or ""
            desc = alert.get("short_description") or ""
            combined = f"{headline} {desc}"
            rows.append(
                {
                    "city": city,
                    "alert_id": str(alert.get("alert_id", "")),
                    "headline": headline,
                    "short_description": desc,
                    "severity": alert.get("severity") or "",
                    "service": alert.get("service") or "",
                    "alert_category": _headline_category(headline),
                    "neighborhood_hint": _neighborhood_hint(combined, keywords) or "",
                    "ingested_at": ingested_at,
                    "bronze_file": path.name,
                }
            )
    return rows


def parse_noaa_alerts_bronze(paths: list[Path], city: str = "chicago") -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        doc = _load_json(path)
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
    base = ROOT / "datasets" / "bronze" / city / source
    if not base.is_dir():
        return []
    return sorted(base.glob(pattern))


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
                "station": doc.get("station") or raw.get("icaoId") or "KORD",
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
