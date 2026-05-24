"""Silver Delta transforms — Chicago."""

from __future__ import annotations

from pathlib import Path

from pulsegrid.config import DELTA, get_city
from pulsegrid.io.delta_writer import (
    use_spark_engine,
    merge_delta_table,
    write_delta_dataframe,
    write_delta_table,
)
from pulsegrid.transforms.bronze_parsers import (
    bronze_glob,
    parse_airport_bronze,
    parse_cta_bronze,
    parse_transit_bronze,
    parse_events_bronze,
    parse_fred_bronze,
    parse_noaa_alerts_bronze,
    parse_noaa_forecast_bronze,
    parse_open_meteo_forecast_bronze,
    parse_opensky_bronze,
    parse_transit_bronze,
    parse_usgs_bronze,
    parse_air_quality_bronze,
    parse_civic311_bronze,
    parse_meteoalarm_alerts_bronze,
    parse_osm_bronze,
    parse_trends_bronze,
)

SILVER_ROOT = DELTA / "silver"

_SILVER_SCHEMAS = None


def _spark_schemas():
    global _SILVER_SCHEMAS
    if _SILVER_SCHEMAS is not None:
        return _SILVER_SCHEMAS
    from pyspark.sql.types import (
        BooleanType,
        DoubleType,
        IntegerType,
        StringType,
        StructField,
        StructType,
    )

    _SILVER_SCHEMAS = {
        "transit_alerts": StructType(
            [
                StructField("city", StringType(), False),
                StructField("alert_id", StringType(), False),
                StructField("headline", StringType(), True),
                StructField("short_description", StringType(), True),
                StructField("severity", StringType(), True),
                StructField("service", StringType(), True),
                StructField("alert_category", StringType(), True),
                StructField("neighborhood_hint", StringType(), True),
                StructField("ingested_at", StringType(), True),
                StructField("bronze_file", StringType(), True),
            ]
        ),
        "weather_alerts": StructType(
            [
                StructField("city", StringType(), False),
                StructField("alert_id", StringType(), False),
                StructField("event", StringType(), True),
                StructField("severity", StringType(), True),
                StructField("urgency", StringType(), True),
                StructField("headline", StringType(), True),
                StructField("area_desc", StringType(), True),
                StructField("effective", StringType(), True),
                StructField("expires", StringType(), True),
                StructField("ingested_at", StringType(), True),
                StructField("bronze_file", StringType(), True),
            ]
        ),
        "weather_forecast_periods": StructType(
            [
                StructField("city", StringType(), False),
                StructField("period_number", IntegerType(), True),
                StructField("period_name", StringType(), True),
                StructField("start_time", StringType(), True),
                StructField("end_time", StringType(), True),
                StructField("is_daytime", BooleanType(), True),
                StructField("temperature_f", IntegerType(), True),
                StructField("precip_pct", IntegerType(), True),
                StructField("short_forecast", StringType(), True),
                StructField("wind_speed", StringType(), True),
                StructField("wind_direction", StringType(), True),
                StructField("ingested_at", StringType(), True),
                StructField("bronze_file", StringType(), True),
            ]
        ),
        "airport_observations": StructType(
            [
                StructField("city", StringType(), False),
                StructField("station", StringType(), True),
                StructField("observation_time", StringType(), True),
                StructField("flight_category", StringType(), True),
                StructField("visibility_sm", DoubleType(), True),
                StructField("wind_speed_kt", DoubleType(), True),
                StructField("temperature_c", DoubleType(), True),
                StructField("altimeter_inhg", DoubleType(), True),
                StructField("raw_ob", StringType(), True),
                StructField("ingested_at", StringType(), True),
                StructField("bronze_file", StringType(), True),
            ]
        ),
        "fred_observations": StructType(
            [
                StructField("city", StringType(), False),
                StructField("series_id", StringType(), False),
                StructField("series_label", StringType(), True),
                StructField("observation_date", StringType(), False),
                StructField("value", DoubleType(), True),
                StructField("ingested_at", StringType(), True),
                StructField("bronze_file", StringType(), True),
            ]
        ),
        "trend_interest": StructType(
            [
                StructField("city", StringType(), False),
                StructField("keyword", StringType(), False),
                StructField("observation_date", StringType(), False),
                StructField("interest_index", IntegerType(), True),
                StructField("ingested_at", StringType(), True),
                StructField("bronze_file", StringType(), True),
            ]
        ),
        "city_events": StructType(
            [
                StructField("city", StringType(), False),
                StructField("event_id", StringType(), False),
                StructField("event_name", StringType(), True),
                StructField("event_category", StringType(), True),
                StructField("neighborhood_hint", StringType(), True),
                StructField("location", StringType(), True),
                StructField("start_date", StringType(), True),
                StructField("end_date", StringType(), True),
                StructField("ingested_at", StringType(), True),
                StructField("bronze_file", StringType(), True),
            ]
        ),
        "osm_pois": StructType(
            [
                StructField("city", StringType(), False),
                StructField("osm_id", StringType(), True),
                StructField("amenity", StringType(), True),
                StructField("name", StringType(), True),
                StructField("lat", DoubleType(), True),
                StructField("lon", DoubleType(), True),
                StructField("ingested_at", StringType(), True),
                StructField("bronze_file", StringType(), True),
            ]
        ),
    }
    return _SILVER_SCHEMAS


def _dedupe_rows(rows: list[dict], key_fields: list[str]) -> list[dict]:
    latest: dict[tuple, dict] = {}
    for row in rows:
        key = tuple(row[k] for k in key_fields)
        prev = latest.get(key)
        if prev is None or row.get("ingested_at", "") >= prev.get("ingested_at", ""):
            latest[key] = row
    return list(latest.values())


