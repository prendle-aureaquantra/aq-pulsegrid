# Phase 2 — Worldwide Metros + Databricks + Public Feeds

Phase 2 extends AQ PulseGrid from a Chicago MVP to a **worldwide metro platform** with config-driven ingest, a unified metro slicer, and production Databricks jobs.

## Metro tiers

| Tier | Count | Capabilities |
|------|-------|----------------|
| **full** | 10 | Weather + transit adapters + airports + extended feeds |
| **weather_only** | 61+ | NOAA (US) or Open-Meteo + optional METAR |

Registry: [`datasets/metros/registry.yaml`](../datasets/metros/registry.yaml)

## CLI

```bash
# Single metro (unchanged)
python generate_city.py --city chicago --extended-ingest --with-visuals

# Multiple metros
python generate_city.py --metros chicago,boston,london --extended-ingest

# All Tier-1 metros + platform PBIP
python generate_city.py --all-metros --tier full --extended-ingest --with-visuals

# Platform export only (union CSVs + PulseGrid.pbip)
python generate_city.py --platform-only --tier full --with-visuals
```

## Metro slicer

- **PBIP:** `generated_reports/platform/PulseGrid.pbip` — `DimMetro` table + slicer on every page
- **Ops console:** `pulse.aureaquantra.com/?metro=london` — shareable query string

## Databricks

Deploy global job:

```powershell
python tools/deploy_databricks_job.py --repo-path /Repos/YOUR_USER/aq-pulsegrid
```

Job **`aq-pulsegrid-daily-global`**: ingest → transform → ML → platform CSV export.

Set `PULSEGRID_UC_CATALOG=pulsegrid` for Unity Catalog volume paths (optional).

## Public feeds (Phase 2)

See [DATA_FEEDS.md](DATA_FEEDS.md).

## Manual steps

1. `DATABRICKS_HOST` + `DATABRICKS_TOKEN` in `.env`
2. Publish `PulseGrid.pbip` → set `POWERBI_PULSEGRID_EMBED_URL`
3. Redeploy Lightsail: `python tools/deploy_pulsegrid_lightsail.py`
