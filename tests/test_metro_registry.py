"""Phase 2 metro registry tests."""

from __future__ import annotations

from pulsegrid.config import get_city, get_metro, list_metros
from pulsegrid.metros import load_metro


def test_registry_loads_tier1_metros():
    chicago = load_metro("chicago")
    assert chicago.tier == "full"
    assert chicago.transit_adapter == "cta"
    assert chicago.display_name == "Chicago, US"


def test_registry_tier2_weather_only():
    berlin = load_metro("berlin")
    assert berlin.tier == "weather_only"
    assert berlin.transit_adapter == "none"
    assert berlin.weather_adapter == "open_meteo"


def test_list_metros_tier_filter():
    full = list_metros(tier="full")
    weather = list_metros(tier="weather_only")
    assert len(full) >= 10
    assert len(weather) >= 50
    assert all(m.tier == "full" for m in full)


def test_get_city_backward_compat():
    city = get_city("boston")
    assert city.slug == "boston"
    assert city.noaa_area == "MA"
    metro = get_metro("boston")
    assert metro.transit_adapter == "mbta"


def test_transit_feeds_enable_tier2_metros():
    seattle = load_metro("seattle")
    assert "transit" in seattle.modules
    assert seattle.transit_adapter == "gtfs_rt"
    assert seattle.gtfs_rt_url
