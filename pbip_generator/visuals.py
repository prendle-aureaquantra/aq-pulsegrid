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
DEEP_BG = "#0D1117"
ACCENT = "#3D5A80"

# Canvas 1280×720 — shared layout grid (FitToPage)
HDR_Y, HDR_H = 8, 48
SUB_Y, SUB_H = 58, 34
BODY_Y = 100
MARGIN_X = 24
FULL_W = 1232
HALF_W = 608
THIRD_W = 400
TWO_THIRD_W = 816
PAGE_H = 620

PAGE_HEADER_CONFIG: dict[str, tuple[str, str, str]] = {
    "page.live-pulse": (
        "Operational Command Center",
        "Bronze → silver → gold Delta · ML City Stress Index · 71 metros · cross-domain KPIs",
        "Header Live Pulse",
    ),
    "page.metro-compare": (
        "Worldwide Metro Comparison",
        "Compare stress, transit, anomalies & infrastructure across all PulseGrid metros",
        "Header Metro Compare",
    ),
    "page.geospatial": (
        "Geospatial Intelligence",
        "H3 hex grid · neighborhood resolution · transit & event density",
        "Header Geospatial",
    ),
    "page.transit": (
        "Transit & Mobility",
        "GTFS-RT alerts · station/route/street geo enrichment · drill category ↔ neighborhood",
        "Header Transit",
    ),
    "page.infrastructure": (
        "Infrastructure Risk",
        "Civic 311 · bridge / road / structural fatigue & failure scoring",
        "Header Infrastructure",
    ),
    "page.weather": (
        "Weather & Environment",
        "NOAA alerts · forecast periods · precip & temperature risk components",
        "Header Weather",
    ),
    "page.airport": (
        "Multi-Station Airport Ops",
        "METAR per metro · flight category · visibility · ops stress rollup",
        "Header Airport",
    ),
    "page.events": (
        "Events & Activity",
        "Venue & festival signals · neighborhood drill · event detail list",
        "Header Events",
    ),
    "page.ai-signals": (
        "Anomaly Detection Engine",
        "Z-score baselines · severity tiers · multi-signal operational spikes",
        "Header AI Signals",
    ),
    "page.streaming": (
        "Data Pipeline Monitor",
        "Bronze ingest telemetry · batch counts · source freshness",
        "Header Streaming",
    ),
    "page.macro": (
        "Macro & Social Trends",
        "FRED macro series · Google Trends interest · regional context",
        "Header Macro",
    ),
    "page.studio": (
        "Semantic Model Studio",
        "Auto-generated TMDL · table catalog · PBIP metadata",
        "Header Studio",
    ),
}


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


METRO_SLICER_VISUAL_NAME = "aq_pulsegrid_metro_slicer"
# Same groupName on every page → View → Sync slicers (PBIR: visual.syncGroup).
METRO_SLICER_SYNC_GROUP = "DimMetro.metro_label"


