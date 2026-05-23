# Roadmap

Status key: **Done** · **Scaffold** · **Planned**

## Public demo (stretch)

| Item | Status | Notes |
|------|--------|-------|
| Standalone GitHub repo | **Scaffold** | [GITHUB_PUBLISH.md](GITHUB_PUBLISH.md) |
| README + architecture diagram | **Done** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Sample `ChicagoPulse.pbip` in repo | **Done** | `generated_reports/chicago/` |
| One-command demo | **Done** | `python generate_city.py --city chicago --with-visuals` |
| Programmatic PBIP visuals | **Done** | `pbip_generator/visuals.py` + Aurea Quantra theme |
| Publish to web embed | **Planned** | Publish `.pbix` from Desktop → Fabric embed on site |

## Phase 1 data gaps

| Source | Status | Module |
|--------|--------|--------|
| NOAA + CTA | **Done** | `ingest/noaa.py`, `ingest/cta.py` |
| Airport METAR (ORD) | **Done** | `ingest/airport.py` — `--extended-ingest` |
| Google Trends | **Done** | `ingest/google_trends.py` — `pip install -e ".[trends]"` |
| FRED macro series | **Done** | `ingest/fred.py` — needs `FRED_API_KEY` |
| Silver/gold for new sources | **Done** | `silver_chicago.py`, `gold_chicago.py` |
| Geospatial / Sedona hex maps | **Done** | `geo/hex_grid.py` + `reference/chicago_hex_grid.csv` |

## Streaming & platform

| Item | Status | Notes |
|------|--------|-------|
| Micro-batch bronze log | **Done** | `jobs/streaming_microbatch.py` — `--stream` |
| Spark Structured Streaming | **Done** | `jobs/streaming_spark.py` — `--stream-spark` |
| Databricks daily job | **Done** | `databricks.yml` + `tools/deploy_databricks_job.py` |
| High-severity alerting | **Scaffold** | `alerts/notify.py` — Slack webhook / email |
| Site `/pulsegrid/` page | **Planned** | [SITE_INTEGRATION.md](SITE_INTEGRATION.md) |

## Suggested order

1. Publish GitHub repo + link from aureaquantra.com  
2. Extend PBIP export for new gold tables (airport, trends, hex)  
3. Wire alerting into scheduled job  
4. Fabric embed on marketing site  
