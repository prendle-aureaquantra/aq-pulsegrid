"""Metadata-driven ingestion framework (NWS, GTFS-RT, OpenSky, civic 311)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from pulsegrid.metros import MetroConfig

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "datasets" / "reference"

CORE_FEED_IDS = (
    "nws_weather",
    "gtfs_rt",
    "opensky_aviation",
    "civic311",
)


@dataclass(frozen=True)
class FeedTypeSpec:
    feed_id: str
    label: str
    module: str
    bronze_subdir: str
    adapter: str
    description: str = ""
    requires_country: str | None = None
    requires_field: str | None = None
    requires_module: str | None = None
    registry_field: str | None = None
    registry_value: str | None = None
    adapters: tuple[str, ...] = ()
    config_file: str | None = None


@dataclass
class ResolvedFeed:
    feed_id: str
    label: str
    module: str
    bronze_subdir: str
    adapter: str
    enabled: bool
    reason: str = ""
    config: dict[str, Any] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_ingest_catalog() -> dict[str, Any]:
    path = REF / "ingest_feeds.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _parse_feed_type(feed_id: str, raw: dict[str, Any]) -> FeedTypeSpec:
    req = raw.get("requires") or {}
    if isinstance(req, dict):
        country = req.get("country")
        req_field = req.get("field")
    else:
        country = None
        req_field = None
    adapters = raw.get("adapters") or []
    return FeedTypeSpec(
        feed_id=feed_id,
        label=str(raw.get("label", feed_id)),
        module=str(raw.get("module", "")),
        bronze_subdir=str(raw.get("bronze_subdir", feed_id)),
        adapter=str(raw.get("adapter", feed_id)),
        description=str(raw.get("description", "")),
        requires_country=str(country) if country else None,
        requires_field=str(req_field) if req_field else None,
        requires_module=str(raw.get("requires_module") or raw.get("module") or ""),
        registry_field=str(raw.get("registry_field") or ""),
        registry_value=str(raw.get("registry_value") or ""),
        adapters=tuple(str(a) for a in adapters),
        config_file=str(raw.get("config_file") or ""),
    )


@lru_cache(maxsize=1)
def feed_type_specs() -> dict[str, FeedTypeSpec]:
    catalog = load_ingest_catalog()
    out: dict[str, FeedTypeSpec] = {}
    for fid, raw in (catalog.get("feed_types") or {}).items():
        if isinstance(raw, dict):
            out[str(fid)] = _parse_feed_type(str(fid), raw)
    return out


def metro_override(metro_slug: str) -> dict[str, Any]:
    catalog = load_ingest_catalog()
    overrides = catalog.get("metro_overrides") or {}
    raw = overrides.get(metro_slug) or {}
    return raw if isinstance(raw, dict) else {}


def _override_enabled(metro_slug: str, feed_id: str) -> bool | None:
    feeds = metro_override(metro_slug).get("feeds") or {}
    entry = feeds.get(feed_id)
    if not isinstance(entry, dict):
        return None
    if "enabled" in entry:
        return bool(entry.get("enabled"))
    return None


def _has_module(metro: MetroConfig, module: str) -> bool:
    return module in metro.modules


def _resolve_nws_weather(metro: MetroConfig, spec: FeedTypeSpec) -> ResolvedFeed:
    enabled = False
    reason = "weather module not enabled"
    if _has_module(metro, "weather"):
        if metro.country.upper() != "US":
            reason = "NWS requires US metro (noaa_area)"
        elif not metro.noaa_area.strip():
            reason = "missing noaa_area on metro registry"
        elif metro.weather_adapter != "noaa":
            reason = f"weather_adapter is {metro.weather_adapter!r}, not noaa"
        else:
            enabled = True
            reason = "noaa_area + weather module"
    override = _override_enabled(metro.slug, spec.feed_id)
    if override is not None:
        enabled = override
        reason = "metro_overrides" if enabled else "disabled in metro_overrides"
    return ResolvedFeed(
        feed_id=spec.feed_id,
        label=spec.label,
        module=spec.module,
        bronze_subdir=spec.bronze_subdir,
        adapter=spec.adapter,
        enabled=enabled,
        reason=reason,
        config={"noaa_area": metro.noaa_area, "lat": metro.lat, "lon": metro.lon},
    )


def _resolve_transit_metro(metro: MetroConfig) -> MetroConfig:
    from pulsegrid.ingest.transit_resolve import resolve_transit_metro

    return resolve_transit_metro(metro)


def _resolve_gtfs_rt(metro: MetroConfig, spec: FeedTypeSpec) -> ResolvedFeed:
    resolved_metro = _resolve_transit_metro(metro)
    adapter = resolved_metro.transit_adapter
    enabled = False
    reason = "transit not configured"
    config: dict[str, Any] = {}
    if "transit" in resolved_metro.modules and adapter != "none":
        if spec.adapters and adapter not in spec.adapters:
            reason = f"transit_adapter {adapter!r} not in framework adapters"
        else:
            enabled = True
            reason = f"transit_adapter={adapter}"
            config = {
                "transit_adapter": adapter,
                "gtfs_rt_url": resolved_metro.gtfs_rt_url,
            }
            if adapter == "transit_json":
                from pulsegrid.metro_feeds import transit_json_adapter

                config["json_adapter"] = transit_json_adapter(metro.slug) or ""
    override = _override_enabled(metro.slug, spec.feed_id)
    if override is not None:
        enabled = override and adapter != "none"
        reason = "metro_overrides"
    return ResolvedFeed(
        feed_id=spec.feed_id,
        label=spec.label,
        module=spec.module,
        bronze_subdir=spec.bronze_subdir,
        adapter=adapter if enabled else spec.adapter,
        enabled=enabled,
        reason=reason,
        config=config,
    )


def _resolve_opensky(metro: MetroConfig, spec: FeedTypeSpec) -> ResolvedFeed:
    from pulsegrid.metro_feeds import airport_station_codes

    has_airports = _has_module(metro, "airports") or bool(metro.airports) or bool(
        airport_station_codes(metro.slug)
    )
    enabled = has_airports
    reason = "airports module or station catalog" if enabled else "no airports module"
    override = _override_enabled(metro.slug, spec.feed_id)
    if override is not None:
        enabled = override
        reason = "metro_overrides"
    return ResolvedFeed(
        feed_id=spec.feed_id,
        label=spec.label,
        module=spec.module,
        bronze_subdir=spec.bronze_subdir,
        adapter=spec.adapter,
        enabled=enabled,
        reason=reason,
        config={"airports": list(metro.airports)},
    )


def _resolve_civic311(metro: MetroConfig, spec: FeedTypeSpec) -> ResolvedFeed:
    from pulsegrid.metro_feeds import civic311_config

    cfg = civic311_config(metro.slug)
    enabled = False
    reason = "no civic311.yaml entry"
    if metro.country.upper() != "US":
        reason = "civic311 limited to US Socrata portals"
    elif cfg:
        enabled = True
        reason = "civic311.yaml"
    override = _override_enabled(metro.slug, spec.feed_id)
    if override is not None:
        enabled = override and bool(cfg)
        reason = "metro_overrides"
    return ResolvedFeed(
        feed_id=spec.feed_id,
        label=spec.label,
        module=spec.module,
        bronze_subdir=spec.bronze_subdir,
        adapter=spec.adapter,
        enabled=enabled,
        reason=reason,
        config=dict(cfg or {}),
    )


_RESOLVERS = {
    "nws_weather": _resolve_nws_weather,
    "gtfs_rt": _resolve_gtfs_rt,
    "opensky_aviation": _resolve_opensky,
    "civic311": _resolve_civic311,
}


def resolve_feed(metro: MetroConfig, feed_id: str) -> ResolvedFeed:
    specs = feed_type_specs()
    if feed_id not in specs:
        raise KeyError(f"Unknown feed_id {feed_id!r}")
    resolver = _RESOLVERS.get(feed_id)
    if not resolver:
        raise KeyError(f"No resolver for feed_id {feed_id!r}")
    return resolver(metro, specs[feed_id])


def list_metro_feeds(
    metro: MetroConfig, *, feed_ids: tuple[str, ...] = CORE_FEED_IDS
) -> list[ResolvedFeed]:
    return [resolve_feed(metro, fid) for fid in feed_ids if fid in feed_type_specs()]


def enabled_feed_modules(metro: MetroConfig) -> tuple[str, ...]:
    """Modules implied by enabled framework feeds (for registry enrichment)."""
    mods: set[str] = set()
    for feed in list_metro_feeds(metro):
        if feed.enabled and feed.module:
            mods.add(feed.module)
    return tuple(sorted(mods))


def run_feed(
    metro: MetroConfig,
    feed_id: str,
    out_dir: Path | None = None,
) -> list[Path]:
    """Execute a single feed by metadata id."""
    resolved = resolve_feed(metro, feed_id)
    if not resolved.enabled:
        return []
    from pulsegrid.config import metro_to_city

    city = metro_to_city(metro)
    adapter = resolved.adapter

    if feed_id == "nws_weather":
        from pulsegrid.ingest.noaa import ingest_noaa

        return ingest_noaa(city, out_dir=out_dir)

    if feed_id == "gtfs_rt":
        from pulsegrid.ingest.registry import ingest_transit

        return ingest_transit(metro, out_dir=out_dir)

    if feed_id == "opensky_aviation":
        from pulsegrid.ingest.opensky import ingest_opensky

        return ingest_opensky(metro, out_dir=out_dir)

    if feed_id == "civic311":
        from pulsegrid.ingest.civic311 import ingest_civic311

        return ingest_civic311(city, out_dir=out_dir)

    raise ValueError(f"No runner for feed_id {feed_id!r}")


def run_core_feeds(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    """Run NWS, transit, OpenSky, and 311 when enabled for this metro."""
    paths: list[Path] = []
    for feed_id in CORE_FEED_IDS:
        try:
            written = run_feed(metro, feed_id, out_dir=out_dir)
            if written:
                paths.extend(written)
        except Exception as exc:
            print(f"  {feed_id.upper()} -> skip ({exc})")
    return paths


def coverage_report(
    metros: list[MetroConfig] | None = None,
) -> list[dict[str, Any]]:
    """Tabular coverage for CLI / docs."""
    from pulsegrid.metros import list_metros

    rows: list[dict[str, Any]] = []
    for metro in metros or list_metros():
        row: dict[str, Any] = {"metro": metro.slug, "country": metro.country}
        for feed in list_metro_feeds(metro):
            row[feed.feed_id] = "yes" if feed.enabled else "no"
            row[f"{feed.feed_id}_reason"] = feed.reason
        rows.append(row)
    return rows
