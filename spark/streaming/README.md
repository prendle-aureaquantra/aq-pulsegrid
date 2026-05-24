# Spark Structured Streaming

PulseGrid supports two bronze streaming modes:

| Mode | CLI | Engine |
|------|-----|--------|
| Python micro-batch poll | `--stream` | delta-rs (default) |
| **Structured Streaming** | `--stream-spark` | `PULSEGRID_ENGINE=spark` |

## Local run

```powershell
$env:PULSEGRID_ENGINE = "spark"
$env:PULSEGRID_DATA_ROOT = "$env:USERPROFILE\.local\aq-pulsegrid"
python generate_city.py --city chicago --stream-spark --stream-batches 3
```

Each trigger calls NOAA + CTA ingest and appends rows to `delta/bronze/ingest_events`.

Checkpoints: `delta/_checkpoints/stream_ingest_chicago/`.

## Production path

Replace the `rate` source with:

- **Kafka / Event Hubs** — `readStream.format("kafka")`
- **Auto Loader** — `readStream.format("cloudFiles")` on landing-zone JSON
- **Delta CDF** — `readStream.format("delta").option("readChangeFeed", "true")`

Sedona hex enrichment runs in gold Spark (`pulsegrid/geo/sedona_hex.py`):

- UDFs: `pulsegrid_nearest_hex_id`, `pulsegrid_lat_lon_to_hex`, `pulsegrid_geodesic_m`, `pulsegrid_neighborhood_to_hex`
- `aggregate_transit_alerts_hex_spark()` writes `gold/hex_pulse_grid` without driver `collect()`

Local optional: `pip install -e ".[spark-gis]"` (apache-sedona). On Databricks attach
`org.apache.sedona:sedona-spark-3.5_2.12` (or matching DBR) for `ST_Point` / `ST_DistanceSphere` SQL.
