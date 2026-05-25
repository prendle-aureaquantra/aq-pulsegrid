# Fabric / Power BI embed on aureaquantra.com

## 1. Regenerate portable PBIP (after pull)

CSV partitions use **absolute** paths (required by Power BI Desktop `File.Contents` on Windows). After cloning the repo on a new machine, regenerate or patch paths:

```powershell
cd aq-pulsegrid
python generate_city.py --platform-only --with-visuals
# or fix existing PBIP without full rebuild:
python tools/fix_pbip_csv_paths.py generated_reports/chicago generated_reports/platform
```

Open: `generated_reports/platform/PulseGrid.pbip`

## 2. Publish to Power BI Service

**Automated (if report already exists in your workspace):**

```powershell
cd aq-pulsegrid
python tools/publish_pulsegrid_fabric.py
```

Requires in parent `.env`: `FABRIC_TENANT_ID`, `FABRIC_CLIENT_ID`, `FABRIC_CLIENT_SECRET`.  
The script enables **Publish to web**, writes `POWERBI_PULSEGRID_EMBED_URL` to `.env` and `deploy/lightsail/secrets/pulsegrid.env`.

**Manual (first time):**

1. Sign in to [Power BI](https://app.powerbi.com).
2. Open `generated_reports/platform/PulseGrid.pbip` in **Power BI Desktop** → **Load** all tables → **Publish**.
3. Re-run `python tools/publish_pulsegrid_fabric.py` (or paste embed URL into `.env` yourself).

Copy the iframe `src` URL.

## 3. Configure Lightsail / local ops app

In `.env` on the server (or local):

```env
POWERBI_PULSEGRID_EMBED_URL=https://app.powerbi.com/view?r=...
PULSEGRID_PUBLIC_URL=https://pulse.aureaquantra.com/
```

Redeploy status app:

```powershell
python tools/deploy_pulsegrid_lightsail.py
```

## 4. WordPress page

```powershell
python tools/sync_pulsegrid_site_page.py
```

Uses `POWERBI_PULSEGRID_EMBED_URL` from the parent repo `.env` when configured.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Ambiguous relationship paths | Regenerate PBIP (`build_pbip` validates AirportOps → DimAirport → DimMetro) |
| Missing CSV | Run `python generate_city.py --all-metros --tier full --ingest-only` then `--platform-only` |
| Stale data | Check `data_refreshed_at` on `CityPulseSnapshot`; re-run ingest |

See also [SITE_INTEGRATION.md](SITE_INTEGRATION.md) · [PHASE2.md](PHASE2.md).
