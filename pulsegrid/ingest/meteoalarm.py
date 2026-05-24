"""MeteoAlarm CAP atom feeds — international weather warnings (live API only)."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

from pulsegrid.config import BRONZE, http_user_agent
from pulsegrid.metros import MetroConfig

ATOM_NS = {"a": "http://www.w3.org/2005/Atom", "cap": "urn:oasis:names:tc:emergency:cap:1.2"}
FEED_BASE = "https://feeds.meteoalarm.org/feeds/meteoalarm-legacy-atom-"

# Verified public atom feeds (country ISO2 -> feed slug)
METEOALARM_COUNTRIES: dict[str, str] = {
    "FR": "france",
    "DE": "germany",
    "ES": "spain",
    "IT": "italy",
    "AT": "austria",
    "SE": "sweden",
    "NO": "norway",
    "GR": "greece",
    "PT": "portugal",
    "FI": "finland",
    "RO": "romania",
    "IL": "israel",
}


def _cap_text(entry: ET.Element, tag: str) -> str:
    for el in entry.iter():
        if el.tag.endswith(tag) and el.text:
            return el.text.strip()
    return ""


def fetch_meteoalarm_warnings(metro: MetroConfig) -> list[dict]:
    slug = METEOALARM_COUNTRIES.get(metro.country.upper())
    if not slug:
        return []
    url = f"{FEED_BASE}{slug}"
    resp = requests.get(url, headers={"User-Agent": http_user_agent()}, timeout=45)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    warnings: list[dict] = []
    for entry in root.findall("a:entry", ATOM_NS):
        alert_id = _cap_text(entry, "identifier") or _cap_text(entry, "id")
        if not alert_id:
            continue
        warnings.append(
            {
                "alert_id": alert_id,
                "event": _cap_text(entry, "event"),
                "severity": _cap_text(entry, "severity"),
                "urgency": _cap_text(entry, "urgency"),
                "headline": _cap_text(entry, "headline") or (entry.find("a:title", ATOM_NS).text or "").strip(),
                "area_desc": _cap_text(entry, "areaDesc"),
                "effective": _cap_text(entry, "effective"),
                "expires": _cap_text(entry, "expires"),
            }
        )
    return warnings


def ingest_meteoalarm(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    """Fetch country MeteoAlarm CAP warnings for open_meteo metros."""
    if metro.weather_adapter != "open_meteo":
        return []
    warnings = fetch_meteoalarm_warnings(metro)
    if not warnings and metro.country.upper() not in METEOALARM_COUNTRIES:
        return []
    base = out_dir or BRONZE / metro.slug / "weather"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "source": "meteoalarm_cap",
        "city": metro.slug,
        "country": metro.country,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
    }
    path = base / f"alerts_{ts}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [path]
