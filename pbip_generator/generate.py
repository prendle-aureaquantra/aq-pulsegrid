"""Generate PBIP from city pipeline outputs."""

from __future__ import annotations

from pathlib import Path

from pbip_generator.build_pbip import build_pbip as _build


def generate_pbip(
    city_slug: str,
    *,
    include_visuals: bool = False,
    use_custom_theme: bool = False,
) -> Path:
    return _build(
        city_slug,
        include_visuals=include_visuals,
        use_custom_theme=include_visuals,
    )
