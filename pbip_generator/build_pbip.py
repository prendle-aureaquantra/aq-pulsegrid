"""Build Power BI Project (.pbip) for AQ PulseGrid."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from urllib.request import urlopen

from pulsegrid.config import DATA_ROOT, GENERATED, get_city
from pulsegrid.ml.semantic_metadata import build_semantic_metadata, write_semantic_metadata
from pbip_generator.export_gold_csv import export_city_csv
from pbip_generator.visuals import write_page_visuals

ROOT = Path(__file__).resolve().parent
THEME_FILE = "AureaQuantraPulse.json"
THEME_FILE_LEGACY = "PulseGridDark.json"
BASE_THEME = "CY24SU10"
THEME_URL = (
    "https://raw.githubusercontent.com/RuiRomano/pbip-demo/main/src/"
    "Report01.Report/StaticResources/SharedResources/BaseThemes/CY24SU10.json"
)
_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

TABLE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "CityPulseSnapshot": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("city_stress_index", "type number"),
        ("transit_load_score", "type number"),
        ("weather_risk_score", "type number"),
        ("precip_risk_score", "type number"),
        ("disruption_ratio_score", "type number"),
        ("active_cta_alerts", "Int64.Type"),
        ("active_noaa_alerts", "Int64.Type"),
        ("avg_precip_pct_next_periods", "type number"),
        ("reroute_count", "Int64.Type"),
        ("delay_count", "Int64.Type"),
        ("airport_flight_category", "type text"),
        ("airport_visibility_sm", "type number"),
        ("trend_avg_interest", "type number"),
        ("fred_series_count", "Int64.Type"),
    ],
    "TransitAlertSummary": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("alert_category", "type text"),
        ("alert_count", "Int64.Type"),
    ],
    "AnomalySignals": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("signal_type", "type text"),
        ("metric", "type text"),
        ("observed", "type number"),
        ("baseline", "type number"),
        ("z_score", "type number"),
        ("severity", "type text"),
        ("message", "type text"),
    ],
    "WeatherForecastPeriods": [
        ("city", "type text"),
        ("period_number", "Int64.Type"),
        ("period_name", "type text"),
        ("start_time", "type text"),
        ("end_time", "type text"),
        ("is_daytime", "type logical"),
        ("temperature_f", "Int64.Type"),
        ("precip_pct", "Int64.Type"),
        ("short_forecast", "type text"),
        ("wind_speed", "type text"),
        ("wind_direction", "type text"),
        ("ingested_at", "type text"),
        ("bronze_file", "type text"),
    ],
    "AirportOpsSnapshot": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("station", "type text"),
        ("flight_category", "type text"),
        ("visibility_sm", "type number"),
        ("wind_speed_kt", "type number"),
        ("temperature_c", "type number"),
        ("airport_ops_stress", "type number"),
    ],
    "FredMacroSnapshot": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("series_id", "type text"),
        ("series_label", "type text"),
        ("latest_value", "type number"),
        ("observation_date", "type text"),
    ],
    "TrendInterestSummary": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("keyword", "type text"),
        ("avg_interest", "type number"),
        ("max_interest", "Int64.Type"),
        ("observation_count", "Int64.Type"),
    ],
    "HexPulseGrid": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("hex_id", "type text"),
        ("neighborhood", "type text"),
        ("alert_count", "Int64.Type"),
        ("reroute_count", "Int64.Type"),
        ("delay_count", "Int64.Type"),
    ],
    "EventHeatmap": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("hex_id", "type text"),
        ("neighborhood", "type text"),
        ("event_category", "type text"),
        ("event_count", "Int64.Type"),
    ],
    "StreamingTelemetry": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("source", "type text"),
        ("batch_count", "Int64.Type"),
        ("last_ingested_at", "type text"),
    ],
    "OsmAmenitySummary": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("amenity", "type text"),
        ("poi_count", "Int64.Type"),
    ],
    "PbipStudioCatalog": [
        ("city", "type text"),
        ("snapshot_at", "type text"),
        ("table_name", "type text"),
        ("source_path", "type text"),
        ("column_count", "Int64.Type"),
        ("columns_list", "type text"),
    ],
}

REQUIRED_TABLES = [
    "CityPulseSnapshot",
    "TransitAlertSummary",
    "AnomalySignals",
    "WeatherForecastPeriods",
]

OPTIONAL_TABLES = [
    "AirportOpsSnapshot",
    "FredMacroSnapshot",
    "TrendInterestSummary",
    "HexPulseGrid",
    "EventHeatmap",
    "StreamingTelemetry",
    "OsmAmenitySummary",
    "PbipStudioCatalog",
]

TABLE_ORDER = REQUIRED_TABLES + OPTIONAL_TABLES

REPORT_PAGES: list[tuple[str, str]] = [
    ("page.live-pulse", "Live City Pulse"),
    ("page.transit", "Transit & Mobility"),
    ("page.weather", "Weather Impact Analysis"),
    ("page.airport", "Airport Operations"),
    ("page.events", "Event Heatmaps"),
    ("page.ai-signals", "AI Signal Detection"),
    ("page.streaming", "Streaming Monitor"),
    ("page.macro", "Macro & Trends"),
    ("page.studio", "PBIP Generator Studio"),
]


def _lid(s: str) -> str:
    return str(uuid.uuid5(_NS, f"aq.pulsegrid.{s}"))


def _lid_short(s: str, n: int = 20) -> str:
    return uuid.uuid5(_NS, s).hex[:n]


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _m_transform_pairs(cols: list[tuple[str, str]]) -> str:
    return ",\n\t\t".join(f'{{"{name}", {pq}}}' for name, pq in cols)


def _csv_absolute(csv_path: Path) -> str:
    """Power BI File.Contents requires an absolute path (forward slashes on Windows)."""
    return csv_path.resolve().as_posix()


def _partition_m(table: str, csv_path: Path) -> str:
    cols = TABLE_COLUMNS[table]
    pairs = _m_transform_pairs(cols)
    csv_m = _csv_absolute(csv_path).replace('"', '""')
    return f"""let
	Source = Csv.Document(
		File.Contents("{csv_m}"),
		[Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
	),
	#"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
	#"Changed Column Types" = Table.TransformColumnTypes(
		#"Promoted Headers",
		{{
		{pairs}
		}}
	)
