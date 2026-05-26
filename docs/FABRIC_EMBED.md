# Fabric / Power BI embed on aureaquantra.com

**Live:** [pulse.aureaquantra.com/embed](https://pulse.aureaquantra.com/embed) · [aureaquantra.com/demo-dashboard](https://aureaquantra.com/demo-dashboard/)

When the tenant blocks **Publish to web** for service principals (or returns 404), the status app serves an authenticated embed via **`GenerateToken`** at `/embed`. Set `FABRIC_*` + `POWERBI_PULSEGRID_WORKSPACE_ID` / `POWERBI_PULSEGRID_REPORT_ID` on Lightsail (`pulsegrid.env`).

## Automated wiring (Azure service principal)

Uses `FABRIC_TENANT_ID`, `FABRIC_CLIENT_ID`, `FABRIC_CLIENT_SECRET` (or `AZURE_*` aliases) from the parent repo `.env`.

```powershell
cd aq-pulsegrid
python tools/fabric_wire_pulsegrid.py
```

This script:

1. Creates or reuses workspace **`AQ PulseGrid`** (override with `POWERBI_WORKSPACE`).
2. Imports platform CSVs as an Excel semantic model (`PulseGrid_platform` dataset).
3. Clones a shell report (default: `AMC_ProduceOps` from `Produce Ops - amc_marano`) and binds it to that dataset.
4. Calls **Publish to web** and writes `POWERBI_PULSEGRID_EMBED_URL` when the tenant allows it.

If step 4 returns **403** (`API is not accessible for application`), publish to web once in the browser:

1. Open the report URL printed by the script (workspace **AQ PulseGrid** → report **PulseGrid**).
2. **File → Embed report → Publish to web**.
3. Re-run: `python tools/publish_pulsegrid_fabric.py --workspace "AQ PulseGrid"`

Then redeploy and sync WordPress:

```powershell
cd ..
python deploy_pulsegrid.py --from-dotenv
cd aq-pulsegrid
python tools/sync_pulsegrid_wp_page.py
```

Verify: https://pulse.aureaquantra.com/health → `embedConfigured: true`

## List workspaces / reports

```powershell
python tools/list_powerbi_reports.py
```

## Full PBIP (optional, richer visuals)

CSV partitions use **absolute** paths (required by Power BI Desktop). Regenerate after clone:

```powershell
python generate_city.py --platform-only --with-visuals
python tools/fix_pbip_csv_paths.py generated_reports/chicago generated_reports/platform
```

Open `generated_reports/platform/PulseGrid.pbip` in Desktop → publish to **AQ PulseGrid** (refresh the publish dialog if you do not see it; `fabric_wire_pulsegrid.py` adds your account as workspace admin) → publish to web (manual or `publish_pulsegrid_fabric.py`).

## Configure Lightsail / local ops app

```env
POWERBI_WORKSPACE=AQ PulseGrid
POWERBI_PULSEGRID_EMBED_URL=https://app.powerbi.com/view?r=...
PULSEGRID_PUBLIC_URL=https://pulse.aureaquantra.com/
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| PublishToWeb 403 for SP | One-time manual publish to web (see above) |
| Desktop: “Only users with certain licenses…” | Publish to **Produce Ops - amc_marano** (shared/Pro), or get **Power BI Pro** for `prendleman@aureaquantra.com`. Do not put AQ PulseGrid on PPU unless you have a PPU license. |
| Excel import dataset-only | Expected — script clones a report via REST |
| No PulseGrid report | Run `fabric_wire_pulsegrid.py` |
| Ambiguous relationship paths | Regenerate PBIP; validate AirportOps → DimMetro |
| Missing CSV | `python generate_city.py --all-metros --platform-csv-only` |

See also [SITE_INTEGRATION.md](SITE_INTEGRATION.md).
