# ML layer

## City Stress Index (0–100)

| Component | Weight cap | Signals |
|-----------|------------|---------|
| Transit load | 40 | Active transit alerts |
| Weather risk | 25 | NOAA alerts + severe events |
| Precip risk | 20 | Forecast precipitation % |
| Disruption ratio | 15 | Reroutes, delays, stop changes |

```bash
python generate_city.py --city chicago --ml-only
python -m pulsegrid.jobs.ml_chicago
```

## Anomaly detection

Z-score vs rolling `ml/pulse_history` or `datasets/reference/chicago_baselines.yaml`.

Signal types: `transit_alert_spike`, `weather_alert_spike`, `precip_forecast_spike`, `reroute_share_spike`, `neighborhood_activity_spike`.

Output: `gold/anomaly_signals` Delta table.

## Spark MLlib (optional)

Set `PULSEGRID_ENGINE=spark` to run gold/ML via Spark (`pulsegrid/jobs/gold_chicago_spark.py`, `pulsegrid/jobs/ml_spark.py`). `run_ml()` auto-selects the Spark path when the engine is set; metrics get an optional `mllib_z_score` and `mllib_multivariate_spike` anomaly signal.

Default local path uses pandas + z-score anomaly detection — sufficient for demo and &lt;100 metros. Use Spark when bronze/silver volumes require cluster scale.

```bash
# Optional Spark ML path (Docker / Python 3.11 recommended)
$env:PULSEGRID_ENGINE = "spark"
python generate_city.py --city chicago --ml-only
```
