# Site integration (aureaquantra.com)

## Goal

Expose AQ PulseGrid like the operational ASP demo at `/demo-dashboard/`.

## Option A — Link to published Fabric report

1. Publish `ChicagoPulse` from Power BI Desktop to a **public** or **org** workspace.
2. Get embed URL or share link from Fabric.
3. Add WordPress page `/pulsegrid/` with iframe or Power BI embed block (same pattern as demo dashboard).

Example HTML block:

```html
<section class="aq-pulsegrid-hero">
  <h1>Chicago Live City Pulse</h1>
  <p>Streaming public data · ML stress index · automated PBIP</p>
  <iframe title="Chicago Pulse" width="1140" height="541"
    src="https://app.powerbi.com/view?r=YOUR_REPORT_ID"
    frameborder="0" allowFullScreen="true"></iframe>
</section>
```

## Option B — Static screenshots + CTA (fastest)

Use committed PNGs from `docs/screenshots/` and link to GitHub repo + sample PBIP download.

## Option C — ASP.NET mini-site (like operational demo)

Copy `asp-demo-dashboard` pattern:

- New project `pulsegrid-demo/` with KPI cards fed from Delta/CSV API  
- Deploy to Lightsail subdomain `pulse.aureaquantra.com`  
- Link from main site nav

## Config hook (parent repo)

In `config/site_spec.yaml`, add a page slug `pulsegrid` mirroring `demo-dashboard` content pattern. Use `tools/update_site_spec_demo_urls.py` as a template for URL rewrites.

## Branding

Match Aurea Quantra palette: gold `#D4AF37`, charcoal `#2C2C2C`, cream `#FFF8E7` (same as chat widget + PBIP theme `AureaQuantraPulse.json`).
