"""Road / bridge / infrastructure fatigue and failure risk from civic 311 requests."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

ASSET_BRIDGE = "bridge"
ASSET_ROAD = "road_surface"
ASSET_STRUCTURAL = "structural"
ASSET_UTILITY = "utility"
ASSET_OTHER = "other"

FAILURE_KEYWORDS = (
    "collapse",
    "cave-in",
    "cave in",
    "sinkhole",
    "failure",
    "buckl",
    "unsafe",
    "hazard",
    "emergency",
    "structural",
    "crumbling",
    "fallen",
    "damaged beyond",
)

FATIGUE_KEYWORDS = (
    "pothole",
    "pavement",
    "asphalt",
    "street surface",
    "road surface",
    "deteriorat",
    "alligator",
    "crack",
    "depression",
    "rough",
    "worn",
    "patch",
    "resurfac",
)

BRIDGE_KEYWORDS = (
    "bridge",
    "overpass",
    "underpass",
    "viaduct",
    "expressway structure",
)

ROAD_KEYWORDS = (
    "pothole",
    "pavement",
    "street",
    "roadway",
    "asphalt",
    "alley",
    "sidewalk",
    "curb",
)

UTILITY_KEYWORDS = (
    "sewer",
    "water main",
    "gas leak",
    "hydrant",
    "manhole",
)

OPEN_STATUS = re.compile(
    r"open|pending|in progress|assigned|new|submitted|active",
    re.IGNORECASE,
)


def _combined_text(*parts: str) -> str:
    return " ".join(p for p in parts if p).strip().lower()


def classify_infrastructure_request(
    request_type: str = "",
    descriptor: str = "",
    *,
    status: str = "",
) -> dict[str, str]:
    """Classify a 311 row into asset class and risk tier."""
    text = _combined_text(request_type, descriptor, status)
    asset = ASSET_OTHER
    if any(k in text for k in BRIDGE_KEYWORDS):
        asset = ASSET_BRIDGE
    elif any(k in text for k in FAILURE_KEYWORDS) and "bridge" not in text:
        asset = ASSET_STRUCTURAL
    elif any(k in text for k in ROAD_KEYWORDS) or any(k in text for k in FATIGUE_KEYWORDS):
        asset = ASSET_ROAD
    elif any(k in text for k in UTILITY_KEYWORDS):
        asset = ASSET_UTILITY

    if any(k in text for k in FAILURE_KEYWORDS):
        tier = "failure"
    elif any(k in text for k in FATIGUE_KEYWORDS) or asset == ASSET_ROAD:
        tier = "fatigue"
    elif asset in (ASSET_BRIDGE, ASSET_STRUCTURAL):
        tier = "failure_watch"
    else:
        tier = "routine"

    return {
        "asset_class": asset,
        "risk_tier": tier,
    }


def request_failure_risk_score(
    request_type: str = "",
    descriptor: str = "",
    *,
    status: str = "",
    asset_class: str | None = None,
) -> float:
    """Per-request failure/fatigue stress (0–20)."""
    meta = classify_infrastructure_request(request_type, descriptor, status=status)
    asset = asset_class or meta["asset_class"]
    tier = meta["risk_tier"]
    text = _combined_text(request_type, descriptor)

    score = 1.0
    if tier == "failure":
        score += 12.0
    elif tier == "failure_watch":
        score += 7.0
    elif tier == "fatigue":
        score += 4.0

    if asset == ASSET_BRIDGE:
        score += 4.0
    elif asset == ASSET_STRUCTURAL:
        score += 6.0
    elif asset == ASSET_ROAD:
        score += 2.0

    if OPEN_STATUS.search(status or ""):
        score += 2.0

    if any(k in text for k in ("major", "severe", "emergency", "immediate")):
        score += 3.0

    return round(min(20.0, score), 2)


def enrich_civic311_rows(rows: list[dict]) -> list[dict]:
    """Add infrastructure classification columns to silver-bound 311 rows."""
    out: list[dict] = []
    for row in rows:
        req_type = str(row.get("request_type") or "")
        descriptor = str(row.get("descriptor") or "")
        status = str(row.get("status") or "")
        meta = classify_infrastructure_request(req_type, descriptor, status=status)
        enriched = {
            **row,
            "descriptor": descriptor,
            "asset_class": meta["asset_class"],
            "risk_tier": meta["risk_tier"],
            "failure_risk_score": request_failure_risk_score(
                req_type, descriptor, status=status, asset_class=meta["asset_class"]
            ),
        }
        out.append(enriched)
    return out


def infrastructure_detail_rows(
    civic311: pd.DataFrame | None,
    city: str,
    snapshot_at: str,
) -> list[dict]:
    if civic311 is None or civic311.empty:
        return []
    cc = civic311[civic311["city"] == city].copy()
    if cc.empty:
        return []
    rows: list[dict] = []
    for _, row in cc.iterrows():
        req_type = str(row.get("request_type") or "")
        descriptor = str(row.get("descriptor") or row.get("request_type") or "")
        status = str(row.get("status") or "")
        meta = classify_infrastructure_request(req_type, descriptor, status=status)
        rows.append(
            {
                "city": city,
                "snapshot_at": snapshot_at,
                "request_id": str(row.get("request_id") or ""),
                "request_type": req_type,
                "descriptor": descriptor[:500],
                "status": status,
                "asset_class": meta["asset_class"],
                "risk_tier": meta["risk_tier"],
                "failure_risk_score": request_failure_risk_score(
                    req_type, descriptor, status=status
                ),
            }
        )
    return rows


def infrastructure_risk_rollup(
    civic311: pd.DataFrame | None,
    city: str,
    snapshot_at: str,
    *,
    avg_precip_pct: float = 0.0,
) -> dict[str, Any]:
    """Metro-level infrastructure fatigue / failure risk snapshot."""
    empty = {
        "city": city,
        "snapshot_at": snapshot_at,
        "infrastructure_failure_risk": 0.0,
        "infrastructure_fatigue_risk": 0.0,
        "bridge_risk_score": 0.0,
        "road_surface_risk_score": 0.0,
        "structural_risk_score": 0.0,
        "active_infrastructure_requests": 0,
        "open_infrastructure_requests": 0,
        "critical_open_requests": 0,
        "infrastructure_summary": "",
    }
    if civic311 is None or civic311.empty:
        return empty

    cc = civic311[civic311["city"] == city].copy()
    if cc.empty:
        return empty

    enriched = enrich_civic311_rows(cc.to_dict("records"))
    ic = pd.DataFrame(enriched)
    ic = ic[ic["asset_class"] != ASSET_OTHER]
    if ic.empty:
        return empty

    scores = ic["failure_risk_score"].astype(float).tolist()
    bridge = ic[ic["asset_class"] == ASSET_BRIDGE]
    road = ic[ic["asset_class"] == ASSET_ROAD]
    structural = ic[ic["asset_class"] == ASSET_STRUCTURAL]

    def _asset_scores(df: pd.DataFrame) -> float:
        if df.empty:
            return 0.0
        return round(float(df["failure_risk_score"].max()), 2)

    status_col = ic["status"].astype(str) if "status" in ic.columns else pd.Series([""] * len(ic))
    open_mask = status_col.str.contains(OPEN_STATUS)
    open_count = int(open_mask.sum())
    critical = ic[ic["risk_tier"] == "failure"]
    critical_open = 0
    if not critical.empty:
        critical_open = int(
            critical["status"].astype(str).str.contains(OPEN_STATUS).sum()
        )

    bridge_risk = _asset_scores(bridge)
    road_risk = _asset_scores(road)
    struct_risk = _asset_scores(structural)
    max_score = max(scores) if scores else 0.0
    mean_score = sum(scores) / len(scores) if scores else 0.0

    fatigue_base = min(100.0, len(road) * 2.5 + mean_score * 3.0)
    precip_boost = min(15.0, float(avg_precip_pct or 0) * 0.12)
    fatigue_risk = round(min(100.0, fatigue_base + precip_boost), 2)

    failure_risk = round(
        min(
            100.0,
            max_score * 4.0
            + bridge_risk * 3.0
            + struct_risk * 4.0
            + critical_open * 8.0
            + open_count * 0.5,
        ),
        2,
    )

    parts: list[str] = []
    if bridge_risk > 0:
        parts.append(f"bridge {bridge_risk:.0f}")
    if road_risk > 0:
        parts.append(f"road {road_risk:.0f}")
    if struct_risk > 0:
        parts.append(f"structural {struct_risk:.0f}")
    if critical_open:
        parts.append(f"{critical_open} critical open")

    return {
        "city": city,
        "snapshot_at": snapshot_at,
        "infrastructure_failure_risk": failure_risk,
        "infrastructure_fatigue_risk": fatigue_risk,
        "bridge_risk_score": bridge_risk,
        "road_surface_risk_score": road_risk,
        "structural_risk_score": struct_risk,
        "active_infrastructure_requests": len(ic),
        "open_infrastructure_requests": open_count,
        "critical_open_requests": critical_open,
        "infrastructure_summary": "; ".join(parts[:6]),
    }


def infrastructure_summary_by_asset(
    civic311: pd.DataFrame | None, city: str, snapshot_at: str
) -> list[dict]:
    """Grouped counts for PBIP drill (asset_class → request types)."""
    if civic311 is None or civic311.empty:
        return []
    cc = civic311[civic311["city"] == city]
    if cc.empty:
        return []
    rows: list[dict] = []
    for _, row in cc.iterrows():
        req_type = str(row.get("request_type") or "")
        descriptor = str(row.get("descriptor") or "")
        status = str(row.get("status") or "")
        meta = classify_infrastructure_request(req_type, descriptor, status=status)
        if meta["asset_class"] == ASSET_OTHER:
            continue
        rows.append(
            {
                "city": city,
                "snapshot_at": snapshot_at,
                "asset_class": meta["asset_class"],
                "risk_tier": meta["risk_tier"],
                "request_type": req_type,
            }
        )
    if not rows:
        return []
    df = pd.DataFrame(rows)
    summary = (
        df.groupby(["city", "snapshot_at", "asset_class", "risk_tier", "request_type"])
        .size()
        .reset_index(name="request_count")
    )
    return summary.to_dict("records")
