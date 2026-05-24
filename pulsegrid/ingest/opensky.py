"""OpenSky Network ADS-B states near metro airports — bronze JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, http_user_agent
from pulsegrid.metros import MetroConfig

STATES_URL = "https://openskynetwork.org/api/states/all"


def fetch_opensky_bbox(metro: MetroConfig, *, delta: float = 1.0) -> dict:
    params = {
        "lamin": metro.lat - delta,
        "lomin": metro.lon - delta,
        "lamax": metro.lat + delta,
        "lomax": metro.lon + delta,
    }
    resp = requests.get(
        STATES_URL,
        params=params,
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    resp.raise_for_status()
    data = resp.json()
    states = data.get("states") or []
    return {
        "time": data.get("time"),
        "aircraft_count": len(states),
        "states": states[:200],
        "bbox": params,
    }


def ingest_opensky(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    base = out_dir or BRONZE / metro.slug / "opensky"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot = fetch_opensky_bbox(metro)
    payload = {
        "source": "opensky_states",
        "city": metro.slug,
        "airports": list(metro.airports),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        **snapshot,
    }
    path = base / f"states_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [path]
