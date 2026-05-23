"""Chicago public events (City open data) — bronze JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent

# Chicago Special Events / festival permits (Socrata)
CHICAGO_EVENTS_URL = "https://data.cityofchicago.org/resource/7jas-7yny.json"


def fetch_events(*, limit: int = 100) -> list[dict]:
    resp = requests.get(
        CHICAGO_EVENTS_URL,
        params={"$limit": limit, "$order": "start_date DESC"},
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def ingest_events(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    base = out_dir or BRONZE / city.slug / "events"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw = fetch_events()
    payload = {
        "source": "chicago_open_data_events",
        "city": city.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "records": raw,
    }
    path = base / f"events_{ts}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return [path]
