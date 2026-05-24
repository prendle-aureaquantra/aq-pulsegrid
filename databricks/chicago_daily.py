# Databricks notebook source
# MAGIC %md
# MAGIC # AQ PulseGrid — Chicago daily job
# MAGIC Run silver → gold → ML on cluster. Bronze ingest runs via scheduled REST job or local CI.

# COMMAND ----------

dbutils.widgets.text("city", "chicago")
dbutils.widgets.text("repo_path", "/Repos/prendleman@aureaquantra.com/aq-pulsegrid")

# COMMAND ----------

city = dbutils.widgets.get("city")
print(f"PulseGrid daily job for {city}")

# COMMAND ----------

# MAGIC %pip install deltalake pandas pyarrow requests pyyaml python-dotenv

# COMMAND ----------

import subprocess
import sys

repo_path = dbutils.widgets.get("repo_path").strip()
if not repo_path.startswith("/Workspace"):
    repo_path = "/Workspace" + (repo_path if repo_path.startswith("/") else f"/{repo_path}")
repo = repo_path.rstrip("/")
for step in ("--transform-only", "--ml-only"):
    subprocess.check_call(
        [sys.executable, f"{repo}/generate_city.py", "--city", city, step]
    )

print("Done. Refresh semantic model / PBIP separately or mount generated CSVs.")
