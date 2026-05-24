#!/usr/bin/env python3
"""Generate per-metro transit_geo reference files and metro_transit_geo.yaml."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.metros import MetroConfig, list_metros  # noqa: E402

REF = ROOT / "datasets" / "reference"
GEO_ROOT = REF / "transit_geo"
MANIFEST = REF / "metro_transit_geo.yaml"

# slug -> list of (neighborhood, [keywords])
DISTRICTS: dict[str, list[tuple[str, list[str]]]] = {
    "nyc": [
        ("Manhattan", ["Manhattan", "Midtown", "Times Square", "Wall Street", "Harlem"]),
        ("Brooklyn", ["Brooklyn", "Williamsburg", "Bushwick"]),
        ("Queens", ["Queens", "Flushing", "JFK"]),
        ("Bronx", ["Bronx", "Yankee"]),
        ("Staten Island", ["Staten Island"]),
    ],
    "london": [
        ("Westminster", ["Westminster", "Victoria", "Waterloo"]),
        ("City of London", ["City of London", "Bank", "Liverpool Street"]),
        ("West End", ["West End", "Oxford Circus", "Piccadilly"]),
        ("Canary Wharf", ["Canary Wharf", "Docklands", "DLR"]),
        ("South London", ["South London", "Brixton", "Clapham"]),
        ("North London", ["North London", "Camden", "King's Cross"]),
        ("East London", ["East London", "Stratford", "Shoreditch"]),
    ],
    "la": [
        ("Downtown LA", ["Downtown LA", "Downtown Los Angeles", "Union Station"]),
        ("Hollywood", ["Hollywood", "Highland"]),
        ("Santa Monica", ["Santa Monica"]),
        ("Long Beach", ["Long Beach"]),
        ("San Fernando Valley", ["Valley", "North Hollywood", "Burbank"]),
    ],
    "san-francisco": [
        ("Downtown SF", ["Downtown", "Embarcadero", "Montgomery"]),
        ("Mission", ["Mission District", "Mission Bay"]),
        ("Oakland", ["Oakland", "Lake Merritt"]),
        ("Berkeley", ["Berkeley"]),
    ],
    "boston": [
        ("Downtown Boston", ["Downtown Boston", "Park Street", "Government Center"]),
        ("Cambridge", ["Cambridge", "Harvard", "MIT", "Kendall"]),
        ("Back Bay", ["Back Bay", "Copley"]),
        ("South Boston", ["South Boston", "South Station"]),
    ],
    "washington-dc": [
        ("Downtown DC", ["Downtown DC", "Metro Center", "Gallery Place"]),
        ("Arlington", ["Arlington", "Rosslyn", "Crystal City"]),
        ("Alexandria", ["Alexandria"]),
        ("Bethesda", ["Bethesda", "Silver Spring"]),
    ],
    "paris": [
        ("Paris Centre", ["Paris Centre", "Châtelet", "République"]),
        ("Left Bank", ["Rive Gauche", "Saint-Germain", "Montparnasse"]),
        ("La Défense", ["La Défense"]),
    ],
    "tokyo": [
        ("Central Tokyo", ["Shinjuku", "Shibuya", "Tokyo Station", "Marunouchi"]),
        ("North Tokyo", ["Ikebukuro", "Ueno"]),
        ("South Tokyo", ["Shinagawa", "Odaiba"]),
    ],
    "singapore": [
        ("Central Singapore", ["Orchard", "Marina Bay", "Raffles Place"]),
        ("East Singapore", ["Changi", "Tampines"]),
        ("West Singapore", ["Jurong"]),
    ],
    "hong-kong": [
        ("Hong Kong Island", ["Central", "Admiralty", "Causeway Bay"]),
        ("Kowloon", ["Kowloon", "Tsim Sha Tsui", "Mong Kok"]),
        ("New Territories", ["New Territories", "Sha Tin"]),
    ],
    "sydney": [
        ("Sydney CBD", ["Sydney CBD", "Circular Quay", "Town Hall"]),
        ("North Sydney", ["North Sydney", "Chatswood"]),
        ("Inner West", ["Inner West", "Newtown"]),
    ],
    "toronto": [
        ("Downtown Toronto", ["Union Station", "Yonge", "King Street"]),
        ("North York", ["North York", "Finch"]),
        ("Scarborough", ["Scarborough"]),
    ],
    "berlin": [
        ("Mitte", ["Mitte", "Alexanderplatz", "Brandenburg"]),
        ("Kreuzberg", ["Kreuzberg", "Friedrichshain"]),
    ],
    "amsterdam": [
        ("Centrum", ["Centrum", "Amsterdam Central", "Dam Square"]),
        ("Zuid", ["Amsterdam Zuid", "Zuidas"]),
        ("Noord", ["Amsterdam Noord", "NDSM"]),
    ],
}

# slug -> list of (line_or_route_pattern, neighborhood)
LINES: dict[str, list[tuple[str, str]]] = {
    "london": [
        ("Bakerloo", "Westminster"),
        ("Central", "City of London"),
        ("Circle", "City of London"),
        ("District", "Westminster"),
        ("DLR", "Canary Wharf"),
        ("Elizabeth", "City of London"),
        ("Hammersmith & City", "West End"),
        ("Jubilee", "Canary Wharf"),
        ("Metropolitan", "North London"),
        ("Northern", "West End"),
        ("Overground", "North London"),
        ("Piccadilly", "West End"),
        ("Victoria", "Westminster"),
        ("Waterloo & City", "City of London"),
        ("Tram", "South London"),
    ],
    "nyc": [
        ("1", "Manhattan"),
        ("2", "Manhattan"),
        ("3", "Brooklyn"),
        ("4", "Bronx"),
        ("5", "Bronx"),
        ("6", "Manhattan"),
        ("7", "Queens"),
        ("A", "Manhattan"),
        ("B", "Brooklyn"),
        ("C", "Manhattan"),
        ("D", "Brooklyn"),
        ("E", "Queens"),
        ("F", "Queens"),
        ("G", "Brooklyn"),
        ("L", "Brooklyn"),
        ("N", "Manhattan"),
        ("Q", "Manhattan"),
        ("R", "Queens"),
        ("W", "Manhattan"),
        ("S", "Manhattan"),
        ("Metro-North", "Manhattan"),
        ("LIRR", "Queens"),
    ],
    "boston": [
        ("Red Line", "Cambridge"),
        ("Orange Line", "Downtown Boston"),
        ("Blue Line", "Downtown Boston"),
        ("Green Line", "Back Bay"),
        ("Mattapan", "South Boston"),
        ("Silver Line", "Downtown Boston"),
    ],
    "la": [
        ("Red Line", "Downtown LA"),
        ("Purple Line", "Downtown LA"),
        ("Blue Line", "Long Beach"),
        ("Green Line", "South LA"),
        ("Gold Line", "Downtown LA"),
        ("Expo Line", "Santa Monica"),
        ("B Line", "Downtown LA"),
    ],
    "san-francisco": [
        ("BART", "Downtown SF"),
        ("Richmond", "Oakland"),
        ("Warm Springs", "Oakland"),
        ("Millbrae", "Downtown SF"),
    ],
    "washington-dc": [
        ("Red Line", "Downtown DC"),
        ("Blue Line", "Arlington"),
        ("Orange Line", "Arlington"),
        ("Silver Line", "Arlington"),
        ("Green Line", "Downtown DC"),
        ("Yellow Line", "Alexandria"),
    ],
    "paris": [
        ("Line 1", "Paris Centre"),
        ("Ligne 1", "Paris Centre"),
        ("RER A", "La Défense"),
        ("RER B", "Paris Centre"),
        ("Metro", "Paris Centre"),
    ],
    "tokyo": [
        ("Yamanote", "Central Tokyo"),
        ("Chuo", "Central Tokyo"),
        ("Marunouchi", "Central Tokyo"),
        ("Hibiya", "Central Tokyo"),
        ("Ginza", "Central Tokyo"),
    ],
    "singapore": [
        ("North-South", "Central Singapore"),
        ("East-West", "Central Singapore"),
        ("Circle", "Central Singapore"),
        ("Downtown", "Central Singapore"),
    ],
    "hong-kong": [
        ("Island Line", "Hong Kong Island"),
        ("Tsuen Wan", "Kowloon"),
        ("Kwun Tong", "Kowloon"),
        ("East Rail", "New Territories"),
    ],
    "sydney": [
        ("T1", "Sydney CBD"),
        ("T2", "Sydney CBD"),
        ("T3", "Sydney CBD"),
        ("T4", "North Sydney"),
        ("Metro", "Sydney CBD"),
    ],
    "toronto": [
        ("Line 1", "Downtown Toronto"),
        ("Line 2", "Downtown Toronto"),
        ("Yonge", "Downtown Toronto"),
        ("Bloor", "Downtown Toronto"),
    ],
    "berlin": [
        ("U1", "Kreuzberg"),
        ("U2", "Mitte"),
        ("U5", "Mitte"),
        ("S-Bahn", "Mitte"),
    ],
    "amsterdam": [
        ("Metro 51", "Centrum"),
        ("Metro 52", "Zuid"),
        ("Metro 53", "Noord"),
        ("Tram", "Centrum"),
    ],
    "chicago": [],  # uses legacy detailed files
}


def _synthetic_districts(metro: MetroConfig) -> list[tuple[str, list[str]]]:
    n = metro.name
    short = n.split(",")[0].strip()
    tokens = [short, metro.slug.replace("-", " ")]
    if metro.country:
        tokens.append(metro.country)
    return [
        (f"{short} — Central", tokens + ["central", "downtown", "city centre", "city center", "cbd"]),
        (f"{short} — North", [f"north {short}", f"{short} north", "northern"]),
        (f"{short} — South", [f"south {short}", f"{short} south", "southern"]),
        (f"{short} — East", [f"east {short}", f"{short} east", "eastern"]),
        (f"{short} — West", [f"west {short}", f"{short} west", "western"]),
    ]


def _write_keywords(path: Path, districts: list[tuple[str, list[str]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["neighborhood", "keyword"])
        for hood, keys in districts:
            for kw in keys:
                if kw.strip():
                    w.writerow([hood, kw.strip()])


def _write_routes(path: Path, lines: list[tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    routes = []
    for line, hood in lines:
        patterns = [line, f"{line}:"]
        if not line.startswith("#") and line.isdigit() is False:
            patterns.append(f"{line} Line")
        routes.append({"patterns": patterns, "neighborhood": hood})
    path.write_text(
        yaml.safe_dump({"routes": routes}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_empty_stations(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("stations: []\n", encoding="utf-8")


def _write_empty_streets(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(["street", "neighborhood"])


def _manifest_entry(slug: str, *, legacy: bool = False) -> dict[str, str]:
    if legacy:
        return {
            "keywords": "chicago_neighborhood_keywords.csv",
            "streets": "chicago_transit_streets.csv",
            "stations": "chicago_transit_stations.yaml",
            "routes": "chicago_transit_routes.yaml",
        }
    base = f"transit_geo/{slug}"
    return {
        "keywords": f"{base}/keywords.csv",
        "routes": f"{base}/routes.yaml",
        "stations": f"{base}/stations.yaml",
        "streets": f"{base}/streets.csv",
    }


def main() -> int:
    metros = list_metros()
    manifest: dict[str, dict[str, str]] = {}

    for metro in metros:
        slug = metro.slug
        if slug == "chicago":
            manifest[slug] = _manifest_entry(slug, legacy=True)
            continue

        out_dir = GEO_ROOT / slug
        districts = DISTRICTS.get(slug) or _synthetic_districts(metro)
        lines = LINES.get(slug, [])
        # Generic US/UK line colors for metros with transit modules
        if not lines and "transit" in metro.modules:
            lines = [
                ("Red Line", f"{metro.name.split(',')[0]} — Central"),
                ("Blue Line", f"{metro.name.split(',')[0]} — Central"),
                ("Green Line", f"{metro.name.split(',')[0]} — North"),
                ("Orange Line", f"{metro.name.split(',')[0]} — South"),
                ("Yellow Line", f"{metro.name.split(',')[0]} — East"),
            ]

        _write_keywords(out_dir / "keywords.csv", districts)
        _write_routes(out_dir / "routes.yaml", lines)
        _write_empty_stations(out_dir / "stations.yaml")
        _write_empty_streets(out_dir / "streets.csv")
        manifest[slug] = _manifest_entry(slug)

    MANIFEST.write_text(
        yaml.safe_dump(
            {"metros": manifest},
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(manifest)} metros -> {MANIFEST}")
    print(f"Per-metro files under {GEO_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
