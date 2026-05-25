# Databricks notebook source
# MAGIC %md
# MAGIC # AQ PulseGrid — global daily (transform / ML / platform export)

# COMMAND ----------

dbutils.widgets.text("tier", "full")
dbutils.widgets.text("step", "transform")
dbutils.widgets.text("repo_path", "/Repos/prendleman@aureaquantra.com/aq-pulsegrid")

# COMMAND ----------

# MAGIC %pip install deltalake pandas pyarrow requests pyyaml python-dotenv

# COMMAND ----------

import os
import subprocess
import sys
from pathlib import Path

_dbfs = Path("/dbfs/tmp/aq_pulsegrid")
_dbfs.mkdir(parents=True, exist_ok=True)
os.environ["PULSEGRID_DATA_ROOT"] = str(_dbfs)
os.environ["PULSEGRID_ENGINE"] = "delta-rs"

tier = dbutils.widgets.get("tier")
step = dbutils.widgets.get("step")
repo_path = dbutils.widgets.get("repo_path").strip()
if not repo_path.startswith("/Workspace"):
    repo_path = "/Workspace" + (repo_path if repo_path.startswith("/") else f"/{repo_path}")
repo = repo_path.rstrip("/")
base = [sys.executable, f"{repo}/generate_city.py", "--all-metros", "--tier", tier]

subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", repo, "-q"])

if step == "transform":
    subprocess.check_call(base + ["--transform-only"])
elif step == "ml":
    subprocess.check_call(base + ["--ml-only"])
elif step == "export":
    subprocess.check_call(
        [
            sys.executable,
            f"{repo}/generate_city.py",
            "--platform-csv-only",
            "--all-metros",
            "--tier",
            tier,
        ]
    )
else:
    raise ValueError(f"Unknown step: {step}")

print("Done:", step, "tier:", tier)
