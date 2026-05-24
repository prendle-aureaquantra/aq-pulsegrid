# Roadmap

Status key: **Done** · **Scaffold** · **Planned**

## Manifest checklist

- [x] Spark streaming ingestion (`--stream`, `--stream-spark`)
- [x] Delta Lake medallion architecture
- [x] Geospatial hex grid + OpenStreetMap enrichment
- [x] ML anomaly detection + City Pulse Score
- [x] Automated PBIP semantic model + layout generation
- [x] Docker + Dev Containers
- [x] GitHub Actions CI/CD
- [x] Multi-city scaffold (Chicago + Boston config)
- [x] Historical replay engine (`replay_city.py`)
- [x] AI copilot layer (`pulsegrid.copilot.insights`)
- [x] Site embed tooling (`tools/sync_pulsegrid_site_page.py`)
- [x] **Phase 2:** Worldwide metro registry + metro slicer ([PHASE2.md](PHASE2.md))
- [x] **Phase 2:** OpenSky, GTFS-RT, USGS, Open-Meteo, AQI feeds ([DATA_FEEDS.md](DATA_FEEDS.md))
- [x] **Phase 2:** Databricks global job (`aq-pulsegrid-daily-global`)
- [ ] Fabric live embed on aureaquantra.com (docs: [FABRIC_EMBED.md](FABRIC_EMBED.md); needs published `.pbix` + `POWERBI_PULSEGRID_EMBED_URL`)
- [x] Lightsail ops app + **https://pulse.aureaquantra.com/** (Apache + Let's Encrypt)
- [x] Apache Sedona Spark UDFs (`pulsegrid/geo/sedona_hex.py` — UDFs + Spark hex aggregation)
- [ ] Spark MLlib production anomaly model (optional z-score path when `PULSEGRID_ENGINE=spark`)
- [x] Boston full pipeline (MBTA adapter)

## Dashboard pages (PBIP)

| Page | Status |
|------|--------|
| Live City Pulse | **Done** |
| Transit & Mobility | **Done** |
| Weather Impact Analysis | **Done** |
| Airport Operations | **Done** |
| Event Heatmaps | **Done** |
| AI Signal Detection | **Done** |
| Streaming Monitor | **Done** |
| Macro & Trends | **Done** |
| PBIP Generator Studio | **Done** |

## Public demo

| Item | Status |
|------|--------|
| GitHub repo | **Done** — [prendle-aureaquantra/aq-pulsegrid](https://github.com/prendle-aureaquantra/aq-pulsegrid) |
| README + positioning | **Done** — [POSITIONING.md](POSITIONING.md) |
| Sample PBIP + visuals | **Done** |
| One-command demo | **Done** — `python generate_city.py --city chicago --extended-ingest --with-visuals` |
| Ops status app | **Done** — [pulse.aureaquantra.com](https://pulse.aureaquantra.com) |

## Data sources

| Source | Status |
|--------|--------|
| NOAA + CTA | **Done** |
| Airport METAR | **Done** |
| FRED + Google Trends | **Done** |
| Chicago events (open data) | **Done** |
| OpenStreetMap Overpass POIs | **Done** |

See [ARCHITECTURE.md](ARCHITECTURE.md) · [SITE_INTEGRATION.md](SITE_INTEGRATION.md)
