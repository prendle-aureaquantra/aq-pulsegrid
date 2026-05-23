# Site integration (aureaquantra.com)

## Goal

Expose AQ PulseGrid like the operational ASP demo at `/demo-dashboard/`.

## Generate WordPress page HTML

```powershell
cd aq-pulsegrid
python tools/sync_pulsegrid_site_page.py --out docs/pulsegrid-page.html
```

Set in `.env`:

```text
POWERBI_PULSEGRID_EMBED_URL=https://app.powerbi.com/view?r=YOUR_REPORT_TOKEN
PULSEGRID_REPO=https://github.com/prendle-aureaquantra/aq-pulsegrid
```

Paste `docs/pulsegrid-page.html` into `config/site_spec.yaml` under slug `pulsegrid`, or deploy via your existing page sync tooling.

## Option A — Fabric embed (recommended)

1. Publish `ChicagoPulse` from Power BI Desktop to workspace.
2. **Publish to web** or copy embed URL → `POWERBI_PULSEGRID_EMBED_URL`.
3. Run `sync_pulsegrid_site_page.py` — iframe is injected automatically when URL is set.

## Option B — Static screenshots + GitHub CTA

Use `docs/screenshots/` PNGs and link to [github.com/prendle-aureaquantra/aq-pulsegrid](https://github.com/prendle-aureaquantra/aq-pulsegrid).

## Branding

Gold `#D4AF37`, charcoal `#2C2C2C`, cream `#FFF8E7` — matches `AureaQuantraPulse.json` PBIP theme.
