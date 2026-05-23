"""Shared SparkSession factory (local or Databricks)."""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

from pulsegrid.config import DELTA, load_dotenv


def _ensure_winutils() -> None:
    """Windows Spark needs HADOOP_HOME + winutils.exe for jar fetch/chmod."""
    if os.name != "nt":
        return
    hadoop = Path.home() / ".local" / "hadoop"
    bin_dir = hadoop / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    winutils = bin_dir / "winutils.exe"
    if not winutils.is_file():
        url = "https://github.com/cdarlint/winutils/raw/master/hadoop-3.3.5/bin/winutils.exe"
        urllib.request.urlretrieve(url, winutils)
    os.environ["HADOOP_HOME"] = str(hadoop)


def build_spark(app_name: str = "aq-pulsegrid") -> SparkSession:
    load_dotenv()
    _ensure_winutils()
    for key in ("SPARK_HOME", "JAVA_HOME"):
        val = os.getenv(key)
        if val:
            os.environ[key] = val

    builder = (
        SparkSession.builder.appName(app_name)
        .master(os.getenv("SPARK_MASTER", "local[1]"))
        .config("spark.sql.warehouse.dir", str(DELTA))
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "2g"))
    )
    builder = configure_spark_with_delta_pip(builder)
    return builder.getOrCreate()
