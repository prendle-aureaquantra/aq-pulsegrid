"""CSV-backed PulseGrid copilot for Lightsail (no Delta / full package required)."""

from __future__ import annotations

import csv
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(os.getenv("PULSEGRID_DATA_DIR", "data"))
PROMPTS_PATH = Path(
    os.getenv("PULSEGRID_COPILOT_PROMPTS", "")
).expanduser() or (Path(__file__).with_name("synthetic_questions.yaml"))

DEFAULT_PROMPTS = (
    "Why is the City Stress Index elevated?",
    "What transit or weather signals are driving risk today?",
    "Summarize anomalies and recommended actions in 3 bullets.",
    "How does infrastructure failure risk compare to last snapshot?",
    "Which public feeds look stale or missing for this metro?",
)


def _read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _filter_city(rows: list[dict[str, str]], metro: str) -> list[dict[str, str]]:
    if not rows or "city" not in rows[0]:
        return rows
    slug = metro.lower()
    return [r for r in rows if (r.get("city") or "").lower() == slug]


def build_context(metro: str) -> dict[str, Any]:
    slug = metro.strip().lower()
    ctx: dict[str, Any] = {"city": slug}
    for table, limit in (
        ("CityPulseSnapshot.csv", 3),
        ("AnomalySignals.csv", 10),
        ("TransitAlertSummary.csv", 8),
        ("TransitAlertDetail.csv", 8),
        ("DimMetro.csv", 1),
    ):
        rows = _filter_city(_read_csv(table), slug)
        if rows:
            ctx[table.replace(".csv", "")] = rows[-limit:]
    return ctx


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, Any]:
    if not PROMPTS_PATH.is_file():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    return yaml.safe_load(PROMPTS_PATH.read_text(encoding="utf-8")) or {}


def sample_questions(
    metro: str,
    *,
    limit: int = 6,
    categories: tuple[str, ...] = (
        "executive",
        "root_cause_analysis",
        "transit",
        "weather",
    ),
) -> list[str]:
    catalog = _load_catalog()
    cats = catalog.get("categories") or {}
    city_title = metro.replace("-", " ").title()
    prompts: list[str] = []
    for key in categories:
        block = cats.get(key) or {}
        for raw in block.get("prompts") or []:
            text = str(raw).replace("Chicago", city_title).replace("chicago", metro)
            prompts.append(text)
            if len(prompts) >= limit:
                return prompts
    if prompts:
        return prompts[:limit]
    return [p.replace("this metro", city_title) for p in DEFAULT_PROMPTS[:limit]]


def copilot_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def ask(
    metro: str,
    question: str,
    *,
    model: str | None = None,
) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not configured on server.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("pip install openai") from exc

    slug = metro.strip().lower()
    ctx = build_context(slug)
    model_name = (model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AQ PulseGrid Copilot — urban intelligence analyst for public "
                    "metro feeds (transit, weather, airports, civic data). Use only the "
                    "provided CSV snapshot JSON; say when data is missing. Plain language "
                    "for executives; cite metric names when helpful. Synthetic/public data only."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Metro: {slug}\nQuestion: {question}\n\n"
                    f"Metrics JSON:\n{json.dumps(ctx, indent=2, default=str)}"
                ),
            },
        ],
        temperature=0.3,
    )
    return (resp.choices[0].message.content or "").strip()
