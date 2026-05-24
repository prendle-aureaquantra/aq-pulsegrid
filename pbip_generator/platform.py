"""Multi-metro platform CSV export and PulseGrid.pbip generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pulsegrid.config import GENERATED, list_metros
from pulsegrid.jobs.dim_metro import build_dim_metro_rows, write_dim_metro
from pbip_generator.export_gold_csv import core_export_map, optional_export_map, _merge_pulse_extensions
from pulsegrid.io.delta_writer import read_delta_table


def export_platform_csv(metro_slugs: list[str] | None = None) -> Path:
    """Union gold/silver Delta tables for all metros into platform CSV folder."""
    from pulsegrid.config import DELTA

    data_dir = GENERATED / "platform" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    if metro_slugs is None:
        metro_slugs = [m.slug for m in list_metros()]
    active = set(metro_slugs)

    snapshot_cities: set[str] = set()
    snap_path = DELTA / "gold" / "city_pulse_snapshot"
    if snap_path.exists():
        snap_df = read_delta_table(snap_path)
        if not snap_df.empty and "city" in snap_df.columns:
            snapshot_cities = set(snap_df["city"].astype(str).unique())

    write_dim_metro(active_cities=snapshot_cities or active)

    dim_rows = build_dim_metro_rows(active_cities=active)
    dim_df = pd.DataFrame(dim_rows)
    if "metro_label" in dim_df.columns:
        dim_df = dim_df.sort_values("metro_label", key=lambda s: s.str.lower())
    dim_df.to_csv(data_dir / "DimMetro.csv", index=False, encoding="utf-8-sig")

    from pulsegrid.jobs.dim_airport import build_dim_airport_rows

    ap_rows = build_dim_airport_rows()
    if ap_rows:
        pd.DataFrame(ap_rows).to_csv(
            data_dir / "DimAirport.csv", index=False, encoding="utf-8-sig"
        )

    export_map = {**core_export_map(), **optional_export_map()}
    for table, delta_path in export_map.items():
        if not delta_path.exists():
            continue
        df = read_delta_table(delta_path)
        if df.empty:
            continue
        if "city" in df.columns:
            df = df[df["city"].isin(active)]
        if df.empty:
            continue
        if table == "CityPulseSnapshot":
            frames = []
            for slug in active:
                sub = df[df["city"] == slug].copy()
                if not sub.empty:
                    sub = _merge_pulse_extensions(sub, slug)
                    frames.append(sub)
            if frames:
                df = pd.concat(frames, ignore_index=True)
        df.to_csv(data_dir / f"{table}.csv", index=False, encoding="utf-8-sig")

    from pbip_generator.studio_catalog import build_studio_catalog, write_studio_catalog_csv

    catalog: list[dict] = []
    for slug in metro_slugs:
        catalog.extend(build_studio_catalog(slug))
    if catalog:
        pd.DataFrame(catalog).to_csv(
            data_dir / "PbipStudioCatalog.csv", index=False, encoding="utf-8-sig"
        )
    else:
        write_studio_catalog_csv("chicago")
        src = GENERATED / "chicago" / "data" / "PbipStudioCatalog.csv"
        if src.is_file():
            import shutil

            shutil.copy2(src, data_dir / "PbipStudioCatalog.csv")

    return data_dir


def generate_platform_pbip(*, include_visuals: bool = False) -> Path:
    from pbip_generator.build_pbip import build_pbip

    return build_pbip(
        "platform",
        include_visuals=include_visuals,
        use_custom_theme=include_visuals,
        platform_mode=True,
    )