def _write_silver(rows: list[dict], table: str):
    path = SILVER_ROOT / table
    if use_spark_engine():
        from pulsegrid.spark_session import build_spark

        spark = build_spark("pulsegrid-silver")
        try:
            df = spark.createDataFrame(rows, schema=_spark_schemas()[table])
            return write_delta_dataframe(df, path)
        finally:
            spark.stop()
    return merge_delta_table(rows, path)


def run_silver(city_slug: str = "chicago") -> dict[str, Path]:
    city = get_city(city_slug)
    cta_paths = bronze_glob(city_slug, "cta", "alerts_*.json")
    transit_paths = bronze_glob(city_slug, "transit", "alerts_*.json")
    noaa_alert_paths = bronze_glob(city_slug, "noaa", "alerts_*.json")
    weather_alert_paths = bronze_glob(city_slug, "weather", "alerts_*.json")
    noaa_forecast_paths = bronze_glob(city_slug, "noaa", "forecast_*.json")
    open_meteo_paths = bronze_glob(city_slug, "weather", "forecast_*.json")
    airport_paths = bronze_glob(city_slug, "airport", "metar_*.json")
    fred_paths = bronze_glob(city_slug, "fred", "*.json")
    trends_paths = bronze_glob(city_slug, "google_trends", "*.json")
    events_paths = bronze_glob(city_slug, "events", "*.json")
    civic311_paths = bronze_glob(city_slug, "civic311", "requests_*.json")
    osm_paths = bronze_glob(city_slug, "osm", "*.json")
    opensky_paths = bronze_glob(city_slug, "opensky", "states_*.json")
    usgs_paths = bronze_glob(city_slug, "usgs", "quakes_*.json")
    aqi_paths = bronze_glob(city_slug, "air_quality", "aqi_*.json")

    if not any(
        [
            cta_paths,
            transit_paths,
            noaa_alert_paths,
            weather_alert_paths,
            noaa_forecast_paths,
            open_meteo_paths,
            airport_paths,
            fred_paths,
            trends_paths,
            events_paths,
            civic311_paths,
            osm_paths,
            opensky_paths,
            usgs_paths,
            aqi_paths,
        ]
    ):
        raise FileNotFoundError(
            f"No bronze data under datasets/bronze/{city_slug}/. Run ingest first."
        )

    written: dict[str, Path] = {}
    engine = "spark" if use_spark_engine() else "delta-rs"
    print(f"  engine: {engine}")

    if cta_paths or transit_paths:
        rows = _dedupe_rows(
            parse_transit_bronze(cta_paths + transit_paths, city.slug),
            ["city", "alert_id"],
        )
        written["transit_alerts"] = _write_silver(rows, "transit_alerts")

    alert_paths = noaa_alert_paths + weather_alert_paths
    if alert_paths:
        rows = _dedupe_rows(
            parse_noaa_alerts_bronze(noaa_alert_paths, city.slug)
            + parse_meteoalarm_alerts_bronze(weather_alert_paths, city.slug),
            ["city", "alert_id"],
        )
        written["weather_alerts"] = _write_silver(rows, "weather_alerts")

    forecast_paths = noaa_forecast_paths + open_meteo_paths
    if forecast_paths:
        rows = _dedupe_rows(
            parse_noaa_forecast_bronze(noaa_forecast_paths, city.slug)
            + parse_open_meteo_forecast_bronze(open_meteo_paths, city.slug),
            ["city", "period_number", "start_time"],
        )
        written["weather_forecast_periods"] = _write_silver(
            rows, "weather_forecast_periods"
        )

    if airport_paths:
        rows = _dedupe_rows(
            parse_airport_bronze(airport_paths, city.slug),
            ["city", "station", "observation_time"],
        )
        written["airport_observations"] = _write_silver(rows, "airport_observations")

    if fred_paths:
        rows = _dedupe_rows(
            parse_fred_bronze(fred_paths, city.slug),
            ["city", "series_id", "observation_date"],
        )
        written["fred_observations"] = _write_silver(rows, "fred_observations")

    if trends_paths:
        rows = _dedupe_rows(
            parse_trends_bronze(trends_paths, city.slug),
            ["city", "keyword", "observation_date"],
        )
        written["trend_interest"] = _write_silver(rows, "trend_interest")

    if events_paths:
        rows = _dedupe_rows(
            parse_events_bronze(events_paths, city.slug),
            ["city", "event_id"],
        )
        written["city_events"] = _write_silver(rows, "city_events")

    if civic311_paths:
        rows = _dedupe_rows(
            parse_civic311_bronze(civic311_paths, city.slug),
            ["city", "request_id"],
        )
        written["civic311_requests"] = _write_silver(rows, "civic311_requests")

    if osm_paths:
        rows = _dedupe_rows(
            parse_osm_bronze(osm_paths, city.slug),
            ["city", "osm_id"],
        )
        written["osm_pois"] = _write_silver(rows, "osm_pois")

    if opensky_paths:
        rows = _dedupe_rows(
            parse_opensky_bronze(opensky_paths, city.slug),
            ["city", "ingested_at"],
        )
        written["opensky_states"] = _write_silver(rows, "opensky_states")

    if usgs_paths:
        rows = _dedupe_rows(
            parse_usgs_bronze(usgs_paths, city.slug),
            ["city", "event_id"],
        )
        written["usgs_earthquakes"] = _write_silver(rows, "usgs_earthquakes")

    if aqi_paths:
        rows = _dedupe_rows(
            parse_air_quality_bronze(aqi_paths, city.slug),
            ["city", "ingested_at"],
        )
        written["air_quality"] = _write_silver(rows, "air_quality")

    return written


def main() -> int:
    paths = run_silver("chicago")
    for name, path in paths.items():
        print(f"  silver.{name} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
