"""Open-Meteo forecast for non-US metros — bronze JSON (live API only, no synthetic alerts)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, http_user_agent
from pulsegrid.metros import MetroConfig

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_open_meteo(metro: MetroConfig) -> dict:
    resp = requests.get(
        FORECAST_URL,
        params={
            "latitude": metro.lat,
            "longitude": metro.lon,
            "hourly": "temperature_2m,precipitation_probability,weather_code",
            "forecast_days": 2,
            "timezone": metro.timezone,
        },
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()


def ingest_open_meteo(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    """Landing zone: Open-Meteo hourly forecast JSON only."""
    base = out_dir or BRONZE / metro.slug / "weather"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fetched_at = datetime.now(timezone.utc).isoformat()
    forecast = fetch_open_meteo(metro)
    payload = {
        "source": "open_meteo_forecast",
        "city": metro.slug,
        "fetched_at": fetched_at,
        "forecast": forecast,
    }
    path = base / f"forecast_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [path]
