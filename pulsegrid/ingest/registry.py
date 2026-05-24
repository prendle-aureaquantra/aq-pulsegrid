"""Dispatch transit, weather, and events ingest by metro adapter config."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pulsegrid.config import CityConfig, get_metro, metro_to_city
from pulsegrid.metros import MetroConfig

IngestFn = Callable[[CityConfig], list[Path]]


def _metro_city(metro: MetroConfig) -> CityConfig:
    return metro_to_city(metro)


def _resolve_transit_metro(metro: MetroConfig) -> MetroConfig:
    """Apply MobilityData catalog when registry has no explicit transit URL."""
    from dataclasses import replace

    if metro.transit_adapter in ("cta", "mbta", "transit_json"):
        return metro
    if metro.transit_adapter == "gtfs_rt" and metro.gtfs_rt_url.strip():
        return metro
    if "transit" not in metro.modules and metro.transit_adapter == "none":
        pass
    from pulsegrid.ingest.mobility_catalog import lookup_gtfs_rt_alerts_url

    url = lookup_gtfs_rt_alerts_url(metro)
    if not url:
        return metro
    modules = tuple(sorted({*metro.modules, "transit"}))
    return replace(
        metro,
        modules=modules,
        transit_adapter="gtfs_rt",
        gtfs_rt_url=url,
    )


def ingest_transit(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    metro = _resolve_transit_metro(metro)
    adapter = metro.transit_adapter
    if adapter == "none" or "transit" not in metro.modules:
        return []
    city = _metro_city(metro)
    if adapter == "cta":
        from pulsegrid.ingest.cta import ingest_cta

        return ingest_cta(city, out_dir=out_dir)
    if adapter == "mbta":
        from pulsegrid.ingest.mbta import ingest_mbta

        return ingest_mbta(city, out_dir=out_dir)
    if adapter == "gtfs_rt":
        from pulsegrid.ingest.gtfs_rt import ingest_gtfs_rt

        return ingest_gtfs_rt(metro, out_dir=out_dir)
    if adapter == "transit_json":
        from pulsegrid.ingest.transit_json import ingest_transit_json
        from pulsegrid.metro_feeds import transit_json_adapter

        json_adapter = transit_json_adapter(metro.slug) or ""
        return ingest_transit_json(
            metro, city, json_adapter=json_adapter, out_dir=out_dir
        )
    raise ValueError(f"Unknown transit_adapter {adapter!r} for {metro.slug}")


def ingest_weather(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    if "weather" not in metro.modules:
        return []
    city = _metro_city(metro)
    if metro.weather_adapter == "open_meteo":
        from pulsegrid.ingest.open_meteo import ingest_open_meteo

        paths = ingest_open_meteo(metro, out_dir=out_dir)
        from pulsegrid.ingest.meteoalarm import ingest_meteoalarm

        try:
            paths.extend(ingest_meteoalarm(metro, out_dir=out_dir))
        except Exception as exc:
            print(f"  METEOALARM -> skip ({exc})")
        return paths
    from pulsegrid.ingest.noaa import ingest_noaa

    return ingest_noaa(city, out_dir=out_dir)


def ingest_events_for_metro(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    if "events" not in metro.modules or metro.events_adapter == "none":
        return []
    city = _metro_city(metro)
    if metro.events_adapter == "socrata" and metro.events_url:
        from pulsegrid.ingest.events import ingest_events_socrata

        order = metro.events_order or "start_date DESC"
        return ingest_events_socrata(
            city, metro.events_url, out_dir=out_dir, order=order
        )
    return []


def ingest_civic311_for_metro(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    if metro.country.upper() != "US":
        return []
    from pulsegrid.ingest.civic311 import ingest_civic311
    from pulsegrid.metro_feeds import civic311_config

    if not civic311_config(metro.slug):
        return []
    city = _metro_city(metro)
    return ingest_civic311(city, out_dir=out_dir)


def ingest_global_feeds(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    """Real public feeds keyed by lat/lon — available for every metro."""
    paths: list[Path] = []

    from pulsegrid.ingest.usgs import ingest_usgs

    try:
        paths.extend(ingest_usgs(metro, out_dir=out_dir))
    except Exception as exc:
        print(f"  USGS -> skip ({exc})")

    from pulsegrid.ingest.air_quality import ingest_air_quality

    try:
        paths.extend(ingest_air_quality(metro, out_dir=out_dir))
    except Exception as exc:
        print(f"  AQI -> skip ({exc})")

    return paths


def ingest_extended(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    """Airport, OpenSky, USGS, air quality, trends, FRED, OSM, events."""
    city = _metro_city(metro)
    paths: list[Path] = []
    modules = set(metro.modules)

    if "airports" in modules:
        from pulsegrid.ingest.opensky import ingest_opensky

        try:
            paths.extend(ingest_opensky(metro, out_dir=out_dir))
        except Exception as exc:
            print(f"  OPENSKY -> skip ({exc})")

    if "events" in modules or metro.events_adapter not in ("none", ""):
        try:
            paths.extend(ingest_events_for_metro(metro, out_dir=out_dir))
        except Exception as exc:
            print(f"  EVENTS -> skip ({exc})")

    if "osm" in modules:
        from pulsegrid.geo.osm_enrich import ingest_osm_pois

        try:
            paths.extend(ingest_osm_pois(city, out_dir=out_dir))
        except Exception as exc:
            print(f"  OSM -> skip ({exc})")

    if "trends" in modules:
        from pulsegrid.ingest.google_trends import ingest_google_trends

        try:
            paths.extend(ingest_google_trends(city, out_dir=out_dir))
        except RuntimeError as exc:
            print(f"  TREND -> skip ({exc})")

    if "fred" in modules:
        from pulsegrid.ingest.fred import ingest_fred

        try:
            paths.extend(ingest_fred(city, out_dir=out_dir))
        except RuntimeError as exc:
            print(f"  FRED -> skip ({exc})")

    return paths


def ingest_airports_for_metro(metro: MetroConfig, out_dir: Path | None = None) -> list[Path]:
    if "airports" not in metro.modules and not metro.airports:
        from pulsegrid.metro_feeds import airport_station_codes

        if not airport_station_codes(metro.slug):
            return []
    from pulsegrid.ingest.airport import ingest_airport_for_metro

    return ingest_airport_for_metro(metro, out_dir=out_dir)


def run_metro_ingest(metro_slug: str, *, extended: bool = False) -> list[Path]:
    metro = get_metro(metro_slug)
    paths: list[Path] = []
    try:
        paths.extend(ingest_weather(metro))
    except Exception as exc:
        print(f"  WEATHER -> skip ({exc})")
    try:
        paths.extend(ingest_transit(metro))
    except Exception as exc:
        print(f"  TRANSIT -> skip ({exc})")
    try:
        paths.extend(ingest_airports_for_metro(metro))
    except Exception as exc:
        print(f"  AIRPORT -> skip ({exc})")
    paths.extend(ingest_global_feeds(metro))
    try:
        paths.extend(ingest_civic311_for_metro(metro))
    except Exception as exc:
        print(f"  CIVIC311 -> skip ({exc})")
    if extended:
        paths.extend(ingest_extended(metro))
    return paths
