#!/usr/bin/env python3
"""
Wire PulseGrid Fabric embed using Azure AD service principal (no Desktop required).

1. Create or reuse workspace (POWERBI_WORKSPACE or AQ PulseGrid)
2. Import platform CSVs as Excel -> dataset + report in Power BI Service
3. Publish to web -> POWERBI_PULSEGRID_EMBED_URL
4. Optionally redeploy Lightsail + sync WordPress /pulsegrid/
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import requests

from powerbi_auth import token_delegated

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
POWER_BI_API = "https://api.powerbi.com/v1.0/myorg"
DEFAULT_WORKSPACE = "AQ PulseGrid"
# Shell report cloned when Excel import creates dataset-only (no report via API).
DEFAULT_CLONE_WORKSPACE = "Produce Ops - amc_marano"
DEFAULT_CLONE_REPORT = "AMC_ProduceOps"
PLATFORM_DATA = ROOT / "generated_reports" / "platform" / "data"
IMPORT_SHEETS = (
    "DimMetro.csv",
    "CityPulseSnapshot.csv",
    "AnomalySignals.csv",
    "TransitAlertSummary.csv",
)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in (REPO_ROOT / ".env", ROOT / ".env"):
        if p.is_file():
            load_dotenv(p)


def _import_publish_module():
    import importlib.util

    path = ROOT / "tools" / "publish_pulsegrid_fabric.py"
    spec = importlib.util.spec_from_file_location("publish_pulsegrid_fabric", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _find_dataset(token: str, workspace_id: str, pub, name_hint: str = "PulseGrid") -> str | None:
    r = requests.get(
        f"{POWER_BI_API}/groups/{workspace_id}/datasets",
        headers=pub._headers(token),
        timeout=60,
    )
    if r.status_code != 200:
        return None
    for ds in r.json().get("value", []):
        n = (ds.get("name") or "").lower()
        if name_hint.lower() in n:
            return ds["id"]
    return None


def _find_report(token: str, workspace_id: str, pub, name: str = "PulseGrid") -> str | None:
    r = requests.get(
        f"{POWER_BI_API}/groups/{workspace_id}/reports",
        headers=pub._headers(token),
        timeout=60,
    )
    if r.status_code != 200:
        return None
    for rep in r.json().get("value", []):
        if (rep.get("name") or "").strip().lower() == name.lower():
            return rep["id"]
    return None


def _clone_report_shell(
    token: str, target_workspace_id: str, dataset_id: str, pub
) -> str:
    src_ws = (
        os.getenv("POWERBI_CLONE_SOURCE_WORKSPACE", DEFAULT_CLONE_WORKSPACE) or ""
    ).strip()
    src_name = (
        os.getenv("POWERBI_CLONE_SOURCE_REPORT", DEFAULT_CLONE_REPORT) or ""
    ).strip()
    workspaces = pub._list_workspaces(token)
    src = next(
        (w for w in workspaces if (w.get("name") or "").lower() == src_ws.lower()),
        None,
    )
    if not src:
        raise RuntimeError(f"Clone source workspace not found: {src_ws}")
    r = requests.get(
        f"{POWER_BI_API}/groups/{src['id']}/reports",
        headers=pub._headers(token),
        timeout=60,
    )
    r.raise_for_status()
    src_rep = next(
        (
            x
            for x in r.json().get("value", [])
            if (x.get("name") or "").strip().lower() == src_name.lower()
        ),
        None,
    )
    if not src_rep:
        raise RuntimeError(f"Clone source report not found: {src_name}")
    body = {
        "name": "PulseGrid",
        "targetWorkspaceId": target_workspace_id,
        "targetModelId": dataset_id,
    }
    cr = requests.post(
        f"{POWER_BI_API}/groups/{src['id']}/reports/{src_rep['id']}/Clone",
        headers=pub._headers(token),
        json=body,
        timeout=120,
    )
    if cr.status_code not in (200, 201):
        raise RuntimeError(f"Clone report failed: {cr.status_code} {cr.text[:400]}")
    return cr.json()["id"]


def _ensure_dataset(token: str, workspace_id: str, pub) -> str:
    existing = _find_dataset(token, workspace_id, pub)
    if existing:
        print(f"Using existing dataset: {existing[:8]}…")
        return existing
    with tempfile.TemporaryDirectory() as tmp:
        xlsx = Path(tmp) / "PulseGrid_platform.xlsx"
        print("Building Excel from platform CSVs…")
        _build_platform_xlsx(xlsx)
        print(f"Importing {xlsx.name} (dataset only)…")
        try:
            ds_id, _ = _import_excel(token, workspace_id, xlsx, pub)
            return ds_id
        except RuntimeError as exc:
            if "ExcelWorkbookHasNoData" not in str(exc) and "no report" not in str(exc).lower():
                raise
            print(f"Excel import issue ({exc}); using push dataset API…")
            ds_id, _ = _push_dataset(token, workspace_id, pub)
            return ds_id


def _ensure_report(token: str, workspace_id: str, dataset_id: str, pub) -> str:
    existing = _find_report(token, workspace_id, pub)
    if existing:
        print(f"Using existing report: {existing[:8]}…")
        return existing
    print(
        f"Cloning shell report '{os.getenv('POWERBI_CLONE_SOURCE_REPORT', DEFAULT_CLONE_REPORT)}' "
        f"→ PulseGrid (dataset {dataset_id[:8]}…)…"
    )
    return _clone_report_shell(token, workspace_id, dataset_id, pub)


def _ensure_workspace(token: str, name: str, pub) -> str:
    for ws in pub._list_workspaces(token):
        if (ws.get("name") or "").lower() == name.lower():
            wid = ws["id"]
            _ensure_workspace_admin(token, wid, pub)
            _assign_workspace_capacity(token, wid, pub)
            return wid
    r = requests.post(
        f"{POWER_BI_API}/groups",
        headers=pub._headers(token),
        json={"name": name},
        timeout=60,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Create workspace failed: {r.status_code} {r.text[:300]}")
    wid = r.json()["id"]
    _ensure_workspace_admin(token, wid, pub)
    _assign_workspace_capacity(token, wid, pub)
    return wid


def _assign_workspace_capacity(token: str, workspace_id: str, pub) -> None:
    """Optional: assign workspace to a Fabric/Premium capacity (POWERBI_CAPACITY_ID).

    Do not auto-assign Premium Per User — Desktop publishers need a PPU license on
    that workspace. Leave shared (default) so Power BI Pro matches Produce Ops workspaces.
    """
    cap_id = (os.getenv("POWERBI_CAPACITY_ID") or "").strip()
    if not cap_id:
        return
    g = requests.get(
        f"{POWER_BI_API}/groups/{workspace_id}",
        headers=pub._headers(token),
        timeout=60,
    )
    if g.status_code == 200 and g.json().get("capacityId") == cap_id:
        return
    ar = requests.post(
        f"{POWER_BI_API}/groups/{workspace_id}/AssignToCapacity",
        headers=pub._headers(token),
        json={"capacityId": cap_id},
        timeout=60,
    )
    if ar.status_code not in (200, 202):
        print(
            f"Note: capacity assign failed ({ar.status_code}) — "
            "assign workspace to Premium Per User in Fabric admin if Desktop publish fails.",
            file=sys.stderr,
        )
        return
    for _ in range(20):
        time.sleep(2)
        st = requests.get(
            f"{POWER_BI_API}/groups/{workspace_id}/CapacityAssignmentStatus",
            headers=pub._headers(token),
            timeout=60,
        )
        if st.status_code == 200 and st.json().get("status") in (
            "CompletedSuccessfully",
            "AssignmentFailed",
        ):
            break
    print(f"Workspace assigned to capacity {cap_id[:8]}…")


def _ensure_workspace_admin(token: str, workspace_id: str, pub) -> None:
    """Grant a human admin so Power BI Desktop publish lists the workspace."""
    import re

    # Must match the account signed into Power BI Desktop (not necessarily BOOKINGS_URL).
    email = (os.getenv("POWERBI_WORKSPACE_ADMIN_EMAIL") or "").strip()
    if not email:
        m = re.search(
            r"[\w.+-]+@[\w.-]+\.\w+",
            os.getenv("BOOKINGS_URL", ""),
        )
        if m:
            email = m.group(0)
            print(
                f"Note: using BOOKINGS_URL email {email} — set POWERBI_WORKSPACE_ADMIN_EMAIL "
                "if Desktop uses a different Microsoft account.",
                file=sys.stderr,
            )
    if not email:
        return
    users = requests.get(
        f"{POWER_BI_API}/groups/{workspace_id}/users",
        headers=pub._headers(token),
        timeout=60,
    )
    if users.status_code == 200:
        for u in users.json().get("value", []):
            if (u.get("emailAddress") or "").lower() == email.lower():
                return
            if (u.get("identifier") or "").lower() == email.lower():
                return
    body = {
        "identifier": email,
        "groupUserAccessRight": "Admin",
        "principalType": "User",
    }
    r = requests.post(
        f"{POWER_BI_API}/groups/{workspace_id}/users",
        headers=pub._headers(token),
        json=body,
        timeout=60,
    )
    if r.status_code in (200, 201):
        print(f"Added workspace admin: {email}")
    elif r.status_code != 409:
        print(f"Note: could not add workspace admin ({r.status_code})", file=sys.stderr)


def _build_platform_xlsx(out_path: Path) -> None:
    import pandas as pd
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.table import Table, TableStyleInfo

    if not PLATFORM_DATA.is_dir():
        raise FileNotFoundError(
            f"Missing {PLATFORM_DATA} — run: python generate_city.py --all-metros --platform-csv-only"
        )
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        wrote = 0
        for csv_name in IMPORT_SHEETS:
            csv_path = PLATFORM_DATA / csv_name
            if not csv_path.is_file():
                continue
            sheet = csv_name.replace(".csv", "")[:31]
            df = pd.read_csv(csv_path, encoding="utf-8-sig")
            if df.empty:
                continue
            df.to_excel(writer, sheet_name=sheet, index=False)
            ws = writer.sheets[sheet]
            ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"
            table_name = "".join(ch for ch in sheet if ch.isalnum())[:20] or "PulseGrid"
            tab = Table(displayName=f"{table_name}{wrote}", ref=ref)
            tab.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium2",
                showFirstColumn=False,
                showLastColumn=False,
                showRowStripes=True,
                showColumnStripes=False,
            )
            ws.add_table(tab)
            wrote += 1
        if wrote == 0:
            raise FileNotFoundError(f"No CSV files in {PLATFORM_DATA}")


def _import_excel(token: str, workspace_id: str, xlsx_path: Path, pub) -> tuple[str, str]:
    """Return (dataset_id, report_id)."""
    display_name = xlsx_path.name
    url = (
        f"{POWER_BI_API}/groups/{workspace_id}/imports"
        f"?datasetDisplayName={requests.utils.quote(display_name)}"
        "&nameConflict=Overwrite"
    )
    headers = {"Authorization": f"Bearer {token}"}
    with xlsx_path.open("rb") as handle:
        resp = requests.post(
            url,
            headers=headers,
            files={
                "file": (
                    display_name,
                    handle,
                    "application/octet-stream",
                )
            },
            timeout=300,
        )
    if resp.status_code != 202:
        raise RuntimeError(f"Import failed: {resp.status_code} {resp.text[:400]}")
    import_id = resp.json().get("id")
    for _ in range(120):
        time.sleep(2)
        st = requests.get(
            f"{POWER_BI_API}/groups/{workspace_id}/imports/{import_id}",
            headers=pub._headers(token),
            timeout=60,
        )
        if st.status_code != 200:
            continue
        data = st.json()
        state = data.get("importState")
        if state == "Succeeded":
            datasets = data.get("datasets") or []
            reports = data.get("reports") or []
            ds_id = datasets[0]["id"] if datasets else ""
            if reports:
                return ds_id, reports[0]["id"]
            if ds_id:
                rpt = requests.post(
                    f"{POWER_BI_API}/groups/{workspace_id}/reports",
                    headers=pub._headers(token),
                    json={"name": "PulseGrid", "datasetId": ds_id},
                    timeout=60,
                )
                if rpt.status_code in (200, 201):
                    return ds_id, rpt.json()["id"]
            raise RuntimeError("Import succeeded but no report returned")
        if state == "Failed":
            raise RuntimeError(f"Import failed: {data.get('error')}")
    raise RuntimeError("Import timed out")


def _json_cell(value) -> object:
    import math

    import pandas as pd

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, (bool, int, float)):
        return value
    return str(value)


def _pbi_type(series) -> str:
    import pandas as pd

    if pd.api.types.is_bool_dtype(series):
        return "Boolean"
    if pd.api.types.is_integer_dtype(series):
        return "Int64"
    if pd.api.types.is_float_dtype(series):
        return "Double"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "DateTime"
    return "String"


def _push_dataset(token: str, workspace_id: str, pub) -> tuple[str, str]:
    """Create push dataset + blank report via REST (no Excel/Desktop)."""
    import pandas as pd

    tables = []
    for csv_name in IMPORT_SHEETS:
        csv_path = PLATFORM_DATA / csv_name
        if not csv_path.is_file():
            continue
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
        if df.empty:
            continue
        cols = [
            {"name": str(c), "dataType": _pbi_type(df[c])}
            for c in df.columns
        ]
        rows = []
        for _, row in df.iterrows():
            rows.append([_json_cell(v) for v in row.tolist()])
        tables.append({"name": csv_name.replace(".csv", ""), "columns": cols, "rows": rows})
    if not tables:
        raise FileNotFoundError(f"No tables to push from {PLATFORM_DATA}")

    body = {"name": "PulseGrid", "defaultMode": "Push", "tables": tables}
    r = requests.post(
        f"{POWER_BI_API}/groups/{workspace_id}/datasets",
        headers=pub._headers(token),
        json=body,
        timeout=120,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Push dataset failed: {r.status_code} {r.text[:400]}")
    dataset_id = r.json()["id"]

    r2 = requests.post(
        f"{POWER_BI_API}/groups/{workspace_id}/reports",
        headers=pub._headers(token),
        json={"name": "PulseGrid", "datasetId": dataset_id},
        timeout=60,
    )
    if r2.status_code not in (200, 201):
        raise RuntimeError(f"Create report failed: {r2.status_code} {r2.text[:400]}")
    return dataset_id, r2.json()["id"]


class PublishToWebBlocked(RuntimeError):
    """Service principal cannot call PublishToWeb (tenant policy)."""

    def __init__(self, report_web_url: str, detail: str) -> None:
        self.report_web_url = report_web_url
        super().__init__(detail)


def _publish_to_web(token: str, workspace_id: str, report_id: str, pub) -> str:
    """Publish to web (workspace-scoped, then fallback global)."""
    last_status = 0
    last_body = ""
    for url in (
        f"{POWER_BI_API}/groups/{workspace_id}/reports/{report_id}/PublishToWeb",
        f"{POWER_BI_API}/reports/{report_id}/PublishToWeb",
    ):
        r = requests.post(url, headers=pub._headers(token), timeout=60)
        last_status, last_body = r.status_code, r.text[:300]
        if r.status_code == 200:
            embed = (r.json().get("embedUrl") or "").strip()
            if embed and "view?r=" in embed:
                return embed
    r2 = requests.get(
        f"{POWER_BI_API}/groups/{workspace_id}/reports/{report_id}",
        headers=pub._headers(token),
        timeout=60,
    )
    web = ""
    if r2.status_code == 200:
        web = (r2.json().get("webUrl") or "").strip()
        if "view?r=" in web:
            return web
    if last_status == 403:
        raise PublishToWebBlocked(
            web,
            f"PublishToWeb blocked for service principal ({last_body}). "
            "One-time manual step: open the report in Power BI Service → "
            "File → Embed report → Publish to web, then re-run "
            "python tools/publish_pulsegrid_fabric.py",
        )
    raise RuntimeError(
        f"PublishToWeb failed ({last_status}): {last_body}. "
        "Publish manually: Report → Embed → Publish to web."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--workspace",
        default=os.getenv("POWERBI_WORKSPACE", DEFAULT_WORKSPACE),
    )
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--skip-wordpress", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--device-code", action="store_true", help="Delegated login via device code")
    args = ap.parse_args()
    _load_env()
    pub = _import_publish_module()

    try:
        sp_token = pub._token()
    except Exception as exc:
        print(f"Auth error: {exc}", file=sys.stderr)
        return 1

    ws_name = (args.workspace or DEFAULT_WORKSPACE).strip()
    print(f"Azure auth OK (service principal) — workspace: {ws_name}")

    if args.dry_run:
        print("[dry-run] would import platform xlsx, publish to web, update .env")
        return 0

    wid = _ensure_workspace(sp_token, ws_name, pub)
    print(f"Workspace id: {wid}")

    ds_id = _ensure_dataset(sp_token, wid, pub)
    report_id = _ensure_report(sp_token, wid, ds_id, pub)
    print(f"Dataset id: {ds_id}")
    print(f"Report id: {report_id}")

    try:
        print("Delegated user sign-in (Publish to web)…")
        user_token = token_delegated(prefer_device_code=args.device_code)
        embed = _publish_to_web(user_token, wid, report_id, pub)
    except PublishToWebBlocked as exc:
        print(str(exc), file=sys.stderr)
        if exc.report_web_url:
            print(f"Report URL (publish to web here): {exc.report_web_url}")
        print(
            "Retry: python tools/publish_pulsegrid_fabric.py "
            f'--workspace "{ws_name}" --device-code'
        )
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"Embed URL: {embed}")
    pub._update_env_files(embed)

    if not args.skip_deploy:
        import subprocess

        deploy = REPO_ROOT / "deploy_pulsegrid.py"
        if deploy.is_file():
            print("Redeploying Lightsail status app…")
            subprocess.run(
                [sys.executable, str(deploy), "--from-dotenv"],
                cwd=str(REPO_ROOT),
                check=False,
            )

    if not args.skip_wordpress:
        import subprocess

        wp = ROOT / "tools" / "sync_pulsegrid_wp_page.py"
        if wp.is_file():
            print("Syncing WordPress /pulsegrid/ page…")
            subprocess.run([sys.executable, str(wp)], cwd=str(ROOT), check=False)

    print("Done. Verify: https://pulse.aureaquantra.com/health (embedConfigured: true)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
