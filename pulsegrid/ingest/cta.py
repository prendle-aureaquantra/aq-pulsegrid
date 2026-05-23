"""Chicago Transit Authority alerts API (XML)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, CityConfig, http_user_agent

CTA_ALERTS_URL = "https://www.transitchicago.com/api/1.0/alerts.aspx"


def _xml_text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _parse_alert(node: ET.Element) -> dict:
    return {
        "alert_id": _xml_text(node.find("AlertId")),
        "headline": _xml_text(node.find("Headline")),
        "short_description": _xml_text(node.find("ShortDescription")),
        "severity": _xml_text(node.find("Severity")),
        "service": _xml_text(node.find("Service")),
        "url": _xml_text(node.find("Url")),
    }


def fetch_cta_alerts() -> dict:
    resp = requests.get(
        CTA_ALERTS_URL,
        headers={"User-Agent": http_user_agent()},
        timeout=30,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    error_code = _xml_text(root.find("ErrorCode"))
    if error_code and error_code != "0":
        msg = _xml_text(root.find("ErrorMessage"))
        raise RuntimeError(f"CTA API error {error_code}: {msg}")

    alerts = [_parse_alert(a) for a in root.findall("Alert")]
    return {
        "source": "cta_alerts",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "timestamp": _xml_text(root.find("TimeStamp")),
        "alert_count": len(alerts),
        "alerts": alerts,
        "raw_xml": resp.text,
    }


def ingest_cta(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    if city.slug != "chicago":
        raise ValueError("CTA ingest is Chicago-only in Phase 1")
    base = (out_dir or BRONZE / city.slug / "cta")
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = fetch_cta_alerts()
    path = base / f"alerts_{ts}.json"
    # Omit raw_xml from JSON file (large); keep parsed alerts
    to_write = {k: v for k, v in payload.items() if k != "raw_xml"}
    path.write_text(json.dumps(to_write, indent=2), encoding="utf-8")
    return [path]
