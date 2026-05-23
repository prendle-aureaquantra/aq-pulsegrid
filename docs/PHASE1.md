# Phase 1 MVP — Chicago

## Scope

- City: **Chicago**
- Sources: NOAA, CTA (+ Google Trends, airports in later sprints)
- Deliverables: streaming-ready bronze ingest, 3 PBIP pages, basic anomaly detection

## Build schedule

### Week 1 ✓ (this scaffold)

- [x] Repo structure
- [x] Docker / devcontainer
- [x] Spark session helper
- [x] NOAA bronze ingest
- [x] CTA bronze ingest
- [x] `generate_city.py` CLI stub

### Week 2 ✓

- [x] Bronze → Silver Delta transforms (`pulsegrid/jobs/silver_chicago.py`)
- [x] Gold KPI tables (`pulsegrid/jobs/gold_chicago.py`)
- [x] Neighborhood keyword enrichment (CTA alerts)
- [x] `python generate_city.py --city chicago --transform-only`

Silver tables: `transit_alerts`, `weather_alerts`, `weather_forecast_periods`

Gold tables: `transit_alert_summary`, `city_pulse_snapshot` (includes `city_stress_score`)

### Week 3 ✓

- [x] City Stress Index (`pulsegrid/ml/city_stress.py`) — 0–100 multi-component score
- [x] Anomaly detection (`pulsegrid/ml/anomaly.py`) — z-score vs history + baselines
- [x] Neighborhood activity spikes
- [x] Semantic model metadata JSON for PBIP (`generated_reports/chicago/semantic_model_metadata.json`)
- [x] `python generate_city.py --city chicago --ml-only`

Gold tables: `city_stress_index`, `anomaly_signals`, `pulse_history` (append)

### Week 4 ✓

- [x] CSV export from gold/silver Delta (`pbip_generator/export_gold_csv.py`)
- [x] TMDL semantic model + DAX measures
- [x] Dark PulseGrid theme (`pbip_generator/themes/PulseGridDark.json`)
- [x] 3 report pages (Live City Pulse, Transit & Mobility, Weather Impact Analysis)
- [x] `python generate_city.py --city chicago --pbip-only`

Output: `generated_reports/chicago/ChicagoPulse.pbip`

## Example questions (target)

- Why is downtown activity spiking tonight?
- What weather patterns correlate with transit slowdowns?
- Which neighborhoods show unusual congestion signals?
