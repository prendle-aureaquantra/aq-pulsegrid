"""Table writers: delta-rs (default local) or PySpark."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd


def _prepare_for_delta(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce pandas nulls to Delta-safe scalar types."""
    out = df.copy()
    for col in out.columns:
        series = out[col]
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().any():
            out[col] = numeric.fillna(0)
        else:
            out[col] = series.fillna("").astype(str)
    return out


def use_spark_engine() -> bool:
    if os.getenv("PULSEGRID_ENGINE", "").lower() == "spark":
        return True
    if os.getenv("PULSEGRID_ENGINE", "").lower() == "delta-rs":
        return False
    # PySpark 3.5 + cloudpickle is unreliable on Python 3.14+ locally
    return sys.version_info < (3, 14)


def write_delta_table(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return path if path.exists() else path
    df = _prepare_for_delta(pd.DataFrame(rows))
    from deltalake import write_deltalake

    write_deltalake(str(path), df, mode="overwrite", schema_mode="merge")
    return path


def merge_delta_table(
    rows: list[dict], path: Path, *, partition_key: str = "city"
) -> Path:
    """Upsert rows for one or more partition keys (e.g. city) into a Delta table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return path if path.exists() else path

    new_df = pd.DataFrame(rows)
    if path.exists():
        try:
            existing = read_delta_table(path)
        except Exception:
            existing = pd.DataFrame()
        if (
            not existing.empty
            and partition_key in new_df.columns
            and partition_key in existing.columns
        ):
            keys = new_df[partition_key].dropna().astype(str).unique().tolist()
            existing = existing[~existing[partition_key].astype(str).isin(keys)]
            all_cols = list(dict.fromkeys(list(existing.columns) + list(new_df.columns)))
            existing = existing.reindex(columns=all_cols)
            new_df = new_df.reindex(columns=all_cols)
            new_df = pd.concat([existing, new_df], ignore_index=True)

    new_df = _prepare_for_delta(new_df)
    from deltalake import write_deltalake

    write_deltalake(str(path), new_df, mode="overwrite", schema_mode="merge")
    return path


def append_delta_table(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    from deltalake import write_deltalake

    mode = "append" if path.exists() else "overwrite"
    write_deltalake(str(path), df, mode=mode, schema_mode="merge")
    return path


def read_delta_table(path: Path) -> pd.DataFrame:
    from deltalake import DeltaTable

    return DeltaTable(str(path)).to_pandas()


def write_delta_dataframe(spark_df, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    spark_df.write.format("delta").mode("overwrite").save(str(path))
    return path
