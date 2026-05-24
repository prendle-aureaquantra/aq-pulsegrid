"""City Stress Index — multi-signal urban stress scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StressComponents:
    transit_load: float
    weather_risk: float
    precip_risk: float
    disruption_ratio: float

    @property
    def total(self) -> float:
        return round(
            self.transit_load
            + self.weather_risk
            + self.precip_risk
            + self.disruption_ratio,
            2,
        )


def _category_counts(transit_df) -> dict[str, int]:
    if transit_df is None or transit_df.empty:
        return {}
    return transit_df["alert_category"].value_counts().to_dict()


def compute_stress_index(
    *,
    active_transit: int,
    active_noaa: int,
    avg_precip: float,
    severe_weather_count: int = 0,
    active_civic311: int = 0,
    infrastructure_failure_risk: float = 0.0,
    infrastructure_fatigue_risk: float = 0.0,
    category_counts: dict[str, int] | None = None,
) -> tuple[float, StressComponents]:
    """Return 0–100 City Stress Index and component breakdown."""
    counts = category_counts or {}
    reroutes = counts.get("reroute", 0)
    delays = counts.get("delay", 0)
    disruption_types = reroutes + delays + counts.get("stop_change", 0)

    transit_load = min(40.0, active_transit * 0.28)
    weather_risk = min(
        25.0,
        active_noaa * 4.0 + severe_weather_count * 8.0 + active_civic311 * 0.08,
    )
    precip_risk = min(20.0, avg_precip * 0.22)
    share = disruption_types / max(active_transit, 1)
    disruption_ratio = min(15.0, share * 20.0)
    infra_component = min(
        15.0, infrastructure_failure_risk * 0.12 + infrastructure_fatigue_risk * 0.06
    )

    components = StressComponents(
        transit_load=round(transit_load, 2),
        weather_risk=round(weather_risk, 2),
        precip_risk=round(precip_risk, 2),
        disruption_ratio=round(disruption_ratio, 2),
    )
    return min(100.0, components.total + infra_component), components


def stress_from_frames(
    transit_df,
    weather_df,
    forecast_df,
    city: str,
    civic311_df=None,
    *,
    infrastructure_rollup: dict | None = None,
) -> dict:
    tc = (
        transit_df[transit_df["city"] == city]
        if transit_df is not None and not transit_df.empty
        else None
    )
    wc = (
        weather_df[weather_df["city"] == city]
        if weather_df is not None and not weather_df.empty
        else None
    )
    fc = (
        forecast_df[forecast_df["city"] == city]
        if forecast_df is not None and not forecast_df.empty
        else None
    )
    c311 = (
        civic311_df[civic311_df["city"] == city]
        if civic311_df is not None and not civic311_df.empty
        else None
    )

    active_transit = len(tc) if tc is not None else 0
    active_noaa = len(wc) if wc is not None else 0
    active_civic311 = len(c311) if c311 is not None else 0
    avg_precip = (
        float(fc["precip_pct"].mean()) if fc is not None and not fc.empty else 0.0
    )
    severe = 0
    if wc is not None and not wc.empty and "severity" in wc.columns:
        severe = int(
            wc["severity"].str.contains("Severe|Extreme", case=False, na=False).sum()
        )

    counts = _category_counts(tc)
    infra = infrastructure_rollup or {}
    score, parts = compute_stress_index(
        active_transit=active_transit,
        active_noaa=active_noaa,
        avg_precip=avg_precip,
        severe_weather_count=severe,
        active_civic311=active_civic311,
        infrastructure_failure_risk=float(
            infra.get("infrastructure_failure_risk") or 0
        ),
        infrastructure_fatigue_risk=float(
            infra.get("infrastructure_fatigue_risk") or 0
        ),
        category_counts=counts,
    )
    return {
        "city_stress_index": score,
        "transit_load_score": parts.transit_load,
        "weather_risk_score": parts.weather_risk,
        "precip_risk_score": parts.precip_risk,
        "disruption_ratio_score": parts.disruption_ratio,
        "active_transit_alerts": active_transit,
        "active_noaa_alerts": active_noaa,
        "active_civic311_requests": active_civic311,
        "avg_precip_pct_next_periods": round(avg_precip, 2),
        "reroute_count": counts.get("reroute", 0),
        "delay_count": counts.get("delay", 0),
        "infrastructure_failure_risk": float(
            infra.get("infrastructure_failure_risk") or 0
        ),
        "infrastructure_fatigue_risk": float(
            infra.get("infrastructure_fatigue_risk") or 0
        ),
        "bridge_risk_score": float(infra.get("bridge_risk_score") or 0),
        "road_surface_risk_score": float(infra.get("road_surface_risk_score") or 0),
    }
