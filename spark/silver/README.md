# Silver layer

Normalized Delta tables under `datasets/delta/silver/`.

```bash
python generate_city.py --city chicago --transform-only
# or
python -m pulsegrid.jobs.silver_chicago
python -m pulsegrid.jobs.gold_chicago
```

Tables:
- `transit_alerts` — deduped public transit alerts + `alert_category` + `neighborhood_hint`
- `weather_alerts` — flattened NOAA NWS alerts
- `weather_forecast_periods` — forecast periods with precip %
