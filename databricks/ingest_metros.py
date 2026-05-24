# Databricks notebook source
# MAGIC %md
# MAGIC # AQ PulseGrid — ingest Tier metros (bronze)

# COMMAND ----------

dbutils.widgets.text("tier", "full")

# COMMAND ----------

import subprocess
import sys

tier = dbutils.widgets.get("tier")
repo = "/Workspace/Repos/pulsegrid/aq-pulsegrid"

subprocess.check_call(
    [
        sys.executable,
        f"{repo}/generate_city.py",
        "--all-metros",
        "--tier",
        tier,
        "--ingest-only",
        "--extended-ingest",
    ]
)
print("Bronze ingest complete for tier:", tier)
