"""Power BI tokens: service principal (automation) and delegated user (Publish to web)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

POWER_BI_SCOPES = ["https://analysis.windows.net/powerbi/api/.default"]
POWER_BI_API = "https://api.powerbi.com/v1.0/myorg"

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
CACHE_FILE = ROOT / "deploy" / "secrets" / ".msal_powerbi_cache.json"


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in (REPO_ROOT / ".env", ROOT / ".env"):
        if p.is_file():
            load_dotenv(p)


def tenant_id() -> str:
    load_env()
    t = (os.getenv("FABRIC_TENANT_ID") or os.getenv("AZURE_TENANT_ID") or "").strip()
    if not t:
        raise RuntimeError("Set FABRIC_TENANT_ID in .env")
    return t


def client_id() -> str:
    load_env()
    cid = (os.getenv("FABRIC_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID") or "").strip()
    if not cid:
        raise RuntimeError("Set FABRIC_CLIENT_ID in .env")
    return cid


def client_secret() -> str:
    load_env()
    return (
        os.getenv("FABRIC_CLIENT_SECRET") or os.getenv("AZURE_CLIENT_SECRET") or ""
    ).strip()


def login_hint() -> str:
    load_env()
    return (
        (os.getenv("FABRIC_USERNAME") or "").strip()
        or (os.getenv("POWERBI_WORKSPACE_ADMIN_EMAIL") or "").strip()
    )


def _load_cache():
    from msal import SerializableTokenCache

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache = SerializableTokenCache()
    if CACHE_FILE.is_file():
        cache.deserialize(CACHE_FILE.read_text(encoding="utf-8"))
    return cache


def _persist_cache(cache) -> None:
    if cache.has_state_changed:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(cache.serialize(), encoding="utf-8")


def token_service_principal() -> str:
    from msal import ConfidentialClientApplication

    secret = client_secret()
    if not secret:
        raise RuntimeError("Set FABRIC_CLIENT_SECRET in .env")
    app = ConfidentialClientApplication(
        client_id(),
        authority=f"https://login.microsoftonline.com/{tenant_id()}",
        client_credential=secret,
    )
    result = app.acquire_token_for_client(scopes=POWER_BI_SCOPES)
    if "access_token" not in result:
        raise RuntimeError(
            f"Service principal token failed: {result.get('error_description', result)}"
        )
    return result["access_token"]


def _delegated_app():
    """Public client + token cache (FABRIC app is registered as public)."""
    from msal import PublicClientApplication

    cache = _load_cache()
    app = PublicClientApplication(
        client_id(),
        authority=f"https://login.microsoftonline.com/{tenant_id()}",
        token_cache=cache,
    )
    return app, cache


def _interactive_public_auth_code(app, scopes: list[str], login_hint: str) -> dict:
    """Auth-code flow with local redirect (confidential FABRIC app)."""
    import threading
    import urllib.parse
    import webbrowser
    from http.server import BaseHTTPRequestHandler, HTTPServer

    redirect_uri = "http://localhost:8400"
    state = "aq-pulsegrid-pbi"
    auth_url = app.get_authorization_request_url(
        scopes,
        state=state,
        redirect_uri=redirect_uri,
        login_hint=login_hint or None,
    )
    captured: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            if parsed.path in ("/", ""):
                captured.update({k: v[0] for k, v in qs.items() if v})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><p>Signed in. You can close this tab.</p></body></html>"
            )
            threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, *_args) -> None:
            return

    print(f"  If the browser does not open, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)
    server = HTTPServer(("127.0.0.1", 8400), Handler)
    server.timeout = 300
    server.handle_request()
    if captured.get("error"):
        raise RuntimeError(captured.get("error_description") or captured["error"])
    code = captured.get("code")
    if not code:
        raise RuntimeError("No authorization code received on http://localhost:8400")
    if captured.get("state") and captured.get("state") != state:
        raise RuntimeError("OAuth state mismatch")
    return app.acquire_token_by_authorization_code(code, scopes=scopes, redirect_uri=redirect_uri)


def token_delegated(*, prefer_device_code: bool = False) -> str:
    """
    User-delegated token (required for PublishToWeb).
    Browser login on http://localhost:8400; token cached for later runs.
    """
    app, cache = _delegated_app()
    hint = login_hint()
    accounts = app.get_accounts(username=hint) if hint else app.get_accounts()
    if accounts and not prefer_device_code:
        result = app.acquire_token_silent(POWER_BI_SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _persist_cache(cache)
            user = (result.get("id_token_claims") or {}).get("preferred_username", "?")
            print(f"  Power BI (cached): {user}")
            return result["access_token"]

    password = (os.getenv("FABRIC_PASSWORD") or "").strip()
    if hint and password:
        try:
            result = app.acquire_token_by_username_password(
                username=hint,
                password=password,
                scopes=POWER_BI_SCOPES,
            )
            if result and "access_token" in result:
                _persist_cache(cache)
                print(f"  Power BI (ROPC): {hint}")
                return result["access_token"]
        except Exception:
            pass

    if prefer_device_code:
        flow = app.initiate_device_flow(scopes=POWER_BI_SCOPES)
        if not flow or "user_code" not in flow:
            raise RuntimeError(f"Device flow failed: {flow}")
        print("\n" + "=" * 70)
        if hint:
            print(f"Sign in as: {hint}")
        print(flow["message"])
        print("=" * 70 + "\n")
        result = app.acquire_token_by_device_flow(flow)
    else:
        try:
            print("  Browser sign-in (localhost:8400)…")
            if hint:
                print(f"  Use account: {hint}")
            kwargs: dict = {"scopes": POWER_BI_SCOPES, "port": 8400}
            if hint:
                kwargs["login_hint"] = hint
            result = app.acquire_token_interactive(**kwargs)
        except AttributeError:
            result = _interactive_public_auth_code(app, POWER_BI_SCOPES, hint)

    if "access_token" not in result:
        raise RuntimeError(
            f"Delegated login failed: {result.get('error_description', result)}. "
            "Add redirect URI http://localhost:8400 on the FABRIC app (Authentication) "
            "and Power BI delegated permission Report.ReadWrite.All with admin consent."
        )
    _persist_cache(cache)
    user = (result.get("id_token_claims") or {}).get("preferred_username", "?")
    print(f"  Power BI signed in: {user}")
    return result["access_token"]
