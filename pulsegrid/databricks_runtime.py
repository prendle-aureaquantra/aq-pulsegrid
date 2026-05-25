"""Shared env for Databricks job tasks (DBFS-backed bronze + delta-rs)."""

from __future__ import annotations

import os
from pathlib import Path


def setup_databricks_env(
    *,
    data_root: str | None = None,
    engine: str = "delta-rs",
) -> Path:
    """
    Use DBFS so ingest/transform/ML tasks in one job run share bronze and Delta paths.
    Call before importing pulsegrid.config in notebooks.
    """
    root = Path(
        data_root or os.getenv("PULSEGRID_DATABRICKS_DATA_ROOT", "/dbfs/tmp/aq_pulsegrid")
    )
    root.mkdir(parents=True, exist_ok=True)
    os.environ["PULSEGRID_DATA_ROOT"] = str(root)
    os.environ["PULSEGRID_ENGINE"] = engine
    return root
