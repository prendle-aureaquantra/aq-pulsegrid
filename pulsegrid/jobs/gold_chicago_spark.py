"""PySpark gold path (Docker / Python 3.11 / PULSEGRID_ENGINE=spark)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import functions as F

from pulsegrid.config import DELTA, get_city
from pulsegrid.geo.hex_grid import aggregate_transit_by_hex
from pulsegrid.io.delta_writer import write_delta_dataframe
from pulsegrid.spark_session import build_spark

GOLD_ROOT = DELTA / "gold"
SILVER_ROOT = DELTA / "silver"


def run_gold_spark(city_slug: str = "chicago") -> dict[str, Path]:
    city = get_city(city_slug)
    spark = build_spark(f"pulsegrid-gold-{city_slug}")
    snapshot_at = datetime.now(timezone.utc).isoformat()
    written: dict[str, Path] = {}

    try:
        active_cta = 0
        transit_path = SILVER_ROOT / "transit_alerts"
        if transit_path.exists():
            transit = spark.read.format("delta").load(str(transit_path))
            transit_city = transit.filter(F.col("city") == city.slug)
            summary = (
                transit_city.groupBy("city", "alert_category")
                .count()
                .withColumnRenamed("count", "alert_count")
                .withColumn("snapshot_at", F.lit(snapshot_at))
            )
            written["transit_alert_summary"] = write_delta_dataframe(
                summary, GOLD_ROOT / "transit_alert_summary"
            )
            active_cta = transit_city.count()
            hex_rows = aggregate_transit_by_hex(
                [r.asDict() for r in transit_city.collect()]
            )
            if hex_rows:
                for row in hex_rows:
                    row["city"] = city.slug
                    row["snapshot_at"] = snapshot_at
                hex_df = spark.createDataFrame(hex_rows)
                written["hex_pulse_grid"] = write_delta_dataframe(
                    hex_df, GOLD_ROOT / "hex_pulse_grid"
                )

        active_noaa = 0
        wx_path = SILVER_ROOT / "weather_alerts"
        if wx_path.exists():
            active_noaa = (
                spark.read.format("delta")
                .load(str(wx_path))
                .filter(F.col("city") == city.slug)
                .count()
            )

        avg_precip = 0.0
        fc_path = SILVER_ROOT / "weather_forecast_periods"
        if fc_path.exists():
            row = (
                spark.read.format("delta")
                .load(str(fc_path))
                .filter(F.col("city") == city.slug)
                .agg(F.avg("precip_pct"))
                .collect()[0][0]
            )
            if row is not None:
                avg_precip = float(row)

        airport_stress = 0.0
        airport_flt = ""
        airport_vis = None
        ap_path = SILVER_ROOT / "airport_observations"
        if ap_path.exists():
            ap = (
                spark.read.format("delta")
                .load(str(ap_path))
                .filter(F.col("city") == city.slug)
                .orderBy(F.col("ingested_at").desc())
            )
            if ap.head(1):
                latest = ap.first()
                airport_flt = latest.flight_category or ""
                airport_vis = latest.visibility_sm
                if airport_vis is not None and float(airport_vis) < 3:
                    airport_stress += 5.0
                if airport_flt.upper() in ("IFR", "LIFR"):
                    airport_stress += 8.0
                snap_df = spark.createDataFrame(
                    [
                        {
                            "city": city.slug,
                            "snapshot_at": snapshot_at,
                            "station": latest.station,
                            "flight_category": airport_flt,
                            "visibility_sm": airport_vis,
                            "wind_speed_kt": latest.wind_speed_kt,
                            "temperature_c": latest.temperature_c,
                            "airport_ops_stress": round(airport_stress, 2),
                        }
                    ]
                )
                written["airport_ops_snapshot"] = write_delta_dataframe(
                    snap_df, GOLD_ROOT / "airport_ops_snapshot"
                )

        fred_count = 0
        trend_avg = 0.0
        fr_path = SILVER_ROOT / "fred_observations"
        if fr_path.exists():
            fred = spark.read.format("delta").load(str(fr_path)).filter(
                F.col("city") == city.slug
            )
            from pyspark.sql.window import Window

            w = Window.partitionBy("series_id").orderBy(F.col("observation_date").desc())
            latest_fred = (
                fred.withColumn("rn", F.row_number().over(w))
                .filter(F.col("rn") == 1)
                .drop("rn")
                .withColumn("snapshot_at", F.lit(snapshot_at))
                .select(
                    "city",
                    "series_id",
                    "series_label",
                    F.col("value").alias("latest_value"),
                    "observation_date",
                    "snapshot_at",
                )
            )
            if latest_fred.head(1):
                fred_count = latest_fred.count()
                written["fred_macro_snapshot"] = write_delta_dataframe(
                    latest_fred, GOLD_ROOT / "fred_macro_snapshot"
                )

        tr_path = SILVER_ROOT / "trend_interest"
        if tr_path.exists():
            trends = spark.read.format("delta").load(str(tr_path)).filter(
                F.col("city") == city.slug
            )
            trend_summary = (
                trends.groupBy("city", "keyword")
                .agg(
                    F.avg("interest_index").alias("avg_interest"),
                    F.max("interest_index").alias("max_interest"),
                    F.count("*").alias("observation_count"),
                )
                .withColumn("snapshot_at", F.lit(snapshot_at))
            )
            if trend_summary.head(1):
                written["trend_interest_summary"] = write_delta_dataframe(
                    trend_summary, GOLD_ROOT / "trend_interest_summary"
                )
                avg_row = trend_summary.agg(F.avg("avg_interest")).collect()[0][0]
                if avg_row is not None:
                    trend_avg = round(float(avg_row), 2)

        stress = round(
            active_cta * 0.05 + active_noaa * 2.0 + avg_precip * 0.1 + airport_stress, 2
        )
        pulse_df = spark.createDataFrame(
            [
                {
                    "city": city.slug,
                    "snapshot_at": snapshot_at,
                    "active_cta_alerts": active_cta,
                    "active_noaa_alerts": active_noaa,
                    "avg_precip_pct_next_periods": avg_precip,
                    "city_stress_score": stress,
                    "airport_flight_category": airport_flt,
                    "airport_visibility_sm": airport_vis,
                    "trend_avg_interest": trend_avg,
                    "fred_series_count": fred_count,
                }
            ]
        )
        written["city_pulse_snapshot"] = write_delta_dataframe(
            pulse_df, GOLD_ROOT / "city_pulse_snapshot"
        )
    finally:
        spark.stop()
    return written
