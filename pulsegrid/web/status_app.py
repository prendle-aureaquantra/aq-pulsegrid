"""FastAPI status app — worldwide metro slicer + pulse KPIs."""

from __future__ import annotations

import csv
import html
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="AQ PulseGrid", version="0.2.0")

DATA_DIR = Path(os.getenv("PULSEGRID_DATA_DIR", "data"))
EMBED_URL = (os.getenv("POWERBI_PULSEGRID_EMBED_URL") or "").strip()
PUBLIC_URL = (
    os.getenv("PULSEGRID_PUBLIC_URL") or "https://pulse.aureaquantra.com/"
).strip()
REPO_URL = "https://github.com/prendle-aureaquantra/aq-pulsegrid"
DEFAULT_METRO = (os.getenv("PULSEGRID_CITY") or "chicago").strip().lower()

PHASE2_STATUS: list[tuple[str, str]] = [
    ("Worldwide metro registry (71 metros)", "Done"),
    ("Metro slicer — PBIP + ops console", "Done"),
    ("Multi-metro ingest adapters", "Done"),
    ("OpenSky + GTFS-RT + USGS + AQI feeds", "Done"),
    ("Platform PulseGrid.pbip export", "Done"),
    ("Databricks global daily job", "Done"),
    ("Fabric / Publish-to-web embed", "Next"),
]

ROADMAP: list[tuple[str, str]] = [
    ("HTTPS pulse.aureaquantra.com", "Done"),
    ("Phase 2 worldwide metro slicer", "Done"),
    ("Full Databricks deployment", "Done"),
    ("Expanded public data feeds", "Done"),
    ("Apache Sedona Spark UDFs", "Done"),
    ("Fabric embed on status + WordPress", "Planned"),
]


def _read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _filter_city(rows: list[dict[str, str]], metro: str) -> list[dict[str, str]]:
    if not rows or "city" not in rows[0]:
        return rows
    return [r for r in rows if r.get("city", "").lower() == metro.lower()]


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


def _metro_options(selected: str) -> str:
    metros = _read_csv("DimMetro.csv")
    if not metros:
        return f'<option value="{html.escape(selected)}" selected>{html.escape(selected.title())}</option>'
    opts = []
    for row in metros:
        slug = row.get("city", "")
        label = row.get("display_name") or row.get("metro_name") or slug
        sel = " selected" if slug.lower() == selected.lower() else ""
        opts.append(
            f'<option value="{html.escape(slug)}"{sel}>{html.escape(label)}</option>'
        )
    return "\n".join(opts)


@app.get("/health")
def health() -> dict[str, object]:
    snap = _read_csv("CityPulseSnapshot.csv")
    metros = _read_csv("DimMetro.csv")
    return {
        "status": "ok",
        "defaultMetro": DEFAULT_METRO,
        "metroCount": len(metros),
        "dataDir": str(DATA_DIR),
        "snapshotRows": len(snap),
        "embedConfigured": bool(EMBED_URL),
        "publicUrl": PUBLIC_URL,
    }


@app.get("/api/metros")
def api_metros() -> JSONResponse:
    return JSONResponse({"metros": _read_csv("DimMetro.csv")})


@app.get("/api/feed-coverage")
def api_feed_coverage() -> JSONResponse:
    try:
        from pulsegrid.ingest.feed_framework import CORE_FEED_IDS, coverage_report
        from pulsegrid.metros import list_metros

        rows = coverage_report(list_metros())
        counts = {
            fid: sum(1 for r in rows if r.get(fid) == "yes") for fid in CORE_FEED_IDS
        }
        return JSONResponse({"totalMetros": len(rows), "enabled": counts, "rows": rows})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/example-prompts")
def api_example_prompts(metro: str = Query(default="")) -> JSONResponse:
    slug = (metro or DEFAULT_METRO).strip().lower()
    try:
        from pulsegrid.copilot.prompts import sample_questions

        return JSONResponse({"metro": slug, "prompts": sample_questions(slug)})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/pipeline-status")
def api_pipeline_status() -> JSONResponse:
    from pulsegrid.pipeline_status import read_pipeline_status

    return JSONResponse(read_pipeline_status() or {"status": "unknown"})


@app.get("/api/pulse")
def api_pulse(metro: str = Query(default="")) -> JSONResponse:
    slug = (metro or DEFAULT_METRO).strip().lower()
    snap = _filter_city(_read_csv("CityPulseSnapshot.csv"), slug)
    anomalies = _filter_city(_read_csv("AnomalySignals.csv"), slug)
    transit = _filter_city(_read_csv("TransitAlertSummary.csv"), slug)
    dim = _filter_city(_read_csv("DimMetro.csv"), slug)
    return JSONResponse(
        {
            "metro": slug,
            "metroInfo": dim[-1] if dim else None,
            "snapshot": snap[-1] if snap else None,
            "anomalies": anomalies[-10:],
            "transitAlerts": transit[:20],
            "phase2Status": [{"item": n, "status": s} for n, s in PHASE2_STATUS],
            "roadmap": [{"item": n, "status": s} for n, s in ROADMAP],
        }
    )


