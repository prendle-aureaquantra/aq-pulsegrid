"""Synthetic question catalog for copilot demos."""

from __future__ import annotations

from pulsegrid.copilot.prompts import sample_questions


def test_sample_questions_substitutes_city():
    prompts = sample_questions("boston", limit=3)
    assert len(prompts) >= 1
    assert any("Boston" in p or "boston" in p for p in prompts)
