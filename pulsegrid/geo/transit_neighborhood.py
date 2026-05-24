"""Resolve transit alert text to a neighborhood label (metro-specific reference data)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from pulsegrid.config import ROOT

REF = ROOT / "datasets" / "reference"

# Bus / L route tokens in CTA alert copy
_ROUTE_NUM_RE = re.compile(r"#\s*(\d+[A-Z]?)", re.IGNORECASE)
_LINE_RE = re.compile(
    r"\b("
    r"red|blue|green|brown|orange|pink|purple|yellow"
    r")\s+line\b",
    re.IGNORECASE,
)
_COLON_LINE_HEADLINE = re.compile(r"^([^:]{2,48}):\s", re.IGNORECASE)
GEO_ROOT = REF / "transit_geo"


@dataclass(frozen=True)
class TransitGeoConfig:
    keywords: tuple[tuple[str, str], ...]  # (neighborhood, keyword)
    streets: tuple[tuple[str, str], ...]  # (street token, neighborhood)
    stations: tuple[tuple[str, str], ...]  # (station match, neighborhood)
    routes: tuple[tuple[tuple[str, ...], str], ...]  # (patterns, neighborhood)


def _read_csv_pairs(path: Path, *, swap: bool = False) -> tuple[tuple[str, str], ...]:
    if not path.is_file():
        return ()
    rows: list[tuple[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            a = (row.get("neighborhood") or row.get("hood") or "").strip()
            b = (row.get("keyword") or row.get("street") or row.get("match") or "").strip()
            if not a or not b:
                continue
            rows.append((b, a) if swap else (a, b))
    return tuple(rows)


def _read_keywords_csv(path: Path) -> tuple[tuple[str, str], ...]:
    if not path.is_file():
        return ()
    out: list[tuple[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            n = (row.get("neighborhood") or "").strip()
            k = (row.get("keyword") or "").strip()
            if n and k:
                out.append((n, k))
    return tuple(out)


def _load_yaml_list(path: Path, key: str) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = data.get(key) or []
    return items if isinstance(items, list) else []


def _manifest_entry(city: str) -> dict[str, str] | None:
    manifest = REF / "metro_transit_geo.yaml"
    if manifest.is_file():
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        entry = (data.get("metros") or {}).get(city)
        if isinstance(entry, dict):
            return entry
    auto = GEO_ROOT / city
    if (auto / "keywords.csv").is_file():
        base = f"transit_geo/{city}"
        return {
            "keywords": f"{base}/keywords.csv",
            "routes": f"{base}/routes.yaml",
            "stations": f"{base}/stations.yaml",
            "streets": f"{base}/streets.csv",
        }
    return None


@lru_cache(maxsize=128)
def load_transit_geo_config(city: str) -> TransitGeoConfig | None:
    """Load metro transit→neighborhood rules from reference YAML manifest."""
    entry = _manifest_entry(city)
    if entry is None:
        return None

    keywords: list[tuple[str, str]] = []
    kw_file = entry.get("keywords")
    if kw_file:
        keywords.extend(_read_keywords_csv(REF / str(kw_file)))

    streets: list[tuple[str, str]] = []
    st_file = entry.get("streets")
    if st_file:
        path = REF / str(st_file)
        if path.is_file():
            with path.open(encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f):
                    street = (row.get("street") or "").strip()
                    hood = (row.get("neighborhood") or "").strip()
                    if street and hood:
                        streets.append((street, hood))

    stations: list[tuple[str, str]] = []
    st_path = entry.get("stations")
    if st_path:
        for item in _load_yaml_list(REF / str(st_path), "stations"):
            match = str(item.get("match") or "").strip()
            hood = str(item.get("neighborhood") or "").strip()
            if match and hood:
                stations.append((match, hood))

    routes: list[tuple[tuple[str, ...], str]] = []
    rt_path = entry.get("routes")
    if not rt_path:
        return TransitGeoConfig(
            keywords=tuple(keywords),
            streets=tuple(streets),
            stations=tuple(stations),
            routes=(),
        )
    for item in _load_yaml_list(REF / str(rt_path), "routes"):
        hood = str(item.get("neighborhood") or "").strip()
        patterns = item.get("patterns") or []
        if hood and patterns:
            routes.append(
                (tuple(str(p).strip() for p in patterns if str(p).strip()), hood)
            )

    return TransitGeoConfig(
        keywords=tuple(keywords),
        streets=tuple(streets),
        stations=tuple(stations),
        routes=tuple(routes),
    )


def _sorted_by_length(pairs: tuple[tuple[str, str], ...]) -> list[tuple[str, str]]:
    return sorted(pairs, key=lambda x: len(x[0]), reverse=True)


def _text_contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


def _headline_line_name(headline: str) -> str | None:
    m = _COLON_LINE_HEADLINE.match((headline or "").strip())
    if not m:
        return None
    line = m.group(1).strip()
    lower = line.lower()
    if any(
        token in lower
        for token in (
            "notice",
            "following",
            "detour",
            "route ",
            "stop is",
            "bus stop",
            "stops are",
        )
    ):
        return None
    return line


def _match_line_token(token: str, routes: tuple[tuple[tuple[str, ...], str], ...]) -> str | None:
    if not token:
        return None
    return _match_routes(token, routes) or _match_routes(f"{token}:", routes)


def _match_routes(text: str, routes: tuple[tuple[tuple[str, ...], str], ...]) -> str | None:
    lower = text.lower()
    for patterns, hood in routes:
        for pat in patterns:
            pl = pat.lower()
            if pl.startswith("#"):
                for num in _ROUTE_NUM_RE.findall(text):
                    token = f"#{num}".lower()
                    if pl.replace(" ", "").lower() == token:
                        return hood
            if pl in lower:
                return hood
    for line_color in _LINE_RE.findall(text):
        token = f"{line_color} line"
        for patterns, hood in routes:
            if any(p.lower() == token for p in patterns):
                return hood
    return None


def resolve_transit_alert_neighborhood(
    *,
    city: str,
    headline: str = "",
    short_description: str = "",
    service: str = "",
) -> str:
    """
    Best-effort neighborhood from alert copy.
    Priority: station → street/intersection → keyword → route.
    """
    text = " ".join(p for p in (headline, short_description, service) if p).strip()
    if not text:
        return ""
    cfg = load_transit_geo_config(city)
    if cfg is None:
        line = _headline_line_name(headline)
        if line:
            return line
        return _fallback_keywords(text, city)

    for station, hood in _sorted_by_length(cfg.stations):
        if _text_contains(text, station):
            return hood

    # Explicit #bus or 'L line' in copy — before street tokens (e.g. Kingsbury).
    if _ROUTE_NUM_RE.search(text) or _LINE_RE.search(text):
        route_hood = _match_routes(text, cfg.routes)
        if route_hood:
            return route_hood

    for street, hood in _sorted_by_length(cfg.streets):
        if _text_contains(text, street):
            return hood

    for hood, keyword in _sorted_by_length(cfg.keywords):
        if _text_contains(text, keyword):
            return hood

    route_hood = _match_routes(text, cfg.routes)
    if route_hood:
        return route_hood

    line = _headline_line_name(headline)
    if line:
        route_hood = _match_line_token(line, cfg.routes)
        if route_hood:
            return route_hood
        if len(line) <= 40:
            return line

    return ""


def _fallback_keywords(text: str, city: str) -> str:
    cfg = load_transit_geo_config(city)
    if cfg:
        for hood, keyword in _sorted_by_length(cfg.keywords):
            if _text_contains(text, keyword):
                return hood
    path = REF / "chicago_neighborhood_keywords.csv"
    if city == "chicago" and path.is_file():
        for hood, keyword in _sorted_by_length(_read_keywords_csv(path)):
            if _text_contains(text, keyword):
                return hood
    return ""
