"""Tests for PBIP visual generation."""

from __future__ import annotations

from pbip_generator.visuals import visuals_for_page, write_page_visuals


def test_live_pulse_visual_count():
    assert len(visuals_for_page("page.live-pulse")) == 6


def test_all_pages_have_visuals(tmp_path):
    total = 0
    for seed in ("page.live-pulse", "page.transit", "page.weather"):
        pdir = tmp_path / seed
        pdir.mkdir()
        total += write_page_visuals(pdir, seed)
    assert total == 13
    assert (tmp_path / "page.live-pulse" / "visuals").is_dir()
