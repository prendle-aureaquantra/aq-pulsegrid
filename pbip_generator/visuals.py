"""Programmatic PBIR visual.json generation for AQ PulseGrid reports."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.0.0/schema.json"
)
_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

GOLD = "#D4AF37"
CREAM = "#FFF8E7"
MUTED = "#D9C89A"
CHARCOAL = "#2C2C2C"


def _vid(seed: str) -> str:
    return uuid.uuid5(_NS, f"aq.pulsegrid.visual.{seed}").hex[:20]


def _lit(value: str) -> dict[str, Any]:
    return {"expr": {"Literal": {"Value": value}}}


def _col(entity: str, prop: str) -> dict[str, Any]:
    return {
        "Column": {
            "Expression": {"SourceRef": {"Entity": entity}},
            "Property": prop,
        }
    }


def _measure(entity: str, prop: str) -> dict[str, Any]:
    return {
        "Measure": {
            "Expression": {"SourceRef": {"Entity": entity}},
            "Property": prop,
        }
    }


def _proj_col(entity: str, prop: str, *, active: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "field": {"Column": _col(entity, prop)["Column"]},
        "queryRef": f"{entity}.{prop}",
    }
    if active:
        out["active"] = True
    return out


def _proj_measure(entity: str, prop: str) -> dict[str, Any]:
    return {
        "field": {"Measure": _measure(entity, prop)["Measure"]},
        "queryRef": f"{entity}.{prop}",
    }


def _proj_sum_col(entity: str, prop: str) -> dict[str, Any]:
    return {
        "field": {
            "Aggregation": {
                "Expression": _col(entity, prop),
                "Function": 0,
            }
        },
        "queryRef": f"Sum({entity}.{prop})",
    }


def _proj_avg_col(entity: str, prop: str) -> dict[str, Any]:
    return {
        "field": {
            "Aggregation": {
                "Expression": _col(entity, prop),
                "Function": 1,
            }
        },
        "queryRef": f"Average({entity}.{prop})",
    }


def _container(
    name: str,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    z: int,
    tab_order: int,
    visual: dict[str, Any],
) -> dict[str, Any]:
    return {
        "$schema": VISUAL_SCHEMA,
        "name": name,
        "position": {
            "x": x,
            "y": y,
            "z": z,
            "height": height,
            "width": width,
            "tabOrder": tab_order,
        },
        "visual": visual,
    }


def _chart_title(title: str) -> dict[str, Any]:
    return {
        "visualContainerObjects": {
            "title": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "text": _lit(f"'{title}'"),
                        "fontColor": {"solid": {"color": GOLD}},
                        "fontSize": _lit("12D"),
                        "bold": _lit("true"),
                    }
                }
            ],
            "background": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "color": {"solid": {"color": CHARCOAL}},
                        "transparency": _lit("0D"),
                    }
                }
            ],
            "border": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "color": {"solid": {"color": GOLD}},
                        "radius": _lit("8D"),
                    }
                }
            ],
        }
    }


def _textbox(
    lines: list[tuple[str, str, str]],
    *,
    font_size: str = "22pt",
) -> dict[str, Any]:
    """lines: list of (text, color, weight) where weight is '' or 'bold'."""
    text_runs = []
    for text, color, weight in lines:
        style: dict[str, Any] = {
            "fontFamily": "Segoe UI",
            "fontSize": font_size,
            "color": color,
        }
        if weight:
            style["fontWeight"] = weight
        text_runs.append({"value": text, "textStyle": style})
    return {
        "visualType": "textbox",
        "objects": {
            "general": [{"properties": {"paragraphs": [{"textRuns": text_runs}]}}]
        },
        "drillFilterOtherVisuals": True,
    }


def _card_visual(measures: list[tuple[str, str]], *, columns: int) -> dict[str, Any]:
    return {
        "visualType": "cardVisual",
        "query": {
            "queryState": {
                "Data": {
                    "projections": [_proj_measure(entity, measure) for entity, measure in measures],
                }
            }
        },
        "objects": {
            "layout": [
                {
                    "properties": {
                        "orientation": _lit("0D"),
                        "columnCount": _lit(f"{columns}L"),
                        "style": _lit("'Cards'"),
                    }
                }
            ],
            "value": [
                {
                    "properties": {
                        "fontSize": _lit("32D"),
                        "fontColor": {"solid": {"color": CREAM}},
                    },
                    "selector": {"id": "default"},
                }
            ],
            "label": [
                {
                    "properties": {
                        "fontColor": {"solid": {"color": GOLD}},
                    },
                    "selector": {"id": "default"},
                }
            ],
            "accentBar": [
                {
                    "properties": {"show": _lit("true")},
                    "selector": {"id": "default"},
                }
            ],
        },
        "visualContainerObjects": {
            "background": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "color": {"solid": {"color": CHARCOAL}},
                    }
                }
            ],
            "border": [
                {
                    "properties": {
                        "show": _lit("true"),
                        "color": {"solid": {"color": GOLD}},
                        "radius": _lit("8D"),
                    }
                }
            ],
            "title": [{"properties": {"show": _lit("false")}}],
        },
        "drillFilterOtherVisuals": True,
    }


def _hero_card(entity: str, measure: str, *, title: str) -> dict[str, Any]:
    body = _card_visual([(entity, measure)], columns=1)
    body["visualContainerObjects"]["title"] = [
        {
            "properties": {
                "show": _lit("true"),
                "text": _lit(f"'{title}'"),
                "fontColor": {"solid": {"color": GOLD}},
                "fontSize": _lit("11D"),
            }
        }
    ]
    return body


def _clustered_bar(
    entity: str,
    category: str,
    value_col: str,
    *,
    title: str,
    avg: bool = False,
) -> dict[str, Any]:
    y_proj = _proj_avg_col(entity, value_col) if avg else _proj_sum_col(entity, value_col)
    visual: dict[str, Any] = {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": {
                "Category": {
                    "projections": [_proj_col(entity, category, active=True)],
                },
                "Y": {"projections": [y_proj]},
            }
        },
        "drillFilterOtherVisuals": True,
    }
    visual.update(_chart_title(title))
    return visual


def _multi_row_card(entity: str, columns: list[str], *, title: str) -> dict[str, Any]:
    visual: dict[str, Any] = {
        "visualType": "multiRowCard",
        "query": {
            "queryState": {
                "Values": {
                    "projections": [_proj_col(entity, col) for col in columns],
                }
            }
        },
        "drillFilterOtherVisuals": True,
    }
    visual.update(_chart_title(title))
    return visual


def _page_header(title: str, subtitle: str) -> list[tuple[str, dict[str, Any]]]:
    return [
        (
            _vid(f"hdr.{title}"),
            _container(
                _vid(f"hdr.{title}"),
                x=24,
                y=12,
                width=760,
                height=52,
                z=9000,
                tab_order=9000,
                visual=_textbox(
                    [(title, GOLD, "bold")],
                    font_size="26pt",
                ),
            ),
        ),
        (
            _vid(f"sub.{title}"),
            _container(
                _vid(f"sub.{title}"),
                x=800,
                y=16,
                width=456,
                height=44,
                z=9001,
                tab_order=9001,
                visual=_textbox(
                    [(subtitle, MUTED, "")],
                    font_size="11pt",
                ),
            ),
        ),
    ]


def visuals_for_page(
    page_seed: str,
    *,
    available_tables: set[str] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """Return (visual_folder_id, visual_container_dict) for a report page seed."""
    avail = available_tables or set()

    def _has(*tables: str) -> bool:
        return all(t in avail for t in tables)

    if page_seed == "page.live-pulse":
        items = _page_header(
            "Chicago Live City Pulse",
            "AQ PulseGrid · streaming public data · ML stress index",
        )
        items.extend(
            [
                (
                    _vid("live.kpi-row"),
                    _container(
                        _vid("live.kpi-row"),
                        x=24,
                        y=76,
                        width=900,
                        height=148,
                        z=2000,
                        tab_order=2000,
                        visual=_card_visual(
                            [
                                ("CityPulseSnapshot", "City Stress Index"),
                                ("CityPulseSnapshot", "Active CTA Alerts"),
                                ("CityPulseSnapshot", "Active NOAA Alerts"),
                            ],
                            columns=3,
                        ),
                    ),
                ),
                (
                    _vid("live.anomaly-hero"),
                    _container(
                        _vid("live.anomaly-hero"),
                        x=940,
                        y=76,
                        width=316,
                        height=148,
                        z=2100,
                        tab_order=2100,
                        visual=_hero_card(
                            "AnomalySignals",
                            "Anomaly Count",
                            title="ML Anomalies",
                        ),
                    ),
                ),
                (
                    _vid("live.scores"),
                    _container(
                        _vid("live.scores"),
                        x=24,
                        y=236,
                        width=1232,
                        height=100,
                        z=2200,
                        tab_order=2200,
                        visual=_card_visual(
                            [
                                ("CityPulseSnapshot", "Transit Load Score"),
                                ("CityPulseSnapshot", "Weather Risk Score"),
                                ("CityPulseSnapshot", "Avg Precip %"),
                            ],
                            columns=3,
                        ),
                    ),
                ),
                (
                    _vid("live.anomalies"),
                    _container(
                        _vid("live.anomalies"),
                        x=24,
                        y=348,
                        width=1232,
                        height=348,
                        z=3000,
                        tab_order=3000,
                        visual=_multi_row_card(
                            "AnomalySignals",
                            ["signal_type", "metric", "severity", "z_score", "message"],
                            title="Active anomaly signals",
                        ),
                    ),
                ),
            ]
        )
        return items

    if page_seed == "page.transit":
        items = _page_header(
            "Transit & Mobility",
            "CTA alert categories · hex neighborhood grid",
        )
        items.append(
            (
                _vid("transit.bars"),
                _container(
                    _vid("transit.bars"),
                    x=24,
                    y=76,
                    width=600 if _has("HexPulseGrid") else 1232,
                    height=620,
                    z=2000,
                    tab_order=2000,
                    visual=_clustered_bar(
                        "TransitAlertSummary",
                        "alert_category",
                        "alert_count",
                        title="CTA alerts by category",
                    ),
                ),
            )
        )
        if _has("HexPulseGrid"):
            items.append(
                (
                    _vid("transit.hex"),
                    _container(
                        _vid("transit.hex"),
                        x=656,
                        y=76,
                        width=600,
                        height=620,
                        z=2100,
                        tab_order=2100,
                        visual=_clustered_bar(
                            "HexPulseGrid",
                            "neighborhood",
                            "alert_count",
                            title="Alerts by hex / neighborhood",
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.weather":
        items = _page_header(
            "Weather Impact Analysis",
            "NOAA forecast periods · precip & temperature",
        )
        items.extend(
            [
                (
                    _vid("weather.precip"),
                    _container(
                        _vid("weather.precip"),
                        x=24,
                        y=76,
                        width=600,
                        height=620,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar(
                            "WeatherForecastPeriods",
                            "period_name",
                            "precip_pct",
                            title="Precipitation chance %",
                        ),
                    ),
                ),
                (
                    _vid("weather.temp"),
                    _container(
                        _vid("weather.temp"),
                        x=656,
                        y=76,
                        width=600,
                        height=620,
                        z=2100,
                        tab_order=2100,
                        visual=_clustered_bar(
                            "WeatherForecastPeriods",
                            "period_name",
                            "temperature_f",
                            title="Temperature (°F)",
                            avg=True,
                        ),
                    ),
                ),
            ]
        )
        return items

    if page_seed == "page.airport":
        items = _page_header("Airport Operations", "O'Hare METAR · ops stress scoring")
        if _has("AirportOpsSnapshot"):
            items.append(
                (
                    _vid("airport.hero"),
                    _container(
                        _vid("airport.hero"),
                        x=24,
                        y=76,
                        width=400,
                        height=620,
                        z=2000,
                        tab_order=2000,
                        visual=_hero_card(
                            "AirportOpsSnapshot",
                            "ORD Ops Stress",
                            title="O'Hare ops stress",
                        ),
                    ),
                )
            )
            items.append(
                (
                    _vid("airport.kpi"),
                    _container(
                        _vid("airport.kpi"),
                        x=440,
                        y=76,
                        width=816,
                        height=148,
                        z=2100,
                        tab_order=2100,
                        visual=_card_visual(
                            [
                                ("CityPulseSnapshot", "Airport Visibility (sm)"),
                                ("CityPulseSnapshot", "Active NOAA Alerts"),
                                ("CityPulseSnapshot", "City Stress Index"),
                            ],
                            columns=3,
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.events":
        items = _page_header("Event Heatmaps", "Concerts · festivals · public events by neighborhood")
        if _has("EventHeatmap"):
            items.append(
                (
                    _vid("events.heat"),
                    _container(
                        _vid("events.heat"),
                        x=24,
                        y=76,
                        width=1232,
                        height=620,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar(
                            "EventHeatmap",
                            "neighborhood",
                            "event_count",
                            title="Events by neighborhood / hex",
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.ai-signals":
        items = _page_header("AI Signal Detection", "ML anomalies · z-scores · severity")
        items.append(
            (
                _vid("ai.hero"),
                _container(
                    _vid("ai.hero"),
                    x=24,
                    y=76,
                    width=316,
                    height=148,
                    z=2000,
                    tab_order=2000,
                    visual=_hero_card("AnomalySignals", "Anomaly Count", title="Active anomalies"),
                ),
            )
        )
        items.append(
            (
                _vid("ai.table"),
                _container(
                    _vid("ai.table"),
                    x=24,
                    y=236,
                    width=1232,
                    height=460,
                    z=3000,
                    tab_order=3000,
                    visual=_multi_row_card(
                        "AnomalySignals",
                        ["signal_type", "metric", "severity", "z_score", "message"],
                        title="Anomaly signal feed",
                    ),
                ),
            )
        )
        return items

    if page_seed == "page.streaming":
        items = _page_header("Streaming Monitor", "Bronze ingest telemetry · batch counts by source")
        if _has("StreamingTelemetry"):
            items.append(
                (
                    _vid("stream.bars"),
                    _container(
                        _vid("stream.bars"),
                        x=24,
                        y=76,
                        width=1232,
                        height=620,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar(
                            "StreamingTelemetry",
                            "source",
                            "batch_count",
                            title="Ingest batches by source",
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.macro":
        items = _page_header("Macro & Trends", "FRED macro · Google Trends interest")
        if _has("FredMacroSnapshot"):
            items.append(
                (
                    _vid("macro.fred"),
                    _container(
                        _vid("macro.fred"),
                        x=24,
                        y=76,
                        width=600 if _has("TrendInterestSummary") else 1232,
                        height=620,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar(
                            "FredMacroSnapshot",
                            "series_label",
                            "latest_value",
                            title="FRED macro indicators",
                        ),
                    ),
                )
            )
        if _has("TrendInterestSummary"):
            items.append(
                (
                    _vid("macro.trends"),
                    _container(
                        _vid("macro.trends"),
                        x=656 if _has("FredMacroSnapshot") else 24,
                        y=76,
                        width=600 if _has("FredMacroSnapshot") else 1232,
                        height=620,
                        z=2100,
                        tab_order=2100,
                        visual=_clustered_bar(
                            "TrendInterestSummary",
                            "keyword",
                            "avg_interest",
                            title="Google Trends avg interest",
                            avg=True,
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.studio":
        items = _page_header("PBIP Generator Studio", "Semantic model catalog · metadata-driven automation")
        if _has("PbipStudioCatalog"):
            items.append(
                (
                    _vid("studio.catalog"),
                    _container(
                        _vid("studio.catalog"),
                        x=24,
                        y=76,
                        width=1232,
                        height=620,
                        z=2000,
                        tab_order=2000,
                        visual=_multi_row_card(
                            "PbipStudioCatalog",
                            ["table_name", "source_path", "column_count", "columns_list"],
                            title="Generated semantic model catalog",
                        ),
                    ),
                )
            )
        return items

    return []


def write_page_visuals(
    page_dir: Path,
    page_seed: str,
    *,
    available_tables: set[str] | None = None,
) -> int:
    """Write visual.json files under page_dir/visuals/. Returns count written."""
    specs = visuals_for_page(page_seed, available_tables=available_tables)
    visuals_root = page_dir / "visuals"
    visuals_root.mkdir(parents=True, exist_ok=True)
    count = 0
    for folder_id, payload in specs:
        vdir = visuals_root / folder_id
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "visual.json").write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        count += 1
    return count
