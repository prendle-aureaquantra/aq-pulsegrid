"""FastAPI status app for Lightsail — serves latest Chicago pulse CSV + health."""
from __future__ import annotations

import csv
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="AQ PulseGrid", version="0.1.0")

DATA_DIR = Path(os.getenv("PULSEGRID_DATA_DIR", "data"))
EMBED_URL = (os.getenv("POWERBI_PULSEGRID_EMBED_URL") or "").strip()
CITY = (os.getenv("PULSEGRID_CITY") or "chicago").strip()


def _read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


@app.get("/health")
def health() -> dict[str, object]:
    snap = _read_csv("CityPulseSnapshot.csv")
    return {
        "status": "ok",
        "city": CITY,
        "dataDir": str(DATA_DIR),
        "snapshotRows": len(snap),
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
        f'<iframe title="Chicago PulseGrid" src="{EMBED_URL}" '
        'style="width:100%;min-height:520px;border:0;border-radius:8px"></iframe>'
        if EMBED_URL
        else "<p><em>Set POWERBI_PULSEGRID_EMBED_URL for live Fabric embed.</em></p>"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>AQ PulseGrid — {CITY.title()}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0f1419; color: #e7ecf1; }}
    .kpis {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 1rem; }}
    .kpi {{ background: #1a2332; padding: 1rem; border-radius: 8px; }}
    .kpi strong {{ display: block; font-size: 1.75rem; color: #7dd3fc; }}
    header {{ margin-bottom: 1.5rem; }}
    a {{ color: #7dd3fc; }}
  </style>
</head>
<body>
  <header>
    <h1>AQ PulseGrid — {CITY.title()}</h1>
    <p>Operational demo · snapshot {snapshot_at}</p>
  </header>
  <section class="kpis">
    <div class="kpi"><span>City stress</span><strong>{stress}</strong></div>
    <div class="kpi"><span>Transit load</span><strong>{transit}</strong></div>
    <div class="kpi"><span>Weather risk</span><strong>{weather}</strong></div>
  </section>
  <section style="margin-top:2rem">{embed}</section>
  <p style="margin-top:2rem"><a href="/api/pulse">JSON API</a> · <a href="/health">health</a></p>
</body>
</html>"""
