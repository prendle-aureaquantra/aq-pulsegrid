"""USGS earthquake feed near metro — bronze JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, http_user_agent
from pulsegrid.metros import MetroConfig

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"


def fetch_usgs_near_metro(metro: MetroConfig, *, radius_km: int = 500) -> dict:
    resp = requests.get(
        USGS_URL,
        params={
            "format": "geojson",
            "latitude": metro.lat,
            "longitude": metro.lon,
            "maxradiuskm": radius_km,
            "limit": 50,
            "orderby": "time",
        },
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()


def ingest_usgs(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    base = out_dir or BRONZE / metro.slug / "usgs"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw = fetch_usgs_near_metro(metro)
    features = raw.get("features") or []
    payload = {
        "source": "usgs_earthquakes",
        "city": metro.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "event_count": len(features),
        "raw": raw,
    }
    path = base / f"quakes_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [path]
