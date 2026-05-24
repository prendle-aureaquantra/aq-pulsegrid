# Databricks notebook source
# MAGIC %md
# MAGIC # AQ PulseGrid — ingest Tier metros (bronze)

# COMMAND ----------

dbutils.widgets.text("tier", "full")
dbutils.widgets.text("repo_path", "/Repos/prendleman@aureaquantra.com/aq-pulsegrid")

# COMMAND ----------

# MAGIC %pip install deltalake pandas pyarrow requests pyyaml python-dotenv

# COMMAND ----------

import subprocess
import sys

tier = dbutils.widgets.get("tier")
repo_path = dbutils.widgets.get("repo_path").strip()
if not repo_path.startswith("/Workspace"):
    repo_path = "/Workspace" + (repo_path if repo_path.startswith("/") else f"/{repo_path}")
repo = repo_path.rstrip("/")

subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", repo, "-q"])
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