def _slicer(
    entity: str,
    column: str,
    *,
    dropdown: bool = False,
    searchable: bool = False,
    title: str = "Metro",
    sync_group_name: str | None = None,
) -> dict[str, Any]:
    """Slicer visual; use dropdown=True for long lists (71 metros)."""
    col_proj = _proj_col(entity, column, active=True)
    objects: dict[str, Any] = {
        "header": [
            {
                "properties": {
                    "show": _lit("true"),
                    "title": _lit(f"'{title}'"),
                    "fontColor": {"solid": {"color": GOLD}},
                    "fontSize": _lit("11D"),
                    "bold": _lit("true"),
                }
            }
        ],
        "items": [
            {
                "properties": {
                    "fontColor": {"solid": {"color": CREAM}},
                    "background": {"solid": {"color": DEEP_BG}},
                    "textSize": _lit("10D"),
                }
            }
        ],
    }
    if dropdown:
        objects["data"] = [{"properties": {"mode": _lit("'Dropdown'")}}]
        objects["selection"] = [
            {
                "properties": {
                    "singleSelect": _lit("false"),
                    "selectAllCheckboxEnabled": _lit("true"),
                    "strictSingleSelect": _lit("false"),
                }
            }
        ]
        if searchable:
            objects["general"] = [
                {"properties": {"selfFilterEnabled": _lit("true")}}
            ]
    else:
        objects["general"] = [{"properties": {"orientation": _lit("1D")}}]

    query: dict[str, Any] = {
        "queryState": {
            "Values": {"projections": [col_proj]},
        },
        "sortDefinition": {
            "sort": [
                {
                    "field": col_proj["field"],
                    "direction": "Ascending",
                }
            ],
            "isDefaultSort": True,
        },
    }

    out: dict[str, Any] = {
        "visualType": "slicer",
        "query": query,
        "objects": objects,
        "visualContainerObjects": {
            "title": [
                {
                    "properties": {
                        "show": _lit("false"),
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
            "padding": [
                {
                    "properties": {
                        "top": _lit("4D"),
                        "bottom": _lit("4D"),
                        "left": _lit("8D"),
                        "right": _lit("8D"),
                    }
                }
            ],
        },
        "drillFilterOtherVisuals": True,
    }
    if sync_group_name:
        out["syncGroup"] = {
            "groupName": sync_group_name,
            "fieldChanges": True,
            "filterChanges": True,
        }
    return out


def _metro_slicer_container(page_seed: str) -> tuple[str, dict[str, Any]]:
    """Top-right searchable dropdown; syncGroup links selection across all pages."""
    return (
        _vid(f"metro.slicer.{page_seed}"),
        _container(
            METRO_SLICER_VISUAL_NAME,
            x=884,
            y=8,
            width=372,
            height=60,
            z=10000,
            tab_order=10000,
            visual=_slicer(
                "DimMetro",
                "metro_label",
                dropdown=True,
                searchable=True,
                title="Metro (71 worldwide)",
                sync_group_name=METRO_SLICER_SYNC_GROUP,
            ),
        ),
    )


def _text_measure_card(
    entity: str,
    measure: str,
    *,
    font_size: str = "22D",
    color: str = GOLD,
    hide_label: bool = True,
) -> dict[str, Any]:
    """Single-measure card for dynamic DAX text (metro-aware headers)."""
    objects: dict[str, Any] = {
        "value": [
            {
                "properties": {
                    "fontSize": _lit(font_size),
                    "fontColor": {"solid": {"color": color}},
                    "bold": _lit("true"),
                },
                "selector": {"id": "default"},
            }
        ],
        "accentBar": [
            {"properties": {"show": _lit("false")}, "selector": {"id": "default"}}
        ],
    }
    if hide_label:
        objects["label"] = [
            {"properties": {"show": _lit("false")}, "selector": {"id": "default"}}
        ]
    return {
        "visualType": "cardVisual",
        "query": {
            "queryState": {
                "Data": {"projections": [_proj_measure(entity, measure)]},
            }
        },
        "objects": objects,
        "visualContainerObjects": {
            "background": [{"properties": {"show": _lit("false")}}],
            "border": [{"properties": {"show": _lit("false")}}],
            "title": [{"properties": {"show": _lit("false")}}],
            "padding": [{"properties": {"top": _lit("0D"), "left": _lit("0D")}}],
        },
        "drillFilterOtherVisuals": False,
    }


def _page_header(
    title: str,
    subtitle: str,
    *,
    platform_mode: bool = False,
    has_dim_metro: bool = False,
    title_measure: str = "Header Live Pulse",
) -> list[tuple[str, dict[str, Any]]]:
    if platform_mode and has_dim_metro:
        return [
            (
                _vid(f"hdr.dyn.{title_measure}"),
                _container(
                    _vid(f"hdr.dyn.{title_measure}"),
                    x=24,
                    y=8,
                    width=848,
                    height=56,
                    z=9000,
                    tab_order=9000,
                    visual=_text_measure_card(
                        "DimMetro", title_measure, font_size="24D", color=GOLD
                    ),
                ),
            ),
        ]
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


def _page_header_for(
    page_seed: str,
    *,
    platform_mode: bool = False,
    has_dim_metro: bool = False,
) -> list[tuple[str, dict[str, Any]]]:
    static_title, static_subtitle, title_measure = PAGE_HEADER_CONFIG[page_seed]
    items = _page_header(
        static_title,
        static_subtitle,
        platform_mode=platform_mode,
        has_dim_metro=has_dim_metro,
        title_measure=title_measure,
    )
    if platform_mode and has_dim_metro:
        items.append(
            (
                _vid(f"sub.dyn.{page_seed}"),
                _container(
                    _vid(f"sub.dyn.{page_seed}"),
                    x=MARGIN_X,
                    y=SUB_Y,
                    width=848,
                    height=SUB_H,
                    z=8999,
                    tab_order=8999,
                    visual=_text_measure_card(
                        "DimMetro",
                        "Selected Metro Subtitle",
                        font_size="11D",
                        color=MUTED,
                    ),
                ),
            )
        )
    elif not platform_mode:
        items.append(
            (
                _vid(f"ctx.{page_seed}"),
                _container(
                    _vid(f"ctx.{page_seed}"),
                    x=MARGIN_X,
                    y=SUB_Y,
                    width=FULL_W,
                    height=SUB_H,
                    z=8998,
                    tab_order=8998,
                    visual=_textbox(
                        [(static_subtitle, MUTED, "")],
                        font_size="10pt",
                    ),
                ),
            )
        )
    return items


def _clustered_bar_measure(
    category_entity: str,
    category: str,
    measure_entity: str,
    measure: str,
    *,
    title: str,
    drill_categories: list[str] | None = None,
) -> dict[str, Any]:
    """Bar chart with DAX measure on Y (cross-table via relationships)."""
    cats = drill_categories or [category]
    visual: dict[str, Any] = {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": {
                "Category": {
                    "projections": [
                        _proj_col(category_entity, cat, active=(i == 0))
                        for i, cat in enumerate(cats)
                    ],
                },
                "Y": {"projections": [_proj_measure(measure_entity, measure)]},
            }
        },
        "drillFilterOtherVisuals": True,
    }
    visual.update(_chart_title(title))
    return visual


def _stacked_bar_drill(
    category_entity: str,
    categories: list[str],
    legend_entity: str,
    legend: str,
    measure_entity: str,
    measure: str,
    *,
    title: str,
) -> dict[str, Any]:
    """Stacked bar with drill hierarchy on category + legend series."""
    visual: dict[str, Any] = {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": {
                "Category": {
                    "projections": [
                        _proj_col(category_entity, cat, active=(i == 0))
                        for i, cat in enumerate(categories)
                    ],
                },
                "Series": {
                    "projections": [_proj_col(legend_entity, legend, active=True)],
                },
                "Y": {"projections": [_proj_measure(measure_entity, measure)]},
            }
        },
        "drillFilterOtherVisuals": True,
    }
    visual.update(_chart_title(title))
    return visual


