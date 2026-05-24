"""PBIP structure smoke test."""

from __future__ import annotations


from pbip_generator.build_pbip import (
    _validate_relationship_paths,
    _write_relationships,
    build_pbip,
)


def test_build_pbip_structure(tmp_path, monkeypatch):
    import pulsegrid.config as cfg
    import pbip_generator.export_gold_csv as exp

    city = "chicago"
    data = tmp_path / "delta"
    gold = data / "gold"
    silver = data / "silver"
    monkeypatch.setattr(cfg, "DATA_ROOT", tmp_path / "local")
    table_rows = {
        "city_stress_index": [
            {
                "city": city,
                "snapshot_at": "2026-05-23T12:00:00+00:00",
                "city_stress_index": 50.0,
                "transit_load_score": 20.0,
                "weather_risk_score": 10.0,
                "precip_risk_score": 5.0,
                "disruption_ratio_score": 5.0,
                "active_transit_alerts": 10,
                "active_noaa_alerts": 1,
                "avg_precip_pct_next_periods": 12.0,
                "reroute_count": 5,
                "delay_count": 1,
            }
        ],
        "transit_alert_summary": [
            {
                "city": city,
                "snapshot_at": "2026-05-23T12:00:00+00:00",
                "alert_category": "reroute",
                "alert_count": 5,
            }
        ],
        "transit_alert_detail": [
            {
                "city": city,
                "snapshot_at": "2026-05-23T12:00:00+00:00",
                "hex_id": "hex-1",
                "neighborhood": "Loop",
                "alert_id": "alert-1",
                "headline": "Red Line delay",
                "short_description": "minor",
                "severity": "low",
                "service": "Red",
                "alert_category": "delay",
            }
        ],
        "anomaly_signals": [
            {
                "city": city,
                "snapshot_at": "2026-05-23T12:00:00+00:00",
                "signal_type": "none",
                "metric": "n/a",
                "observed": 0,
                "baseline": 0,
                "z_score": 0,
                "severity": "low",
                "message": "ok",
            }
        ],
    }
    silver_rows = [
        {
            "city": city,
            "period_number": 1,
            "period_name": "Today",
            "start_time": "2026-05-23T09:00:00-05:00",
            "end_time": "2026-05-23T18:00:00-05:00",
            "is_daytime": True,
            "temperature_f": 61,
            "precip_pct": 8,
            "short_forecast": "Fog",
            "wind_speed": "5 mph",
            "wind_direction": "N",
            "ingested_at": "2026-05-23T12:00:00+00:00",
            "bronze_file": "f.json",
        }
    ]

    monkeypatch.setattr(cfg, "DELTA", data)
    monkeypatch.setattr(cfg, "GENERATED", tmp_path / "generated")
    monkeypatch.setattr(exp, "DELTA", data)
    monkeypatch.setattr(exp, "GENERATED", tmp_path / "generated")

    from pulsegrid.io.delta_writer import write_delta_table

    for name, rows in table_rows.items():
        write_delta_table(rows, gold / name)
    write_delta_table(silver_rows, silver / "weather_forecast_periods")

    pbip = build_pbip(city, include_visuals=True)
    assert pbip.is_file()
    assert (
        pbip.parent / "ChicagoPulse.SemanticModel" / "definition" / "model.tmdl"
    ).is_file()
    pages_root = pbip.parent / "ChicagoPulse.Report" / "definition" / "pages"
    assert (pages_root / "pages.json").is_file()
    visual_files = list(pages_root.glob("*/visuals/*/visual.json"))
    assert (
        len(visual_files) >= 25
    ), f"expected at least 25 visuals after redesign, got {len(visual_files)}"

    tables_dir = (
        pbip.parent / "ChicagoPulse.SemanticModel" / "definition" / "tables"
    )
    names: list[str] = []
    import re

    for tmdl in tables_dir.glob("*.tmdl"):
        names.extend(
            re.findall(r"\tmeasure '([^']+)'", tmdl.read_text(encoding="utf-8"))
        )
    assert len(names) == len(set(names)), f"duplicate measure names: {names}"


