# AQ PulseGrid — Product Direction + Architecture + GitHub Positioning

Repository: [github.com/prendle-aureaquantra/aq-pulsegrid](https://github.com/prendle-aureaquantra/aq-pulsegrid)

## Core positioning

AQ PulseGrid is **not** a tutorial project. It is positioned as:

- an urban intelligence platform
- a modern data engineering system
- a Spark-powered operational analytics platform
- an AI-ready semantic BI architecture
- a metadata-driven Power BI automation framework

The repository should feel closer to Palantir, Databricks, Microsoft Fabric, Bloomberg terminals, and real-time city operations systems than a traditional BI portfolio project.

## Core vision

AQ PulseGrid combines streaming public datasets, Spark processing, Delta Lake architecture, machine learning, geospatial analytics, semantic BI modeling, and automated Power BI PBIP generation into a unified analytics platform.

## Primary value proposition

This project demonstrates Spark engineering, PySpark, streaming pipelines, Delta Lake medallion architecture, ML feature engineering, anomaly detection, geospatial intelligence, Power BI semantic modeling, PBIP automation, dashboard generation, and modern analytics architecture.

## Recommended repo subtitle

```text
Real-time Spark-powered urban intelligence platform combining streaming public datasets, machine learning, geospatial analytics, and automated Power BI PBIP generation.
```

## Architecture (reference)

```text
┌──────────────────────────────┐
│ Public APIs / Live Feeds     │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Spark Structured Streaming   │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Bronze / Silver / Gold       │
│ Delta Lakehouse              │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ ML + Signal Scoring Engine   │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ PBIP Generator               │
│ Semantic Model Automation    │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Power BI Dashboards          │
└──────────────────────────────┘
```

## Primary public data sources

| Domain | Source | Uses |
|--------|--------|------|
| Weather | NOAA | Alerts, forecast, disruption scoring |
| Transit | Chicago CTA | Alerts, mobility analytics, anomalies |
| Aviation | FAA / METAR (ORD) | Ops stress, travel disruption |
| Economic | FRED | Macro overlays |
| Search | Google Trends | Behavioral / momentum signals |
| Geospatial | OSM + hex grid | Heatmaps, neighborhood intelligence |

## Core differentiator — PBIP generator

Many public repos demonstrate Spark and dashboards. Few demonstrate semantic model generation, metadata-driven BI automation, PBIP report generation, and automated dashboard creation. **This is the strongest differentiator.**

Example generator input:

```json
{
  "city": "Chicago",
  "theme": "dark",
  "modules": ["weather", "transit", "airports", "events"]
}
```

Example output:

```text
generated_reports/chicago/
  ChicagoPulse.pbip
  ChicagoPulse.SemanticModel/
  ChicagoPulse.Report/
  data/*.csv
  dax/measures.txt
```

## Signature KPI — City Pulse Score

Composite operational score (0–100) from weather, transit, airport congestion, trend signals, and ML anomalies. Implemented as **City Stress Index** in `pulsegrid/ml/city_stress.py`.

## Dashboard pages (target)

| Page | Status |
|------|--------|
| Live City Pulse | Done |
| Transit & Mobility | Done |
| Weather Impact Analysis | Done |
| Airport, Macro & Hex | Done (Phase 1 extended) |
| Event Heatmaps | Planned |
| AI Signal Detection | Partial (anomaly table + visuals) |
| Streaming Monitor | Scaffold |
| PBIP Generator Studio | Planned |

## Visual style

Dark operations-center UI — Aurea Quantra gold/charcoal theme in `pbip_generator/themes/AureaQuantraPulse.json`. Inspiration: Databricks, Palantir, Fabric, Bloomberg.

## Target roles (final positioning)

- Data Platform Architect
- Principal BI Engineer
- Modern Analytics Engineer
- Databricks / Fabric Architect
- AI/BI Strategy Lead

Not: traditional dashboard developer or basic BI portfolio project.

## Stretch goals

- `python generate_city.py --city chicago` — full ingest → Spark → ML → PBIP (MVP done)
- `python replay_city.py --city chicago --date 2025-12-31` — historical replay engine (planned)
- Fabric embed on [aureaquantra.com](https://aureaquantra.com) — see [SITE_INTEGRATION.md](SITE_INTEGRATION.md)

See also [ROADMAP.md](ROADMAP.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
