# Operational Web Console

AQ PulseGrid ships multiple delivery surfaces for demos and production-style reviews.

## FastAPI status app (primary)

- **Source:** [`pulsegrid/web/status_app.py`](../pulsegrid/web/status_app.py)
- **Deploy:** [`deploy/lightsail/`](../deploy/lightsail/)
- **Live URL:** [https://pulse.aureaquantra.com](https://pulse.aureaquantra.com)

Endpoints:

| Path | Purpose |
|------|---------|
| `/` | MVP status, roadmap, optional Fabric iframe |
| `/health` | JSON health probe |
| `/api/pulse` | Latest Chicago pulse CSV + metadata |

Monorepo automation (parent repo):

```bash
python deploy_pulsegrid.py --from-dotenv
python enable_pulsegrid_public.py --skip-dns --skip-apache
python enable_pulsegrid_https_ssh.py
```

## ASP.NET operational demo (sibling project)

The Aurea Quantra WordPress monorepo includes a separate **ASP.NET Core** operational
dashboard demo (`asp-demo-dashboard`) deployed to the same Lightsail instance. That demo
uses C# / Kestrel on port 5188 and is **not** part of this Python repo.

PulseGrid’s Python stack is intentionally separate:

- **PulseGrid:** FastAPI + CSV gold exports + PBIP generator
- **ASP demo:** Invoice drill-down ASP.NET reference implementation

Do not bury either surface — each serves a different reviewer story (Python analytics platform
vs. enterprise ASP.NET delivery pattern).

## IIS / legacy ASP note

There is no Classic ASP (`.asp`) page in this repository. If you need an IIS-style portal
prototype, use the ASP.NET demo in the monorepo or add a `legacy-web/` folder with an
intentional README linking back here.
