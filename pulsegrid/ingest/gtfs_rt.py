"""GTFS-Realtime / JSON transit alerts — generic adapter."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, http_user_agent
from pulsegrid.metros import MetroConfig


def _translation_text(field) -> str:
    if field is None:
        return ""
    for trans in getattr(field, "translation", []) or []:
        text = getattr(trans, "text", None)
        if text:
            return str(text)
    return ""


def _parse_gtfs_rt_protobuf(content: bytes) -> list[dict]:
    try:
        from google.transit import gtfs_realtime_pb2
    except ImportError:
        return []

    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(content)
    except Exception:
        return []

    alerts: list[dict] = []
    for entity in feed.entity:
        if not entity.HasField("alert"):
            continue
        alert = entity.alert
        headline = _translation_text(
            alert.header_text if alert.HasField("header_text") else None
        )
        desc = _translation_text(
            alert.description_text if alert.HasField("description_text") else None
        )
        alerts.append(
            {
                "alert_id": str(entity.id or len(alerts)),
                "headline": headline[:300],
                "short_description": desc[:500],
                "severity": "",
                "service": "gtfs_rt",
            }
        )
    return alerts


def _parse_json_alerts(body: dict | list) -> list[dict]:
    """MBTA v3 JSON API and similar {data: [{attributes}]} shapes."""
    alerts: list[dict] = []
    if isinstance(body, dict) and "data" in body:
        for item in body.get("data", [])[:200]:
            attrs = item.get("attributes") or item
            alerts.append(
                {
                    "alert_id": str(item.get("id", len(alerts))),
                    "headline": str(
                        attrs.get("header") or attrs.get("headline") or ""
                    )[:300],
                    "short_description": str(
                        attrs.get("description")
                        or attrs.get("short_description")
                        or ""
                    )[:500],
                    "severity": str(attrs.get("severity") or ""),
                    "service": "gtfs_rt",
                }
            )
    return alerts


def ingest_gtfs_rt(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    base = out_dir or BRONZE / metro.slug / "transit"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    url = metro.gtfs_rt_url.strip()
    if not url:
        from pulsegrid.ingest.mobility_catalog import lookup_gtfs_rt_alerts_url

        url = lookup_gtfs_rt_alerts_url(metro) or ""
    alerts: list[dict] = []
    raw_body: dict | list | str = {}
    if url:
        resp = requests.get(
            url,
            headers={"User-Agent": http_user_agent()},
            timeout=45,
        )
        if resp.status_code == 200:
            ctype = resp.headers.get("Content-Type", "")
            if "json" in ctype or resp.text.strip().startswith(("{", "[")):
                try:
                    raw_body = resp.json()
                except json.JSONDecodeError as exc:
                    print(f"  GTFS-RT JSON parse failed ({metro.slug}): {exc}")
                    raw_body = {}
                alerts = _parse_json_alerts(raw_body)
            else:
                alerts = _parse_gtfs_rt_protobuf(resp.content)
                if not alerts and resp.content:
                    raw_body = {"bytes": len(resp.content)}
    payload = {
        "source": "transit_alerts",
        "adapter": "gtfs_rt",
        "city": metro.slug,
        "feed_url": url,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "alert_count": len(alerts),
        "alerts": alerts,
        "raw_sample": raw_body if isinstance(raw_body, (dict, list)) else str(raw_body)[:2000],
    }
    path = base / f"alerts_{ts}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return [path]