in
	#"Changed Column Types"
"""


def _table_tmdl(table: str, csv_path: Path) -> str:
    cols = TABLE_COLUMNS[table]
    lines = [f"table {table}", f"\tlineageTag: {_lid(f'table.{table}')}", ""]
    for col_name, pq in cols:
        if pq == "Int64.Type":
            dt = "int64"
        elif pq == "type number":
            dt = "decimal"
        elif pq == "type logical":
            dt = "boolean"
        else:
            dt = "string"
        summarize = "none" if pq in ("type text", "type logical") or col_name.endswith("_at") else "sum"
        if table == "CityPulseSnapshot" and col_name.endswith("_score"):
            summarize = "none"
        if table == "CityPulseSnapshot" and col_name in (
            "airport_flight_category",
            "airport_visibility_sm",
            "trend_avg_interest",
            "fred_series_count",
            "city_stress_index",
            "avg_precip_pct_next_periods",
        ):
            summarize = "none"
        if col_name in ("city_stress_index", "z_score", "baseline", "observed"):
            summarize = "none"
        lines.extend(
            [
                f"\tcolumn {col_name}",
                f"\t\tdataType: {dt}",
                f"\t\tlineageTag: {_lid(f'{table}.{col_name}')}",
                f"\t\tsummarizeBy: {summarize}",
                f"\t\tsourceColumn: {col_name}",
                "\t\tannotation SummarizationSetBy = Automatic",
                "",
            ]
        )
    if table == "CityPulseSnapshot":
        measures = [
            ("City Stress Index", "AVERAGE(CityPulseSnapshot[city_stress_index])", "0.0"),
            ("Active CTA Alerts", "SUM(CityPulseSnapshot[active_cta_alerts])", "#,0"),
            ("Active NOAA Alerts", "SUM(CityPulseSnapshot[active_noaa_alerts])", "#,0"),
            ("Avg Precip %", "AVERAGE(CityPulseSnapshot[avg_precip_pct_next_periods])", "0.0"),
            ("Transit Load Score", "AVERAGE(CityPulseSnapshot[transit_load_score])", "0.0"),
            ("Weather Risk Score", "AVERAGE(CityPulseSnapshot[weather_risk_score])", "0.0"),
            ("Trend Avg Interest", "AVERAGE(CityPulseSnapshot[trend_avg_interest])", "0.0"),
            ("Airport Visibility (sm)", "AVERAGE(CityPulseSnapshot[airport_visibility_sm])", "0.0"),
        ]
        for mname, expr, fmt in measures:
            lines.append(f"\tmeasure '{mname}' = {expr}")
            lines.append(f"\t\tformatString: {fmt}")
            lines.append(f"\t\tlineageTag: {_lid(f'measure.{mname}')}")
            lines.append("")
    if table == "AnomalySignals":
        lines.append("\tmeasure 'Anomaly Count' = COUNTROWS(AnomalySignals)")
        lines.append("\t\tformatString: #,0")
        lines.append(f"\t\tlineageTag: {_lid('measure.Anomaly Count')}")
        lines.append("")
    if table == "AirportOpsSnapshot":
        lines.append("\tmeasure 'ORD Ops Stress' = AVERAGE(AirportOpsSnapshot[airport_ops_stress])")
        lines.append("\t\tformatString: 0.0")
        lines.append(f"\t\tlineageTag: {_lid('measure.ORD Ops Stress')}")
        lines.append("")
    if table == "HexPulseGrid":
        lines.append("\tmeasure 'Hex Alert Total' = SUM(HexPulseGrid[alert_count])")
        lines.append("\t\tformatString: #,0")
        lines.append(f"\t\tlineageTag: {_lid('measure.Hex Alert Total')}")
        lines.append("")
    if table == "StreamingTelemetry":
        lines.append("\tmeasure 'Total Ingest Batches' = SUM(StreamingTelemetry[batch_count])")
        lines.append("\t\tformatString: #,0")
        lines.append(f"\t\tlineageTag: {_lid('measure.Total Ingest Batches')}")
        lines.append("")
    if table == "PbipStudioCatalog":
        lines.append("\tmeasure 'Catalog Rows' = COUNTROWS(PbipStudioCatalog)")
        lines.append("\t\tformatString: #,0")
        lines.append(f"\t\tlineageTag: {_lid('measure.Catalog Rows')}")
        lines.append("")
    part_name = f"{table}-{_lid(f'partition.{table}')}"
    m_body = _partition_m(table, csv_path).rstrip("\n")
    lines.append(f"\tpartition {part_name} = m")
    lines.append("\t\tmode: import")
    lines.append("\t\tsource =")
    for ln in m_body.split("\n"):
        lines.append(f"\t\t\t{ln}")
    lines.append("")
    lines.append("\tannotation PBI_ResultType = Table")
    lines.append("")
    return "\n".join(lines) + "\n"


def _write_semantic_tables(
    model_root: Path,
    data_dir: Path,
    project: str,
    meta: dict,
) -> None:
    sm_def = model_root / "definition"
    sm_def.mkdir(parents=True, exist_ok=True)
    (sm_def / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1601\n\n", encoding="utf-8")
    model_lines = [
        f"model {project}",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "",
    ]
    for t in TABLE_ORDER:
        if (data_dir / f"{t}.csv").exists():
            model_lines.append(f"ref table {t}")
    model_lines.extend(["", "ref cultureInfo en-US", ""])
    (sm_def / "model.tmdl").write_text("\n".join(model_lines) + "\n", encoding="utf-8")
    (sm_def / "cultures").mkdir(exist_ok=True)
    (sm_def / "cultures" / "en-US.tmdl").write_text("cultureInfo en-US\n\n", encoding="utf-8")
    (sm_def / "tables").mkdir(parents=True, exist_ok=True)
    for t in TABLE_ORDER:
        csv = data_dir / f"{t}.csv"
        if csv.exists():
            (sm_def / "tables" / f"{t}.tmdl").write_text(
                _table_tmdl(t, csv), encoding="utf-8"
            )
    (sm_def / "relationships.tmdl").write_text("", encoding="utf-8")
    (model_root / "definition.pbism").write_text(
        json.dumps({"version": "4.1", "settings": {"qnaEnabled": True}}, indent=2) + "\n",
        encoding="utf-8",
    )
    dax_dir = model_root.parent / "dax"
    dax_dir.mkdir(parents=True, exist_ok=True)
    (dax_dir / "measures.txt").write_text(
        "\n".join(f"{m['name']} = {m['expression']}" for m in meta.get("measures", [])) + "\n",
        encoding="utf-8",
    )


def _mirror_pbip(out_root: Path, city_slug: str, project: str) -> Path | None:
    """Copy PBIP bundle to local disk (Google Drive breaks Power BI file locks)."""
    mirror = DATA_ROOT / "reports" / city_slug
    try:
        if mirror.resolve() == out_root.resolve():
            return None
    except OSError:
        pass
    if mirror.exists():
        shutil.rmtree(mirror)
    shutil.copytree(out_root, mirror)
    return mirror / f"{project}.pbip"


def _validate_report(report_root: Path, page_ids: list[str], *, require_visuals: bool) -> None:
    pages_root = report_root / "definition" / "pages"
    missing_pages = [pid for pid in page_ids if not (pages_root / pid / "page.json").is_file()]
    if missing_pages:
        raise RuntimeError(f"PBIP build incomplete — missing page.json for: {missing_pages}")
    visuals = list(pages_root.glob("*/visuals/*/visual.json"))
    if require_visuals and not visuals:
        raise RuntimeError("PBIP build incomplete — no visual.json files written")


def _download_base_theme(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    with urlopen(THEME_URL, timeout=60) as r:
        dest.write_bytes(r.read())


def build_pbip(city_slug: str, *, include_visuals: bool = False, use_custom_theme: bool = False) -> Path:
    city = get_city(city_slug)
    meta = build_semantic_metadata(city_slug)
    project = meta["model_name"]
    write_semantic_metadata(city_slug)

    data_dir = export_city_csv(city_slug)
    available_tables = {t for t in TABLE_ORDER if (data_dir / f"{t}.csv").exists()}
    missing = [t for t in REQUIRED_TABLES if t not in available_tables]
    if missing:
        raise FileNotFoundError(
            f"Missing CSV exports for {missing}. Run ML/transform pipeline first: "
            f"python generate_city.py --city {city_slug} --transform-only && "
            f"python generate_city.py --city {city_slug} --ml-only"
        )

    out_root = GENERATED / city_slug
    report_name = f"{project}.Report"
    model_name = f"{project}.SemanticModel"
    pbip_path = out_root / f"{project}.pbip"
    report_root = out_root / report_name
    model_root = out_root / model_name

    _write_json(
        pbip_path,
        {
            "version": "1.0",
            "artifacts": [{"report": {"path": report_name}}],
            "settings": {"enableAutoRecovery": True},
        },
    )

    _write_json(
        report_root / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": project},
            "config": {"version": "2.0", "logicalId": _lid("report.logical")},
        },
    )
    _write_json(
        model_root / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "SemanticModel", "displayName": project},
            "config": {"version": "2.0", "logicalId": _lid("model.logical")},
        },
    )
    _write_json(
        report_root / "definition.pbir",
        {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{model_name}"}}},
    )

    base_theme_path = (
        report_root / "StaticResources" / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json"
    )
    _download_base_theme(base_theme_path)
    reg_dir = report_root / "StaticResources" / "RegisteredResources"
    reg_dir.mkdir(parents=True, exist_ok=True)
    if use_custom_theme:
        theme_src = ROOT / "themes" / THEME_FILE
        if not theme_src.is_file():
            theme_src = ROOT / "themes" / THEME_FILE_LEGACY
        shutil.copy2(theme_src, reg_dir / THEME_FILE)

    def_dir = report_root / "definition"
    _write_json(
        def_dir / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )
    theme_collection: dict[str, object] = {
        "baseTheme": {
            "name": BASE_THEME,
            "reportVersionAtImport": "5.61",
            "type": "SharedResources",
        },
    }
    resource_packages: list[dict[str, object]] = [
        {
            "name": "SharedResources",
            "type": "SharedResources",
            "items": [
                {
                    "name": BASE_THEME,
                    "path": f"BaseThemes/{BASE_THEME}.json",
                    "type": "BaseTheme",
                }
            ],
        },
    ]
    if use_custom_theme:
        theme_collection["customTheme"] = {
            "name": THEME_FILE,
            "reportVersionAtImport": "5.61",
            "type": "RegisteredResources",
        }
        resource_packages.append(
            {
                "name": "RegisteredResources",
                "type": "RegisteredResources",
                "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": "CustomTheme"}],
            }
        )
    _write_json(
        def_dir / "report.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.3.0/schema.json",
            "layoutOptimization": "None",
            "themeCollection": theme_collection,
            "resourcePackages": resource_packages,
            "settings": {
                "useStylableVisualContainerHeader": True,
                "exportDataMode": "AllowSummarizedAndUnderlying",
                "defaultDrillFilterOtherVisuals": True,
            },
        },
    )

    pages_root = def_dir / "pages"
    if pages_root.exists():
        shutil.rmtree(pages_root)
    pages_root.mkdir(parents=True)
    page_entries = [(seed, _lid_short(seed, 20), title) for seed, title in REPORT_PAGES]
    page_order = [pid for _, pid, _ in page_entries]
    for seed, pid, display_name in page_entries:
        pdir = pages_root / pid
        pdir.mkdir(parents=True)
        _write_json(
            pdir / "page.json",
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.4.0/schema.json",
                "name": pid,
                "displayName": display_name,
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
            },
        )
        if include_visuals:
            write_page_visuals(pdir, seed, available_tables=available_tables)
    _write_json(
        pages_root / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": page_order,
            "activePageName": page_order[0],
        },
    )
    _write_json(
        def_dir / "bookmarks" / "bookmarks.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/bookmarksMetadata/1.0.0/schema.json",
            "items": [],
        },
    )

    _validate_report(report_root, page_order, require_visuals=include_visuals)
    local_pbip = _mirror_pbip(out_root, city_slug, project)
    bundle_root = local_pbip.parent if local_pbip else out_root
    bundle_data = bundle_root / "data"
    bundle_model = bundle_root / model_name
    _write_semantic_tables(bundle_model, bundle_data, project, meta)
    if bundle_root != out_root:
        _write_semantic_tables(model_root, data_dir, project, meta)
    open_path = local_pbip or pbip_path
    (out_root / "OPEN_IN_POWER_BI.txt").write_text(
        "\n".join(
            [
                "Fabric browser error 'Failed to load the report'? Follow this exactly:",
                "",
                "A) CLEAN UP FABRIC (one time if you already published a broken report)",
                "   1. app.powerbi.com -> your workspace",
                "   2. Delete the ChicagoPulse REPORT only (keep the semantic model/dataset)",
                "",
                "B) DESKTOP (required — .pbip never opens in the browser directly)",
                f"   1. Open: {open_path}",
                "   2. Click Load on all tables when prompted",
                "   3. Confirm report pages render in Desktop",
                "   4. File -> Save",
                "   5. File -> Publish -> same workspace as step A",
                "",
                "C) BROWSER",
                "   Open the newly published report from the workspace list (not an old link).",
                "",
                "If browser still fails: File -> Save as -> ChicagoPulse.pbix, then",
                "upload the .pbix to the workspace (Upload -> Browse).",
                "",
                "Optional programmatic visuals (Desktop only):",
                f"   python generate_city.py --city {city_slug} --pbip-only --with-visuals",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return open_path


def main() -> int:
    path = build_pbip("chicago")
    print(f"Wrote PBIP: {path}")
    print(f"Open in Power BI Desktop: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
