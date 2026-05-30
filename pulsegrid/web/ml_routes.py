"""ML API routes — stress breakdown, anomalies, pulse history."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

try:
    from csv_store import (
        DEFAULT_METRO,
        DEFAULT_PAGE_SIZE,
        FRESHNESS_FIELDS,
        MAX_PAGE_SIZE,
        STRESS_COMPONENT_FIELDS,
        filter_city,
        latest_snapshot,
        pick_fields,
        read_csv_rows,
    )
except ImportError:
    from pulsegrid.web.csv_store import (  # type: ignore[no-redef]
        DEFAULT_METRO,
        DEFAULT_PAGE_SIZE,
        FRESHNESS_FIELDS,
        MAX_PAGE_SIZE,
        STRESS_COMPONENT_FIELDS,
        filter_city,
        latest_snapshot,
        pick_fields,
        read_csv_rows,
    )

router = APIRouter(prefix="/api/ml", tags=["ml"])


def _parse_snapshot_at(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def _filter_history_days(rows: list[dict[str, str]], days: int) -> list[dict[str, str]]:
    if days <= 0 or not rows:
        return rows
    cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    kept: list[dict[str, str]] = []
    for row in rows:
        ts = _parse_snapshot_at(row.get("snapshot_at", ""))
        if ts is None or ts.timestamp() >= cutoff:
            kept.append(row)
    return kept


@router.get("/stress")
def api_ml_stress(metro: str = Query(default="")) -> JSONResponse:
    slug = (metro or DEFAULT_METRO).strip().lower()
    snap = latest_snapshot(slug)
    history_rows = filter_city(read_csv_rows("PulseHistory.csv"), slug)
    latest_hist = history_rows[-1] if history_rows else None
    mllib_score = None
    if snap and snap.get("mllib_z_score"):
        mllib_score = snap.get("mllib_z_score")
    elif latest_hist and latest_hist.get("mllib_z_score"):
        mllib_score = latest_hist.get("mllib_z_score")
    return JSONResponse(
        {
            "metro": slug,
            "snapshotAt": snap.get("snapshot_at") if snap else None,
            "stressIndex": snap.get("city_stress_index") if snap else None,
            "mllibZScore": mllib_score,
            "mllibNote": (
                "Multivariate z-score vs pulse_history; improves after ~3 daily ML runs."
                if mllib_score is None
                else None
            ),
            "components": pick_fields(snap, STRESS_COMPONENT_FIELDS),
            "freshness": pick_fields(snap, FRESHNESS_FIELDS),
            "airport": pick_fields(
                snap,
                (
                    "airport_flight_category",
                    "airport_visibility_sm",
                    "airport_ops_stress",
                    "active_airport_stations",
                    "airport_stations_summary",
                ),
            )
            if snap
            else {},
        }
    )


@router.get("/anomalies")
def api_ml_anomalies(
    metro: str = Query(default=""),
    severity: str = Query(default=""),
    signal_type: str = Query(default=""),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> JSONResponse:
    slug = (metro or DEFAULT_METRO).strip().lower()
    rows = filter_city(read_csv_rows("AnomalySignals.csv"), slug)
    sev = severity.strip().lower()
    sig = signal_type.strip().lower()
    if sev:
        rows = [r for r in rows if r.get("severity", "").lower() == sev]
    if sig:
        rows = [r for r in rows if r.get("signal_type", "").lower() == sig]
    mllib_rows = [r for r in rows if r.get("signal_type") == "mllib_multivariate_spike"]
    rows = rows[-limit:]
    return JSONResponse(
        {
            "metro": slug,
            "severityFilter": sev or None,
            "signalTypeFilter": sig or None,
            "count": len(rows),
            "mllibSpikeCount": len(mllib_rows),
            "anomalies": rows,
        }
    )


@router.get("/history")
def api_ml_history(
    metro: str = Query(default=""),
    days: int = Query(default=30, ge=0, le=365),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> JSONResponse:
    slug = (metro or DEFAULT_METRO).strip().lower()
    rows = filter_city(read_csv_rows("PulseHistory.csv"), slug)
    rows = _filter_history_days(rows, days)
    if limit and len(rows) > limit:
        rows = rows[-limit:]
    return JSONResponse(
        {
            "metro": slug,
            "days": days,
            "count": len(rows),
            "history": rows,
            "note": (
                "Anomaly z-scores improve after ~7 daily ML runs as pulse_history grows."
                if not rows
                else None
            ),
        }
    )
