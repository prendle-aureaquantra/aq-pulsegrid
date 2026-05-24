"""Semantic model metadata for PBIP generator (Week 4)."""

from __future__ import annotations

import json
from pathlib import Path

from pulsegrid.config import GENERATED, load_city_yaml


def build_semantic_metadata(city_slug: str) -> dict:
    city_yaml = load_city_yaml(city_slug)
    return {
        "city": city_slug,
        "model_name": f"{city_slug.title()}Pulse",
        "theme": city_yaml.get("pbip", {}).get("theme", "dark"),
        "tables": [
            {
                "name": "CityPulseSnapshot",
                "source": "gold/city_stress_index",
                "columns": [
                    "city_stress_index",
                    "transit_load_score",
                    "weather_risk_score",
                    "precip_risk_score",
                    "disruption_ratio_score",
                    "active_transit_alerts",
                    "active_noaa_alerts",
                ],
            },
            {
                "name": "TransitAlertSummary",
                "source": "gold/transit_alert_summary",
                "columns": ["alert_category", "alert_count"],
            },
            {
                "name": "TransitAlertDetail",
                "source": "gold/transit_alert_detail",
                "columns": [
                    "neighborhood",
                    "alert_category",
                    "headline",
                    "service",
                    "severity",
                ],
            },
            {
                "name": "AnomalySignals",
                "source": "gold/anomaly_signals",
                "columns": ["signal_type", "severity", "message", "z_score"],
            },
            {
                "name": "CityEventDetail",
                "source": "gold/event_detail",
                "columns": [
                    "neighborhood",
                    "event_category",
                    "event_name",
                    "location",
                    "start_date",
                ],
            },
            {
                "name": "AirportOpsSnapshot",
                "source": "gold/airport_ops_snapshot",
                "columns": [
                    "station",
                    "station_label",
                    "flight_category",
                    "visibility_sm",
                    "airport_ops_stress",
                ],
            },
            {
                "name": "FredMacroSnapshot",
                "source": "gold/fred_macro_snapshot",
                "columns": ["series_label", "latest_value"],
            },
            {
                "name": "TrendInterestSummary",
                "source": "gold/trend_interest_summary",
                "columns": ["keyword", "avg_interest"],
            },
            {
                "name": "HexPulseGrid",
                "source": "gold/hex_pulse_grid",
                "columns": ["neighborhood", "alert_count"],
            },
        ],
        "measures": [
            {
                "name": "City Stress Index",
                "expression": "AVERAGE(CityPulseSnapshot[city_stress_index])",
                "format": "0.0",
            },
            {
                "name": "Active Transit Alerts",
                "expression": "SUM(CityPulseSnapshot[active_transit_alerts])",
                "format": "#,0",
            },
            {
                "name": "Anomaly Count",
                "expression": "COUNTROWS(AnomalySignals)",
                "format": "#,0",
            },
        ],
        "pages": city_yaml.get("pbip", {}).get("pages", []),
    }


def write_semantic_metadata(city_slug: str) -> Path:
    meta = build_semantic_metadata(city_slug)
    out_dir = GENERATED / city_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "semantic_model_metadata.json"
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path
