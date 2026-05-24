# Automated pipeline ops (Option A)

PulseGrid **scores and detects anomalies on a schedule** — no supervised model training. Each run appends `ml/pulse_history`, which improves z-score baselines over time.

## Pipeline steps

| Step | CLI flag | Output |
|------|----------|--------|
| Ingest | `--ingest-only` | Bronze JSON |
| Transform | `--transform-only` | Silver + gold Delta |
| ML | `--ml-only` | Stress index, anomalies, `pulse_history` |
| Export | `--platform-only` | Platform CSV + PBIP data paths |

## 1. Databricks (recommended)

**Job:** `aq-pulsegrid-daily-global` — daily **06:00 UTC**, `pause_status: UNPAUSED`.

```powershell
cd aq-pulsegrid
python tools/deploy_databricks_job.py --repo-path /Repos/YOUR_USER/aq-pulsegrid
python tools/deploy_databricks_job.py --run-now   # optional smoke run
```

Tasks: `ingest_metros` → `transform_metros` → `ml_metros` → `export_platform` (see `databricks.yml`).

After deploy, confirm in **Workflows** that the job is **Active** and the Repos path matches your Git integration.

## 2. GitHub Actions (cloud trigger)

Workflow: [`.github/workflows/scheduled-pipeline.yml`](../.github/workflows/scheduled-pipeline.yml)

**Repo secrets:** `DATABRICKS_HOST`, `DATABRICKS_TOKEN`  
**Optional repo variable:** `DATABRICKS_REPO_PATH`

- Runs `databricks bundle run pulsegrid_daily_global` daily at 06:15 UTC
- **Actions → Scheduled pipeline → Run workflow** for manual run
- Enable **run_deploy** to `bundle deploy` before run (after bundle definition changes)

If secrets are missing, the workflow skips without failing.

## 3. Local / Lightsail (no Databricks)

```powershell
cd aq-pulsegrid
python tools/run_scheduled_pipeline.py
# ML only after fresh bronze:
python tools/run_scheduled_pipeline.py --step transform,ml
```

**Windows Task Scheduler:** run `tools\run_scheduled_pipeline.ps1` daily (e.g. 06:00), or register once:

```powershell
powershell -ExecutionPolicy Bypass -File tools\register_scheduled_task.ps1
```

Task name: **AQ-PulseGrid-Daily-Pipeline** (06:00 local, full ingest → transform → ML → export).

**Linux systemd** (clone repo to `/var/aq-pulsegrid/repo`, venv, then):

```bash
sudo cp publish/linux/systemd/aq-pulsegrid-pipeline.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aq-pulsegrid-pipeline.timer
sudo systemctl list-timers aq-pulsegrid-pipeline.timer
```

Ops status: `generated_reports/platform/last_pipeline_run.json` (also exposed on the status app when deployed).

## Verify

```powershell
python -m pulsegrid.web.status_app   # local
# GET https://pulse.aureaquantra.com/health
```

Check `last_pipeline_run.json` for `job: scheduled-pipeline` or `ml-only` with recent `finished_at`.