def _clustered_bar_drill_col(
    entity: str,
    categories: list[str],
    value_col: str,
    *,
    title: str,
    avg: bool = False,
) -> dict[str, Any]:
    """Drill bar chart aggregating a numeric column (no table measure required)."""
    y_proj = _proj_avg_col(entity, value_col) if avg else _proj_sum_col(entity, value_col)
    visual: dict[str, Any] = {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": {
                "Category": {
                    "projections": [
                        _proj_col(entity, cat, active=(i == 0))
                        for i, cat in enumerate(categories)
                    ],
                },
                "Y": {"projections": [y_proj]},
            }
        },
        "drillFilterOtherVisuals": True,
    }
    visual.update(_chart_title(title))
    return visual


def _card_visual(measures: list[tuple[str, str]], *, columns: int) -> dict[str, Any]:
    return {
        "visualType": "cardVisual",
        "query": {
            "queryState": {
                "Data": {
                    "projections": [
                        _proj_measure(entity, measure) for entity, measure in measures
                    ],
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


def _clustered_bar_drill(
    entity: str,
    categories: list[str],
    measure: str,
    *,
    title: str,
) -> dict[str, Any]:
    """Bar chart with axis drill hierarchy (e.g. neighborhood → category)."""
    visual: dict[str, Any] = {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": {
                "Category": {
                    "projections": [
                        _proj_col(entity, cat, active=(i == 0))
                        for i, cat in enumerate(categories)
                    ],
                },
                "Y": {"projections": [_proj_measure(entity, measure)]},
            }
        },
        "drillFilterOtherVisuals": True,
    }
    visual.update(_chart_title(title))
    return visual


def _clustered_bar(
    entity: str,
    category: str,
    value_col: str,
    *,
    title: str,
    avg: bool = False,
) -> dict[str, Any]:
    y_proj = (
        _proj_avg_col(entity, value_col) if avg else _proj_sum_col(entity, value_col)
    )
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


def visuals_for_page(
    page_seed: str,
    *,
    available_tables: set[str] | None = None,
    platform_mode: bool = False,
) -> list[tuple[str, dict[str, Any]]]:
    """Return (visual_folder_id, visual_container_dict) for a report page seed."""
    avail = available_tables or set()

    def _has(*tables: str) -> bool:
        return all(t in avail for t in tables)

    has_dim = "DimMetro" in avail

    if page_seed == "page.live-pulse":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        items.append(
            (
                _vid("live.hero.stress"),
                _container(
                    _vid("live.hero.stress"),
                    x=MARGIN_X,
                    y=y,
                    width=280,
                    height=168,
                    z=2000,
                    tab_order=2000,
                    visual=_hero_card(
                        "CityPulseSnapshot",
                        "City Stress Index",
                        title="City Stress Index (0–100)",
                    ),
                ),
            )
        )
        primary_kpis: list[tuple[str, str]] = [
            ("CityPulseSnapshot", "Active Transit Alerts"),
            ("CityPulseSnapshot", "Active NOAA Alerts"),
            ("AnomalySignals", "Anomaly Count"),
        ]
        items.append(
            (
                _vid("live.kpi.primary"),
                _container(
                    _vid("live.kpi.primary"),
                    x=320,
                    y=y,
                    width=640,
                    height=168,
                    z=2100,
                    tab_order=2100,
                    visual=_card_visual(primary_kpis, columns=3),
                ),
            )
        )
        if _has("InfrastructureRiskSnapshot"):
            items.append(
                (
                    _vid("live.hero.infra"),
                    _container(
                        _vid("live.hero.infra"),
                        x=980,
                        y=y,
                        width=276,
                        height=168,
                        z=2200,
                        tab_order=2200,
                        visual=_hero_card(
                            "InfrastructureRiskSnapshot",
                            "Max Infrastructure Failure Risk",
                            title="Infrastructure failure risk",
                        ),
                    ),
                )
            )
        elif _has("AirportOpsSnapshot"):
            items.append(
                (
                    _vid("live.hero.airport"),
                    _container(
                        _vid("live.hero.airport"),
                        x=980,
                        y=y,
                        width=276,
                        height=168,
                        z=2200,
                        tab_order=2200,
                        visual=_hero_card(
                            "AirportOpsSnapshot",
                            "Max Airport Ops Stress",
                            title="Worst airport ops stress",
                        ),
                    ),
                )
            )
        y2 = y + 184
        domain_kpis: list[tuple[str, str]] = [
            ("CityPulseSnapshot", "Transit Load Score"),
            ("CityPulseSnapshot", "Weather Risk Score"),
            ("CityPulseSnapshot", "Precip Risk Score"),
            ("CityPulseSnapshot", "Disruption Ratio Score"),
            ("CityPulseSnapshot", "Metro Airport Ops Stress"),
            ("CityPulseSnapshot", "Infrastructure Fatigue Risk"),
        ]
        items.append(
            (
                _vid("live.domain.ribbon"),
                _container(
                    _vid("live.domain.ribbon"),
                    x=MARGIN_X,
                    y=y2,
                    width=FULL_W,
                    height=108,
                    z=2300,
                    tab_order=2300,
                    visual=_card_visual(domain_kpis, columns=6),
                ),
            )
        )
        y3 = y2 + 124
        if _has("AnomalySignals"):
            items.append(
                (
                    _vid("live.anomaly.types"),
                    _container(
                        _vid("live.anomaly.types"),
                        x=MARGIN_X,
                        y=y3,
                        width=HALF_W,
                        height=240,
                        z=3000,
                        tab_order=3000,
                        visual=_clustered_bar_drill(
                            "AnomalySignals",
                            ["signal_type", "severity"],
                            "Anomaly Count",
                            title="Anomalies by signal type → severity",
                        ),
                    ),
                )
            )
        if _has("TransitAlertSummary"):
            items.append(
                (
                    _vid("live.transit.cats"),
                    _container(
                        _vid("live.transit.cats"),
                        x=656,
                        y=y3,
                        width=HALF_W,
                        height=240,
                        z=3100,
                        tab_order=3100,
                        visual=_clustered_bar(
                            "TransitAlertSummary",
                            "alert_category",
                            "alert_count",
                            title="Transit disruption mix",
                        ),
                    ),
                )
            )
        y4 = y3 + 256
        if _has("AnomalySignals"):
            items.append(
                (
                    _vid("live.anomaly.feed"),
                    _container(
                        _vid("live.anomaly.feed"),
                        x=MARGIN_X,
                        y=y4,
                        width=FULL_W,
                        height=PAGE_H - (y4 - BODY_Y),
                        z=4000,
                        tab_order=4000,
                        visual=_multi_row_card(
                            "AnomalySignals",
                            [
                                "signal_type",
                                "metric",
                                "severity",
                                "z_score",
                                "observed",
                                "baseline",
                                "message",
                            ],
                            title="Anomaly signal feed (z-score vs baseline)",
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.metro-compare":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        if not _has("DimMetro", "CityPulseSnapshot"):
            return items
        y = BODY_Y
        items.append(
            (
                _vid("metro.stress.rank"),
                _container(
                    _vid("metro.stress.rank"),
                    x=MARGIN_X,
                    y=y,
                    width=FULL_W,
                    height=300,
                    z=2000,
                    tab_order=2000,
                    visual=_clustered_bar_measure(
                        "DimMetro",
                        "display_name",
                        "CityPulseSnapshot",
                        "City Stress Index",
                        title="City Stress Index by metro (clear slicer to compare all)",
                        drill_categories=["tier", "display_name"],
                    ),
                ),
            )
        )
        y2 = y + 316
        items.append(
            (
                _vid("metro.transit.rank"),
                _container(
                    _vid("metro.transit.rank"),
                    x=MARGIN_X,
                    y=y2,
                    width=HALF_W,
                    height=280,
                    z=2100,
                    tab_order=2100,
                    visual=_clustered_bar_measure(
                        "DimMetro",
                        "display_name",
                        "CityPulseSnapshot",
                        "Active Transit Alerts",
                        title="Active transit alerts by metro",
                    ),
                ),
            )
        )
        if _has("AnomalySignals"):
            items.append(
                (
                    _vid("metro.anomaly.rank"),
                    _container(
                        _vid("metro.anomaly.rank"),
                        x=656,
                        y=y2,
                        width=HALF_W,
                        height=280,
                        z=2200,
                        tab_order=2200,
                        visual=_clustered_bar_measure(
                            "DimMetro",
                            "display_name",
                            "AnomalySignals",
                            "Anomaly Count",
                            title="Anomaly count by metro",
                        ),
                    ),
                )
            )
        y3 = y2 + 296
        infra_measures: list[tuple[str, str]] = [
            ("CityPulseSnapshot", "Infrastructure Failure Risk"),
            ("CityPulseSnapshot", "Infrastructure Fatigue Risk"),
            ("CityPulseSnapshot", "Bridge Risk Score"),
            ("CityPulseSnapshot", "Metro Airport Ops Stress"),
        ]
        items.append(
            (
                _vid("metro.domain.compare"),
                _container(
                    _vid("metro.domain.compare"),
                    x=MARGIN_X,
                    y=y3,
                    width=FULL_W,
                    height=PAGE_H - (y3 - BODY_Y),
                    z=3000,
                    tab_order=3000,
                    visual=_card_visual(infra_measures, columns=4),
                ),
            )
        )
        return items

    if page_seed == "page.geospatial":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("HexPulseGrid"):
            items.append(
                (
                    _vid("geo.hex.alerts"),
                    _container(
                        _vid("geo.hex.alerts"),
                        x=MARGIN_X,
                        y=y,
                        width=HALF_W,
                        height=280,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar_drill_col(
                            "HexPulseGrid",
                            ["neighborhood", "hex_id"],
                            "alert_count",
                            title="Transit alert density · neighborhood → hex",
                        ),
                    ),
                )
            )
        if _has("EventHeatmap"):
            items.append(
                (
                    _vid("geo.events.heat"),
                    _container(
                        _vid("geo.events.heat"),
                        x=656,
                        y=y,
                        width=HALF_W,
                        height=280,
                        z=2100,
                        tab_order=2100,
                        visual=_clustered_bar_drill_col(
                            "EventHeatmap",
                            ["neighborhood", "event_category"],
                            "event_count",
                            title="Event density · neighborhood → category",
                        ),
                    ),
                )
            )
        y2 = y + 296
        if _has("TransitAlertDetail"):
            items.append(
                (
                    _vid("geo.transit.hoods"),
                    _container(
                        _vid("geo.transit.hoods"),
                        x=MARGIN_X,
                        y=y2,
                        width=FULL_W,
                        height=240,
                        z=3000,
                        tab_order=3000,
                        visual=_clustered_bar_drill(
                            "TransitAlertDetail",
                            ["neighborhood", "alert_category"],
                            "Transit Alert Count",
                            title="Neighborhood operational hotspots (transit)",
                        ),
                    ),
                )
            )
        y3 = y2 + 256
        if _has("CityEventDetail"):
            items.append(
                (
                    _vid("geo.events.detail"),
                    _container(
                        _vid("geo.events.detail"),
                        x=MARGIN_X,
                        y=y3,
                        width=FULL_W,
                        height=PAGE_H - (y3 - BODY_Y),
                        z=4000,
                        tab_order=4000,
                        visual=_multi_row_card(
                            "CityEventDetail",
                            [
                                "event_name",
                                "event_category",
                                "neighborhood",
                                "location",
                                "start_date",
                            ],
                            title="Event detail (geospatial filter)",
                        ),
                    ),
                )
            )
        elif _has("HexPulseGrid"):
            items.append(
                (
                    _vid("geo.hex.table"),
                    _container(
                        _vid("geo.hex.table"),
                        x=MARGIN_X,
                        y=y3,
                        width=FULL_W,
                        height=PAGE_H - (y3 - BODY_Y),
                        z=4000,
                        tab_order=4000,
                        visual=_multi_row_card(
                            "HexPulseGrid",
                            [
                                "neighborhood",
                                "hex_id",
                                "alert_count",
                                "reroute_count",
                                "delay_count",
                            ],
                            title="Hex pulse grid detail",
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.transit":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("CityPulseSnapshot"):
            items.append(
                (
                    _vid("transit.kpi"),
                    _container(
                        _vid("transit.kpi"),
                        x=MARGIN_X,
                        y=y,
                        width=FULL_W,
                        height=96,
                        z=1500,
                        tab_order=1500,
                        visual=_card_visual(
                            [
                                ("CityPulseSnapshot", "Active Transit Alerts"),
                                ("CityPulseSnapshot", "Transit Load Score"),
                                ("CityPulseSnapshot", "Disruption Ratio Score"),
                                ("CityPulseSnapshot", "Reroute Count"),
                            ],
                            columns=4,
                        ),
                    ),
                )
            )
            y += 112
        if _has("TransitAlertDetail"):
            items.append(
                (
                    _vid("transit.drill.cat"),
                    _container(
                        _vid("transit.drill.cat"),
                        x=MARGIN_X,
                        y=y,
                        width=HALF_W,
                        height=280,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar_drill(
                            "TransitAlertDetail",
                            ["alert_category", "neighborhood"],
                            "Transit Alert Count",
                            title="Drill: category → neighborhood",
                        ),
                    ),
                )
            )
            items.append(
                (
                    _vid("transit.drill.hood"),
                    _container(
                        _vid("transit.drill.hood"),
                        x=656,
                        y=y,
                        width=HALF_W,
                        height=280,
                        z=2100,
                        tab_order=2100,
                        visual=_clustered_bar_drill(
                            "TransitAlertDetail",
                            ["neighborhood", "alert_category"],
                            "Transit Alert Count",
                            title="Drill: neighborhood → category",
                        ),
                    ),
                )
            )
            y2 = y + 296
            items.append(
                (
                    _vid("transit.detail"),
                    _container(
                        _vid("transit.detail"),
                        x=MARGIN_X,
                        y=y2,
                        width=FULL_W,
                        height=PAGE_H - (y2 - BODY_Y),
                        z=3000,
                        tab_order=3000,
                        visual=_multi_row_card(
                            "TransitAlertDetail",
                            [
                                "headline",
                                "alert_category",
                                "neighborhood",
                                "service",
                                "severity",
                                "short_description",
                            ],
                            title="Alert detail (filtered by chart selection)",
                        ),
                    ),
                )
            )
        else:
            items.append(
                (
                    _vid("transit.bars"),
                    _container(
                        _vid("transit.bars"),
                        x=MARGIN_X,
                        y=y,
                        width=HALF_W if _has("HexPulseGrid") else FULL_W,
                        height=280,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar(
                            "TransitAlertSummary",
                            "alert_category",
                            "alert_count",
                            title="Transit alerts by category",
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
                            y=y,
                            width=HALF_W,
                            height=280,
                            z=2100,
                            tab_order=2100,
                            visual=_clustered_bar(
                                "HexPulseGrid",
                                "neighborhood",
                                "alert_count",
                                title="Alerts by neighborhood",
                            ),
                        ),
                    )
                )
        return items

    if page_seed == "page.infrastructure":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("InfrastructureRiskSnapshot"):
            items.append(
                (
                    _vid("infra.hero"),
                    _container(
                        _vid("infra.hero"),
                        x=MARGIN_X,
                        y=y,
                        width=THIRD_W,
                        height=176,
                        z=2000,
                        tab_order=2000,
                        visual=_hero_card(
                            "InfrastructureRiskSnapshot",
                            "Max Infrastructure Failure Risk",
                            title="Failure risk score",
                        ),
                    ),
                )
            )
            kpi_measures: list[tuple[str, str]] = [
                ("InfrastructureRiskSnapshot", "Max Infrastructure Failure Risk"),
            ]
            if _has("CityPulseSnapshot"):
                kpi_measures.extend(
                    [
                        ("CityPulseSnapshot", "Infrastructure Fatigue Risk"),
                        ("CityPulseSnapshot", "Bridge Risk Score"),
                        ("CityPulseSnapshot", "Road Surface Risk Score"),
                        ("CityPulseSnapshot", "Open Infrastructure Requests"),
                    ]
                )
            items.append(
                (
                    _vid("infra.kpi"),
                    _container(
                        _vid("infra.kpi"),
                        x=440,
                        y=y,
                        width=TWO_THIRD_W,
                        height=176,
                        z=2100,
                        tab_order=2100,
                        visual=_card_visual(
                            kpi_measures, columns=min(5, len(kpi_measures))
                        ),
                    ),
                )
            )
            y += 192
        if _has("InfrastructureAssetSummary"):
            items.append(
                (
                    _vid("infra.drill"),
                    _container(
                        _vid("infra.drill"),
                        x=MARGIN_X,
                        y=y,
                        width=HALF_W,
                        height=260,
                        z=2200,
                        tab_order=2200,
                        visual=_clustered_bar_drill(
                            "InfrastructureAssetSummary",
                            ["asset_class", "risk_tier"],
                            "Request Count",
                            title="Asset class → risk tier (bridge · road · structural)",
                        ),
                    ),
                )
            )
            items.append(
                (
                    _vid("infra.types"),
                    _container(
                        _vid("infra.types"),
                        x=656,
                        y=y,
                        width=HALF_W,
                        height=260,
                        z=2300,
                        tab_order=2300,
                        visual=_clustered_bar(
                            "InfrastructureAssetSummary",
                            "request_type",
                            "request_count",
                            title="311 request types (open data)",
                        ),
                    ),
                )
            )
            y += 276
        if _has("InfrastructureRequestDetail"):
            items.append(
                (
                    _vid("infra.detail"),
                    _container(
                        _vid("infra.detail"),
                        x=MARGIN_X,
                        y=y,
                        width=FULL_W,
                        height=PAGE_H - (y - BODY_Y),
                        z=3000,
                        tab_order=3000,
                        visual=_multi_row_card(
                            "InfrastructureRequestDetail",
                            [
                                "request_type",
                                "descriptor",
                                "asset_class",
                                "risk_tier",
                                "failure_risk_score",
                                "status",
                            ],
                            title="Infrastructure 311 detail (filtered by charts)",
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.weather":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("CityPulseSnapshot"):
            items.append(
                (
                    _vid("weather.kpi"),
                    _container(
                        _vid("weather.kpi"),
                        x=MARGIN_X,
                        y=y,
                        width=FULL_W,
                        height=96,
                        z=1500,
                        tab_order=1500,
                        visual=_card_visual(
                            [
                                ("CityPulseSnapshot", "Weather Risk Score"),
                                ("CityPulseSnapshot", "Precip Risk Score"),
                                ("CityPulseSnapshot", "Active NOAA Alerts"),
                                ("CityPulseSnapshot", "Avg Precip %"),
                            ],
                            columns=4,
                        ),
                    ),
                )
            )
            y += 112
        items.extend(
            [
                (
                    _vid("weather.precip"),
                    _container(
                        _vid("weather.precip"),
                        x=MARGIN_X,
                        y=y,
                        width=HALF_W,
                        height=PAGE_H - (y - BODY_Y),
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar(
                            "WeatherForecastPeriods",
                            "period_name",
                            "precip_pct",
                            title="Forecast precip probability %",
                        ),
                    ),
                ),
                (
                    _vid("weather.temp"),
                    _container(
                        _vid("weather.temp"),
                        x=656,
                        y=y,
                        width=HALF_W,
                        height=PAGE_H - (y - BODY_Y),
                        z=2100,
                        tab_order=2100,
                        visual=_clustered_bar(
                            "WeatherForecastPeriods",
                            "period_name",
                            "temperature_f",
                            title="Forecast temperature (°F)",
                            avg=True,
                        ),
                    ),
                ),
            ]
        )
        return items

    if page_seed == "page.airport":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("AirportOpsSnapshot"):
            items.append(
                (
                    _vid("airport.hero"),
                    _container(
                        _vid("airport.hero"),
                        x=MARGIN_X,
                        y=y,
                        width=THIRD_W,
                        height=176,
                        z=2000,
                        tab_order=2000,
                        visual=_hero_card(
                            "AirportOpsSnapshot",
                            "Max Airport Ops Stress",
                            title="Worst-station ops stress",
                        ),
                    ),
                )
            )
            kpi_measures: list[tuple[str, str]] = [
                ("CityPulseSnapshot", "Airport Visibility (sm)"),
                ("CityPulseSnapshot", "Active NOAA Alerts"),
            ]
            if _has("CityPulseSnapshot"):
                kpi_measures.insert(
                    0, ("CityPulseSnapshot", "Active Airport Stations")
                )
                kpi_measures.append(
                    ("AirportOpsSnapshot", "Max Airport Ops Stress")
                )
            items.append(
                (
                    _vid("airport.kpi"),
                    _container(
                        _vid("airport.kpi"),
                        x=440,
                        y=y,
                        width=TWO_THIRD_W,
                        height=176,
                        z=2100,
                        tab_order=2100,
                        visual=_card_visual(
                            kpi_measures, columns=min(4, len(kpi_measures))
                        ),
                    ),
                )
            )
            y += 192
            items.append(
                (
                    _vid("airport.bars"),
                    _container(
                        _vid("airport.bars"),
                        x=MARGIN_X,
                        y=y,
                        width=HALF_W,
                        height=260,
                        z=2050,
                        tab_order=2050,
                        visual=_clustered_bar(
                            "AirportOpsSnapshot",
                            "station_label",
                            "airport_ops_stress",
                            title="Ops stress by station (multi-airport metro)",
                            avg=True,
                        ),
                    ),
                )
            )
            items.append(
                (
                    _vid("airport.metar"),
                    _container(
                        _vid("airport.metar"),
                        x=656,
                        y=y,
                        width=HALF_W,
                        height=260,
                        z=2060,
                        tab_order=2060,
                        visual=_multi_row_card(
                            "AirportOpsSnapshot",
                            [
                                "station_label",
                                "flight_category",
                                "visibility_sm",
                                "wind_speed_kt",
                                "temperature_c",
                                "airport_ops_stress",
                            ],
                            title="METAR snapshot by station",
                        ),
                    ),
                )
            )
            y += 276
            items.append(
                (
                    _vid("airport.visibility"),
                    _container(
                        _vid("airport.visibility"),
                        x=MARGIN_X,
                        y=y,
                        width=FULL_W,
                        height=PAGE_H - (y - BODY_Y),
                        z=3000,
                        tab_order=3000,
                        visual=_clustered_bar(
                            "AirportOpsSnapshot",
                            "station_label",
                            "visibility_sm",
                            title="Visibility (sm) by airport station",
                            avg=True,
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.events":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("CityEventDetail"):
            items.append(
                (
                    _vid("events.drill"),
                    _container(
                        _vid("events.drill"),
                        x=MARGIN_X,
                        y=y,
                        width=FULL_W,
                        height=280,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar_drill(
                            "CityEventDetail",
                            ["neighborhood", "event_category"],
                            "Event Count",
                            title="Drill: neighborhood → category",
                        ),
                    ),
                )
            )
            y2 = y + 296
            items.append(
                (
                    _vid("events.detail"),
                    _container(
                        _vid("events.detail"),
                        x=MARGIN_X,
                        y=y2,
                        width=FULL_W,
                        height=PAGE_H - (y2 - BODY_Y),
                        z=2100,
                        tab_order=2100,
                        visual=_multi_row_card(
                            "CityEventDetail",
                            [
                                "event_name",
                                "event_category",
                                "neighborhood",
                                "location",
                                "start_date",
                                "end_date",
                            ],
                            title="Event detail (filtered by chart selection)",
                        ),
                    ),
                )
            )
        elif _has("EventHeatmap"):
            items.append(
                (
                    _vid("events.heat"),
                    _container(
                        _vid("events.heat"),
                        x=MARGIN_X,
                        y=y,
                        width=FULL_W,
                        height=PAGE_H,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar_drill_col(
                            "EventHeatmap",
                            ["neighborhood", "event_category"],
                            "event_count",
                            title="Events by neighborhood / category",
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.ai-signals":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        items.append(
            (
                _vid("ai.hero"),
                _container(
                    _vid("ai.hero"),
                    x=MARGIN_X,
                    y=y,
                    width=THIRD_W,
                    height=148,
                    z=2000,
                    tab_order=2000,
                    visual=_hero_card(
                        "AnomalySignals", "Anomaly Count", title="Active anomalies"
                    ),
                ),
            )
        )
        items.append(
            (
                _vid("ai.severity"),
                _container(
                    _vid("ai.severity"),
                    x=440,
                    y=y,
                    width=TWO_THIRD_W,
                    height=148,
                    z=2100,
                    tab_order=2100,
                    visual=_clustered_bar_drill(
                        "AnomalySignals",
                        ["severity", "signal_type"],
                        "Anomaly Count",
                        title="Severity → signal type",
                    ),
                ),
            )
        )
        y2 = y + 164
        items.append(
            (
                _vid("ai.table"),
                _container(
                    _vid("ai.table"),
                    x=MARGIN_X,
                    y=y2,
                    width=FULL_W,
                    height=PAGE_H - (y2 - BODY_Y),
                    z=3000,
                    tab_order=3000,
                    visual=_multi_row_card(
                        "AnomalySignals",
                        [
                            "signal_type",
                            "metric",
                            "severity",
                            "z_score",
                            "observed",
                            "baseline",
                            "message",
                        ],
                        title="Anomaly signal feed · z-score vs historical baseline",
                    ),
                ),
            )
        )
        return items

    if page_seed == "page.streaming":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("StreamingTelemetry"):
            items.append(
                (
                    _vid("stream.bars"),
                    _container(
                        _vid("stream.bars"),
                        x=MARGIN_X,
                        y=y,
                        width=HALF_W,
                        height=280,
                        z=2000,
                        tab_order=2000,
                        visual=_clustered_bar(
                            "StreamingTelemetry",
                            "source",
                            "batch_count",
                            title="Bronze ingest batches by source",
                        ),
                    ),
                )
            )
            items.append(
                (
                    _vid("stream.detail"),
                    _container(
                        _vid("stream.detail"),
                        x=656,
                        y=y,
                        width=HALF_W,
                        height=PAGE_H,
                        z=2100,
                        tab_order=2100,
                        visual=_multi_row_card(
                            "StreamingTelemetry",
                            [
                                "source",
                                "batch_count",
                                "last_ingested_at",
                                "snapshot_at",
                            ],
                            title="Pipeline freshness by source",
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.macro":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("FredMacroSnapshot"):
            items.append(
                (
                    _vid("macro.fred"),
                    _container(
                        _vid("macro.fred"),
                        x=MARGIN_X,
                        y=y,
                        width=HALF_W if _has("TrendInterestSummary") else FULL_W,
                        height=PAGE_H,
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
                        x=656 if _has("FredMacroSnapshot") else MARGIN_X,
                        y=y,
                        width=HALF_W if _has("FredMacroSnapshot") else FULL_W,
                        height=PAGE_H,
                        z=2100,
                        tab_order=2100,
                        visual=_clustered_bar(
                            "TrendInterestSummary",
                            "keyword",
                            "avg_interest",
                            title="Google Trends · regional interest",
                            avg=True,
                        ),
                    ),
                )
            )
        return items

    if page_seed == "page.studio":
        items = _page_header_for(
            page_seed, platform_mode=platform_mode, has_dim_metro=has_dim
        )
        y = BODY_Y
        if _has("PbipStudioCatalog"):
            items.append(
                (
                    _vid("studio.catalog"),
                    _container(
                        _vid("studio.catalog"),
                        x=MARGIN_X,
                        y=y,
                        width=FULL_W,
                        height=PAGE_H,
                        z=2000,
                        tab_order=2000,
                        visual=_multi_row_card(
                            "PbipStudioCatalog",
                            [
                                "table_name",
                                "source_path",
                                "column_count",
                                "columns_list",
                            ],
                            title="Auto-generated semantic model catalog",
                        ),
                    ),
                )
            )
        return items

    return []


def validate_metro_slicer_sync(report_root: Path) -> None:
    """Ensure every metro slicer shares the same PBIR syncGroup (cross-page filter)."""
    pages_root = report_root / "definition" / "pages"
    expected = {
        "groupName": METRO_SLICER_SYNC_GROUP,
        "fieldChanges": True,
        "filterChanges": True,
    }
    missing: list[str] = []
    for visual_path in pages_root.glob("*/visuals/*/visual.json"):
        payload = json.loads(visual_path.read_text(encoding="utf-8"))
        if payload.get("name") != METRO_SLICER_VISUAL_NAME:
            continue
        sync = (payload.get("visual") or {}).get("syncGroup")
        if sync != expected:
            page = visual_path.parents[2].name
            missing.append(page)
    if missing:
        raise RuntimeError(
            "Metro slicer syncGroup missing or mismatched on pages: "
            + ", ".join(missing)
        )


def write_page_visuals(
    page_dir: Path,
    page_seed: str,
    *,
    available_tables: set[str] | None = None,
    include_metro_slicer: bool = False,
    platform_mode: bool = False,
) -> int:
    """Write visual.json files under page_dir/visuals/. Returns count written."""
    specs = list(
        visuals_for_page(
            page_seed,
            available_tables=available_tables,
            platform_mode=platform_mode,
        )
    )
    if include_metro_slicer and available_tables and "DimMetro" in available_tables:
        specs.insert(0, _metro_slicer_container(page_seed))
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
