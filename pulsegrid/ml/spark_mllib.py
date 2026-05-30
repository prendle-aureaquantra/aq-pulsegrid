"""Multivariate anomaly scoring — pandas (delta-rs) or Spark MLlib (optional)."""

from __future__ import annotations

from typing import Any

import pandas as pd

MLLIB_FEATURE_KEYS = (
    "active_transit_alerts",
    "active_noaa_alerts",
    "avg_precip_pct_next_periods",
    "city_stress_index",
)


def _vector_from_mapping(row: dict[str, Any] | pd.Series) -> list[float]:
    return [float(row.get(k) or 0) for k in MLLIB_FEATURE_KEYS]


def build_feature_matrix(
    metrics: dict[str, Any], history: pd.DataFrame | None
) -> list[list[float]]:
    """History rows plus the current snapshot as the final row to score."""
    matrix: list[list[float]] = []
    if history is not None and not history.empty:
        hist = history
        if "city" in hist.columns and metrics.get("city"):
            hist = hist[hist["city"] == metrics["city"]]
        if "snapshot_at" in hist.columns:
            hist = hist.sort_values("snapshot_at")
        for _, row in hist.iterrows():
            matrix.append(_vector_from_mapping(row))
    matrix.append(_vector_from_mapping(metrics))
    return matrix


def pandas_multivariate_score(features: list[list[float]]) -> float | None:
    """Score the last row vs mean/std of prior rows (sum of abs z-scores)."""
    if len(features) < 2:
        return None
    baseline, current = features[:-1], features[-1]
    if not baseline:
        return None
    n_feat = len(current)
    means: list[float] = []
    stds: list[float] = []
    for i in range(n_feat):
        col = [row[i] for row in baseline]
        mean = sum(col) / len(col)
        var = sum((v - mean) ** 2 for v in col) / len(col)
        std = var**0.5 or 1.0
        means.append(mean)
        stds.append(std)
    score = sum(
        abs((v - m) / s) for v, m, s in zip(current, means, stds, strict=False)
    )
    return round(float(score), 3)


def mllib_anomaly_score(features: list[list[float]]) -> list[float]:
    """Spark MLlib path: z-style multivariate scores for each row."""
    if not features:
        return []
    if len(features) == 1:
        return [0.0]
    from pyspark.ml.feature import VectorAssembler
    from pyspark.ml.stat import Summarizer
    from pyspark.sql import Row

    from pulsegrid.spark_session import build_spark

    spark = build_spark("pulsegrid-mllib")
    try:
        cols = [f"f{i}" for i in range(len(features[0]))]
        rows = [Row(**dict(zip(cols, vals, strict=False))) for vals in features]
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


def score_current_snapshot(
    metrics: dict[str, Any], history: pd.DataFrame | None
) -> float | None:
    matrix = build_feature_matrix(metrics, history)
    if len(matrix) < 2:
        return None
    from pulsegrid.io.delta_writer import use_spark_engine

    if use_spark_engine():
        scores = mllib_anomaly_score(matrix)
        return scores[-1] if scores else None
    return pandas_multivariate_score(matrix)


def enrich_metrics_with_mllib(
    metrics: dict[str, Any], *, history: pd.DataFrame | None = None
) -> dict[str, Any]:
    """Add mllib_z_score using pulse_history when available."""
    score = score_current_snapshot(metrics, history)
    if score is not None:
        metrics["mllib_z_score"] = score
    return metrics
