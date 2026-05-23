"""NOAA / NWS weather alerts and forecast points."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent


def _get(url: str) -> dict | list:
    resp = requests.get(
        url,
        headers={"User-Agent": http_user_agent(), "Accept": "application/geo+json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_active_alerts(city: CityConfig) -> dict:
    """NWS active alerts for state (no API key required)."""
    url = f"https://api.weather.gov/alerts/active?area={city.noaa_area}"
    payload = _get(url)
    return {
        "source": "noaa_nws_alerts",
        "city": city.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "area": city.noaa_area,
        "feature_count": len(payload.get("features", [])),
        "raw": payload,
    }


def fetch_gridpoint_forecast(city: CityConfig) -> dict:
    """Resolve lat/lon → gridpoint → forecast."""
    points_url = f"https://api.weather.gov/points/{city.lat},{city.lon}"
    points = _get(points_url)
    forecast_url = points.get("properties", {}).get("forecast")
    forecast = _get(forecast_url) if forecast_url else {}
    return {
        "source": "noaa_nws_forecast",
        "city": city.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "points": points,
        "forecast": forecast,
    }


def ingest_noaa(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    """Write NOAA bronze JSON files; return paths written."""
    base = (out_dir or BRONZE / city.slug / "noaa")
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    written: list[Path] = []

    for name, payload in (
        ("alerts", fetch_active_alerts(city)),
        ("forecast", fetch_gridpoint_forecast(city)),
    ):
        path = base / f"{name}_{ts}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written.append(path)
    return written
