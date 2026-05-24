"""Resolve transit adapter + GTFS-RT URL (registry, transit_feeds, MobilityData catalog)."""

from __future__ import annotations

from dataclasses import replace

from pulsegrid.metros import MetroConfig


def resolve_transit_metro(metro: MetroConfig) -> MetroConfig:
    """Apply MobilityData catalog when registry has no explicit transit URL."""
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
