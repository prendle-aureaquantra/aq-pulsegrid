#!/usr/bin/env python3
"""Add Power BI delegated API permissions to FABRIC app via Microsoft Graph (admin consent still required)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from msal import ConfidentialClientApplication

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
GRAPH = "https://graph.microsoft.com/v1.0"

# Power BI Service
POWER_BI_RESOURCE = "00000009-0000-0000-c000-000000000000"
# Verified delegated scope IDs (Power BI Service app 00000009-...)
DELEGATED_SCOPES = (
    ("Report.ReadWrite.All", "7504609f-c495-4c64-8542-686125a5a36f"),
)


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")
    tenant = (os.getenv("FABRIC_TENANT_ID") or "").strip()
    client_id = (os.getenv("FABRIC_CLIENT_ID") or "").strip()
    secret = (os.getenv("FABRIC_CLIENT_SECRET") or "").strip()
    if not all([tenant, client_id, secret]):
        print("Set FABRIC_TENANT_ID, FABRIC_CLIENT_ID, FABRIC_CLIENT_SECRET", file=sys.stderr)
        return 1

    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant}",
        client_credential=secret,
    )
    token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in token:
        print("Graph token failed:", token.get("error_description"), file=sys.stderr)
        return 1

    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/json",
    }
    r = requests.get(
        f"{GRAPH}/applications",
        headers=headers,
        params={"$filter": f"appId eq '{client_id}'"},
        timeout=60,
    )
    if r.status_code == 403:
        print(
            "Graph 403 — add Application.ReadWrite.All to FABRIC app, or add permissions manually:\n"
            "  Power BI Service (delegated): Dataset.ReadWrite.All, Report.ReadWrite.All, "
            "Workspace.ReadWrite.All, Content.Create\n"
            "  Then Grant admin consent.",
            file=sys.stderr,
        )
        return 1
    r.raise_for_status()
    apps = r.json().get("value", [])
    if not apps:
        print("Application not found.", file=sys.stderr)
        return 1

    app_obj = apps[0]
    obj_id = app_obj["id"]
    required = list(app_obj.get("requiredResourceAccess") or [])
    pbi = next(
        (x for x in required if x.get("resourceAppId") == POWER_BI_RESOURCE),
        None,
    )
    if not pbi:
        pbi = {"resourceAppId": POWER_BI_RESOURCE, "resourceAccess": []}
        required.append(pbi)
    existing = {a["id"] for a in pbi.get("resourceAccess", [])}
    added = []
    for _name, scope_id in DELEGATED_SCOPES:
        if scope_id not in existing:
            pbi["resourceAccess"].append({"id": scope_id, "type": "Scope"})
            added.append(_name)
    if not added:
        print("Power BI delegated permissions already present.")
        return 0

    pr = requests.patch(
        f"{GRAPH}/applications/{obj_id}",
        headers=headers,
        json={"requiredResourceAccess": required},
        timeout=60,
    )
    if not pr.ok:
        print(f"PATCH failed: {pr.status_code} {pr.text[:400]}", file=sys.stderr)
        return 1
    print("Added delegated permissions:", ", ".join(added))
    print(
        "Next: Azure Portal → API permissions → Grant admin consent for Aurea Quantra tenant."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
