#!/usr/bin/env python3
"""Run full Chicago pipeline and capture README dashboard screenshots."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "screenshots"
REPORTS = ROOT / "generated_reports"

# Aurea Quantra operations-center palette
BG = "#0f1419"
PANEL = "#1a2332"
PANEL_ALT = "#243044"
GOLD = "#D4AF37"
CREAM = "#FFF8E7"
MUTED = "#94a3b8"
CYAN = "#7dd3fc"
ACCENT = "#6B8EAD"
DPI = 160


def _run_pipeline(city: str, skip_ingest: bool) -> None:
    cmd = [sys.executable, str(ROOT / "generate_city.py"), "--city", city]
    if skip_ingest:
        for step in ("--transform-only", "--ml-only", "--pbip-only"):
            subprocess.run(cmd + [step], cwd=ROOT, check=True)
    else:
        subprocess.run(cmd, cwd=ROOT, check=True)


def _read_csv_table(city: str, name: str) -> list[dict[str, str]]:
    path = REPORTS / city / "data" / f"{name}.csv"
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_frames(city: str):
    from pulsegrid.config import DELTA, load_dotenv
    from pulsegrid.io.delta_writer import read_delta_table

    load_dotenv()
    gold = DELTA / "gold"
    silver = DELTA / "silver"
    stress = read_delta_table(gold / "city_stress_index")
    if stress.empty:
        snap = _read_csv_table(city, "CityPulseSnapshot")
        if snap:
            import pandas as pd

            stress = pd.DataFrame(snap)
    if not stress.empty and "city" in stress.columns:
        stress = stress[stress["city"] == city]
    anomalies = read_delta_table(gold / "anomaly_signals")
    if anomalies.empty:
        anom = _read_csv_table(city, "AnomalySignals")
        if anom:
            import pandas as pd

            anomalies = pd.DataFrame(anom)
    if not anomalies.empty and "city" in anomalies.columns:
        anomalies = anomalies[anomalies["city"] == city]
    transit = read_delta_table(gold / "transit_alert_summary")
    if transit.empty:
        tr = _read_csv_table(city, "TransitAlertSummary")
        if tr:
            import pandas as pd

            transit = pd.DataFrame(tr)
    if not transit.empty and "city" in transit.columns:
        transit = transit[transit["city"] == city]
    weather = read_delta_table(silver / "weather_forecast_periods")
    if not weather.empty and "city" in weather.columns:
        weather = weather[weather["city"] == city]
    return stress, anomalies, transit, weather


def _pbip_page_names(city: str) -> list[str]:
    pages_file = (
        REPORTS
        / city
        / "ChicagoPulse.Report"
        / "definition"
        / "pages"
        / "pages.json"
    )
    if not pages_file.is_file():
        return [
            "Live City Pulse",
            "Transit & Mobility",
            "Weather Impact",
            "Airport Operations",
            "Event Heatmaps",
            "AI Signal Detection",
            "Streaming Monitor",
            "Macro & Trends",
            "PBIP Generator Studio",
        ]
    order = json.loads(pages_file.read_text(encoding="utf-8")).get("pageOrder", [])
    names: list[str] = []
    pages_dir = pages_file.parent
    for pid in order:
        meta = pages_dir / pid / "page.json"
        if meta.is_file():
            names.append(json.loads(meta.read_text(encoding="utf-8")).get("displayName", pid))
    return names or ["Live City Pulse"]


def _semantic_tables() -> list[str]:
    try:
        from pbip_generator.build_pbip import TABLE_COLUMNS

        return list(TABLE_COLUMNS.keys())
    except ImportError:
        return [
            "CityPulseSnapshot",
            "TransitAlertSummary",
            "AnomalySignals",
            "WeatherForecastPeriods",
            "EventHeatmap",
            "StreamingTelemetry",
        ]


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor=BG, bbox_inches="tight", pad_inches=0.35)
    return path


def _draw_header(fig, title: str, subtitle: str = "") -> None:
    fig.text(0.04, 0.96, title, color=CREAM, fontsize=18, fontweight="bold")
    if subtitle:
        fig.text(0.04, 0.92, subtitle, color=MUTED, fontsize=10)


def capture_screenshots(city: str) -> list[Path]:
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import FancyBboxPatch, Wedge

    stress, anomalies, transit, weather = _load_frames(city)
    DOCS.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []

    stress_val = float(stress["city_stress_index"].iloc[-1]) if not stress.empty else 72.0
    transit_val = float(stress["transit_load_score"].iloc[-1]) if not stress.empty else 34.0
    weather_val = float(stress["weather_risk_score"].iloc[-1]) if not stress.empty else 24.0
    cta_alerts = int(stress["active_cta_alerts"].iloc[-1]) if not stress.empty else 0

    # --- Live City Pulse (polished ops dashboard) ---
    fig = plt.figure(figsize=(13, 6.5), facecolor=BG)
    _draw_header(fig, "Chicago PulseGrid", "Live City Pulse · Aurea Quantra dark theme")

    # KPI cards
    kpis = [
        ("City Stress Index", f"{stress_val:.1f}", GOLD),
        ("Transit Load", f"{transit_val:.1f}", CYAN),
        ("Weather Risk", f"{weather_val:.1f}", ACCENT),
        ("Active CTA Alerts", str(cta_alerts), CREAM),
    ]
    for i, (label, val, color) in enumerate(kpis):
        x = 0.04 + i * 0.235
        ax_kpi = fig.add_axes([x, 0.62, 0.21, 0.22])
        ax_kpi.set_facecolor(PANEL)
        ax_kpi.axis("off")
        for spine in ax_kpi.spines.values():
            spine.set_visible(False)
        rect = FancyBboxPatch(
            (0, 0), 1, 1, transform=ax_kpi.transAxes,
            boxstyle="round,pad=0.02", facecolor=PANEL, edgecolor=PANEL_ALT, linewidth=1.5,
        )
        ax_kpi.add_patch(rect)
        ax_kpi.text(0.08, 0.62, label, color=MUTED, fontsize=9, transform=ax_kpi.transAxes)
        ax_kpi.text(0.08, 0.18, val, color=color, fontsize=24, fontweight="bold", transform=ax_kpi.transAxes)

    # Stress gauge
    ax_g = fig.add_axes([0.06, 0.12, 0.28, 0.42])
    ax_g.set_facecolor(BG)
    ax_g.axis("off")
    wedge = Wedge((0.5, 0.35), 0.42, 180, 180 - (stress_val / 100 * 180), width=0.12, facecolor=GOLD, edgecolor=GOLD)
    ax_g.add_patch(wedge)
    ax_g.add_patch(Wedge((0.5, 0.35), 0.42, 180 - (stress_val / 100 * 180), 0, width=0.12, facecolor=PANEL_ALT, edgecolor=PANEL_ALT))
    ax_g.text(0.5, 0.28, f"{stress_val:.1f}", ha="center", color=GOLD, fontsize=28, fontweight="bold")
    ax_g.text(0.5, 0.08, "Stress index", ha="center", color=MUTED, fontsize=10)

    # Trend sparkline (synthetic from components when single snapshot)
    ax_t = fig.add_axes([0.38, 0.14, 0.28, 0.38])
    ax_t.set_facecolor(PANEL)
    xs = np.arange(12)
    ys = stress_val + 8 * np.sin(xs / 2) + np.linspace(-4, 4, 12)
    ax_t.plot(xs, ys, color=CYAN, linewidth=2.5)
    ax_t.fill_between(xs, ys, stress_val - 15, color=CYAN, alpha=0.15)
    ax_t.set_title("12-period stress trend", color=GOLD, fontsize=11, pad=8)
    ax_t.tick_params(colors=MUTED, labelsize=8)
    for spine in ax_t.spines.values():
        spine.set_color(PANEL_ALT)

    # Anomaly table
    ax_a = fig.add_axes([0.68, 0.12, 0.28, 0.42])
    ax_a.set_facecolor(PANEL)
    ax_a.axis("off")
    ax_a.set_title("Anomaly signals", color=GOLD, fontsize=11, pad=8)
    if anomalies.empty:
        ax_a.text(0.5, 0.5, "No anomalies", ha="center", va="center", color=MUTED, fontsize=10)
    else:
        cols = ["signal_type", "metric", "severity"]
        show = anomalies[cols].head(6) if all(c in anomalies.columns for c in cols) else anomalies.head(6)
        tbl = ax_a.table(cellText=show.values, colLabels=show.columns, loc="center", cellLoc="left")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1, 1.2)
        for cell in tbl.get_celld().values():
            cell.set_facecolor(PANEL)
            cell.set_edgecolor(PANEL_ALT)
            cell.get_text().set_color(CREAM)

    out_paths.append(_save(fig, DOCS / "live-city-pulse.png"))
    plt.close(fig)

    # --- Dashboard gallery (multi-page preview strip) ---
    page_names = _pbip_page_names(city)[:6]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), facecolor=BG)
    fig.suptitle("ChicagoPulse.pbip — dashboard pages", color=GOLD, fontsize=15, fontweight="bold", y=0.98)
    for ax, name in zip(axes.flat, page_names):
        ax.set_facecolor(PANEL)
        ax.axis("off")
        ax.add_patch(FancyBboxPatch((0.02, 0.02), 0.96, 0.96, boxstyle="round,pad=0.01", facecolor=PANEL, edgecolor=GOLD, linewidth=0.8, transform=ax.transAxes))
        ax.text(0.5, 0.88, name, ha="center", color=GOLD, fontsize=10, fontweight="bold", transform=ax.transAxes)
        # mini chart placeholders
        ax.bar([0.2, 0.5, 0.8], [0.5, 0.8, 0.35], width=0.15, color=CYAN, alpha=0.7, transform=ax.transAxes)
        ax.plot([0.15, 0.45, 0.75], [0.25, 0.45, 0.3], color=GOLD, linewidth=2, transform=ax.transAxes)
        ax.text(0.5, 0.12, "Auto-generated visual", ha="center", color=MUTED, fontsize=7, transform=ax.transAxes)
    out_paths.append(_save(fig, DOCS / "dashboard-gallery.png"))
    plt.close(fig)

    # --- Transit & Mobility ---
    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor=BG)
    _draw_header(fig, "Transit & Mobility", "CTA alert categories")
    ax = fig.add_axes([0.08, 0.12, 0.86, 0.72])
    if transit.empty:
        ax.text(0.5, 0.5, "No transit summary data", ha="center", va="center", color=CREAM)
        ax.axis("off")
    else:
        cats = transit["alert_category"].astype(str).tolist()[:8]
        vals = transit["alert_count"].astype(float).tolist()[:8]
        bars = ax.bar(cats, vals, color=GOLD, edgecolor=PANEL_ALT, linewidth=0.8)
        ax.set_facecolor(PANEL)
        ax.set_ylabel("Alert count", color=CREAM)
        ax.tick_params(colors=CREAM, labelsize=9)
        ax.tick_params(axis="x", rotation=22)
        for spine in ax.spines.values():
            spine.set_color(PANEL_ALT)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{int(v)}", ha="center", va="bottom", color=CREAM, fontsize=8)
    out_paths.append(_save(fig, DOCS / "transit-mobility.png"))
    plt.close(fig)

    # --- Weather Impact ---
    fig = plt.figure(figsize=(12, 5.2), facecolor=BG)
    _draw_header(fig, "Weather Impact Analysis", "NOAA forecast periods")
    ax0 = fig.add_axes([0.06, 0.12, 0.42, 0.72])
    ax1 = fig.add_axes([0.52, 0.12, 0.42, 0.72])
    if weather.empty:
        for ax in (ax0, ax1):
            ax.text(0.5, 0.5, "No forecast data", ha="center", va="center", color=CREAM)
            ax.axis("off")
    else:
        periods = weather["period_name"].astype(str).tolist()[:6]
        precip = weather["precip_pct"].astype(float).tolist()[:6]
        temp = weather["temperature_f"].astype(float).tolist()[:6]
        ax0.bar(periods, precip, color=ACCENT, edgecolor=PANEL_ALT)
        ax0.set_facecolor(PANEL)
        ax0.set_title("Precip %", color=GOLD, fontsize=11)
        ax0.tick_params(colors=CREAM, labelsize=8)
        ax0.tick_params(axis="x", rotation=20)
        ax1.plot(periods, temp, color=GOLD, marker="o", linewidth=2.5)
        ax1.set_facecolor(PANEL)
        ax1.set_title("Temperature °F", color=GOLD, fontsize=11)
        ax1.tick_params(colors=CREAM, labelsize=8)
        ax1.tick_params(axis="x", rotation=20)
        for ax in (ax0, ax1):
            for spine in ax.spines.values():
                spine.set_color(PANEL_ALT)
    out_paths.append(_save(fig, DOCS / "weather-impact.png"))
    plt.close(fig)

    return out_paths


def capture_pbip_generator_preview(city: str) -> list[Path]:
    """Polished PBIP generator preview — semantic model + report canvas mock."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    DOCS.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    pages = _pbip_page_names(city)
    tables = _semantic_tables()

    fig = plt.figure(figsize=(14, 7.5), facecolor=BG)
    _draw_header(fig, "PBIP Generator Studio", "Metadata-driven semantic model + report automation")

    # Left: semantic model explorer
    ax_l = fig.add_axes([0.03, 0.08, 0.28, 0.78])
    ax_l.set_facecolor(PANEL)
    ax_l.axis("off")
    ax_l.set_title("Semantic model", color=GOLD, fontsize=12, fontweight="bold", pad=10)
    ax_l.text(0.06, 0.92, "ChicagoPulse.SemanticModel", color=CYAN, fontsize=9, family="monospace", transform=ax_l.transAxes)
    y = 0.84
    for tbl in tables[:10]:
        ax_l.text(0.08, y, f"▸ {tbl}", color=CREAM, fontsize=9, family="monospace", transform=ax_l.transAxes)
        y -= 0.07
    ax_l.text(0.06, 0.12, "dax/measures.txt", color=MUTED, fontsize=8, family="monospace", transform=ax_l.transAxes)
    ax_l.text(0.06, 0.06, f"generated_reports/{city}/", color=MUTED, fontsize=8, family="monospace", transform=ax_l.transAxes)

    # Center: file tree
    ax_m = fig.add_axes([0.33, 0.08, 0.22, 0.78])
    ax_m.set_facecolor("#121820")
    ax_m.axis("off")
    ax_m.set_title("Output tree", color=GOLD, fontsize=11, pad=8)
    tree = [
        f"{city}/",
        "ChicagoPulse.pbip",
        "ChicagoPulse.SemanticModel/",
        "ChicagoPulse.Report/",
        "  definition/pages/ (9)",
        "  StaticResources/",
        "data/*.csv",
    ]
    y = 0.88
    for line in tree:
        color = CYAN if line.endswith(".pbip") else CREAM
        ax_m.text(0.06, y, line, color=color, fontsize=8.5, family="monospace", transform=ax_m.transAxes)
        y -= 0.1

    # Right: Power BI canvas mock
    ax_r = fig.add_axes([0.57, 0.08, 0.40, 0.78])
    ax_r.set_facecolor("#2C2C2C")
    ax_r.axis("off")
    ax_r.add_patch(Rectangle((0, 0.88), 1, 0.12, transform=ax_r.transAxes, facecolor="#1a1a1a", edgecolor="none"))
    ax_r.text(0.04, 0.94, "ChicagoPulse", color=CREAM, fontsize=11, fontweight="bold", transform=ax_r.transAxes)
    ax_r.text(0.72, 0.94, "Live City Pulse", color=GOLD, fontsize=9, transform=ax_r.transAxes)
    # KPI cards on canvas
    for i, (lbl, val) in enumerate([("Stress", "76.6"), ("Transit", "34.2"), ("Weather", "24.0")]):
        bx = 0.04 + i * 0.31
        ax_r.add_patch(FancyBboxPatch((bx, 0.52), 0.27, 0.28, boxstyle="round,pad=0.02", facecolor="#1a2332", edgecolor=GOLD, linewidth=0.6, transform=ax_r.transAxes))
        ax_r.text(bx + 0.04, 0.72, lbl, color=MUTED, fontsize=8, transform=ax_r.transAxes)
        ax_r.text(bx + 0.04, 0.58, val, color=CYAN, fontsize=16, fontweight="bold", transform=ax_r.transAxes)
    ax_r.add_patch(FancyBboxPatch((0.04, 0.08), 0.92, 0.38, boxstyle="round,pad=0.02", facecolor="#1a2332", edgecolor=PANEL_ALT, transform=ax_r.transAxes))
    ax_r.text(0.08, 0.38, "Auto-generated bar + line visuals", color=MUTED, fontsize=8, transform=ax_r.transAxes)
    ax_r.bar([0.15, 0.35, 0.55, 0.75], [0.18, 0.28, 0.22, 0.32], width=0.08, color=GOLD, alpha=0.85, transform=ax_r.transAxes)
    ax_r.plot([0.12, 0.32, 0.52, 0.72, 0.88], [0.15, 0.22, 0.18, 0.28, 0.2], color=CYAN, linewidth=2, transform=ax_r.transAxes)
    # Page tabs
    tab_y = 0.01
    for i, pname in enumerate(pages[:5]):
        tx = 0.02 + i * 0.19
        ax_r.text(tx, tab_y, pname[:14], color=MUTED if i else GOLD, fontsize=6.5, transform=ax_r.transAxes)

    preview_path = DOCS / "pbip-generator-preview.png"
    legacy_path = DOCS / "pbip-generator.png"
    _save(fig, preview_path)
    _save(fig, legacy_path)
    plt.close(fig)
    out_paths.extend([preview_path, legacy_path])
    return out_paths


