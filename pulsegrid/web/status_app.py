"""FastAPI status app for Lightsail — serves latest Chicago pulse CSV + health."""
from __future__ import annotations

import csv
import html
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="AQ PulseGrid", version="0.1.0")

DATA_DIR = Path(os.getenv("PULSEGRID_DATA_DIR", "data"))
EMBED_URL = (os.getenv("POWERBI_PULSEGRID_EMBED_URL") or "").strip()
PUBLIC_URL = (os.getenv("PULSEGRID_PUBLIC_URL") or "https://pulse.aureaquantra.com/").strip()
REPO_URL = "https://github.com/prendle-aureaquantra/aq-pulsegrid"
CITY = (os.getenv("PULSEGRID_CITY") or "chicago").strip()

MVP_STATUS: list[tuple[str, str]] = [
    ("Chicago ingest + bronze/silver/gold", "Done"),
    ("City Pulse Score (stress index 0–100)", "Done"),
    ("Spark streaming + Delta medallion", "Done"),
    ("9 PBIP pages · ~28 visuals", "Done"),
    ("Metadata-driven PBIP generator", "Done"),
    ("AI copilot + historical replay", "Done"),
    ("Lightsail ops status app", "Done"),
    ("Fabric / Publish-to-web embed", "Next"),
]

ROADMAP: list[tuple[str, str]] = [
    ("HTTPS pulse.aureaquantra.com", "Done"),
    ("Fabric embed on status + WordPress", "Planned"),
    ("Boston full pipeline", "Planned"),
    ("Apache Sedona Spark UDFs", "Planned"),
    ("OpenSky aviation feed", "Planned"),
    ("Databricks production job", "Scaffold"),
]


def _read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _status_badge(label: str) -> str:
    key = label.lower()
    if key == "done":
        cls = "done"
    elif key in ("in progress", "next", "scaffold"):
        cls = "progress"
    else:
        cls = "planned"
    return f'<span class="badge {cls}">{html.escape(label)}</span>'


def _item_rows(items: list[tuple[str, str]]) -> str:
    rows = []
    for name, status in items:
        rows.append(f"<li><span>{html.escape(name)}</span>{_status_badge(status)}</li>")
    return "\n".join(rows)


@app.get("/health")
def health() -> dict[str, object]:
    snap = _read_csv("CityPulseSnapshot.csv")
    return {
        "status": "ok",
        "city": CITY,
        "dataDir": str(DATA_DIR),
        "snapshotRows": len(snap),
        "embedConfigured": bool(EMBED_URL),
        "publicUrl": PUBLIC_URL,
    }


@app.get("/api/pulse")
def api_pulse() -> JSONResponse:
    snap = _read_csv("CityPulseSnapshot.csv")
    anomalies = _read_csv("AnomalySignals.csv")
    transit = _read_csv("TransitAlertSummary.csv")
    return JSONResponse(
        {
            "city": CITY,
            "snapshot": snap[-1] if snap else None,
            "anomalies": anomalies[-10:],
            "transitAlerts": transit[:20],
            "mvpStatus": [{"item": n, "status": s} for n, s in MVP_STATUS],
            "roadmap": [{"item": n, "status": s} for n, s in ROADMAP],
        }
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    snap = _read_csv("CityPulseSnapshot.csv")
    latest = snap[-1] if snap else {}
    stress = latest.get("city_stress_index", "—")
    transit = latest.get("transit_load_score", "—")
    weather = latest.get("weather_risk_score", "—")
    snapshot_at = latest.get("snapshot_at", "—")
    embed = (
        f'<iframe title="Chicago PulseGrid" src="{html.escape(EMBED_URL)}" '
        'style="width:100%;min-height:520px;border:0;border-radius:8px"></iframe>'
        if EMBED_URL
        else (
            "<p class=\"muted\">Fabric embed pending — publish Chicago Pulse to Power BI Service, "
            "then set <code>POWERBI_PULSEGRID_EMBED_URL</code> in deploy secrets.</p>"
            f'<p><a href="{REPO_URL}">View repo &amp; sample PBIP</a></p>'
        )
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>AQ PulseGrid — {CITY.title()}</title>
  <style>
    :root {{ --bg:#0f1419; --panel:#1a2332; --text:#e7ecf1; --muted:#94a3b8; --accent:#7dd3fc; --done:#34d399; --prog:#fbbf24; }}
    body {{ font-family: system-ui, sans-serif; margin: 0; background: var(--bg); color: var(--text); line-height: 1.5; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1.25rem 3rem; }}
    header {{ margin-bottom: 1.5rem; }}
  header p {{ color: var(--muted); margin: .35rem 0 0; }}
    .kpis {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 1rem; }}
    .kpi {{ background: var(--panel); padding: 1rem; border-radius: 8px; }}
    .kpi span {{ color: var(--muted); font-size: .85rem; }}
    .kpi strong {{ display: block; font-size: 1.75rem; color: var(--accent); margin-top: .25rem; }}
    .grid2 {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(280px,1fr)); gap: 1rem; margin-top: 1.5rem; }}
    .panel {{ background: var(--panel); border-radius: 8px; padding: 1rem 1.25rem; }}
    .panel h2 {{ margin: 0 0 .75rem; font-size: 1.1rem; }}
    .panel ul {{ list-style: none; padding: 0; margin: 0; }}
    .panel li {{ display: flex; justify-content: space-between; gap: .75rem; padding: .45rem 0; border-bottom: 1px solid #243044; font-size: .92rem; }}
    .panel li:last-child {{ border-bottom: 0; }}
    .badge {{ font-size: .72rem; font-weight: 600; text-transform: uppercase; letter-spacing: .03em; padding: .15rem .45rem; border-radius: 4px; white-space: nowrap; }}
    .badge.done {{ background: rgba(52,211,153,.15); color: var(--done); }}
    .badge.progress {{ background: rgba(251,191,36,.15); color: var(--prog); }}
    .badge.planned {{ background: rgba(148,163,184,.15); color: var(--muted); }}
    a {{ color: var(--accent); }}
    .muted {{ color: var(--muted); }}
    code {{ background: #243044; padding: .1rem .35rem; border-radius: 4px; font-size: .85em; }}
    .embed {{ margin-top: 1.5rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>AQ PulseGrid — {CITY.title()}</h1>
      <p>Spark-powered urban intelligence · snapshot {html.escape(str(snapshot_at))}</p>
      <p><a href="{REPO_URL}">github.com/prendle-aureaquantra/aq-pulsegrid</a></p>
    </header>
    <section class="kpis">
      <div class="kpi"><span>City stress</span><strong>{html.escape(str(stress))}</strong></div>
      <div class="kpi"><span>Transit load</span><strong>{html.escape(str(transit))}</strong></div>
      <div class="kpi"><span>Weather risk</span><strong>{html.escape(str(weather))}</strong></div>
    </section>
    <section class="grid2">
      <div class="panel">
        <h2>Phase 1 MVP status</h2>
        <ul>{_item_rows(MVP_STATUS)}</ul>
      </div>
      <div class="panel">
        <h2>Roadmap</h2>
        <ul>{_item_rows(ROADMAP)}</ul>
      </div>
    </section>
    <section class="embed panel">{embed}</section>
    <p class="muted" style="margin-top:1.5rem"><a href="/api/pulse">JSON API</a> · <a href="/health">health</a></p>
  </div>
</body>
</html>"""
