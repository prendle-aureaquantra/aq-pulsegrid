"""Optional Spark MLlib scoring path when PULSEGRID_ENGINE=spark."""

from __future__ import annotations

from typing import Any


def mllib_anomaly_score(features: list[list[float]]) -> list[float]:
    """Isolation-style outlier scores via Spark MLlib (higher = more anomalous)."""
    if not features:
        return []
    from pyspark.ml.feature import VectorAssembler
    from pyspark.ml.stat import Summarizer
    from pyspark.sql import Row

    from pulsegrid.spark_session import build_spark

    spark = build_spark("pulsegrid-mllib")
    try:
        cols = [f"f{i}" for i in range(len(features[0]))]
        rows = [Row(**dict(zip(cols, vals))) for vals in features]
        df = spark.createDataFrame(rows)
        assembler = VectorAssembler(inputCols=cols, outputCol="features")
        assembled = assembler.transform(df)
        summary = Summarizer.metrics("mean", "std").summary(
            assembled.select("features")
        )
        mean = summary.collect()[0]["features"][0]
        std = summary.collect()[0]["features"][1]
        scores: list[float] = []
        for vals in features:
            z = sum(
                abs((v - m) / (s or 1.0))
                for v, m, s in zip(vals, mean, std, strict=False)
            )
            scores.append(round(float(z), 3))
        return scores
    finally:
        spark.stop()


def enrich_metrics_with_mllib(metrics: dict[str, Any]) -> dict[str, Any]:
    """Add mllib_z_score to metrics dict when spark engine available."""
    from pulsegrid.io.delta_writer import use_spark_engine

    if not use_spark_engine():
        return metrics
    vec = [
        float(metrics.get("active_cta_alerts") or 0),
        float(metrics.get("active_noaa_alerts") or 0),
        float(metrics.get("avg_precip_pct_next_periods") or 0),
        float(metrics.get("city_stress_index") or 0),
    ]
    scores = mllib_anomaly_score([vec])
    if scores:
        metrics["mllib_z_score"] = scores[0]
    return metrics
