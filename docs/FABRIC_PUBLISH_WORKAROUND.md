# Desktop publish blocked by license

If Power BI Desktop shows **“Only users with certain Power BI licenses can publish to this workspace”** for **AQ PulseGrid**, use one of these paths.

## Recommended: publish to Produce Ops

You are already **Admin** on **Produce Ops - amc_marano** (shared capacity — needs **Power BI Pro**, not PPU).

1. In Desktop: **Publish** → **Produce Ops - amc_marano**.
2. Name the report **PulseGrid** (or note the name you used).
3. Tell the agent or run:

```powershell
cd aq-pulsegrid
python tools/publish_pulsegrid_fabric.py --workspace "Produce Ops - amc_marano"
```

That sets `POWERBI_PULSEGRID_EMBED_URL` from the published report. The AQ PulseGrid workspace (API dataset) remains for automation; the live embed can come from Produce Ops until PBIP is moved.

## Alternative: save .pbix and import via API

1. Desktop: **File → Save a copy** → `PulseGrid.pbix`.
2. Service principal import (no Desktop license on target workspace):

```powershell
python tools/publish_pulsegrid_fabric.py --workspace "AQ PulseGrid" --pbix "C:\path\to\PulseGrid.pbix"
```

## Fix licensing (admin)

**Programmatic (same Azure app as Fabric):**

```powershell
cd "G:\My Drive\aq_wp_selenium_bot"
# One-time: add Graph User.ReadWrite.All + Organization.Read.All (browser admin login)
python add_graph_license_permissions.py
# Assign Pro seat
python assign_powerbi_pro_license.py --user prendleman@aureaquantra.com
```

**Manual:** Microsoft 365 admin center → Users → `prendleman@aureaquantra.com` → Licenses → **Power BI Pro**.

Or assign **Premium Per User** only if you will publish to PPU workspaces (`POWERBI_CAPACITY_ID` in `.env`).

## Embed without republishing PBIP

The **PulseGrid** report already exists in **AQ PulseGrid** (API-wired shell). In the browser:

https://app.powerbi.com/groups/8823f792-a990-4c83-887d-7e1ec3e3d07d/reports/2c172b3e-b279-4eca-ac5d-112a0279cc22

→ **Embed → Publish to web** → then `python tools/publish_pulsegrid_fabric.py --workspace "AQ PulseGrid"`

That enables the public iframe without Desktop publish.
