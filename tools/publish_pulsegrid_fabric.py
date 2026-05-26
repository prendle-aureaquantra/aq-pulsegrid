#!/usr/bin/env python3
"""Publish PulseGrid report to Fabric/Power BI and set POWERBI_PULSEGRID_EMBED_URL."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import requests

from powerbi_auth import (
    POWER_BI_API,
    load_env,
    token_delegated,
    token_service_principal,
)

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent

REPORT_NAMES = ("PulseGrid", "ChicagoPulse", "Chicago Pulse", "AQ PulseGrid")


def _token() -> str:
    """Service principal token (import, workspace APIs)."""
    return token_service_principal()


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
        matches = [
            rep
            for rep in r.json().get("value", [])
            if any(
                n.lower() in (rep.get("name") or "").strip().lower()
                for n in REPORT_NAMES
            )
        ]
        if not matches:
            continue
        # Prefer imported PBIX (isFromPbix) or newest id when duplicates exist.
        pbix_only = [m for m in matches if m.get("isFromPbix")]
        pool = pbix_only if pbix_only else matches
        pool.sort(key=lambda rep: rep.get("id") or "", reverse=True)
        rep = pool[0]
        return wid, rep["id"], rep
    return None


def _publish_to_web(token: str, report_id: str, workspace_id: str | None = None) -> str:
    """Return public embed URL (app.powerbi.com/view?r=...). Requires delegated user token."""
    urls = []
    if workspace_id:
        urls.append(
            f"{POWER_BI_API}/groups/{workspace_id}/reports/{report_id}/PublishToWeb"
        )
    urls.append(f"{POWER_BI_API}/reports/{report_id}/PublishToWeb")
    r = None
    for url in urls:
        r = requests.post(url, headers=_headers(token), timeout=60)
        if r.status_code == 200:
            embed = (r.json().get("embedUrl") or "").strip()
            if embed:
                return embed
    last_status = r.status_code if r else 0
    last_body = (r.text[:300] if r else "")
    if last_status == 403 and "not accessible for application" in last_body.lower():
        raise RuntimeError(
            "PublishToWeb requires a signed-in user token, not service principal. "
            "Re-run without --service-principal-only."
        )
    raise RuntimeError(
        f"PublishToWeb failed ({last_status}): {last_body}. "
        "Check tenant setting 'Publish to web' and report edit permissions."
    )


def _import_pbix(token: str, workspace_id: str, pbix_path: Path, name: str) -> str | None:
    display = name if name.lower().endswith(".pbix") else f"{name}.pbix"
    url = (
        f"{POWER_BI_API}/groups/{workspace_id}/imports"
        f"?datasetDisplayName={requests.utils.quote(display)}"
        "&nameConflict=Overwrite"
    )
    headers = {"Authorization": f"Bearer {token}"}
    with pbix_path.open("rb") as f:
        resp = requests.post(
            url,
            headers=headers,
            files={"file": (pbix_path.name, f, "application/octet-stream")},
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


def _pulse_embed_page_url() -> str:
    public = (os.getenv("PULSEGRID_PUBLIC_URL") or "https://pulse.aureaquantra.com/").strip()
    return public.rstrip("/") + "/embed"


def _update_env_files(embed_url: str) -> None:
    embed_url = embed_url.strip()
    for env_path in (REPO_ROOT / ".env", ROOT / ".env"):
        if not env_path.is_file():
            continue
        text = env_path.read_text(encoding="utf-8")
        for key in ("POWERBI_PULSEGRID_EMBED_URL", "POWERBI_DEMO_EMBED_URL"):
            line = f"{key}={embed_url}"
            if re.search(rf"^{re.escape(key)}=", text, flags=re.MULTILINE):
                text = re.sub(rf"^{re.escape(key)}=.*$", line, text, flags=re.MULTILINE)
            else:
                text = text.rstrip() + f"\n{line}\n"
        for key in ("POWERBI_PULSEGRID_WORKSPACE_ID", "POWERBI_PULSEGRID_REPORT_ID"):
            val = (os.getenv(key) or "").strip()
            if not val:
                continue
            line = f"{key}={val}"
            if re.search(rf"^{re.escape(key)}=", text, flags=re.MULTILINE):
                text = re.sub(rf"^{re.escape(key)}=.*$", line, text, flags=re.MULTILINE)
            else:
                text = text.rstrip() + f"\n{line}\n"
        env_path.write_text(text, encoding="utf-8")
        print(f"Updated {env_path}")

    secrets = ROOT / "deploy" / "lightsail" / "secrets" / "pulsegrid.env"
    secrets.parent.mkdir(parents=True, exist_ok=True)
    secret_lines = [
        "# Generated by tools/publish_pulsegrid_fabric.py",
        f"POWERBI_PULSEGRID_EMBED_URL={embed_url}",
    ]
    for key in (
        "FABRIC_TENANT_ID",
        "FABRIC_CLIENT_ID",
        "FABRIC_CLIENT_SECRET",
        "POWERBI_PULSEGRID_WORKSPACE_ID",
        "POWERBI_PULSEGRID_REPORT_ID",
    ):
        val = (os.getenv(key) or "").strip()
        if val:
            secret_lines.append(f"{key}={val}")
    secrets.write_text("\n".join(secret_lines) + "\n", encoding="utf-8")
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
    parser.add_argument(
        "--embed-url",
        default=os.getenv("POWERBI_PULSEGRID_EMBED_URL", ""),
        help="Skip PublishToWeb API; save this https://app.powerbi.com/view?r=... URL",
    )
    parser.add_argument(
        "--service-principal-only",
        action="store_true",
        help="Use SP token only (cannot PublishToWeb; for listing/import)",
    )
    parser.add_argument(
        "--device-code",
        action="store_true",
        help="Force device-code login for delegated token",
    )
    args = parser.parse_args()
    load_env()

    try:
        sp_token = token_service_principal()
        print("Auth: service principal (workspace API)")
    except Exception as exc:
        print(f"Auth error: {exc}", file=sys.stderr)
        return 1

    user_token: str | None = None
    if not args.service_principal_only:
        try:
            user_token = token_delegated(prefer_device_code=args.device_code)
        except Exception as exc:
            print(f"User auth error: {exc}", file=sys.stderr)
            return 1

    ws_filter = args.workspace.strip() or None
    found = _find_report(sp_token, ws_filter)
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
        rid = _import_pbix(sp_token, target["id"], args.pbix, "PulseGrid")
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

    embed = (args.embed_url or "").strip()
    if embed and "view?r=" not in embed:
        # e.g. POWERBI_PULSEGRID_EMBED_URL=https://pulse.../embed — not a Publish-to-web URL
        embed = ""
    os.environ["POWERBI_PULSEGRID_WORKSPACE_ID"] = wid
    os.environ["POWERBI_PULSEGRID_REPORT_ID"] = rid
    if embed:
        print(f"Using provided Publish-to-web URL (report {rid[:8]}…)")
    elif args.service_principal_only or not user_token:
        embed = _pulse_embed_page_url()
        print(f"Using service-principal embed page: {embed}")
    else:
        try:
            embed = _publish_to_web(user_token, rid, wid)
            print(f"Publish to web: {embed}")
        except RuntimeError as exc:
            print(f"PublishToWeb: {exc}", file=sys.stderr)
            embed = _pulse_embed_page_url()
            print(f"Using service-principal embed page: {embed}")
    print(f"Embed URL: {embed}")
    _update_env_files(embed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
