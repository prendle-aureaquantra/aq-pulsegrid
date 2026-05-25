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

# Serverless: writable scratch under /tmp (not /dbfs or /local_disk0 on all runtimes).
_data = Path(os.getenv("PULSEGRID_DATABRICKS_DATA_ROOT", "/tmp/aq_pulsegrid"))
_data.mkdir(parents=True, exist_ok=True)
os.environ["PULSEGRID_DATA_ROOT"] = str(_data)
os.environ["PULSEGRID_ENGINE"] = "delta-rs"
os.environ["PULSEGRID_LENIENT_CLOUD"] = "1"

tier = dbutils.widgets.get("tier")
repo_path = dbutils.widgets.get("repo_path").strip()
if not repo_path.startswith("/Workspace"):
    repo_path = "/Workspace" + (repo_path if repo_path.startswith("/") else f"/{repo_path}")
repo = repo_path.rstrip("/")

# COMMAND ----------

# MAGIC %pip install deltalake pandas pyarrow requests pyyaml python-dotenv -q

# COMMAND ----------

subprocess.run(["git", "-C", repo, "fetch", "origin", "main"], check=False)
subprocess.run(["git", "-C", repo, "checkout", "main"], check=False)
subprocess.run(["git", "-C", repo, "pull", "--ff-only", "origin", "main"], check=False)
subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", repo, "-q"])
gen = [sys.executable, f"{repo}/generate_city.py", "--all-metros", "--tier", tier]

steps = [
    ("ingest", gen + ["--ingest-only", "--extended-ingest"]),
    ("transform", gen + ["--transform-only"]),
    ("ml", gen + ["--ml-only"]),
    ("export", [sys.executable, f"{repo}/generate_city.py", "--platform-csv-only", "--all-metros"]),
]
for name, cmd in steps:
    print("===", name, "===")
    rc = subprocess.call(cmd)
    if rc != 0 and name in ("transform", "ml", "export"):
        print(f"WARN: {name} exited {rc} (lenient cloud — continuing)")
    elif rc != 0:
        raise subprocess.CalledProcessError(rc, cmd)
print("Pipeline complete:", tier)
