# Databricks notebook source
# MAGIC %md
# MAGIC # AQ PulseGrid — daily global pipeline (single task, shared DBFS)
# MAGIC Ingest → transform → ML → platform CSV export.

# COMMAND ----------

dbutils.widgets.text("tier", "full")
dbutils.widgets.text("repo_path", "/Repos/prendleman@aureaquantra.com/aq-pulsegrid")

# COMMAND ----------

import os
import subprocess
import sys
from pathlib import Path

# Serverless: use local_disk0 (DBFS /dbfs/tmp is not writable on serverless).
_data = Path(os.getenv("PULSEGRID_DATABRICKS_DATA_ROOT", "/local_disk0/pulsegrid"))
_data.mkdir(parents=True, exist_ok=True)
os.environ["PULSEGRID_DATA_ROOT"] = str(_data)
os.environ["PULSEGRID_ENGINE"] = "delta-rs"

tier = dbutils.widgets.get("tier")
repo_path = dbutils.widgets.get("repo_path").strip()
if not repo_path.startswith("/Workspace"):
    repo_path = "/Workspace" + (repo_path if repo_path.startswith("/") else f"/{repo_path}")
repo = repo_path.rstrip("/")

# COMMAND ----------

# MAGIC %pip install deltalake pandas pyarrow requests pyyaml python-dotenv -q

# COMMAND ----------

subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", repo, "-q"])
gen = [sys.executable, f"{repo}/generate_city.py", "--all-metros", "--tier", tier]

steps = [
    ("ingest", gen + ["--ingest-only", "--extended-ingest"]),
    ("transform", gen + ["--transform-only"]),
    ("ml", gen + ["--ml-only"]),
    ("export", [sys.executable, f"{repo}/generate_city.py", "--platform-csv-only", "--all-metros", "--tier", tier]),
]
for name, cmd in steps:
    print("===", name, "===")
    subprocess.check_call(cmd)
print("Pipeline complete:", tier)
