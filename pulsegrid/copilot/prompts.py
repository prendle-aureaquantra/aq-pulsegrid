"""Sample prompts from datasets/reference/synthetic_questions.yaml."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS_PATH = ROOT / "datasets" / "reference" / "synthetic_questions.yaml"


@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    if not QUESTIONS_PATH.is_file():
        return {}
    return yaml.safe_load(QUESTIONS_PATH.read_text(encoding="utf-8")) or {}


def sample_questions(
    city_slug: str,
    *,
    limit: int = 8,
    categories: tuple[str, ...] = (
        "executive",
        "root_cause_analysis",
        "infrastructure",
        "transit",
        "weather",
    ),
) -> list[str]:
    """Return demo prompts with city name substituted."""
    catalog = _load_catalog()
    cats = catalog.get("categories") or {}
    city_title = city_slug.replace("-", " ").title()
    prompts: list[str] = []
    for key in categories:
        block = cats.get(key) or {}
        for raw in block.get("prompts") or []:
            text = str(raw).replace("Chicago", city_title).replace("chicago", city_slug)
            prompts.append(text)
            if len(prompts) >= limit:
                return prompts
    return prompts[:limit]