def test_build_pbip_blank_pages(tmp_path, monkeypatch):
    import pulsegrid.config as cfg
    import pbip_generator.export_gold_csv as exp

    city = "chicago"
    data = tmp_path / "delta"
    gold = data / "gold"
    silver = data / "silver"
    monkeypatch.setattr(cfg, "DATA_ROOT", tmp_path / "local")
    table_rows = {
        "city_stress_index": [
            {
                "city": city,
                "snapshot_at": "2026-05-23T12:00:00+00:00",
                "city_stress_index": 50.0,
                "transit_load_score": 20.0,
                "weather_risk_score": 10.0,
                "precip_risk_score": 5.0,
                "disruption_ratio_score": 5.0,
                "active_transit_alerts": 10,
                "active_noaa_alerts": 1,
                "avg_precip_pct_next_periods": 12.0,
                "reroute_count": 5,
                "delay_count": 1,
            }
        ],
        "transit_alert_summary": [
            {
                "city": city,
                "snapshot_at": "2026-05-23T12:00:00+00:00",
                "alert_category": "reroute",
                "alert_count": 0,
            }
        ],
        "transit_alert_detail": [
            {
                "city": city,
                "snapshot_at": "2026-05-23T12:00:00+00:00",
                "hex_id": "hex-0",
                "neighborhood": "citywide",
                "alert_id": "none",
                "headline": "none",
                "short_description": "",
                "severity": "low",
                "service": "",
                "alert_category": "none",
            }
        ],
        "anomaly_signals": [
            {
                "city": city,
                "snapshot_at": "2026-05-23T12:00:00+00:00",
                "signal_type": "none",
                "metric": "n/a",
                "observed": 0,
                "baseline": 0,
                "z_score": 0,
                "severity": "low",
                "message": "ok",
            }
        ],
    }
    silver_rows = [
        {
            "city": city,
            "period_number": 1,
            "period_name": "Today",
            "start_time": "2026-05-23T09:00:00-05:00",
            "end_time": "2026-05-23T18:00:00-05:00",
            "is_daytime": True,
            "temperature_f": 61,
            "precip_pct": 8,
            "short_forecast": "Fog",
            "wind_speed": "5 mph",
            "wind_direction": "N",
            "ingested_at": "2026-05-23T12:00:00+00:00",
            "bronze_file": "f.json",
        }
    ]

    monkeypatch.setattr(cfg, "DELTA", data)
    monkeypatch.setattr(cfg, "GENERATED", tmp_path / "generated")
    monkeypatch.setattr(exp, "DELTA", data)
    monkeypatch.setattr(exp, "GENERATED", tmp_path / "generated")

    from pulsegrid.io.delta_writer import write_delta_table

    for name, rows in table_rows.items():
        write_delta_table(rows, gold / name)
    write_delta_table(silver_rows, silver / "weather_forecast_periods")

    pbip = build_pbip(city, include_visuals=False)
    pages_root = pbip.parent / "ChicagoPulse.Report" / "definition" / "pages"
    assert list(pages_root.glob("*/visuals/*/visual.json")) == []


def test_airport_ops_uses_dim_airport_not_direct_dim_metro(tmp_path):
    """Platform model: AirportOpsSnapshot -> DimAirport -> DimMetro only."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name in ("DimMetro", "DimAirport", "AirportOpsSnapshot"):
        (data_dir / f"{name}.csv").write_text("city\nchicago\n", encoding="utf-8")
    sm_def = tmp_path / "definition"
    sm_def.mkdir()
    _write_relationships(sm_def, data_dir)
    rel = (sm_def / "relationships.tmdl").read_text(encoding="utf-8")
    assert "fromColumn: AirportOpsSnapshot.station" in rel
    assert "fromColumn: DimAirport.city" in rel
    assert "fromColumn: AirportOpsSnapshot.city" not in rel
    _validate_relationship_paths(sm_def)