@app.get("/", response_class=HTMLResponse)
def index(metro: str = Query(default="")) -> str:
    slug = (metro or DEFAULT_METRO).strip().lower()
    snap = _filter_city(_read_csv("CityPulseSnapshot.csv"), slug)
    latest = snap[-1] if snap else {}
    dim_rows = _filter_city(_read_csv("DimMetro.csv"), slug)
    display = (
        dim_rows[-1].get("display_name", slug.title()) if dim_rows else slug.title()
    )
    stress = latest.get("city_stress_index", "—")
    transit = latest.get("transit_load_score", "—")
    weather = latest.get("weather_risk_score", "—")
    infra_fail = latest.get("infrastructure_failure_risk", "—")
    snapshot_at = latest.get("snapshot_at", "—")
    refreshed = latest.get("data_refreshed_at", "—")
    try:
        from pulsegrid.copilot.prompts import sample_questions

        prompts = sample_questions(slug, limit=5)
    except Exception:
        prompts = []
    prompt_items = "".join(f"<li>{html.escape(p)}</li>" for p in prompts) or (
        "<li class='muted'>Run gold transform after civic311 ingest</li>"
    )
    from pulsegrid.pipeline_status import read_pipeline_status

    pipe = read_pipeline_status() or {}
    pipe_line = (
        f"Last job: {html.escape(str(pipe.get('job', '—')))} · "
        f"{html.escape(str(pipe.get('finished_at', '—')))} · "
        f"ok={pipe.get('metros_ok', '—')} failed={pipe.get('metros_failed', '—')}"
        if pipe
        else "No pipeline status file — run multi-metro ingest or platform export."
    )
    embed = (
        f'<iframe title="PulseGrid {html.escape(display)}" src="{html.escape(EMBED_URL)}" '
        'style="width:100%;min-height:520px;border:0;border-radius:8px"></iframe>'
        if EMBED_URL
        else (
            '<p class="muted">Fabric embed pending — publish PulseGrid.pbip to Power BI Service, '
            "then set <code>POWERBI_PULSEGRID_EMBED_URL</code>.</p>"
            f'<p><a href="{REPO_URL}">View repo &amp; platform PBIP</a></p>'
        )
    )
    metro_opts = _metro_options(slug)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>AQ PulseGrid — {html.escape(display)}</title>
  <style>
    :root {{ --bg:#0f1419; --panel:#1a2332; --text:#e7ecf1; --muted:#94a3b8; --accent:#7dd3fc; --done:#34d399; --prog:#fbbf24; --gold:#D4AF37; }}
    body {{ font-family: system-ui, sans-serif; margin: 0; background: var(--bg); color: var(--text); line-height: 1.5; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1.25rem 3rem; }}
    header {{ margin-bottom: 1rem; }}
    header p {{ color: var(--muted); margin: .35rem 0 0; }}
    .slicer-bar {{ background: var(--panel); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.25rem; display: flex; flex-wrap: wrap; gap: .75rem; align-items: center; }}
    .slicer-bar label {{ color: var(--muted); font-size: .85rem; }}
    .slicer-bar select {{ background: #243044; color: var(--text); border: 1px solid #334155; border-radius: 6px; padding: .45rem .65rem; min-width: 220px; }}
    .slicer-bar button {{ background: #243044; color: var(--accent); border: 1px solid #334155; border-radius: 6px; padding: .45rem .85rem; cursor: pointer; }}
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
      <h1>AQ PulseGrid — Worldwide Metros</h1>
      <p>{html.escape(display)} · snapshot {html.escape(str(snapshot_at))} · data refreshed {html.escape(str(refreshed))}</p>
      <p class="muted">{pipe_line}</p>
      <p><a href="{REPO_URL}">github.com/prendle-aureaquantra/aq-pulsegrid</a></p>
    </header>
    <form class="slicer-bar" method="get" action="/">
      <label for="metro">Metro slicer</label>
      <select id="metro" name="metro" aria-label="Select metro">{metro_opts}</select>
      <button type="submit">Apply</button>
      <button type="button" onclick="navigator.clipboard.writeText(location.origin+'/?metro='+document.getElementById('metro').value)">Copy link</button>
      <a class="muted" href="/?metro=chicago">Reset</a>
    </form>
    <section class="kpis">
      <div class="kpi"><span>City stress</span><strong>{html.escape(str(stress))}</strong></div>
      <div class="kpi"><span>Transit load</span><strong>{html.escape(str(transit))}</strong></div>
      <div class="kpi"><span>Weather risk</span><strong>{html.escape(str(weather))}</strong></div>
      <div class="kpi"><span>Infra failure risk</span><strong>{html.escape(str(infra_fail))}</strong></div>
    </section>
    <section class="panel" style="margin-top:1.25rem">
      <h2>Copilot demo prompts</h2>
      <ul>{prompt_items}</ul>
      <p class="muted">CLI: <code>python -m pulsegrid.copilot.insights {html.escape(slug)} --list-prompts</code></p>
    </section>
    <section class="grid2">
      <div class="panel">
        <h2>Phase 2 status</h2>
        <ul>{_item_rows(PHASE2_STATUS)}</ul>
      </div>
      <div class="panel">
        <h2>Roadmap</h2>
        <ul>{_item_rows(ROADMAP)}</ul>
      </div>
    </section>
    <section class="embed panel">{embed}</section>
    <p class="muted" style="margin-top:1.5rem">
      <a href="/api/pulse?metro={quote(slug)}">JSON API</a> ·
      <a href="/api/metros">metros</a> ·
      <a href="/api/feed-coverage">feed coverage</a> ·
      <a href="/api/pipeline-status">pipeline</a> ·
      <a href="/health">health</a>
    </p>
  </div>
  <script>
    document.getElementById('metro').addEventListener('change', function() {{
      history.replaceState(null, '', '/?metro=' + encodeURIComponent(this.value));
    }});
  </script>
</body>
</html>"""
