"""Power BI embed token via service principal (for /embed when Publish-to-web API unavailable)."""

from __future__ import annotations

import os
from functools import lru_cache

import requests

POWER_BI_API = "https://api.powerbi.com/v1.0/myorg"
SCOPE = ["https://analysis.windows.net/powerbi/api/.default"]


def _config() -> tuple[str, str, str, str, str]:
    tenant = (os.getenv("FABRIC_TENANT_ID") or "").strip()
    client_id = (os.getenv("FABRIC_CLIENT_ID") or "").strip()
    secret = (os.getenv("FABRIC_CLIENT_SECRET") or "").strip()
    workspace_id = (os.getenv("POWERBI_PULSEGRID_WORKSPACE_ID") or "").strip()
    report_id = (os.getenv("POWERBI_PULSEGRID_REPORT_ID") or "").strip()
    return tenant, client_id, secret, workspace_id, report_id


def embed_configured() -> bool:
    url = (os.getenv("POWERBI_PULSEGRID_EMBED_URL") or "").strip()
    if url and "view?r=" in url:
        return True
    tenant, client_id, secret, workspace_id, report_id = _config()
    return bool(tenant and client_id and secret and workspace_id and report_id)


@lru_cache(maxsize=1)
def _sp_token() -> str:
    from msal import ConfidentialClientApplication

    tenant, client_id, secret, _, _ = _config()
    if not all([tenant, client_id, secret]):
        raise RuntimeError("FABRIC_* and POWERBI_PULSEGRID_*_ID not set for embed")
    app = ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant}",
        client_credential=secret,
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "token failed"))
    return result["access_token"]


def get_report_embed() -> dict[str, str]:
    """Return embedUrl and short-lived embed token for the configured report."""
    _, _, _, workspace_id, report_id = _config()
    token = _sp_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    rep = requests.get(
        f"{POWER_BI_API}/groups/{workspace_id}/reports/{report_id}",
        headers=headers,
        timeout=60,
    )
    rep.raise_for_status()
    embed_url = (rep.json().get("embedUrl") or "").strip()
    gen = requests.post(
        f"{POWER_BI_API}/groups/{workspace_id}/reports/{report_id}/GenerateToken",
        headers=headers,
        json={"accessLevel": "View"},
        timeout=60,
    )
    gen.raise_for_status()
    embed_token = (gen.json().get("token") or "").strip()
    if not embed_url or not embed_token:
        raise RuntimeError("Missing embedUrl or token from Power BI API")
    return {"embedUrl": embed_url, "accessToken": embed_token}
