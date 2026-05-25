from __future__ import annotations

import csv
from pathlib import Path

from tools.validate_platform_export import validate_platform_data


def test_validate_platform_data_ok(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    dim = data / "DimMetro.csv"
    with dim.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["city"])
        w.writeheader()
        for i in range(71):
            w.writerow({"city": f"metro{i}"})
    snap = data / "CityPulseSnapshot.csv"
    with snap.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["city"])
        w.writeheader()
        for i in range(71):
            w.writerow({"city": f"metro{i}"})
    assert validate_platform_data(data, min_metros=70, min_snapshots=70) == []


def test_validate_platform_data_fails_low_count(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    dim = data / "DimMetro.csv"
    with dim.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["city"])
        w.writeheader()
        w.writerow({"city": "chicago"})
    errs = validate_platform_data(data, min_metros=70)
    assert errs
