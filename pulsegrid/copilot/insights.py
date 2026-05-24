"""AI copilot layer — natural-language summary of city pulse metrics."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pulsegrid.config import DELTA, GENERATED, get_city, load_dotenv
from pulsegrid.copilot.prompts import sample_questions
from pulsegrid.io.delta_writer import read_delta_table


def _load_context(city_slug: str) -> dict:
    ctx: dict = {"city": city_slug}
    for layer, table in (
        ("gold", "city_stress_index"),
        ("gold", "anomaly_signals"),
        ("gold", "city_pulse_snapshot"),
        ("gold", "infrastructure_risk_snapshot"),
    ):
        path = DELTA / layer / table
        if path.exists():
            df = read_delta_table(path)
            if not df.empty and "city" in df.columns:
                df = df[df["city"] == city_slug]
            if not df.empty:
                ctx[table] = (
                    df.sort_values("snapshot_at", ascending=False)
                    .head(5)
                    .to_dict("records")
                )
    meta = GENERATED / city_slug / "semantic_model_metadata.json"
    if meta.is_file():
        ctx["semantic_model"] = json.loads(meta.read_text(encoding="utf-8"))
    return ctx


def ask(
    city_slug: str,
    prompt: str,
    *,
    model: str = "gpt-4o-mini",
) -> str:
    """Answer a natural-language question using latest gold metrics + semantic metadata."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in .env")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("pip install openai") from exc

    city = get_city(city_slug)
    ctx = _load_context(city_slug)
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are AQ PulseGrid copilot — urban intelligence analyst grounded in "
                    "City Stress Index (0-100), transit/weather/airport signals, and anomaly rows. "
                    "Use only the provided metrics JSON; say when data is missing. "
                    "Prefer plain language for executives; cite metric names when helpful."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"City: {city.name} ({city_slug})\n"
                    f"Question: {prompt}\n\n"
                    f"Metrics JSON:\n{json.dumps(ctx, indent=2, default=str)}"
                ),
            },
        ],
        temperature=0.3,
    )
    return (resp.choices[0].message.content or "").strip()


def summarize(city_slug: str, *, model: str = "gpt-4o-mini") -> str:
    return ask(
        city_slug,
        "Summarize operational stress, anomalies, and recommended actions in 3-5 bullets.",
        model=model,
    )


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="AQ PulseGrid AI copilot summary")
    parser.add_argument("city", nargs="?", default="chicago")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument(
        "--prompt",
        help="Custom question (default: executive summary bullets)",
    )
    parser.add_argument("--out", type=Path, help="Write summary markdown file")
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="Print sample training/demo prompts for this city",
    )
    args = parser.parse_args(argv)
    if args.list_prompts:
        for line in sample_questions(args.city):
            print(f"- {line}")
        return 0
    try:
        if args.prompt:
            text = ask(args.city, args.prompt, model=args.model)
        else:
            text = summarize(args.city, model=args.model)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            f"# AQ PulseGrid Copilot — {args.city}\n\n{text}\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
