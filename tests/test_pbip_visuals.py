"""Tests for PBIP visual generation."""

from __future__ import annotations

from pbip_generator.build_pbip import report_pages
from pbip_generator.visuals import visuals_for_page, write_page_visuals


def test_live_pulse_command_center_visual_count():
    avail = {"CityPulseSnapshot", "AnomalySignals", "TransitAlertSummary"}
    n = len(visuals_for_page("page.live-pulse", available_tables=avail))
    assert n >= 7, f"command center should be rich layout, got {n}"


def test_geospatial_page_has_visuals():
    avail = {"HexPulseGrid", "EventHeatmap", "TransitAlertDetail", "CityEventDetail"}
    n = len(visuals_for_page("page.geospatial", available_tables=avail))
    assert n >= 5


def test_metro_compare_platform_page():
    avail = {"DimMetro", "CityPulseSnapshot", "AnomalySignals"}
    n = len(visuals_for_page("page.metro-compare", available_tables=avail, platform_mode=True))
    assert n >= 5


def test_report_page_order_platform_includes_metro_compare():
    seeds = [s for s, _ in report_pages(platform_mode=True)]
    assert seeds[0] == "page.live-pulse"
    assert "page.metro-compare" in seeds
    assert "page.geospatial" in seeds


def test_all_core_pages_have_visuals(tmp_path):
    total = 0
    for seed in ("page.live-pulse", "page.transit", "page.weather", "page.geospatial"):
        pdir = tmp_path / seed
        pdir.mkdir()
        total += write_page_visuals(pdir, seed)
    assert total >= 18
    assert (tmp_path / "page.live-pulse" / "visuals").is_dir()
