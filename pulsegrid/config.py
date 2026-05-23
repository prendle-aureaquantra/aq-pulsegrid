"""City configs and paths."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent

# Delta Lake on Google Drive fails (file locking). Default local path; override with PULSEGRID_DATA_ROOT.
_default_data = Path.home() / ".local" / "aq-pulsegrid"
DATA_ROOT = Path(os.getenv("PULSEGRID_DATA_ROOT", str(_default_data)))
DATASETS = ROOT / "datasets"
BRONZE = DATASETS / "bronze"
SILVER = DATA_ROOT / "silver"
GOLD = DATA_ROOT / "gold"
DELTA = DATA_ROOT / "delta"
GENERATED = ROOT / "generated_reports"


@dataclass(frozen=True)
class CityConfig:
    slug: str
    name: str
    state: str
    noaa_area: str
    lat: float
    lon: float


CITIES: dict[str, CityConfig] = {
    "chicago": CityConfig(
        slug="chicago",
        name="Chicago",
        state="IL",
        noaa_area="IL",
        lat=41.8781,
        lon=-87.6298,
    ),
    "boston": CityConfig(
        slug="boston",
        name="Boston",
        state="MA",
        noaa_area="MA",
        lat=42.3601,
        lon=-71.0589,
    ),
}


def load_dotenv() -> None:
    try:
        from dotenv import load_dotenv as _load

        for path in (REPO_ROOT / ".env", ROOT / ".env"):
            if path.is_file():
                _load(path)
                break
    except ImportError:
        pass


def get_city(slug: str) -> CityConfig:
    key = slug.lower().strip()
    if key not in CITIES:
        raise ValueError(f"Unknown city {slug!r}. Available: {', '.join(CITIES)}")
    return CITIES[key]


def ensure_dirs() -> None:
    for d in (BRONZE, SILVER, GOLD, DELTA, GENERATED):
        d.mkdir(parents=True, exist_ok=True)


def http_user_agent() -> str:
    return os.getenv("PULSEGRID_USER_AGENT", "AQ-PulseGrid/0.1 (aureaquantra.com; demo)")


def load_city_yaml(slug: str) -> dict:
    path = ROOT / "datasets" / "cities" / f"{slug}.yaml"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
