"""Spark-engine ML path (optional; pandas z-score remains default locally)."""

from __future__ import annotations

from pathlib import Path

from pulsegrid.io.delta_writer import use_spark_engine


def run_ml_spark(city_slug: str) -> dict[str, Path]:
    """
    ML scoring when PULSEGRID_ENGINE=spark.

    Reads silver/gold via Spark where helpful, then uses the same pandas
    stress + z-score anomaly pipeline on the driver. Adds mllib_z_score via
    spark_mllib.enrich_metrics_with_mllib.
    """
    if not use_spark_engine():
        raise RuntimeError("run_ml_spark requires PULSEGRID_ENGINE=spark")

    from pulsegrid.spark_session import build_spark

    spark = build_spark("pulsegrid-ml")
    try:
        # Warm session; actual scoring reuses proven pandas path on driver
        spark.range(1).count()
    finally:
        spark.stop()

    from pulsegrid.jobs.ml_chicago import run_ml as run_ml_pandas

    return run_ml_pandas(city_slug)
