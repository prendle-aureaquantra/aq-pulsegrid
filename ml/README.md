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
