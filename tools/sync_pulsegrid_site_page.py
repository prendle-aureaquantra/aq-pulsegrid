#!/usr/bin/env python3
"""Sync /pulsegrid/ WordPress page content from AQ PulseGrid docs."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent


def build_pulsegrid_page_html(*, embed_url: str = "", repo_url: str = "") -> str:
    repo = repo_url or os.getenv(
        "PULSEGRID_REPO", "https://github.com/prendle-aureaquantra/aq-pulsegrid"
    )
    embed = embed_url or os.getenv("POWERBI_PULSEGRID_EMBED_URL", "").strip()
    iframe = ""
    if embed:
        iframe = f"""
<figure style="margin:2rem 0;border-radius:18px;overflow:hidden;box-shadow:0 28px 60px rgba(0,0,0,0.15);">
  <iframe title="Chicago Live City Pulse" width="1140" height="541" src="{embed}"
    frameborder="0" allowFullScreen="true" style="display:block;width:100%;max-width:1140px;"></iframe>
</figure>"""
    return f"""<h1>Chicago Live City Pulse</h1>
<p>AQ PulseGrid — Spark-powered urban intelligence: streaming public data, ML stress index, automated Power BI PBIP.</p>
<p><a class="wp-block-button__link" href="{repo}">View on GitHub</a>
&nbsp; <a class="wp-block-button__link" href="/book/" style="background:#2C2C2C;">Book a discovery call</a></p>
{iframe}
<h2>What it demonstrates</h2>
<ul>
  <li>Delta Lake bronze / silver / gold medallion architecture</li>
  <li>Spark Structured Streaming + ML anomaly detection</li>
  <li>Metadata-driven Power BI PBIP generation</li>
  <li>Geospatial hex grid + OpenStreetMap enrichment</li>
</ul>
<p><img src="/wp-content/uploads/pulsegrid/live-city-pulse.png" alt="Chicago Pulse dashboard" style="max-width:100%;height:auto;border-radius:12px;" loading="lazy" /></p>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate WordPress /pulsegrid/ page HTML snippet"
    )
    parser.add_argument("--embed-url", default="")
    parser.add_argument("--repo-url", default="")
    parser.add_argument("--out", type=Path, help="Write HTML file")
    args = parser.parse_args()
    html = build_pulsegrid_page_html(embed_url=args.embed_url, repo_url=args.repo_url)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(html, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(html)
    print(
        "\nAdd to config/site_spec.yaml slug: pulsegrid — see docs/SITE_INTEGRATION.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
