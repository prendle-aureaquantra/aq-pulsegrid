"""311 / civic service requests — Socrata open data (live API only)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent
from pulsegrid.metro_feeds import civic311_config


def _recent_where(date_field: str, days: int) -> str:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{date_field} > '{cutoff}'"


def fetch_civic311(city: CityConfig, cfg: dict) -> list[dict]:
    params: dict = {"$limit": int(cfg.get("limit", 150))}
    order = cfg.get("order")
    if order:
        params["$order"] = order
    select = cfg.get("select")
    if select:
        params["$select"] = select
    days = int(cfg.get("recent_days", 7))
    date_field = cfg.get("date_field")
    if date_field and days > 0:
        params["$where"] = _recent_where(date_field, days)
    resp = requests.get(
        cfg["url"],
        params=params,
        headers={"User-Agent": http_user_agent()},
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def ingest_civic311(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    cfg = civic311_config(city.slug)
    if not cfg:
        return []
    base = out_dir or BRONZE / city.slug / "civic311"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    records = fetch_civic311(city, cfg)
    host = urlparse(cfg["url"]).netloc
    payload = {
        "source": "socrata_311",
        "city": city.slug,
        "portal": host,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "field_map": {
            "date_field": cfg.get("date_field", ""),
            "type_field": cfg.get("type_field", ""),
            "status_field": cfg.get("status_field", ""),
        },
        "records": records,
    }
    path = base / f"requests_{ts}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return [path]
