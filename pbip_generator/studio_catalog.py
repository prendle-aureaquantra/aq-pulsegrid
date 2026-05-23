"""Export PBIP Generator Studio catalog for semantic model automation demo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pulsegrid.config import GENERATED
from pulsegrid.ml.semantic_metadata import build_semantic_metadata


def build_studio_catalog(city_slug: str) -> list[dict]:
    meta = build_semantic_metadata(city_slug)
    snapshot_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict] = []
    for table in meta.get("tables", []):
        rows.append(
            {
                "city": city_slug,
                "snapshot_at": snapshot_at,
                "table_name": table["name"],
                "source_path": table.get("source", ""),
                "column_count": len(table.get("columns", [])),
                "columns_list": ", ".join(table.get("columns", [])),
            }
        )
    for measure in meta.get("measures", []):
        rows.append(
            {
                "city": city_slug,
                "snapshot_at": snapshot_at,
                "table_name": "DAX",
                "source_path": "semantic_model",
                "column_count": 1,
                "columns_list": f"{measure['name']} = {measure['expression']}",
            }
        )
    rows.append(
        {
            "city": city_slug,
            "snapshot_at": snapshot_at,
            "table_name": "GeneratorConfig",
            "source_path": "datasets/cities",
            "column_count": 3,
            "columns_list": json.dumps(
                {
                    "city": city_slug,
                    "theme": meta.get("theme"),
                    "model": meta.get("model_name"),
                }
            ),
        }
    )
    return rows


def write_studio_catalog_csv(city_slug: str) -> Path:
    import pandas as pd

    data_dir = GENERATED / city_slug / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    rows = build_studio_catalog(city_slug)
    out = data_dir / "PbipStudioCatalog.csv"
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    return out
