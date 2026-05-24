#!/usr/bin/env python3
"""Run synthetic evaluation prompts against the PulseGrid copilot."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pulsegrid.config import load_dotenv
from pulsegrid.copilot.insights import ask

PROMPTS_PATH = ROOT / "datasets" / "reference" / "synthetic_questions.yaml"


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run synthetic copilot eval prompts")
    parser.add_argument("--city", default="chicago")
    parser.add_argument("--category", help="YAML category key (e.g. executive, transit)")
    parser.add_argument("--limit", type=int, default=5, help="Max prompts per category")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--out", type=Path, help="Write combined markdown report")
    args = parser.parse_args()

    doc = yaml.safe_load(PROMPTS_PATH.read_text(encoding="utf-8")) or {}
    categories = doc.get("categories") or {}
    if args.category:
        if args.category not in categories:
            print(f"Unknown category {args.category!r}", file=sys.stderr)
            return 1
        categories = {args.category: categories[args.category]}

    lines: list[str] = [f"# Synthetic eval — {args.city}\n"]
    for name, cfg in categories.items():
        if cfg.get("roadmap"):
            continue
        prompts = list(cfg.get("prompts") or [])[: args.limit]
        if not prompts:
            continue
        lines.append(f"\n## {name}\n")
        for prompt in prompts:
            print(f"\n--- {name}: {prompt[:72]}…")
            try:
                answer = ask(args.city, prompt, model=args.model)
            except Exception as exc:
                answer = f"_Error: {exc}_"
                print(f"  skip: {exc}", file=sys.stderr)
            print(answer)
            lines.append(f"### {prompt}\n\n{answer}\n")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(lines), encoding="utf-8")
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
