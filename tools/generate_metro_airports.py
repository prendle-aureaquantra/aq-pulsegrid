#!/usr/bin/env python3
"""Generate datasets/reference/metro_airports.yaml from catalog + registry."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.metros import list_metros

CATALOG = ROOT / "datasets" / "reference" / "metro_airports_catalog.yaml"
OUT = ROOT / "datasets" / "reference" / "metro_airports.yaml"

# Fallback primary ICAO when catalog has no entry (tier-2 / future metros)
FALLBACK_PRIMARY: dict[str, tuple[str, str]] = {
    "athens": ("LGAV", "Athens International"),
    "atlanta": ("KATL", "Hartsfield-Jackson"),
    "auckland": ("NZAA", "Auckland"),
    "bangalore": ("VOBL", "Kempegowda"),
    "bangkok": ("VTBS", "Suvarnabhumi"),
    "barcelona": ("LEBL", "Barcelona-El Prat"),
    "beijing": ("ZBAA", "Beijing Capital"),
    "berlin": ("EDDB", "Berlin Brandenburg"),
    "bogota": ("SKBO", "El Dorado"),
    "boston": ("KBOS", "Logan International"),
    "brussels": ("EBBR", "Brussels"),
    "budapest": ("LHBP", "Budapest"),
    "buenos-aires": ("SAEZ", "Ezeiza"),
    "cairo": ("HECA", "Cairo International"),
    "chicago": ("KORD", "O'Hare International"),
    "copenhagen": ("EKCH", "Copenhagen"),
    "dallas": ("KDFW", "Dallas/Fort Worth"),
    "delhi": ("VIDP", "Indira Gandhi"),
    "denver": ("KDEN", "Denver International"),
    "doha": ("OTHH", "Hamad International"),
    "dubai": ("OMDB", "Dubai International"),
    "dublin": ("EIDW", "Dublin"),
    "helsinki": ("EFHK", "Helsinki-Vantaa"),
    "hong-kong": ("VHHH", "Hong Kong International"),
    "houston": ("KIAH", "George Bush Intercontinental"),
    "istanbul": ("LTFM", "Istanbul Airport"),
    "jakarta": ("WIII", "Soekarno-Hatta"),
    "johannesburg": ("FAOR", "O.R. Tambo"),
    "kuala-lumpur": ("WMKK", "Kuala Lumpur International"),
    "lagos": ("DNMM", "Murtala Muhammed"),
    "lima": ("SPJC", "Jorge Chávez"),
    "lisbon": ("LPPT", "Lisbon"),
    "london": ("EGLL", "Heathrow"),
    "la": ("KLAX", "Los Angeles International"),
    "madrid": ("LEMD", "Madrid-Barajas"),
    "manila": ("RPLL", "Ninoy Aquino"),
    "melbourne": ("YMML", "Melbourne Tullamarine"),
    "mexico-city": ("MMMX", "Mexico City International"),
    "miami": ("KMIA", "Miami International"),
    "milan": ("LIMC", "Milan Malpensa"),
    "montreal": ("CYUL", "Montréal-Trudeau"),
    "moscow": ("UUEE", "Sheremetyevo"),
    "mumbai": ("VABB", "Mumbai"),
    "munich": ("EDDM", "Munich"),
    "nairobi": ("HKJK", "Jomo Kenyatta"),
    "nyc": ("KJFK", "JFK"),
    "oslo": ("ENGM", "Oslo Gardermoen"),
    "paris": ("LFPG", "Paris Charles de Gaulle"),
    "philadelphia": ("KPHL", "Philadelphia International"),
    "phoenix": ("KPHX", "Phoenix Sky Harbor"),
    "prague": ("LKPR", "Prague"),
    "riyadh": ("OERK", "King Khalid"),
    "rome": ("LIRF", "Rome Fiumicino"),
    "san-francisco": ("KSFO", "San Francisco International"),
    "seattle": ("KSEA", "Seattle-Tacoma"),
    "seoul": ("RKSI", "Incheon"),
    "shanghai": ("ZSPD", "Shanghai Pudong"),
    "singapore": ("WSSS", "Changi"),
    "stockholm": ("ESSA", "Stockholm Arlanda"),
    "sydney": ("YSSY", "Sydney Kingsford Smith"),
    "sao-paulo": ("SBGR", "São Paulo/Guarulhos"),
    "taipei": ("RCTP", "Taiwan Taoyuan"),
    "tel-aviv": ("LLBG", "Ben Gurion"),
    "tokyo": ("RJTT", "Haneda"),
    "toronto": ("CYYZ", "Toronto Pearson"),
    "vancouver": ("CYVR", "Vancouver International"),
    "vienna": ("LOWW", "Vienna"),
    "warsaw": ("EPWA", "Warsaw Chopin"),
    "washington-dc": ("KDCA", "Reagan National"),
    "zurich": ("LSZH", "Zurich"),
    "amsterdam": ("EHAM", "Amsterdam Schiphol"),
}


def _normalize_station(entry: dict) -> dict[str, str] | None:
    icao = str(entry.get("icao", "")).strip().upper()
    name = str(entry.get("name", "")).strip()
    if not icao:
        return None
    return {"icao": icao, "name": name or icao}


def _load_catalog() -> dict[str, list[dict[str, str]]]:
    if not CATALOG.is_file():
        return {}
    data = yaml.safe_load(CATALOG.read_text(encoding="utf-8")) or {}
    raw = data.get("metros") or {}
    out: dict[str, list[dict[str, str]]] = {}
    for slug, stations in raw.items():
        if not isinstance(stations, list):
            continue
        rows: list[dict[str, str]] = []
        for item in stations:
            if not isinstance(item, dict):
                continue
            norm = _normalize_station(item)
            if norm:
                rows.append(norm)
        if rows:
            out[str(slug)] = rows
    return out


def _merge_stations(
    *sources: list[dict[str, str]],
) -> list[dict[str, str]]:
    seen: set[str] = set()
    merged: list[dict[str, str]] = []
    for source in sources:
        for entry in source:
            code = entry["icao"]
            if code in seen:
                continue
            seen.add(code)
            merged.append(entry)
    return merged


def main() -> int:
    catalog = _load_catalog()
    metros_out: dict[str, dict] = {}
    stats: list[tuple[str, int]] = []

    for metro in list_metros():
        slug = metro.slug
        from_registry = [
            {"icao": str(c).strip().upper(), "name": str(c).strip().upper()}
            for c in metro.airports
            if str(c).strip()
        ]
        from_catalog = catalog.get(slug, [])
        if not from_catalog and slug in FALLBACK_PRIMARY:
            icao, name = FALLBACK_PRIMARY[slug]
            from_catalog = [{"icao": icao, "name": name}]

        stations = _merge_stations(from_catalog, from_registry)
        if not stations:
            continue
        metros_out[slug] = {"stations": stations}
        stats.append((slug, len(stations)))

    OUT.write_text(
        yaml.safe_dump({"metros": metros_out}, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    total_stations = sum(n for _, n in stats)
    print(f"Wrote {len(metros_out)} metros, {total_stations} stations -> {OUT}")
    chicago = metros_out.get("chicago", {}).get("stations", [])
    print(f"  chicago ({len(chicago)}):", ", ".join(s["icao"] for s in chicago))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
