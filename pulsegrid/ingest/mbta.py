"""MBTA alerts API (Boston) — bronze JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent

MBTA_ALERTS_URL = "https://api-v3.mbta.com/alerts"


def fetch_mbta_alerts(*, limit: int = 100) -> dict:
    resp = requests.get(
        MBTA_ALERTS_URL,
        params={"filter[activity]": "SERVICE_CHANGE", "page[limit]": limit},
        headers={"User-Agent": http_user_agent(), "Accept": "application/json"},
        timeout=45,
    )
    resp.raise_for_status()
    return resp.json()


def ingest_mbta(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    base = out_dir or BRONZE / city.slug / "transit"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw = fetch_mbta_alerts()
    alerts = []
    for item in raw.get("data", []):
        attrs = item.get("attributes") or {}
        alerts.append(
            {
                "alert_id": item.get("id", ""),
                "headline": attrs.get("header", ""),
                "short_description": (attrs.get("description") or "")[:500],
                "severity": attrs.get("severity", ""),
                "service": "mbta",
            }
        )
    payload = {
        "source": "transit_alerts",
        "adapter": "mbta",
        "city": city.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "alerts": alerts,
    }
    path = base / f"alerts_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [path]
