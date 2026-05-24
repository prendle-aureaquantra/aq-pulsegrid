"""Load worldwide metro registry (Phase 2)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "datasets" / "metros" / "registry.yaml"

MetroTier = Literal["full", "weather_only"]


@dataclass(frozen=True)
class MetroConfig:
    slug: str
    name: str
    country: str
    lat: float
    lon: float
    timezone: str
    tier: MetroTier
    noaa_area: str = ""
    state: str = ""
    modules: tuple[str, ...] = ()
    transit_adapter: str = "none"
    events_adapter: str = "none"
    weather_adapter: str = "noaa"
    airports: tuple[str, ...] = ()
    events_url: str = ""
    events_order: str = "start_date DESC"
    gtfs_rt_url: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.name}, {self.country}"


def _apply_transit_feed(metro: MetroConfig) -> MetroConfig:
    from pulsegrid.metro_feeds import transit_feed_config

    cfg = transit_feed_config(metro.slug)
    if cfg:
        adapter = str(cfg.get("adapter", metro.transit_adapter)).strip()
        if adapter and adapter != "none":
            modules = tuple(sorted({*metro.modules, "transit"}))
            url = str(cfg.get("gtfs_rt_url", metro.gtfs_rt_url)).strip()
            return replace(
                metro,
                modules=modules,
                transit_adapter=adapter,
                gtfs_rt_url=url or metro.gtfs_rt_url,
            )

    if metro.transit_adapter in ("cta", "mbta", "transit_json"):
        if "transit" not in metro.modules:
            return replace(metro, modules=tuple(sorted({*metro.modules, "transit"})))
        return metro

    if metro.transit_adapter == "gtfs_rt" and metro.gtfs_rt_url.strip():
        if "transit" not in metro.modules:
            return replace(metro, modules=tuple(sorted({*metro.modules, "transit"})))
        return metro
    return metro


def _apply_airport_feed(metro: MetroConfig) -> MetroConfig:
    from pulsegrid.metro_feeds import airport_station_codes

    codes = airport_station_codes(metro.slug)
    if not codes:
        merged = metro.airports
    else:
        merged = tuple(dict.fromkeys((*metro.airports, *codes)))
    if not merged:
        return metro
    modules = tuple(sorted({*metro.modules, "airports"}))
    return replace(metro, modules=modules, airports=merged)


def _parse_metro(raw: dict) -> MetroConfig:
    return _apply_airport_feed(
        _apply_transit_feed(
        MetroConfig(
        slug=str(raw["slug"]),
        name=str(raw["name"]),
        country=str(raw.get("country", "")),
        lat=float(raw["lat"]),
        lon=float(raw["lon"]),
        timezone=str(raw.get("timezone", "UTC")),
        tier=str(raw.get("tier", "weather_only")),  # type: ignore[arg-type]
        noaa_area=str(raw.get("noaa_area", "")),
        state=str(raw.get("state", "")),
        modules=tuple(raw.get("modules") or ()),
        transit_adapter=str(raw.get("transit_adapter", "none")),
        events_adapter=str(raw.get("events_adapter", "none")),
        weather_adapter=str(raw.get("weather_adapter", "noaa")),
        airports=tuple(raw.get("airports") or ()),
        events_url=str(raw.get("events_url", "")),
        events_order=str(raw.get("events_order", "start_date DESC")),
        gtfs_rt_url=str(raw.get("gtfs_rt_url", "")),
        )
        )
    )


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, MetroConfig]:
    if not REGISTRY_PATH.is_file():
        raise FileNotFoundError(f"Metro registry missing: {REGISTRY_PATH}")
    data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    metros: dict[str, MetroConfig] = {}
    for section in ("tier1", "tier2"):
        for raw in data.get(section, []):
            metro = _parse_metro(raw)
            metros[metro.slug] = metro
    return metros


def load_metro(slug: str) -> MetroConfig:
    key = slug.lower().strip()
    registry = _load_registry()
    if key not in registry:
        available = ", ".join(sorted(registry)[:20])
        raise ValueError(f"Unknown metro {slug!r}. Sample: {available}…")
    return registry[key]


def list_metros(*, tier: MetroTier | None = None) -> list[MetroConfig]:
    registry = _load_registry()
    items = list(registry.values())
    if tier is not None:
        items = [m for m in items if m.tier == tier]
    return sorted(items, key=lambda m: m.name)


def metro_context(metro: MetroConfig) -> dict[str, str]:
    """Columns appended to silver/gold rows."""
    return {
        "city": metro.slug,
        "metro_name": metro.name,
        "country": metro.country,
        "timezone": metro.timezone,
        "metro_tier": metro.tier,
    }
