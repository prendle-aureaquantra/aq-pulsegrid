#!/usr/bin/env python3
"""Publish PulseGrid report to Fabric/Power BI and set POWERBI_PULSEGRID_EMBED_URL."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
POWER_BI_API = "https://api.powerbi.com/v1.0/myorg"
SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]

REPORT_NAMES = ("PulseGrid", "ChicagoPulse", "Chicago Pulse", "AQ PulseGrid")


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in (REPO_ROOT / ".env", ROOT / ".env"):
        if p.is_file():
            load_dotenv(p)


def _token() -> str:
    from msal import ConfidentialClientApplication

    tenant = (os.getenv("FABRIC_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "").strip()
    client_id = (os.getenv("FABRIC_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID") or "").strip()
    secret = (
        os.getenv("FABRIC_CLIENT_SECRET") or os.getenv("AZURE_CLIENT_SECRET") or ""
    ).strip()
    if not all([tenant, client_id, secret]):
        raise RuntimeError(
            "Set FABRIC_TENANT_ID, FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET in .env"
        )
    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant}",
        client_credential=secret,
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(f"Token failed: {result.get('error_description', result)}")
    return result["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _list_workspaces(token: str) -> list[dict]:
    r = requests.get(f"{POWER_BI_API}/groups", headers=_headers(token), timeout=60)
    r.raise_for_status()
    return r.json().get("value", [])


def _find_report(token: str, workspace: str | None) -> tuple[str, str, dict] | None:
    """Return (workspace_id, report_id, report_json) or None."""
    workspaces = _list_workspaces(token)
    if workspace:
        matched = [w for w in workspaces if w.get("name", "").lower() == workspace.lower()]
        if matched:
            workspaces = matched
    for ws in workspaces:
        wid = ws["id"]
        r = requests.get(
            f"{POWER_BI_API}/groups/{wid}/reports",
            headers=_headers(token),
            timeout=60,
        )
        if r.status_code != 200:
            continue
        for rep in r.json().get("value", []):
            name = (rep.get("name") or "").strip()
            if any(n.lower() in name.lower() for n in REPORT_NAMES):
                return wid, rep["id"], rep
    return None


def _publish_to_web(token: str, report_id: str) -> str:
    """Return public embed URL (app.powerbi.com/view?r=...)."""
    r = requests.post(
        f"{POWER_BI_API}/reports/{report_id}/PublishToWeb",
        headers=_headers(token),
        timeout=60,
    )
    if r.status_code == 200:
        embed = (r.json().get("embedUrl") or "").strip()
        if embed:
            return embed
    # Already published or alternate endpoint
    r2 = requests.get(
        f"{POWER_BI_API}/reports/{report_id}",
        headers=_headers(token),
        timeout=60,
    )
    r2.raise_for_status()
    web = (r2.json().get("webUrl") or "").strip()
    if "view?r=" in web:
        return web
    raise RuntimeError(
        f"PublishToWeb failed ({r.status_code}): {r.text[:300]}. "
        "Publish manually in Power BI Service → Publish to web."
    )


def _import_pbix(token: str, workspace_id: str, pbix_path: Path, name: str) -> str | None:
    headers = {"Authorization": f"Bearer {token}"}
    with pbix_path.open("rb") as f:
        resp = requests.post(
            f"{POWER_BI_API}/groups/{workspace_id}/imports",
            headers=headers,
            files={"file": (pbix_path.name, f, "application/octet-stream")},
            data={"datasetDisplayName": name, "nameConflict": "CreateOrOverwrite"},
            timeout=300,
        )
    if resp.status_code != 202:
        print(f"Import failed: {resp.status_code} {resp.text[:400]}", file=sys.stderr)
        return None
    import_id = resp.json().get("id")
    for _ in range(90):
        time.sleep(2)
        st = requests.get(
            f"{POWER_BI_API}/groups/{workspace_id}/imports/{import_id}",
            headers=_headers(token),
            timeout=60,
        )
        if st.status_code != 200:
            continue
        data = st.json()
        state = data.get("importState")
        if state == "Succeeded":
            reports = data.get("reports") or []
            return reports[0]["id"] if reports else None
        if state == "Failed":
            print(f"Import failed: {data.get('error')}", file=sys.stderr)
            return None
    return None


def _update_env_files(embed_url: str) -> None:
    embed_url = embed_url.strip()
    for env_path in (REPO_ROOT / ".env", ROOT / ".env"):
        if not env_path.is_file():
            continue
        text = env_path.read_text(encoding="utf-8")
        key = "POWERBI_PULSEGRID_EMBED_URL"
        line = f"{key}={embed_url}"
        if re.search(rf"^{re.escape(key)}=", text, flags=re.MULTILINE):
            text = re.sub(rf"^{re.escape(key)}=.*$", line, text, flags=re.MULTILINE)
        else:
            text = text.rstrip() + f"\n{line}\n"
        env_path.write_text(text, encoding="utf-8")
        print(f"Updated {env_path}")

    secrets = ROOT / "deploy" / "lightsail" / "secrets" / "pulsegrid.env"
    secrets.parent.mkdir(parents=True, exist_ok=True)
    secrets.write_text(
        "\n".join(
            [
                "# Generated by tools/publish_pulsegrid_fabric.py",
                f"POWERBI_PULSEGRID_EMBED_URL={embed_url}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {secrets}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        default=os.getenv("POWERBI_WORKSPACE", ""),
        help="Power BI workspace name (empty = search all workspaces)",
    )
    parser.add_argument(
        "--pbix",
        type=Path,
        help="Optional .pbix to import if report not found",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    _load_env()

    try:
        token = _token()
    except Exception as exc:
        print(f"Auth error: {exc}", file=sys.stderr)
        return 1

    ws_filter = args.workspace.strip() or None
    found = _find_report(token, ws_filter)
    if not found and args.pbix and args.pbix.is_file():
        workspaces = _list_workspaces(token)
        target = next(
            (w for w in workspaces if w.get("name", "").lower() == (ws_filter or "").lower()),
            workspaces[0] if workspaces else None,
        )
        if not target:
            print("No workspace found for import.", file=sys.stderr)
            return 1
        print(f"Importing {args.pbix} into {target.get('name')}...")
        rid = _import_pbix(token, target["id"], args.pbix, "PulseGrid")
        if rid:
            found = (target["id"], rid, {"id": rid, "name": "PulseGrid"})

    if not found:
        print(
            "No PulseGrid/ChicagoPulse report in Power BI Service.\n"
            "  1. Open generated_reports/platform/PulseGrid.pbip in Power BI Desktop\n"
            "  2. Publish to workspace, then re-run this script\n"
            "  Or pass --pbix path/to/export.pbix",
            file=sys.stderr,
        )
        return 1

    wid, rid, rep = found
    print(f"Found report: {rep.get('name')} (workspace {wid[:8]}...)")

    if args.dry_run:
        print("[dry-run] would publish to web and update .env")
        return 0

    embed = _publish_to_web(token, rid)
    print(f"Embed URL: {embed}")
    _update_env_files(embed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
