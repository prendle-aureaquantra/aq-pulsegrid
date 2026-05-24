"""City configs, paths, and metro registry (Phase 2)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from pulsegrid.metros import MetroConfig, list_metros, load_metro

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent

_default_data = Path.home() / ".local" / "aq-pulsegrid"
DATA_ROOT = Path(os.getenv("PULSEGRID_DATA_ROOT", str(_default_data)))
DATASETS = ROOT / "datasets"
BRONZE = DATASETS / "bronze"
SILVER = DATA_ROOT / "silver"
GOLD = DATA_ROOT / "gold"
DELTA = DATA_ROOT / "delta"
GENERATED = ROOT / "generated_reports"
PLATFORM_SLUG = "platform"

_uc = os.getenv("PULSEGRID_UC_CATALOG", "").strip()
if _uc:
    DELTA = Path(f"/Volumes/{_uc}/volumes/delta")


@dataclass(frozen=True)
class CityConfig:
    """Backward-compatible view of MetroConfig for Phase 1 callers."""

    slug: str
    name: str
    state: str
    noaa_area: str
    lat: float
    lon: float


def metro_to_city(metro: MetroConfig) -> CityConfig:
    return CityConfig(
        slug=metro.slug,
        name=metro.name,
        state=metro.state,
        noaa_area=metro.noaa_area,
        lat=metro.lat,
        lon=metro.lon,
    )


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
    return metro_to_city(load_metro(slug))


def get_metro(slug: str) -> MetroConfig:
    return load_metro(slug)


def ensure_dirs() -> None:
    for d in (BRONZE, SILVER, GOLD, DELTA, GENERATED):
        d.mkdir(parents=True, exist_ok=True)
    (GENERATED / PLATFORM_SLUG / "data").mkdir(parents=True, exist_ok=True)


def http_user_agent() -> str:
    return os.getenv(
        "PULSEGRID_USER_AGENT", "AQ-PulseGrid/0.2 (aureaquantra.com; demo)"
    )


def load_city_yaml(slug: str) -> dict:
    path = ROOT / "datasets" / "cities" / f"{slug}.yaml"
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    metro = load_metro(slug)
    return {
        "slug": metro.slug,
        "name": metro.name,
        "modules": list(metro.modules),
        "pbip": {"theme": "dark", "pages": []},
    }


__all__ = [
    "BRONZE",
    "CityConfig",
    "DATA_ROOT",
    "DATASETS",
    "DELTA",
    "GENERATED",
    "GOLD",
    "PLATFORM_SLUG",
    "REPO_ROOT",
    "ROOT",
    "SILVER",
    "ensure_dirs",
    "get_city",
    "get_metro",
    "http_user_agent",
    "list_metros",
    "load_city_yaml",
    "load_dotenv",
    "load_metro",
    "metro_to_city",
]