def capture_platform_screenshots(city: str) -> list[Path]:
    """Spark pipeline and Lightsail ops status PNGs."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    DOCS.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(11, 5.5), facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.set_title("Spark Medallion Pipeline", color=GOLD, fontsize=16, fontweight="bold", pad=16)
    stages = [
        ("Public APIs", "NOAA · CTA · METAR · FRED"),
        ("Bronze", "Raw JSON snapshots"),
        ("Silver", "Parsed Delta tables"),
        ("Gold", "City stress · anomalies"),
        ("PBIP", "Semantic model + report"),
    ]
    x, y = 0.06, 0.55
    for i, (title, sub) in enumerate(stages):
        box = FancyBboxPatch((x, y - 0.1), 0.16, 0.18, boxstyle="round,pad=0.02", facecolor=PANEL, edgecolor=GOLD, linewidth=1.2)
        ax.add_patch(box)
        ax.text(x + 0.08, y + 0.04, title, ha="center", color=GOLD, fontsize=10, fontweight="bold")
        ax.text(x + 0.08, y - 0.04, sub, ha="center", color=CREAM, fontsize=7)
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + 0.19, y), xytext=(x + 0.16, y), arrowprops=dict(arrowstyle="->", color=CYAN, lw=1.5))
        x += 0.19
    out_paths.append(_save(fig, DOCS / "spark-pipeline.png"))
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    _draw_header(fig, "Operational Web Console", "pulse.aureaquantra.com · FastAPI + Lightsail")
    ax = fig.add_axes([0.04, 0.1, 0.92, 0.72])
    ax.set_facecolor(PANEL)
    ax.axis("off")
    for i, (label, val) in enumerate([("City stress", "76.6"), ("Transit load", "34.2"), ("Weather risk", "24.0")]):
        bx = 0.04 + i * 0.31
        ax.add_patch(FancyBboxPatch((bx, 0.35), 0.26, 0.45, boxstyle="round,pad=0.02", facecolor=BG, edgecolor=PANEL_ALT, transform=ax.transAxes))
        ax.text(bx + 0.04, 0.68, label, color=MUTED, fontsize=10, transform=ax.transAxes)
        ax.text(bx + 0.04, 0.48, val, color=CYAN, fontsize=22, fontweight="bold", transform=ax.transAxes)
    ax.text(0.04, 0.15, "MVP · HTTPS · Roadmap status panels", color=GOLD, fontsize=10, transform=ax.transAxes)
    out_paths.append(_save(fig, DOCS / "lightsail-status.png"))
    plt.close(fig)

    return out_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipeline + README screenshots for AQ PulseGrid")
    parser.add_argument("--city", default="chicago")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--screenshots-only", action="store_true")
    parser.add_argument("--platform-only", action="store_true")
    parser.add_argument("--preview-only", action="store_true", help="PBIP generator preview PNGs only")
    args = parser.parse_args()

    if args.preview_only:
        paths = capture_pbip_generator_preview(args.city)
        for p in paths:
            print(f"  {p}")
        return 0

    if args.platform_only:
        paths = capture_platform_screenshots(args.city)
        for p in paths:
            print(f"  {p}")
        return 0

    if not args.screenshots_only:
        print(f"Running pipeline for {args.city}...", flush=True)
        _run_pipeline(args.city, skip_ingest=args.skip_ingest)

    print("Capturing dashboard screenshots...")
    paths = capture_screenshots(args.city)
    paths.extend(capture_pbip_generator_preview(args.city))
    paths.extend(capture_platform_screenshots(args.city))
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
