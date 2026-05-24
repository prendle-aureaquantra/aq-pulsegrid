"""Agency-specific JSON transit status APIs (non-GTFS-RT)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent
from pulsegrid.metros import MetroConfig

AlertFn = Callable[[], list[dict]]


def _fetch_tfl_line_status() -> list[dict]:
    resp = requests.get(
        "https://api.tfl.gov.uk/Line/Mode/tube,overground,dlr,tram/Status",
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    resp.raise_for_status()
    alerts: list[dict] = []
    for line in resp.json():
        name = str(line.get("name") or "")
        for status in line.get("lineStatuses") or []:
            desc = str(status.get("statusSeverityDescription") or "")
            if not desc or desc.lower() == "good service":
                continue
            reason = ""
            for disruption in status.get("disruptions") or []:
                reason = str(disruption.get("description") or disruption.get("summary") or "")
                if reason:
                    break
            alerts.append(
                {
                    "alert_id": f"tfl-{name}-{status.get('id', len(alerts))}",
                    "headline": f"{name}: {desc}",
                    "short_description": reason[:500],
                    "severity": str(status.get("statusSeverity") or ""),
                    "service": "tfl",
                }
            )
    return alerts


def _fetch_ovapi_alerts() -> list[dict]:
    """Netherlands OVapi aggregated GTFS-RT alerts (JSON wrapper)."""
    resp = requests.get(
        "http://gtfs.ovapi.nl/new/alerts",
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    if resp.status_code != 200:
        return []
    try:
        body = resp.json()
    except json.JSONDecodeError:
        return []
    alerts: list[dict] = []
    if isinstance(body, list):
        for item in body[:200]:
            if isinstance(item, dict):
                alerts.append(
                    {
                        "alert_id": str(item.get("id", len(alerts))),
                        "headline": str(item.get("title") or item.get("header") or "")[:300],
                        "short_description": str(
                            item.get("description") or item.get("body") or ""
                        )[:500],
                        "severity": "",
                        "service": "ovapi",
                    }
                )
    return alerts


_JSON_ADAPTERS: dict[str, AlertFn] = {
    "tfl": _fetch_tfl_line_status,
    "ovapi": _fetch_ovapi_alerts,
}


def ingest_transit_json(
    metro: MetroConfig,
    city: CityConfig,
    *,
    json_adapter: str,
    out_dir: Path | None = None,
) -> list[Path]:
    fn = _JSON_ADAPTERS.get(json_adapter)
    if fn is None:
        raise ValueError(f"Unknown transit JSON adapter {json_adapter!r}")
    base = out_dir or BRONZE / city.slug / "transit"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    alerts = fn()
    payload = {
        "source": "transit_alerts",
        "adapter": f"json_{json_adapter}",
        "city": city.slug,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "alerts": alerts,
    }
    path = base / f"alerts_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [path]
