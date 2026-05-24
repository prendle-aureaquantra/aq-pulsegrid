"""Google Trends bronze snapshots (optional pytrends)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pulsegrid.config import BRONZE, CityConfig
from pulsegrid.metro_feeds import trends_config

DEFAULT_KEYWORDS = [
    "Chicago traffic",
    "public transit delay",
    "Chicago weather",
    "O'Hare delays",
]
DEFAULT_GEO = "US-IL"


def ingest_google_trends(city: CityConfig, out_dir: Path | None = None) -> list[Path]:
    try:
        from pytrends.request import TrendReq
    except ImportError as exc:
        raise RuntimeError(
            "pytrends not installed. Run: pip install -e '.[trends]'"
        ) from exc

    cfg = trends_config(city.slug) or {}
    keywords = list(cfg.get("keywords") or DEFAULT_KEYWORDS)
    geo = str(cfg.get("geo") or DEFAULT_GEO)

    base = out_dir or BRONZE / city.slug / "google_trends"
    base.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    pytrends = TrendReq(hl="en-US", tz=360)
    pytrends.build_payload(keywords, timeframe="now 7-d", geo=geo)
    interest = pytrends.interest_over_time()
    related = pytrends.related_queries()

    payload = {
        "source": "google_trends",
        "city": city.slug,
        "geo": geo,
        "keywords": keywords,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "interest_over_time": (
            interest.reset_index().to_dict(orient="records")
            if not interest.empty
            else []
        ),
        "related_queries": {
            kw: (
                v.get("top").to_dict(orient="records")
                if v.get("top") is not None
                else []
            )
            for kw, v in related.items()
            if v
        },
    }
    path = base / f"trends_{ts}.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return [path]
