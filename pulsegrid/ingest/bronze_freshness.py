"""Bronze layer last-success timestamps per feed (for gold + ops console)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pulsegrid.config import BRONZE

FEED_SUBDIRS = {
    "weather": ("noaa", "weather"),
    "transit": ("transit",),
    "civic311": ("civic311",),
    "airport": ("airport",),
    "opensky": ("opensky",),
    "usgs": ("usgs",),
    "air_quality": ("air_quality",),
}


def _latest_mtime(base: Path) -> datetime | None:
    if not base.is_dir():
        return None
    latest: datetime | None = None
    for path in base.rglob("*"):
        if path.is_file():
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            if latest is None or mtime > latest:
                latest = mtime
    return latest


def latest_bronze_times(city_slug: str) -> dict[str, str]:
    """ISO timestamps for newest bronze file per logical feed."""
    root = BRONZE / city_slug
    out: dict[str, str] = {}
    for feed, subdirs in FEED_SUBDIRS.items():
        best: datetime | None = None
        for sub in subdirs:
            ts = _latest_mtime(root / sub)
            if ts and (best is None or ts > best):
                best = ts
        if best:
            out[feed] = best.isoformat()
    if out:
        out["data_refreshed_at"] = max(out.values())
    return out


def write_freshness_marker(city_slug: str, feed: str) -> Path:
    """Touch a marker after successful ingest (optional fast path)."""
    marker_dir = BRONZE / city_slug / ".freshness"
    marker_dir.mkdir(parents=True, exist_ok=True)
    path = marker_dir / f"{feed}.txt"
    path.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
    return path
