#!/usr/bin/env python3
"""Create/update WordPress /pulsegrid/ page from docs/pulsegrid-page.html."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MONO = ROOT.parent


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in (MONO / ".env", ROOT / ".env"):
        if p.is_file():
            load_dotenv(p)
            break


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--html", type=Path, default=ROOT / "docs" / "pulsegrid-page.html")
    ap.add_argument("--slug", default="pulsegrid")
    ap.add_argument("--title", default="AQ PulseGrid")
    args = ap.parse_args()
    _load_env()

    try:
        import requests
    except ImportError:
        print("pip install requests", file=sys.stderr)
        return 1

    base = (os.getenv("WP_BASE_URL") or "").rstrip("/")
    user = (os.getenv("WP_USERNAME") or "").strip()
    app_pwd = (os.getenv("WP_APP_PASSWORD") or "").replace(" ", "").strip()
    if not base or not user or not app_pwd:
        print("Set WP_BASE_URL, WP_USERNAME, WP_APP_PASSWORD in .env", file=sys.stderr)
        return 1

    if not args.html.is_file():
        print(f"Missing {args.html} — run sync_pulsegrid_site_page.py --out docs/pulsegrid-page.html", file=sys.stderr)
        return 1

    content = args.html.read_text(encoding="utf-8")
    api = f"{base}/wp-json/wp/v2/pages"
    auth = (user, app_pwd)
    headers = {"Content-Type": "application/json"}

    r = requests.get(
        api, params={"slug": args.slug, "_fields": "id,slug"}, auth=auth, timeout=20
    )
    r.raise_for_status()
    rows = r.json()
    if rows:
        page_id = rows[0]["id"]
        r2 = requests.patch(
            f"{api}/{page_id}",
            json={"content": content},
            auth=auth,
            headers=headers,
            timeout=30,
        )
        if r2.status_code not in (200, 201):
            print(f"PATCH failed: {r2.status_code} {r2.text[:400]}", file=sys.stderr)
            return 1
        print(f"Updated WordPress page id={page_id} slug={args.slug}")
        return 0

    r3 = requests.post(
        api,
        json={
            "title": args.title,
            "slug": args.slug,
            "status": "publish",
            "content": content,
        },
        auth=auth,
        headers=headers,
        timeout=30,
    )
    if r3.status_code not in (200, 201):
        print(f"POST failed: {r3.status_code} {r3.text[:400]}", file=sys.stderr)
        return 1
    print(f"Created WordPress page slug={args.slug} id={r3.json().get('id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
