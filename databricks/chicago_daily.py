# Databricks notebook source
# MAGIC %md
# MAGIC # AQ PulseGrid — Chicago daily job
# MAGIC Run silver → gold → ML on cluster. Bronze ingest runs via scheduled REST job or local CI.

# COMMAND ----------

dbutils.widgets.text("city", "chicago")

# COMMAND ----------

city = dbutils.widgets.get("city")
print(f"PulseGrid daily job for {city}")

# COMMAND ----------

# MAGIC %pip install deltalake pandas pyarrow requests pyyaml python-dotenv

# COMMAND ----------

import subprocess
import sys

repo = "/Workspace/Repos/pulsegrid/aq-pulsegrid"  # adjust after Git integration
for step in ("--transform-only", "--ml-only"):
    subprocess.check_call(
        [sys.executable, f"{repo}/generate_city.py", "--city", city, step]
    )

print("Done. Refresh semantic model / PBIP separately or mount generated CSVs.")
