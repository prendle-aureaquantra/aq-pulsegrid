"""FastAPI status app — worldwide metro slicer + pulse KPIs."""

from __future__ import annotations

import csv
import html
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="AQ PulseGrid", version="0.2.0")

DATA_DIR = Path(os.getenv("PULSEGRID_DATA_DIR", "data"))
EMBED_URL = (os.getenv("POWERBI_PULSEGRID_EMBED_URL") or "").strip()
PUBLIC_URL = (
    os.getenv("PULSEGRID_PUBLIC_URL") or "https://pulse.aureaquantra.com/"
).strip()
REPO_URL = "https://github.com/prendle-aureaquantra/aq-pulsegrid"
SITE_DEMO_URL = (
    os.getenv("AUREAQUANTRA_DEMO_PAGE_URL")
    or "https://aureaquantra.com/demo-dashboard/"
).strip()
DEFAULT_METRO = (os.getenv("PULSEGRID_CITY") or "chicago").strip().lower()
MIN_METRO_COUNT = int(os.getenv("PULSEGRID_MIN_METRO_COUNT", "70"))
PIPELINE_STALE_HOURS = float(os.getenv("PULSEGRID_PIPELINE_STALE_HOURS", "36"))
_insight_calls: list[float] = []
_INSIGHT_LIMIT = int(os.getenv("PULSEGRID_INSIGHT_LIMIT", "12"))
_INSIGHT_WINDOW_SEC = float(os.getenv("PULSEGRID_INSIGHT_WINDOW_SEC", "3600"))

try:
    from copilot_chat import ask as _copilot_ask
    from copilot_chat import copilot_configured as _copilot_configured
    from copilot_chat import sample_questions as _copilot_sample_questions
except ImportError:
    from pulsegrid.web.copilot_chat import (  # type: ignore[no-redef]
        ask as _copilot_ask,
        copilot_configured as _copilot_configured,
        sample_questions as _copilot_sample_questions,
    )


def _embed_ready() -> bool:
    if EMBED_URL and "view?r=" in EMBED_URL:
        return True
    try:
        from pbi_embed_service import embed_configured

        return embed_configured()
    except Exception:
        return False


PHASE2_STATUS: list[tuple[str, str]] = [
    ("Worldwide metro registry (71 metros)", "Done"),
    ("Metro slicer — PBIP + ops console", "Done"),
    ("Multi-metro ingest adapters", "Done"),
    ("OpenSky + GTFS-RT + USGS + AQI feeds", "Done"),
    ("Platform PulseGrid.pbip export", "Done"),
    ("Databricks global daily job", "Done"),
    ("Fabric / service-principal embed", "Done"),
]

ROADMAP: list[tuple[str, str]] = [
    ("HTTPS pulse.aureaquantra.com", "Done"),
    ("Phase 2 worldwide metro slicer", "Done"),
    ("Full Databricks deployment", "Done"),
    ("Expanded public data feeds", "Done"),
    ("Apache Sedona Spark UDFs", "Done"),
    ("Fabric embed on status + WordPress", "Done"),
]


