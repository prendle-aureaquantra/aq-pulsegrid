#!/usr/bin/env python3
"""Run full Chicago pipeline and capture README dashboard screenshots."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "screenshots"


def _run_pipeline(city: str, skip_ingest: bool) -> None:
    cmd = [sys.executable, str(ROOT / "generate_city.py"), "--city", city]
    if skip_ingest:
        for step in ("--transform-only", "--ml-only", "--pbip-only"):
            subprocess.run(cmd + [step], cwd=ROOT, check=True)
    else:
        subprocess.run(cmd, cwd=ROOT, check=True)


def _load_frames(city: str):
    from pulsegrid.config import DELTA, load_dotenv
    from pulsegrid.io.delta_writer import read_delta_table

    load_dotenv()
    gold = DELTA / "gold"
    silver = DELTA / "silver"
    stress = read_delta_table(gold / "city_stress_index")
    if not stress.empty and "city" in stress.columns:
        stress = stress[stress["city"] == city]
    anomalies = read_delta_table(gold / "anomaly_signals")
    if not anomalies.empty and "city" in anomalies.columns:
        anomalies = anomalies[anomalies["city"] == city]
    transit = read_delta_table(gold / "transit_alert_summary")
    if not transit.empty and "city" in transit.columns:
        transit = transit[transit["city"] == city]
    weather = read_delta_table(silver / "weather_forecast_periods")
    if not weather.empty and "city" in weather.columns:
        weather = weather[weather["city"] == city]
    return stress, anomalies, transit, weather


def _style_axes(ax, title: str) -> None:
    ax.set_title(title, color="#D4AF37", fontsize=14, fontweight="bold", pad=12)
    ax.set_facecolor("#2C2C2C")
    ax.tick_params(colors="#FFF8E7")
    ax.xaxis.label.set_color("#FFF8E7")
    ax.yaxis.label.set_color("#FFF8E7")
    for spine in ax.spines.values():
        spine.set_color("#555555")


def capture_screenshots(city: str) -> list[Path]:
    import matplotlib.pyplot as plt

    stress, anomalies, transit, weather = _load_frames(city)
    DOCS.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    bg = "#1a1a1a"
    gold = "#D4AF37"
    cream = "#FFF8E7"

    # Live City Pulse
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), facecolor=bg)
    fig.suptitle("Live City Pulse", color=gold, fontsize=16, fontweight="bold")
    kpis = [
        (
            "City Stress Index",
            stress["city_stress_index"].iloc[-1] if not stress.empty else 0,
        ),
        (
            "Active CTA Alerts",
            stress["active_cta_alerts"].iloc[-1] if not stress.empty else 0,
        ),
        ("Anomaly Count", len(anomalies)),
    ]
    ax0 = axes[0]
    ax0.set_facecolor("#2C2C2C")
    ax0.axis("off")
    for i, (label, val) in enumerate(kpis):
        y = 0.82 - i * 0.28
        ax0.text(0.05, y, label, color=cream, fontsize=11, transform=ax0.transAxes)
        fmt = f"{float(val):.1f}" if isinstance(val, float) else str(int(val))
        ax0.text(
            0.05,
            y - 0.12,
            fmt,
            color=gold,
            fontsize=22,
            fontweight="bold",
            transform=ax0.transAxes,
        )
    ax1 = axes[1]
    ax1.set_facecolor("#2C2C2C")
    ax1.axis("off")
    ax1.set_title("Anomaly Signals", color=gold, fontsize=12, pad=8)
    if anomalies.empty:
        ax1.text(0.05, 0.5, "No anomalies detected", color=cream, fontsize=12)
    else:
        cols = ["signal_type", "metric", "severity", "z_score"]
        show = anomalies[cols].head(8)
        table = ax1.table(
            cellText=show.values,
            colLabels=cols,
            loc="center",
            cellLoc="left",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        for cell in table.get_celld().values():
            cell.set_facecolor("#2C2C2C")
            cell.set_edgecolor("#555555")
            cell.get_text().set_color(cream)
    live_path = DOCS / "live-city-pulse.png"
    fig.tight_layout()
    fig.savefig(live_path, dpi=144, facecolor=bg)
    plt.close(fig)
    out_paths.append(live_path)

    # Transit & Mobility
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=bg)
    if transit.empty:
        ax.text(
            0.5, 0.5, "No transit summary data", ha="center", va="center", color=cream
        )
    else:
        cats = transit["alert_category"].astype(str)
        vals = transit["alert_count"].astype(float)
        bars = ax.bar(cats, vals, color=gold, edgecolor="#555555")
        ax.set_ylabel("Alert count", color=cream)
        ax.set_xlabel("Category", color=cream)
        for bar, v in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{int(v)}",
                ha="center",
                va="bottom",
                color=cream,
                fontsize=9,
            )
    _style_axes(ax, "Transit & Mobility")
    transit_path = DOCS / "transit-mobility.png"
    fig.tight_layout()
    fig.savefig(transit_path, dpi=144, facecolor=bg)
    plt.close(fig)
    out_paths.append(transit_path)

    # Weather Impact
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), facecolor=bg)
    fig.suptitle("Weather Impact Analysis", color=gold, fontsize=16, fontweight="bold")
    if weather.empty:
        for ax in axes:
            ax.set_facecolor("#2C2C2C")
            ax.text(0.5, 0.5, "No forecast data", ha="center", va="center", color=cream)
            ax.axis("off")
    else:
        periods = weather["period_name"].astype(str).tolist()
        precip = weather["precip_pct"].astype(float).tolist()
        temp = weather["temperature_f"].astype(float).tolist()
        axes[0].bar(periods, precip, color="#6B8EAD")
        _style_axes(axes[0], "Precip % by period")
        axes[0].tick_params(axis="x", rotation=25)
        axes[1].plot(periods, temp, color=gold, marker="o", linewidth=2)
        _style_axes(axes[1], "Temperature (°F)")
        axes[1].tick_params(axis="x", rotation=25)
    weather_path = DOCS / "weather-impact.png"
    fig.tight_layout()
    fig.savefig(weather_path, dpi=144, facecolor=bg)
    plt.close(fig)
    out_paths.append(weather_path)

    return out_paths


def capture_platform_screenshots(city: str) -> list[Path]:
    """Render PBIP generator, Spark pipeline, and ops status PNGs for README."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    DOCS.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []
    bg = "#1a1a1a"
    gold = "#D4AF37"
    cream = "#FFF8E7"
    cyan = "#7dd3fc"

    # PBIP generator tree
    fig, ax = plt.subplots(figsize=(10, 6), facecolor=bg)
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.set_title("PBIP Generator Output", color=gold, fontsize=16, fontweight="bold", pad=16)
    tree = [
        f"generated_reports/{city}/",
        "  ChicagoPulse.pbip",
        "  ChicagoPulse.SemanticModel/",
        "  ChicagoPulse.Report/  (9 pages · ~28 visuals)",
        "  data/*.csv",
        "  dax/measures.txt",
    ]
    y = 0.88
    for line in tree:
        ax.text(0.06, y, line, color=cream if not line.startswith("  ") else cyan, fontsize=11, family="monospace")
        y -= 0.12
    pbip_path = DOCS / "pbip-generator.png"
    fig.tight_layout()
    fig.savefig(pbip_path, dpi=144, facecolor=bg)
    plt.close(fig)
    out_paths.append(pbip_path)

    # Spark pipeline flow
    fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=bg)
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.set_title("Spark Medallion Pipeline", color=gold, fontsize=16, fontweight="bold", pad=16)
    stages = [
        ("Public APIs", "NOAA · CTA · METAR · FRED · Trends"),
        ("Bronze", "Raw JSON snapshots"),
        ("Silver", "Parsed Delta tables"),
        ("Gold", "City stress · anomalies · KPIs"),
        ("PBIP", "Semantic model + report"),
    ]
    x, y = 0.08, 0.72
    for i, (title, sub) in enumerate(stages):
        box = FancyBboxPatch((x, y - 0.08), 0.16, 0.14, boxstyle="round,pad=0.02", facecolor="#2C2C2C", edgecolor=gold)
        ax.add_patch(box)
        ax.text(x + 0.08, y + 0.02, title, ha="center", color=gold, fontsize=10, fontweight="bold")
        ax.text(x + 0.08, y - 0.04, sub, ha="center", color=cream, fontsize=7)
        if i < len(stages) - 1:
            ax.annotate("", xy=(x + 0.19, y), xytext=(x + 0.16, y), arrowprops=dict(arrowstyle="->", color=cyan))
        x += 0.19
    spark_path = DOCS / "spark-pipeline.png"
    fig.tight_layout()
    fig.savefig(spark_path, dpi=144, facecolor=bg)
    plt.close(fig)
    out_paths.append(spark_path)

    # Lightsail ops status (styled mock matching live console)
    fig, ax = plt.subplots(figsize=(10, 5), facecolor=bg)
    ax.set_facecolor(bg)
    ax.axis("off")
    ax.text(0.05, 0.92, "AQ PulseGrid — Chicago", color=cream, fontsize=18, fontweight="bold")
    ax.text(0.05, 0.84, "pulse.aureaquantra.com · FastAPI + Lightsail", color="#94a3b8", fontsize=10)
    for i, (label, val) in enumerate([("City stress", "76.6"), ("Transit load", "34.2"), ("Weather risk", "24.0")]):
        bx = 0.05 + i * 0.31
        rect = FancyBboxPatch((bx, 0.55), 0.26, 0.22, boxstyle="round,pad=0.02", facecolor="#1a2332", edgecolor="#243044")
        ax.add_patch(rect)
        ax.text(bx + 0.04, 0.68, label, color="#94a3b8", fontsize=9)
        ax.text(bx + 0.04, 0.58, val, color=cyan, fontsize=20, fontweight="bold")
    ax.text(0.05, 0.38, "Phase 1 MVP: Done · HTTPS: Done · Fabric embed: Planned", color=gold, fontsize=10)
    lightsail_path = DOCS / "lightsail-status.png"
    fig.tight_layout()
    fig.savefig(lightsail_path, dpi=144, facecolor=bg)
    plt.close(fig)
    out_paths.append(lightsail_path)

    return out_paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pipeline + README screenshots for AQ PulseGrid"
    )
    parser.add_argument("--city", default="chicago")
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Reuse bronze; run transform/ml/pbip only",
    )
    parser.add_argument(
        "--screenshots-only",
        action="store_true",
        help="Skip pipeline; render PNGs from Delta",
    )
    parser.add_argument(
        "--platform-only",
        action="store_true",
        help="Render PBIP/spark/lightsail PNGs only (no Delta charts)",
    )
    args = parser.parse_args()

    if args.platform_only:
        print("Capturing platform screenshots...")
        paths = capture_platform_screenshots(args.city)
        for p in paths:
            print(f"  {p}")
        return 0

    if not args.screenshots_only:
        print(f"Running pipeline for {args.city}...", flush=True)
        _run_pipeline(args.city, skip_ingest=args.skip_ingest)

    print("Capturing dashboard screenshots...")
    paths = capture_screenshots(args.city)
    paths.extend(capture_platform_screenshots(args.city))
    for p in paths:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
