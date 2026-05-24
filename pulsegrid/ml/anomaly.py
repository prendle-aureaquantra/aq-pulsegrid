"""Baseline z-score anomaly detection."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import yaml

from pulsegrid.config import ROOT


@dataclass
class AnomalySignal:
    signal_type: str
    metric: str
    observed: float
    baseline: float
    z_score: float
    severity: str
    message: str

    def to_row(self, city: str, snapshot_at: str) -> dict:
        return {
            "city": city,
            "snapshot_at": snapshot_at,
            "signal_type": self.signal_type,
            "metric": self.metric,
            "observed": self.observed,
            "baseline": round(self.baseline, 2),
            "z_score": round(self.z_score, 2),
            "severity": self.severity,
            "message": self.message,
        }


def _load_baselines(city: str) -> dict:
    path = ROOT / "datasets" / "reference" / f"{city}_baselines.yaml"
    if not path.is_file():
        return {"metrics": {}, "thresholds": {"z_score_alert": 2.0}}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _history_stats(history: pd.DataFrame | None, metric: str) -> tuple[float, float]:
    if history is None or history.empty or metric not in history.columns:
        return 0.0, 1.0
    series = history[metric].dropna()
    if len(series) < 2:
        return float(series.mean()) if len(series) else 0.0, 1.0
    return float(series.mean()), float(series.std(ddof=0)) or 1.0


def _z(observed: float, mean: float, std: float) -> float:
    return (observed - mean) / max(std, 1e-6)


def _severity(z: float, threshold: float) -> str:
    az = abs(z)
    if az >= threshold * 1.5:
        return "high"
    if az >= threshold:
        return "medium"
    return "low"


def detect_anomalies(
    *,
    city: str,
    snapshot_at: str,
    metrics: dict,
    history: pd.DataFrame | None = None,
) -> list[AnomalySignal]:
    cfg = _load_baselines(city)
    defaults = cfg.get("metrics") or {}
    threshold = float((cfg.get("thresholds") or {}).get("z_score_alert", 2.0))
    signals: list[AnomalySignal] = []

    mllib_z = metrics.get("mllib_z_score")
    if mllib_z is not None and float(mllib_z) >= threshold * 1.25:
        signals.append(
            AnomalySignal(
                signal_type="mllib_multivariate_spike",
                metric="mllib_z_score",
                observed=float(mllib_z),
                baseline=0.0,
                z_score=float(mllib_z),
                severity=_severity(float(mllib_z), threshold),
                message="Spark MLlib multivariate stress score elevated",
            )
        )

    checks = [
        ("transit_alert_spike", "active_transit_alerts", "Transit alert volume"),
        ("weather_alert_spike", "active_noaa_alerts", "NOAA alert volume"),
        (
            "precip_forecast_spike",
            "avg_precip_pct_next_periods",
            "Forecast precipitation",
        ),
    ]

    for signal_type, key, label in checks:
        observed = float(metrics.get(key, 0))
        hist_mean, hist_std = _history_stats(history, key)
        baseline = (
            hist_mean
            if history is not None and not history.empty
            else float(defaults.get(key, observed))
        )
        std = (
            hist_std
            if history is not None and len(history) >= 2
            else max(baseline * 0.15, 1.0)
        )
        z = _z(observed, baseline, std)
        if abs(z) >= threshold:
            direction = "above" if z > 0 else "below"
            signals.append(
                AnomalySignal(
                    signal_type=signal_type,
                    metric=key,
                    observed=observed,
                    baseline=baseline,
                    z_score=z,
                    severity=_severity(z, threshold),
                    message=f"{label} {observed:.1f} is {direction} baseline ({baseline:.1f}, z={z:.2f})",
                )
            )

    active_transit = max(
        int(metrics.get("active_transit_alerts", metrics.get("active_cta_alerts", 0))),
        1,
    )
    reroute_share = float(metrics.get("reroute_count", 0)) / active_transit
    baseline_share = float(defaults.get("reroute_share", 0.5))
    z_reroute = _z(reroute_share, baseline_share, 0.08)
    if abs(z_reroute) >= threshold:
        signals.append(
            AnomalySignal(
                signal_type="reroute_share_spike",
                metric="reroute_share",
                observed=round(reroute_share, 3),
                baseline=baseline_share,
                z_score=z_reroute,
                severity=_severity(z_reroute, threshold),
                message=(
                    f"Reroute share {reroute_share:.0%} vs baseline {baseline_share:.0%} (z={z_reroute:.2f})"
                ),
            )
        )

    return signals


def detect_neighborhood_spikes(
    transit_df: pd.DataFrame | None,
    city: str,
    snapshot_at: str,
    threshold: float = 2.0,
) -> list[dict]:
    if transit_df is None or transit_df.empty:
        return []
    tc = transit_df[
        (transit_df["city"] == city) & (transit_df["neighborhood_hint"] != "")
    ]
    if tc.empty:
        return []
    counts = tc.groupby("neighborhood_hint").size()
    mean = counts.mean()
    std = counts.std(ddof=0) or 1.0
    rows: list[dict] = []
    for hood, count in counts.items():
        z = (count - mean) / std
        if z >= threshold:
            rows.append(
                {
                    "city": city,
                    "snapshot_at": snapshot_at,
                    "signal_type": "neighborhood_activity_spike",
                    "metric": "neighborhood_alert_count",
                    "observed": int(count),
                    "baseline": round(float(mean), 2),
                    "z_score": round(float(z), 2),
                    "severity": "high" if z >= threshold * 1.5 else "medium",
                    "message": f"Unusual activity in {hood}: {count} alerts (z={z:.2f})",
                }
            )
    return rows
