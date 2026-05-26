"""MobilityData catalog lookup for GTFS-RT service alert (sa) feeds.

Uses the public GitHub catalog (no API key). Lists SA feeds from GitHub; resolves
download URLs lazily for the best filename match per metro.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
import yaml

from pulsegrid.config import DATA_ROOT, http_user_agent
from pulsegrid.metros import MetroConfig

CATALOG_API = (
    "https://api.github.com/repos/MobilityData/mobility-database-catalogs/"
    "contents/catalogs/sources/gtfs/realtime"
)
CATALOG_RAW = (
    "https://raw.githubusercontent.com/MobilityData/mobility-database-catalogs/"
    "main/catalogs/sources/gtfs/realtime/{filename}"
)
ROOT = Path(__file__).resolve().parents[2]
BUNDLED_LIST = ROOT / "datasets" / "reference" / "mobility_sa_filenames.json"
LIST_CACHE = DATA_ROOT / "cache" / "mobility_sa_filenames.json"
URL_CACHE = DATA_ROOT / "cache" / "mobility_sa_urls.json"
LIST_MAX_AGE_SEC = 7 * 24 * 3600

_COUNTRY_PREFIX = {
    "US": "us",
    "GB": "gb",
    "UK": "gb",
    "CA": "ca",
    "AU": "au",
    "DE": "de",
    "FR": "fr",
    "ES": "es",
    "IT": "it",
    "NL": "nl",
    "BE": "be",
    "SE": "se",
    "NO": "no",
    "DK": "dk",
    "FI": "fi",
    "AT": "at",
    "CH": "ch",
    "PL": "pl",
    "PT": "pt",
    "IE": "ie",
    "NZ": "nz",
    "SG": "sg",
    "AE": "ae",
    "JP": "jp",
    "KR": "kr",
    "IN": "in",
    "BR": "br",
    "MX": "mx",
    "AR": "ar",
    "CL": "cl",
    "CO": "co",
}

_US_STATE_NAMES: dict[str, str] = {
    "AL": "alabama",
    "AK": "alaska",
    "AZ": "arizona",
    "AR": "arkansas",
    "CA": "california",
    "CO": "colorado",
    "CT": "connecticut",
    "DC": "district-of-columbia",
    "DE": "delaware",
    "FL": "florida",
    "GA": "georgia",
    "HI": "hawaii",
    "IA": "iowa",
    "ID": "idaho",
    "IL": "illinois",
    "IN": "indiana",
    "KS": "kansas",
    "KY": "kentucky",
    "LA": "louisiana",
    "MA": "massachusetts",
    "MD": "maryland",
    "ME": "maine",
    "MI": "michigan",
    "MN": "minnesota",
    "MO": "missouri",
    "MS": "mississippi",
    "MT": "montana",
    "NC": "north-carolina",
    "ND": "north-dakota",
    "NE": "nebraska",
    "NH": "new-hampshire",
    "NJ": "new-jersey",
    "NM": "new-mexico",
    "NV": "nevada",
    "NY": "new-york",
    "OH": "ohio",
    "OK": "oklahoma",
    "OR": "oregon",
    "PA": "pennsylvania",
    "RI": "rhode-island",
    "SC": "south-carolina",
    "SD": "south-dakota",
    "TN": "tennessee",
    "TX": "texas",
    "UT": "utah",
    "VA": "virginia",
    "VT": "vermont",
    "WA": "washington",
    "WI": "wisconsin",
    "WV": "west-virginia",
    "WY": "wyoming",
}

_MIN_TOKEN_LEN = 3
_SHORT_SLUG_TOKENS = frozenset({"la"})
_MIN_RANK_SCORE = 15


@lru_cache(maxsize=1)
def _alias_catalog() -> dict[str, Any]:
    path = ROOT / "datasets" / "reference" / "transit_metro_aliases.yaml"
    if not path.is_file():
        return {}
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return doc.get("metros") or {}


def _metro_alias_keywords(metro_slug: str) -> tuple[str, ...]:
    raw = _alias_catalog().get(metro_slug) or {}
    if not isinstance(raw, dict):
        return ()
    kws = raw.get("keywords") or []
    return tuple(str(k).strip().lower() for k in kws if str(k).strip())


def _country_prefix(country: str) -> str:
    c = country.upper().strip()
    if c in _COUNTRY_PREFIX:
        return _COUNTRY_PREFIX[c]
    if len(c) == 2:
        return c.lower()
    return c[:2].lower()


def _metro_tokens(metro: MetroConfig) -> set[str]:
    tokens: set[str] = set()
    for part in re.split(r"[-_\s]+", metro.slug.lower()):
        if len(part) >= _MIN_TOKEN_LEN or part in _SHORT_SLUG_TOKENS:
            tokens.add(part)
    for part in re.split(r"[-_\s]+", metro.name.lower()):
        if len(part) >= _MIN_TOKEN_LEN:
            tokens.add(part)
    if metro.state:
        tokens.add(metro.state.lower())
    tokens.update(_metro_alias_keywords(metro.slug))
    return tokens


def _us_subregion_hints(state: str) -> list[str]:
    st = state.upper().strip()
    hints = [st.lower()]
    full = _US_STATE_NAMES.get(st, "")
    if full:
        hints.append(full)
    return hints


def _filename_matches_us_state(fn_l: str, state: str) -> bool:
    return any(hint in fn_l for hint in _us_subregion_hints(state))


def _list_sa_filenames() -> list[str]:
    headers = {
        "User-Agent": http_user_agent(),
        "Accept": "application/vnd.github+json",
    }
    names: list[str] = []
    for page in range(1, 20):
        resp = requests.get(
            CATALOG_API,
            params={"per_page": 100, "page": page},
            headers=headers,
            timeout=60,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for item in batch:
            name = item.get("name", "")
            if "-gtfs-rt-sa-" in name and name.endswith(".json"):
                names.append(name)
    return names


def refresh_sa_index(*, force: bool = False) -> Path:
    """Refresh filename list from GitHub (fast). URL map fills lazily on lookup."""
    LIST_CACHE.parent.mkdir(parents=True, exist_ok=True)
    if (
        not force
        and LIST_CACHE.is_file()
        and (time.time() - LIST_CACHE.stat().st_mtime) < LIST_MAX_AGE_SEC
    ):
        return LIST_CACHE
    print("  MobilityData: listing GTFS-RT service-alert feeds…")
    names = _list_sa_filenames()
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "filename_count": len(names),
        "filenames": names,
    }
    LIST_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  MobilityData: cached {len(names)} SA filenames -> {LIST_CACHE}")
    return LIST_CACHE


@lru_cache(maxsize=1)
def _filename_list() -> list[str]:
    for path in (LIST_CACHE, BUNDLED_LIST):
        if path.is_file():
            doc = json.loads(path.read_text(encoding="utf-8"))
            names = list(doc.get("filenames") or [])
            if names:
                return names
    try:
        refresh_sa_index()
    except requests.HTTPError as exc:
        print(f"  MobilityData list refresh failed ({exc}); using bundled list if present")
    if LIST_CACHE.is_file():
        doc = json.loads(LIST_CACHE.read_text(encoding="utf-8"))
        return list(doc.get("filenames") or [])
    if BUNDLED_LIST.is_file():
        doc = json.loads(BUNDLED_LIST.read_text(encoding="utf-8"))
        return list(doc.get("filenames") or [])
    return []


def _load_url_cache() -> dict[str, str]:
    if not URL_CACHE.is_file():
        return {}
    return json.loads(URL_CACHE.read_text(encoding="utf-8"))


def _save_url_cache(cache: dict[str, str]) -> None:
    URL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    URL_CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def _fetch_download_url(filename: str) -> str | None:
    cache = _load_url_cache()
    if filename in cache:
        return cache[filename]
    url = CATALOG_RAW.format(filename=filename)
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": http_user_agent()},
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        doc = resp.json()
    except (requests.RequestException, json.JSONDecodeError):
        return None
    urls = doc.get("urls") or {}
    download = urls.get("direct_download") or urls.get("direct_download_url") or ""
    if not download:
        return None
    cache[filename] = str(download).strip()
    _save_url_cache(cache)
    return cache[filename]


def _rank_filenames(metro: MetroConfig) -> list[tuple[int, str]]:
    prefix = _country_prefix(metro.country)
    tokens = _metro_tokens(metro)
    alias_kws = _metro_alias_keywords(metro.slug)
    ranked: list[tuple[int, str]] = []
    for fn in _filename_list():
        if not fn.startswith(prefix + "-"):
            continue
        fn_l = fn.lower()
        score = 0
        alias_hit = False
        for tok in tokens:
            if len(tok) < _MIN_TOKEN_LEN and tok not in _SHORT_SLUG_TOKENS:
                continue
            if tok in fn_l:
                score += 12
        for kw in alias_kws:
            if kw in fn_l:
                score += 24
                alias_hit = True
        if metro.country.upper() == "US" and metro.state:
            if _filename_matches_us_state(fn_l, metro.state):
                score += 15
            elif score > 0 and not alias_hit:
                continue
        if score >= _MIN_RANK_SCORE:
            ranked.append((score, fn))
    ranked.sort(key=lambda x: (-x[0], x[1]))
    return ranked


def lookup_gtfs_rt_alerts_url(metro: MetroConfig) -> str | None:
    """Best-effort GTFS-RT alerts URL for a metro from MobilityData catalog."""
    for score, filename in _rank_filenames(metro)[:5]:
        url = _fetch_download_url(filename)
        if url:
            return url
    return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Refresh MobilityData SA filename list")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    path = refresh_sa_index(force=args.force)
    print(path)


if __name__ == "__main__":
    main()
