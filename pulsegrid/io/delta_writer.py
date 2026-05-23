"""Table writers: delta-rs (default local) or PySpark."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd


def use_spark_engine() -> bool:
    if os.getenv("PULSEGRID_ENGINE", "").lower() == "spark":
        return True
    if os.getenv("PULSEGRID_ENGINE", "").lower() == "delta-rs":
        return False
    # PySpark 3.5 + cloudpickle is unreliable on Python 3.14+ locally
    return sys.version_info < (3, 14)


def write_delta_table(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    from deltalake import write_deltalake

    write_deltalake(str(path), df, mode="overwrite")
    return path


def append_delta_table(rows: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    from deltalake import write_deltalake

    mode = "append" if path.exists() else "overwrite"
    write_deltalake(str(path), df, mode=mode)
    return path


def read_delta_table(path: Path) -> pd.DataFrame:
    from deltalake import DeltaTable

    return DeltaTable(str(path)).to_pandas()


def write_delta_dataframe(spark_df, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    spark_df.write.format("delta").mode("overwrite").save(str(path))
    return path
