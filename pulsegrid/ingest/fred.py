"""FRED economic indicators (bronze JSON)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent

# Chicago-relevant macro series (national proxies until city-level FRED IDs added)
DEFAULT_SERIES = {
    "UNRATE": "Unemployment rate",
    "CPIAUCSL": "CPI all urban consumers",
    "DGS10": "10-year Treasury yield",
}


def fetch_series(api_key: str, series_id: str, *, limit: int = 24) -> dict:
    url = "https://api.stlouisfed.org/fred/series/observations"
    resp = requests.get(
        url,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        headers={"User-Agent": http_user_agent()},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def ingest_fred(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY not set. Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    base = out_dir or BRONZE / city.slug / "fred"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    written: list[Path] = []
    for series_id, label in DEFAULT_SERIES.items():
        payload = {
            "source": "fred",
            "city": city.slug,
            "series_id": series_id,
            "series_label": label,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "raw": fetch_series(api_key, series_id),
        }
        path = base / f"{series_id}_{ts}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        written.append(path)
    return written
