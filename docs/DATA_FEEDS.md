# Public data feeds (Phase 2)

## Metadata-driven core feeds

Four high-signal feeds are declared in [`datasets/reference/ingest_feeds.yaml`](../datasets/reference/ingest_feeds.yaml) and resolved per metro by [`pulsegrid/ingest/feed_framework.py`](../pulsegrid/ingest/feed_framework.py):

| Feed ID | Source | When enabled |
|---------|--------|--------------|
| `nws_weather` | NOAA NWS (`noaa.py`) | US metro, `weather` module, `weather_adapter: noaa`, `noaa_area` set |
| `gtfs_rt` | CTA / MBTA / GTFS-RT / agency JSON | `transit` module + adapter from registry, `transit_feeds.yaml`, or MobilityData catalog |
| `opensky_aviation` | OpenSky ADS-B (`opensky.py`) | `airports` module or airport ICAO catalog |
| `civic311` | Socrata 311 (`civic311.py`) | US metro with entry in `civic311.yaml` |

`run_metro_ingest()` runs all enabled core feeds. OpenSky moved from extended-only to core when airports are configured. Each feed uses **exponential backoff** (3 attempts) and writes bronze freshness markers.

Coverage report (CI enforces minimum counts on `main`):

```bash
python tools/ingest_feed_coverage.py
python tools/ingest_feed_coverage.py --check-min
```

| Feed | Module | Adapter key | Bronze path |
|------|--------|-------------|-------------|
| NOAA NWS | `pulsegrid/ingest/noaa.py` | `noaa` | `{metro}/noaa/` |
| Open-Meteo | `pulsegrid/ingest/open_meteo.py` | `open_meteo` | `{metro}/weather/` |
| MeteoAlarm CAP | `pulsegrid/ingest/meteoalarm.py` | (with `open_meteo`) | `{metro}/weather/alerts_*.json` |
| Chicago transit (CTA XML) | `pulsegrid/ingest/cta.py` | `cta` | `{metro}/transit/` |
| Boston transit (MBTA JSON) | `pulsegrid/ingest/mbta.py` | `mbta` | `{metro}/transit/` |
| GTFS-RT / JSON alerts | `pulsegrid/ingest/gtfs_rt.py` | `gtfs_rt` | `{metro}/transit/` |
| METAR | `pulsegrid/ingest/airport.py` | airports module | `{metro}/airport/` |
| OpenSky ADS-B | `pulsegrid/ingest/opensky.py` | extended | `{metro}/opensky/` |
| USGS earthquakes | `pulsegrid/ingest/usgs.py` | global | `{metro}/usgs/` |
| Air quality | `pulsegrid/ingest/air_quality.py` | global | `{metro}/air_quality/` |
| Socrata events | `pulsegrid/ingest/events.py` | `socrata` | `{metro}/events/` |
| 311 / civic requests | `pulsegrid/ingest/civic311.py` | `socrata` | `{metro}/civic311/` |
| OSM POIs | `pulsegrid/geo/osm_enrich.py` | osm module | `{metro}/osm/` |
| Google Trends | `pulsegrid/ingest/google_trends.py` | trends module | `{metro}/google_trends/` |
| FRED macro | `pulsegrid/ingest/fred.py` | fred module | `{metro}/fred/` |

## Config files

- **Ingest catalog:** [`datasets/reference/ingest_feeds.yaml`](../datasets/reference/ingest_feeds.yaml) — feed types, overrides, dispatch metadata
- **311 endpoints:** [`datasets/reference/civic311.yaml`](../datasets/reference/civic311.yaml) — Socrata, ArcGIS, and CARTO adapters
- **Boost coverage (programmatic):** `python generate_city.py --boost-feeds` or `python tools/boost_feed_coverage.py`
- **Curated transit URLs:** [`datasets/reference/curated_transit_feeds.yaml`](../datasets/reference/curated_transit_feeds.yaml) — verified GTFS-RT alert endpoints (override MobilityData guesses)
- **Mobility ranking aliases:** [`datasets/reference/transit_metro_aliases.yaml`](../datasets/reference/transit_metro_aliases.yaml) — extra filename tokens for catalog matching
- **Transit alert feeds:** [`datasets/reference/transit_feeds.yaml`](../datasets/reference/transit_feeds.yaml) — per-metro `cta` / `mbta` / `gtfs_rt` / `transit_json` URLs
- **MobilityData catalog:** [`pulsegrid/ingest/mobility_catalog.py`](../pulsegrid/ingest/mobility_catalog.py) — auto-resolves GTFS-RT service-alert URLs at ingest (cache + `python tools/sync_transit_from_mobility.py`)
- **Agency JSON:** [`pulsegrid/ingest/transit_json.py`](../pulsegrid/ingest/transit_json.py) — TfL, OVapi, etc.
- **Trends keywords:** [`datasets/reference/metro_trends.yaml`](../datasets/reference/metro_trends.yaml)

## MeteoAlarm coverage

Country-level CAP atom feeds (live, no API key) for: France, Germany, Spain, Italy, Austria, Sweden, Norway, Greece, Portugal, Finland, Romania, Israel. Wired automatically for all `weather_adapter: open_meteo` metros in those countries.

### Agency API keys (optional)

| Env var | Metro | Register |
|---------|-------|----------|
| `WMATA_API_KEY` | Washington DC | [developer.wmata.com](https://developer.wmata.com/) |
| `HOUSTON_METRO_API_KEY` | Houston | [api-portal.ridemetro.org](https://api-portal.ridemetro.org/) |
| `DART_GTFS_RT_ALERTS_URL` + `DART_API_KEY` | Dallas | [dart.developer.azure-api.net](https://dart.developer.azure-api.net/) |

Copy `aq-pulsegrid/.env.example`, set keys locally, then from monorepo root: `python tools/sync_pulsegrid_transit_env.py` before `deploy_pulsegrid.py`.

Dispatch: [`pulsegrid/ingest/registry.py`](../pulsegrid/ingest/registry.py)

Silver parsers: [`pulsegrid/transforms/bronze_parsers.py`](../pulsegrid/transforms/bronze_parsers.py)
