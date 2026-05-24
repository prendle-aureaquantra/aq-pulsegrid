"""Aviation weather (METAR) — bronze JSON per station, batched per metro."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent
from pulsegrid.metro_feeds import airport_station_codes, airport_station_labels
from pulsegrid.metros import MetroConfig

METAR_URL = "https://aviationweather.gov/api/data/metar"


def fetch_metar(station: str) -> dict:
    data = fetch_metar_batch((station,))
    return data.get(station.upper(), {})


def fetch_metar_batch(stations: tuple[str, ...]) -> dict[str, dict]:
    """Fetch METAR for one or more ICAO stations (single API call)."""
    codes = [s.strip().upper() for s in stations if s and str(s).strip()]
    if not codes:
        return {}
    resp = requests.get(
        METAR_URL,
        params={"ids": ",".join(codes), "format": "json"},
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    resp.raise_for_status()
    body = resp.json()
    if not isinstance(body, list):
        return {}
    out: dict[str, dict] = {}
    for item in body:
        if not isinstance(item, dict):
            continue
        icao = str(item.get("icaoId") or item.get("station") or "").upper()
        if icao:
            out[icao] = item
    return out


def ingest_airport(
    city: CityConfig,
    *,
    stations: tuple[str, ...] | None = None,
    out_dir: Path | None = None,
) -> list[Path]:
    if stations is None:
        stations = airport_station_codes(city.slug)
    if not stations:
        return []
    labels = airport_station_labels(city.slug)
    base = out_dir or BRONZE / city.slug / "airport"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fetched_at = datetime.now(timezone.utc).isoformat()
    paths: list[Path] = []
    try:
        batch = fetch_metar_batch(stations)
    except requests.RequestException as exc:
        print(f"  AIRPORT METAR batch failed ({city.slug}): {exc}")
        batch = {}
    for station in stations:
        code = station.strip().upper()
        raw = batch.get(code)
        if not raw:
            try:
                raw = fetch_metar(code)
            except requests.RequestException as exc:
                print(f"  AIRPORT {code} -> skip ({exc})")
                continue
        payload = {
            "source": "aviationweather_metar",
            "city": city.slug,
            "station": code,
            "station_label": labels.get(code, code),
            "fetched_at": fetched_at,
            "raw": raw,
        }
        path = base / f"metar_{code}_{ts}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def ingest_airport_for_metro(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    from pulsegrid.config import metro_to_city

    stations = metro.airports or airport_station_codes(metro.slug)
    if not stations:
        return []
    return ingest_airport(metro_to_city(metro), stations=stations, out_dir=out_dir)
