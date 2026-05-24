# Databricks notebook source
# MAGIC %md
# MAGIC # AQ PulseGrid — global daily (transform / ML / platform export)

# COMMAND ----------

dbutils.widgets.text("tier", "full")
dbutils.widgets.text("step", "transform")

# COMMAND ----------

import subprocess
import sys

tier = dbutils.widgets.get("tier")
step = dbutils.widgets.get("step")
repo = "/Workspace/Repos/pulsegrid/aq-pulsegrid"
base = [sys.executable, f"{repo}/generate_city.py", "--all-metros", "--tier", tier]

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
