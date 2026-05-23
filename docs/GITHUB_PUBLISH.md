# Publish AQ PulseGrid as a standalone GitHub repo

## What gets committed

| Included | Excluded (`.gitignore`) |
|----------|-------------------------|
| `pulsegrid/`, `pbip_generator/`, `tests/` | `.env`, credentials |
| `generated_reports/chicago/` sample PBIP + CSV | `datasets/bronze/` live pulls |
| `docs/screenshots/` | `~/.local/aq-pulsegrid/` Delta runtime |
| `.env.example`, `LICENSE`, CI workflow | `*.parquet`, `*.delta/` |

## One-time: create public repo

From the **parent** monorepo (or copy `aq-pulsegrid/` to a new folder):

```powershell
cd "g:\My Drive\aq_wp_selenium_bot\aq-pulsegrid"
git init
git add .
git status   # verify no .env or datasets/bronze/
git commit -m "Initial public release: Chicago MVP pipeline + PBIP sample"
gh repo create prendle-aureaquantra/aq-pulsegrid --public --source=. --remote=origin --push
```

Replace `YOUR_ORG` with your GitHub username or org (e.g. `aureaquantra`).

## CI

Copy or symlink `.github/workflows/aq-pulsegrid.yml` into this repo root, or add:

```yaml
# .github/workflows/ci.yml — see parent repo aq-pulsegrid.yml
```

## After clone (for visitors)

```bash
git clone https://github.com/YOUR_ORG/aq-pulsegrid.git
cd aq-pulsegrid
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python generate_city.py --city chicago --with-visuals
```

Open `generated_reports/chicago/ChicagoPulse.pbip` in Power BI Desktop (or local mirror under `~/.local/aq-pulsegrid/reports/chicago/`).

## Sample PBIP note

Committed CSVs are small static snapshots. For fresh data, run the full pipeline; `--pbip-only` rewrites absolute CSV paths for your machine.
