"""OpenStreetMap POI enrichment via Overpass API."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def overpass_pois(lat: float, lon: float, *, radius_m: int = 8000) -> list[dict]:
    query = f"""
    [out:json][timeout:25];
    (
      node(around:{radius_m},{lat},{lon})["amenity"];
      way(around:{radius_m},{lat},{lon})["amenity"];
    );
    out center 120;
    """
    resp = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers={"User-Agent": http_user_agent()},
        timeout=60,
    )
    resp.raise_for_status()
    elements = resp.json().get("elements", [])
    rows: list[dict] = []
    for el in elements:
        tags = el.get("tags") or {}
        center = el.get("center") or {}
        rows.append(
            {
                "osm_id": el.get("id"),
                "osm_type": el.get("type"),
                "amenity": tags.get("amenity", ""),
                "name": tags.get("name", ""),
                "lat": center.get("lat") or el.get("lat"),
                "lon": center.get("lon") or el.get("lon"),
            }
        )
    return rows


def ingest_osm_pois(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    base = out_dir or BRONZE / city.slug / "osm"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pois = overpass_pois(city.lat, city.lon)
    payload = {
        "source": "openstreetmap_overpass",
        "city": city.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "pois": pois,
    }
    path = base / f"osm_pois_{ts}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return [path]
