# Databricks

## One-time setup

1. Set in parent `.env` (or `aq-pulsegrid/.env`):
   - `DATABRICKS_HOST`
   - `DATABRICKS_TOKEN`
   - optional `DATABRICKS_REPO_PATH` (default `/Repos/pulsegrid/aq-pulsegrid`)
2. Connect repo: Databricks → **Repos** → Add Git URL → `aq-pulsegrid`.
3. Install [Databricks CLI](https://docs.databricks.com/dev-tools/cli/index.html) v0.200+ (bundles).

## Deploy scheduled job (Asset Bundle)

```powershell
cd aq-pulsegrid
python tools/deploy_databricks_job.py --repo-path /Repos/YOUR_USER/aq-pulsegrid
```

This creates **aq-pulsegrid-chicago-daily** (06:00 America/Chicago) running `databricks/chicago_daily.py`.

Validate only:

```powershell
python tools/deploy_databricks_job.py --validate-only
```

## Manual notebook import (fallback)

```powershell
python tools/run_databricks_pipeline.py
```

## Local fallback (no Databricks)

```powershell
python tools/run_databricks_pipeline.py --local-only --with-visuals
```

## Job behavior

The notebook runs `generate_city.py --transform-only` and `--ml-only` against the mounted repo.
Bronze ingest can run from GitHub Actions or local CI and sync JSON to a volume/DBFS prefix.
