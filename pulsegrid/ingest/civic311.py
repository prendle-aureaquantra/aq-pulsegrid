"""311 / civic service requests — Socrata, ArcGIS, and CARTO open data."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent
from pulsegrid.metro_feeds import civic311_config


def _recent_where_socrata(date_field: str, days: int) -> str:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{date_field} > '{cutoff}'"


def fetch_socrata_311(cfg: dict) -> list[dict]:
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
        params["$where"] = _recent_where_socrata(date_field, days)
    resp = requests.get(
        cfg["url"],
        params=params,
        headers={"User-Agent": http_user_agent()},
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []


def fetch_arcgis_311(cfg: dict) -> list[dict]:
    """ArcGIS MapServer/FeatureServer layer query endpoint in cfg['url']."""
    limit = int(cfg.get("limit", 150))
    date_field = cfg.get("date_field", "CreatedDate")
    days = int(cfg.get("recent_days", 14))
    if cfg.get("where"):
        where = str(cfg["where"])
    elif days > 0:
        cutoff_ms = int(
            (datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000
        )
        where = f"{date_field} >= {cutoff_ms}"
    else:
        where = "1=1"
    params = {
        "where": where,
        "outFields": cfg.get("out_fields", "*"),
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": limit,
    }
    order = cfg.get("order_by") or cfg.get("order")
    if order:
        params["orderByFields"] = order.replace(" DESC", " DESC").replace(
            " ASC", " ASC"
        )
    elif date_field:
        params["orderByFields"] = f"{date_field} DESC"
    resp = requests.get(
        cfg["url"],
        params=params,
        headers={"User-Agent": http_user_agent()},
        timeout=90,
    )
    resp.raise_for_status()
    doc = resp.json()
    features = doc.get("features") or []
    return [f.get("attributes") or {} for f in features if isinstance(f, dict)]


def fetch_carto_311(cfg: dict) -> list[dict]:
    """CARTO SQL API (Philadelphia public_cases_fc pattern)."""
    table = cfg.get("table", "public_cases_fc")
    date_field = cfg.get("date_field", "requested_datetime")
    days = int(cfg.get("recent_days", 14))
    limit = int(cfg.get("limit", 150))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    sql = (
        f"SELECT * FROM {table} "
        f"WHERE {date_field} >= '{cutoff}' "
        f"ORDER BY {date_field} DESC LIMIT {limit}"
    )
    base = cfg.get("url", "https://phl.carto.com/api/v2/sql").rstrip("/")
    if base.endswith("/sql"):
        url = base
    else:
        url = f"{base}/api/v2/sql"
    resp = requests.get(
        url,
        params={"q": sql, "format": "json"},
        headers={"User-Agent": http_user_agent()},
        timeout=90,
    )
    resp.raise_for_status()
    doc = resp.json()
    rows = doc.get("rows") or []
    return rows if isinstance(rows, list) else []


def fetch_civic311(city: CityConfig, cfg: dict) -> list[dict]:
    adapter = str(cfg.get("adapter", "socrata")).lower()
    if adapter == "arcgis":
        return fetch_arcgis_311(cfg)
    if adapter == "carto":
        return fetch_carto_311(cfg)
    return fetch_socrata_311(cfg)


def ingest_civic311(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    cfg = civic311_config(city.slug)
    if not cfg:
        return []
    base = out_dir or BRONZE / city.slug / "civic311"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    records = fetch_civic311(city, cfg)
    adapter = str(cfg.get("adapter", "socrata")).lower()
    source = {"socrata": "socrata_311", "arcgis": "arcgis_311", "carto": "carto_311"}.get(
        adapter, "socrata_311"
    )
    host = urlparse(cfg["url"]).netloc
    payload = {
        "source": source,
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
