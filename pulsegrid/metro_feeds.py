"""Supplemental per-metro feed config (311, trends) outside registry.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "datasets" / "reference"


@lru_cache(maxsize=1)
def _load_yaml(name: str) -> dict[str, Any]:
    path = REF / name
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def civic311_config(metro_slug: str) -> dict[str, Any] | None:
    cfg = _load_yaml("civic311.yaml").get("metros", {}).get(metro_slug)
    return cfg if isinstance(cfg, dict) and cfg.get("url") else None


def trends_config(metro_slug: str) -> dict[str, Any] | None:
    cfg = _load_yaml("metro_trends.yaml").get("metros", {}).get(metro_slug)
    return cfg if isinstance(cfg, dict) and cfg.get("keywords") else None


def transit_feed_config(metro_slug: str) -> dict[str, Any] | None:
    cfg = _load_yaml("transit_feeds.yaml").get("metros", {}).get(metro_slug)
    if not isinstance(cfg, dict):
        return None
    adapter = str(cfg.get("adapter", "")).strip()
    if adapter and adapter != "none":
        return cfg
    return None


def airport_stations_config(metro_slug: str) -> dict[str, Any] | None:
    cfg = _load_yaml("metro_airports.yaml").get("metros", {}).get(metro_slug)
    if not isinstance(cfg, dict) or not cfg.get("stations"):
        return None
    return cfg


def airport_station_codes(metro_slug: str) -> tuple[str, ...]:
    cfg = airport_stations_config(metro_slug)
    if not cfg:
        return ()
    codes: list[str] = []
    for entry in cfg.get("stations") or []:
        if isinstance(entry, dict):
            icao = str(entry.get("icao", "")).strip().upper()
        else:
            icao = str(entry).strip().upper()
        if icao:
            codes.append(icao)
    return tuple(codes)


def airport_station_labels(metro_slug: str) -> dict[str, str]:
    cfg = airport_stations_config(metro_slug)
    if not cfg:
        return {}
    out: dict[str, str] = {}
    for entry in cfg.get("stations") or []:
        if isinstance(entry, dict):
            icao = str(entry.get("icao", "")).strip().upper()
            name = str(entry.get("name") or icao).strip()
            if icao:
                out[icao] = name
    return out


def transit_json_adapter(metro_slug: str) -> str | None:
    cfg = transit_feed_config(metro_slug)
    if not cfg or cfg.get("adapter") != "transit_json":
        return None
    name = str(cfg.get("json_adapter", "")).strip()
    return name or None
