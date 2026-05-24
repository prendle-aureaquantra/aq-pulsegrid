"""Discover Socrata 311 datasets for US metros via the public catalog API."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import requests

from pulsegrid.config import http_user_agent
from pulsegrid.metros import MetroConfig

CATALOG_URL = "https://api.us.socrata.com/api/catalog/v1"

DATE_FIELD_CANDIDATES = (
    "created_date",
    "createddate",
    "created_at",
    "open_dt",
    "servicedcdate",
    "date_request_submitted",
    "incident_date",
    "requested_datetime",
    "request_date",
)
TYPE_FIELD_CANDIDATES = (
    "complaint_type",
    "request_type",
    "sr_type",
    "service_request_type",
    "type",
    "issue_type",
    "servicetype",
    "incident_category",
    "problem_type",
)
STATUS_FIELD_CANDIDATES = ("status", "request_status", "current_status")

# Known Socrata domains when catalog search is noisy
# Curated non-catalog endpoints (ArcGIS / CARTO) — merged by sync_civic311_from_socrata.py
CURATED_311: dict[str, dict[str, Any]] = {
    "houston": {
        "adapter": "arcgis",
        "url": "https://mycity2.houstontx.gov/pubgis01/rest/services/311/D365_SR311_PROD/MapServer/1/query",
        "date_field": "CreatedDate",
        "type_field": "CaseType",
        "status_field": "Status",
        "order_by": "CreatedDate DESC",
        "where": "1=1",
        "limit": 150,
        "recent_days": 0,
    },
    "philadelphia": {
        "adapter": "carto",
        "url": "https://phl.carto.com/api/v2/sql",
        "table": "public_cases_fc",
        "date_field": "requested_datetime",
        "type_field": "service_request_type",
        "status_field": "status",
        "limit": 100,
        "recent_days": 14,
    },
}

METRO_DOMAIN_HINTS: dict[str, list[str]] = {
    "houston": ["data.houstontx.gov", "cohweb.houstontx.gov"],
    "philadelphia": ["phillyopa.com", "phila.gov", "opendataphilly.org"],
    "chicago": ["data.cityofchicago.org"],
    "nyc": ["data.cityofnewyork.us"],
    "la": ["data.lacity.org"],
    "san-francisco": ["data.sfgov.org"],
    "boston": ["data.boston.gov"],
    "washington-dc": ["data.dc.gov"],
    "atlanta": ["data.atlantaga.gov"],
    "seattle": ["data.seattle.gov"],
    "denver": ["data.denvergov.org"],
    "dallas": ["www.dallasopendata.com", "dallasopendata.com"],
    "miami": ["opendata.miamidade.gov", "miamidade.gov"],
    "phoenix": ["phoenixopendata.com"],
    "austin": ["data.austintexas.gov"],
}


def _domain_hints(metro: MetroConfig) -> list[str]:
    if metro.slug in METRO_DOMAIN_HINTS:
        return list(METRO_DOMAIN_HINTS[metro.slug])
    slug = metro.slug.replace("-", "")
    return [
        f"data.{slug}.org",
        f"data.cityof{slug}.org",
        f"www.{slug}opendata.com",
        f"{slug}opendata.com",
    ]


def _catalog_search(
    *,
    q: str,
    domains: str | None = None,
    search_context: str | None = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "q": q,
        "only": "datasets",
        "limit": limit,
    }
    if domains:
        params["domains"] = domains
    if search_context:
        params["search_context"] = search_context
    resp = requests.get(
        CATALOG_URL,
        params=params,
        headers={"User-Agent": http_user_agent()},
        timeout=45,
    )
    resp.raise_for_status()
    doc = resp.json()
    return list(doc.get("results") or [])


def _resource_url(domain: str, resource_id: str) -> str:
    host = domain if domain.startswith("http") else f"https://{domain}"
    host = host.rstrip("/")
    if not host.startswith("http"):
        host = f"https://{host}"
    return f"{host}/resource/{resource_id}.json"


def _pick_column(columns: list[dict], candidates: tuple[str, ...]) -> str | None:
    names = {str(c.get("fieldName") or c.get("name") or "").lower() for c in columns}
    for cand in candidates:
        if cand.lower() in names:
            return cand
    for col in columns:
        name = str(col.get("fieldName") or col.get("name") or "")
        if any(k in name.lower() for k in ("date", "created", "open")):
            return name
    return None


def _score_dataset(title: str, description: str, metro: MetroConfig) -> int:
    text = f"{title} {description}".lower()
    score = 0
    if "311" in text:
        score += 30
    if "service request" in text or "service requests" in text:
        score += 20
    if "complaint" in text:
        score += 10
    for tok in re.split(r"[-_\s]+", metro.slug):
        if len(tok) > 2 and tok in text:
            score += 8
    if metro.name.lower() in text:
        score += 6
    return score


def _probe_socrata(url: str) -> tuple[bool, list[str]]:
    """Return (ok, column_names) for a candidate resource URL."""
    try:
        resp = requests.get(
            url,
            params={"$limit": 1},
            headers={"User-Agent": http_user_agent()},
            timeout=30,
        )
        if resp.status_code != 200:
            return False, []
        data = resp.json()
        if not isinstance(data, list) or not data:
            return False, []
        if isinstance(data[0], dict):
            return True, list(data[0].keys())
        return False, []
    except (requests.RequestException, ValueError):
        return False, []


def _build_config_from_columns(
    url: str, columns: list[str], *, limit: int = 150, recent_days: int = 14
) -> dict[str, Any]:
    col_set = {c.lower(): c for c in columns}

    def pick(candidates: tuple[str, ...]) -> str:
        for c in candidates:
            if c.lower() in col_set:
                return col_set[c.lower()]
        return ""

    date_field = pick(DATE_FIELD_CANDIDATES)
    type_field = pick(TYPE_FIELD_CANDIDATES)
    status_field = pick(STATUS_FIELD_CANDIDATES)
    cfg: dict[str, Any] = {
        "url": url,
        "date_field": date_field or "created_date",
        "type_field": type_field or "type",
        "status_field": status_field or "status",
        "order": f"{date_field or 'created_date'} DESC",
        "limit": limit,
        "recent_days": recent_days,
    }
    return cfg


def curated_311_config(metro_slug: str) -> dict[str, Any] | None:
    cfg = CURATED_311.get(metro_slug)
    return dict(cfg) if cfg else None


def discover_311_config(metro: MetroConfig) -> dict[str, Any] | None:
    """Best-effort 311 config for a US metro (curated, then Socrata catalog), or None."""
    if metro.country.upper() != "US":
        return None

    curated = curated_311_config(metro.slug)
    if curated:
        adapter = str(curated.get("adapter", "socrata")).lower()
        if adapter == "socrata":
            ok, columns = _probe_socrata(curated["url"])
            if ok:
                return _build_config_from_columns(curated["url"], columns)
        else:
            return curated

    candidates: list[tuple[int, str, str]] = []
    seen_urls: set[str] = set()

    def add_result(score: int, domain: str, resource: dict) -> None:
        rid = resource.get("id") or resource.get("resource", {}).get("id")
        if not rid:
            return
        url = _resource_url(domain, str(rid))
        if url in seen_urls:
            return
        seen_urls.add(url)
        candidates.append((score, url, str(rid)))

    for domain in _domain_hints(metro):
        try:
            results = _catalog_search(
                q="311 service request",
                domains=domain,
                limit=10,
            )
        except requests.RequestException:
            continue
        for item in results:
            resource = item.get("resource") or {}
            meta = item.get("metadata") or {}
            title = str(meta.get("name") or resource.get("name") or "")
            desc = str(meta.get("description") or "")
            score = _score_dataset(title, desc, metro)
            dom = str(resource.get("name", "")).split("/")[0] or domain
            add_result(score, dom, resource)

    try:
        results = _catalog_search(
            q="311",
            search_context=metro.name,
            limit=12,
        )
        for item in results:
            resource = item.get("resource") or {}
            meta = item.get("metadata") or {}
            title = str(meta.get("name") or "")
            desc = str(meta.get("description") or "")
            score = _score_dataset(title, desc, metro)
            permalink = str(resource.get("permalink") or "")
            parsed = urlparse(permalink)
            domain = parsed.netloc or ""
            if domain:
                add_result(score, domain, resource)
    except requests.RequestException:
        pass

    candidates.sort(key=lambda x: -x[0])
    for score, url, _rid in candidates:
        if score < 15:
            continue
        ok, columns = _probe_socrata(url)
        if ok and columns:
            cfg = _build_config_from_columns(url, columns)
            cfg["_discovery_score"] = score
            return cfg
    return None
