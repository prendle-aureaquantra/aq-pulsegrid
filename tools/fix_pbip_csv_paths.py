#!/usr/bin/env python3
"""Rewrite PBIP partition M queries to absolute CSV paths (fixes Power BI load errors)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_FILE_CONTENTS_RE = re.compile(
    r'File\.Contents\("(?:\.\./)+data/([^"]+\.csv)"\)'
)


def _data_dir_for_bundle(bundle_dir: Path) -> Path | None:
    for candidate in (bundle_dir / "data", bundle_dir.parent / "data"):
        if candidate.is_dir():
            return candidate.resolve()
    return None


def fix_bundle(bundle_dir: Path, *, dry_run: bool = False) -> int:
    """Fix all *.tmdl under bundle_dir/*SemanticModel/definition/tables."""
    data_dir = _data_dir_for_bundle(bundle_dir)
    if not data_dir:
        print(f"  skip {bundle_dir.name}: no data/ folder", file=sys.stderr)
        return 0
    sm_dirs = list(bundle_dir.glob("*.SemanticModel/definition/tables/*.tmdl"))
    if not sm_dirs:
        print(f"  skip {bundle_dir.name}: no TMDL tables", file=sys.stderr)
        return 0
    changed = 0
    for tmdl in sm_dirs:
        text = tmdl.read_text(encoding="utf-8")
        new_text = text

        def repl(match: re.Match[str]) -> str:
            name = match.group(1)
            abs_path = (data_dir / name).resolve().as_posix().replace('"', '""')
            return f'File.Contents("{abs_path}")'

        new_text = _FILE_CONTENTS_RE.sub(repl, new_text)
        if new_text != text:
            changed += 1
            if not dry_run:
                tmdl.write_text(new_text, encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set absolute File.Contents paths in PBIP semantic model TMDL"
    )
    parser.add_argument(
        "bundle",
        nargs="*",
        help="Paths to city folder (e.g. generated_reports/chicago) or platform",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    targets: list[Path] = []
    if args.bundle:
        targets = [Path(p).resolve() for p in args.bundle]
    else:
        reports = ROOT / "generated_reports"
        if reports.is_dir():
            targets = [p for p in reports.iterdir() if p.is_dir()]

    total = 0
    for bundle in targets:
        n = fix_bundle(bundle, dry_run=args.dry_run)
        if n:
            label = "would fix" if args.dry_run else "fixed"
            print(f"{label} {n} table(s) in {bundle}")
            total += n
    if total == 0:
        print("No relative data paths found (already absolute or no TMDL).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
