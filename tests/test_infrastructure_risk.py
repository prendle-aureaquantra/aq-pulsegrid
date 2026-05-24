"""Infrastructure fatigue / failure risk from civic 311."""

from __future__ import annotations

import pandas as pd

from pulsegrid.infrastructure_risk import (
    ASSET_BRIDGE,
    ASSET_ROAD,
    classify_infrastructure_request,
    infrastructure_risk_rollup,
    request_failure_risk_score,
)


def test_classify_bridge_failure():
    meta = classify_infrastructure_request(
        "Bridge Maintenance", "structural crack unsafe for traffic"
    )
    assert meta["asset_class"] == ASSET_BRIDGE
    assert meta["risk_tier"] == "failure"


def test_classify_road_fatigue():
    meta = classify_infrastructure_request("Pothole", "large pothole on main street")
    assert meta["asset_class"] == ASSET_ROAD
    assert meta["risk_tier"] == "fatigue"


def test_rollup_chicago_bridge_and_pothole():
    civic = pd.DataFrame(
        [
            {
                "city": "chicago",
                "request_type": "Bridge Maintenance",
                "descriptor": "deck spalling",
                "status": "Open",
            },
            {
                "city": "chicago",
                "request_type": "Pothole",
                "descriptor": "deep pothole",
                "status": "In Progress",
            },
            {
                "city": "chicago",
                "request_type": "Tree Debris",
                "descriptor": "fallen branch",
                "status": "Open",
            },
        ]
    )
    rollup = infrastructure_risk_rollup(
        civic, "chicago", "2026-05-23T12:00:00Z", avg_precip_pct=40.0
    )
    assert rollup["bridge_risk_score"] > 0
    assert rollup["road_surface_risk_score"] > 0
    assert rollup["infrastructure_failure_risk"] > 0
    assert rollup["infrastructure_fatigue_risk"] > 0
    assert rollup["open_infrastructure_requests"] >= 1
    assert "bridge" in rollup["infrastructure_summary"].lower()


def test_failure_score_higher_for_structural_emergency():
    low = request_failure_risk_score("Alley Light Out", "bulb burned")
    high = request_failure_risk_score(
        "Building Violation", "structural collapse hazard emergency", status="Open"
    )
    assert high > low
