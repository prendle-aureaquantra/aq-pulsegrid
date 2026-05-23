"""Aviation weather (METAR) for Chicago O'Hare — bronze JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent

KORD = "KORD"


def fetch_metar(station: str = KORD) -> dict:
    url = "https://aviationweather.gov/api/data/metar"
    resp = requests.get(
        url,
        params={"ids": station, "format": "json"},
        headers={"User-Agent": http_user_agent()},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data[0] if isinstance(data, list) and data else data


def ingest_airport(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    base = out_dir or BRONZE / city.slug / "airport"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw = fetch_metar()
    payload = {
        "source": "aviationweather_metar",
        "city": city.slug,
        "station": KORD,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "raw": raw,
    }
    path = base / f"metar_{KORD}_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [path]