def _pipeline_status_file() -> Path | None:
    for candidate in (
        DATA_DIR.parent / "last_pipeline_run.json",
        DATA_DIR / "last_pipeline_run.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def _load_pipeline_status() -> dict[str, object] | None:
    import json

    path = _pipeline_status_file()
    if not path:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _pipeline_stale_hours(pipe: dict[str, object] | None) -> float | None:
    if not pipe:
        return None
    raw = pipe.get("finished_at")
    if not raw:
        return None
    try:
        finished = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if finished.tzinfo is None:
            finished = finished.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - finished.astimezone(timezone.utc)
        return round(delta.total_seconds() / 3600.0, 2)
    except (TypeError, ValueError):
        return None


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


@app.get("/embed", response_class=HTMLResponse)
def embed_report() -> str:
    if EMBED_URL and "view?r=" in EMBED_URL:
        safe = html.escape(EMBED_URL, quote=True)
        return (
            f'<!doctype html><html><head><meta charset="utf-8"/>'
            f'<title>PulseGrid report</title></head><body style="margin:0">'
            f'<iframe title="PulseGrid" src="{safe}" style="width:100%;height:100vh;border:0" '
            f'allowfullscreen></iframe></body></html>'
        )
    try:
        from pbi_embed_service import get_report_embed

        cfg = get_report_embed()
    except Exception as exc:
        return (
            "<!doctype html><html><body style='font-family:system-ui;padding:2rem'>"
            f"<p>Power BI embed unavailable: {html.escape(str(exc))}</p></body></html>"
        )
    embed_url = html.escape(cfg["embedUrl"], quote=True)
    token = html.escape(cfg["accessToken"], quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>PulseGrid — Power BI</title>
  <script src="https://cdn.jsdelivr.net/npm/powerbi-client@2.23.1/dist/powerbi.min.js"></script>
  <style>html,body{{margin:0;height:100%}}#report{{height:100vh}}</style>
</head>
<body><div id="report"></div>
  <script>
    const models = window["powerbi-client"].models;
    powerbi.embed(document.getElementById("report"), {{
      type: "report",
      tokenType: models.TokenType.Embed,
      accessToken: "{token}",
      embedUrl: "{embed_url}",
    }});
  </script>
</body></html>"""


@app.get("/health")
def health() -> dict[str, object]:
    snap = _read_csv("CityPulseSnapshot.csv")
    metros = _read_csv("DimMetro.csv")
    pipe = _load_pipeline_status()
    stale_h = _pipeline_stale_hours(pipe)
    metro_n = len(metros)
    snap_n = len(snap)
    degraded: list[str] = []
    if metro_n < MIN_METRO_COUNT:
        degraded.append(f"metroCount<{MIN_METRO_COUNT}")
    if snap_n < MIN_METRO_COUNT:
        degraded.append(f"snapshotRows<{MIN_METRO_COUNT}")
    if stale_h is not None and stale_h > PIPELINE_STALE_HOURS:
        degraded.append(f"pipelineStale>{PIPELINE_STALE_HOURS}h")
    if pipe and int(pipe.get("metros_failed") or 0) > 0:
        degraded.append("lastPipelineHadFailures")
    return {
        "status": "degraded" if degraded else "ok",
        "degradedReasons": degraded,
        "defaultMetro": DEFAULT_METRO,
        "metroCount": metro_n,
        "minMetroCount": MIN_METRO_COUNT,
        "dataDir": str(DATA_DIR),
        "snapshotRows": snap_n,
        "embedConfigured": _embed_ready(),
        "copilotConfigured": _copilot_configured(),
        "publicUrl": PUBLIC_URL,
        "pipeline": pipe,
        "pipelineStaleHours": stale_h,
        "pulseHistoryNote": (
            "Anomaly z-scores improve after ~7 daily ML runs (Option A scoring)."
        ),
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
        return JSONResponse({"metro": slug, "prompts": _copilot_sample_questions(slug)})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/pipeline-status")
def api_pipeline_status() -> JSONResponse:
    return JSONResponse(_load_pipeline_status() or {"status": "unknown"})


class InsightRequest(BaseModel):
    metro: str = Field(default="")
    question: str = Field(min_length=3, max_length=500)


@app.post("/api/insight")
def api_insight(body: InsightRequest) -> JSONResponse:
    """Rate-limited LLM summary of metro pulse (requires OPENAI_API_KEY on server)."""
    now = time.time()
    global _insight_calls
    _insight_calls = [t for t in _insight_calls if now - t < _INSIGHT_WINDOW_SEC]
    if len(_insight_calls) >= _INSIGHT_LIMIT:
        return JSONResponse(
            {"error": "Rate limit exceeded. Try again later."},
            status_code=429,
        )
    slug = (body.metro or DEFAULT_METRO).strip().lower()
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return JSONResponse(
            {"error": "OPENAI_API_KEY not configured on server."},
            status_code=503,
        )
    try:
        answer = _copilot_ask(slug, body.question)
        _insight_calls.append(now)
        return JSONResponse({"metro": slug, "question": body.question, "answer": answer})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


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
        prompts = _copilot_sample_questions(slug, limit=5)
    except Exception:
        prompts = []
    prompt_items = "".join(
        f'<li><button type="button" class="copilot-chip" data-prompt="{html.escape(p, quote=True)}">'
        f"{html.escape(p)}</button></li>"
        for p in prompts
    ) or ("<li class='muted'>Copilot prompts unavailable</li>")
    copilot_ready = _copilot_configured()
    copilot_status = (
        '<p class="muted">Ask about City Pulse, transit, weather, and anomalies for the selected metro.</p>'
        if copilot_ready
        else '<p class="muted">Set <code>OPENAI_API_KEY</code> in pulsegrid.env to enable chat.</p>'
    )
    copilot_panel = f"""
    <section class="panel copilot-panel" id="copilot-chat" style="margin-top:1.25rem">
      <h2>PulseGrid Copilot</h2>
      {copilot_status}
      <div id="chat-log" class="chat-log" aria-live="polite"></div>
      <form id="chat-form" class="chat-form" {"hidden" if not copilot_ready else ""}>
        <label class="sr-only" for="chat-input">Question</label>
        <textarea id="chat-input" rows="2" maxlength="500" placeholder="Ask about stress index, transit, weather…"></textarea>
        <button type="submit" id="chat-send">Ask</button>
      </form>
      <h3 style="font-size:0.95rem;margin:1rem 0 0.5rem;color:var(--muted)">Example prompts</h3>
      <ul class="copilot-prompts">{prompt_items}</ul>
    </section>
    """
    pipe = _load_pipeline_status() or {}
    pipe_line = (
        f"Last job: {html.escape(str(pipe.get('job', '—')))} · "
        f"{html.escape(str(pipe.get('finished_at', '—')))} · "
        f"ok={pipe.get('metros_ok', '—')} failed={pipe.get('metros_failed', '—')}"
        if pipe
        else "No pipeline status file — run multi-metro ingest or platform export."
    )
    if EMBED_URL and "view?r=" in EMBED_URL:
        embed = (
            f'<iframe title="PulseGrid {html.escape(display)}" src="{html.escape(EMBED_URL)}" '
            'style="width:100%;min-height:520px;border:0;border-radius:8px"></iframe>'
        )
    elif _embed_ready():
        embed = (
            '<iframe title="PulseGrid Power BI" src="/embed" '
            'style="width:100%;min-height:520px;border:0;border-radius:8px"></iframe>'
            '<p class="muted"><a href="/embed" target="_blank" rel="noopener">Open Fabric report</a></p>'
        )
    else:
        embed = (
            '<p class="muted">Fabric embed pending.</p>'
            f'<p><a href="{REPO_URL}">View repo</a></p>'
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
    .copilot-panel .chat-log {{
      min-height: 6rem; max-height: 14rem; overflow-y: auto;
      background: #0b1018; border: 1px solid #243044; border-radius: 8px;
      padding: 0.75rem; margin: 0.75rem 0; font-size: 0.92rem;
    }}
    .chat-log .msg {{ margin: 0 0 0.65rem; }}
    .chat-log .msg.user {{ color: var(--accent); }}
    .chat-log .msg.bot {{ color: #e7ecf1; white-space: pre-wrap; }}
    .chat-form {{ display: flex; gap: 0.5rem; align-items: flex-end; flex-wrap: wrap; }}
    .chat-form textarea {{
      flex: 1 1 220px; min-height: 2.5rem; resize: vertical;
      background: #243044; color: var(--text); border: 1px solid #334155;
      border-radius: 6px; padding: 0.5rem 0.65rem; font: inherit;
    }}
    .chat-form button {{
      background: var(--gold); color: #1a1a1a; border: none; border-radius: 6px;
      padding: 0.55rem 1rem; font-weight: 600; cursor: pointer;
    }}
    .chat-form button:disabled {{ opacity: 0.5; cursor: wait; }}
    .copilot-prompts {{ list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 0.4rem; }}
    .copilot-prompts li {{ margin: 0; }}
    .copilot-chip {{
      background: #243044; color: var(--accent); border: 1px solid #334155;
      border-radius: 999px; padding: 0.35rem 0.75rem; font-size: 0.82rem; cursor: pointer;
    }}
    .sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>AQ PulseGrid — Worldwide Metros</h1>
      <p>{html.escape(display)} · snapshot {html.escape(str(snapshot_at))} · data refreshed {html.escape(str(refreshed))}</p>
      <p class="muted">{pipe_line}</p>
      <p class="muted">Anomaly baselines improve after ~7 daily ML runs. <a href="/health">Health</a> shows pipeline staleness.</p>
      <p><a href="{REPO_URL}">GitHub</a> · <a href="{html.escape(SITE_DEMO_URL, quote=True)}">Aurea Quantra demo page</a></p>
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
    {copilot_panel}
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
      <a href="/health">health</a> ·
      POST <code>/api/insight</code> (LLM, rate-limited)
    </p>
  </div>
  <script>
    document.getElementById('metro').addEventListener('change', function() {{
      history.replaceState(null, '', '/?metro=' + encodeURIComponent(this.value));
    }});
    (function() {{
      if (location.hash === '#copilot-chat') {{
        const panel = document.getElementById('copilot-chat');
        if (panel) panel.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
        const focusInput = document.getElementById('chat-input');
        if (focusInput) setTimeout(function() {{ focusInput.focus(); }}, 400);
      }}
    }})();
    (function() {{
      const form = document.getElementById('chat-form');
      const input = document.getElementById('chat-input');
      const log = document.getElementById('chat-log');
      const sendBtn = document.getElementById('chat-send');
      if (!form || !input || !log) return;
      function metro() {{
        const el = document.getElementById('metro');
        return el ? el.value : {json.dumps(slug)};
      }}
      function append(role, text) {{
        const div = document.createElement('div');
        div.className = 'msg ' + role;
        div.textContent = text;
        log.appendChild(div);
        log.scrollTop = log.scrollHeight;
      }}
      async function ask(question) {{
        const q = (question || '').trim();
        if (q.length < 3) return;
        append('user', q);
        input.value = '';
        sendBtn.disabled = true;
        try {{
          const res = await fetch('/api/insight', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ metro: metro(), question: q }}),
          }});
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || res.statusText);
          append('bot', data.answer || '(empty response)');
        }} catch (err) {{
          append('bot', 'Error: ' + err.message);
        }} finally {{
          sendBtn.disabled = false;
          input.focus();
        }}
      }}
      form.addEventListener('submit', function(ev) {{
        ev.preventDefault();
        ask(input.value);
      }});
      document.querySelectorAll('.copilot-chip').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
          ask(btn.getAttribute('data-prompt') || '');
        }});
      }});
    }})();
  </script>
</body>
</html>"""
