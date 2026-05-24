"""Air quality (Open-Meteo air-quality API) — bronze JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, http_user_agent
from pulsegrid.metros import MetroConfig

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


def fetch_air_quality(metro: MetroConfig) -> dict:
    resp = requests.get(
        AQ_URL,
        params={
            "latitude": metro.lat,
            "longitude": metro.lon,
            "hourly": "pm10,pm2_5,us_aqi",
            "timezone": metro.timezone,
        },
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()


def ingest_air_quality(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    base = out_dir or BRONZE / metro.slug / "air_quality"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw = fetch_air_quality(metro)
    hourly = raw.get("hourly") or {}
    pm25 = hourly.get("pm2_5") or []
    us_aqi = hourly.get("us_aqi") or []
    latest_aqi = next((v for v in reversed(us_aqi) if v is not None), None)
    payload = {
        "source": "open_meteo_air_quality",
        "city": metro.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "latest_us_aqi": latest_aqi,
        "latest_pm25": next((v for v in reversed(pm25) if v is not None), None),
        "raw": raw,
    }
    path = base / f"aqi_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [path]
