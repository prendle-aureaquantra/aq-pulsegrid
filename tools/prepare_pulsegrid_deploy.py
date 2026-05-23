#!/usr/bin/env python3
"""Write deploy/lightsail/deploy.config.env + SSH key from monorepo or local .env (SSH_*)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def pulsegrid_root() -> Path:
    return Path(__file__).resolve().parent.parent


def deploy_dir() -> Path:
    return pulsegrid_root() / "deploy" / "lightsail"


def parse_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        k, v = k.strip(), v.strip()
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            v = v[1:-1]
        out[k] = v
    return out


def load_env_files(root: Path) -> None:
    try:
        from dotenv import load_dotenv as _load
    except ImportError:
        _load = None
    for candidate in (root.parent / ".env", root / ".env"):
        if candidate.is_file():
            if _load:
                _load(candidate)
            else:
                for k, v in parse_dotenv(candidate).items():
                    os.environ.setdefault(k, v)


def write_deploy_config(target_dir: Path, *, host: str, user: str) -> Path:
    example = (target_dir / "deploy.config.example.env").read_text(encoding="utf-8")
    merged = parse_dotenv(target_dir / "deploy.config.env")
    merged["AQ_LIGHTSAIL_HOST"] = host
    merged["AQ_LIGHTSAIL_INSTANCE_NAME"] = ""
    merged["AQ_LIGHTSAIL_USER"] = user
    merged["AQ_LIGHTSAIL_KEY"] = "secrets/lightsail-key.pem"
    lines: list[str] = []
    for line in example.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            lines.append(line)
            continue
        k = s.partition("=")[0].strip()
        lines.append(f"{k}={merged.get(k, s.partition('=')[2].strip())}")
    out = target_dir / "deploy.config.env"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out


def apply_from_dotenv(*, dry_run: bool) -> int:
    root = pulsegrid_root()
    ddir = deploy_dir()
    load_env_files(root)

    ssh_host = (os.getenv("SSH_HOST") or "").strip()
    ssh_user = (os.getenv("SSH_USER") or "bitnami").strip()
    key_file = (os.getenv("SSH_KEY_FILE") or "").strip()
    key_content = (os.getenv("SSH_KEY_CONTENT") or "").strip()

    if not ssh_host:
        print("ERROR: Set SSH_HOST in repo .env", file=sys.stderr)
        return 1
    if not key_file and not key_content:
        print("ERROR: Set SSH_KEY_FILE or SSH_KEY_CONTENT in repo .env", file=sys.stderr)
        return 1

    if key_content:
        key_body = key_content.replace("\\n", "\n")
    else:
        kp = Path(key_file)
        if not kp.is_absolute():
            kp = (root.parent / key_file).resolve() if not kp.is_file() else kp.resolve()
            if not kp.is_file():
                kp = (root / key_file).resolve()
        if not kp.is_file():
            print(f"ERROR: SSH key not found: {kp}", file=sys.stderr)
            return 1
        key_body = kp.read_text(encoding="utf-8")

    dest_key = ddir / "secrets" / "lightsail-key.pem"
    print(f"Deploy dir: {ddir}")
    print(f"Host: {ssh_host}  User: {ssh_user}")

    if dry_run:
        print("[dry-run] no files written")
        return 0

    dest_key.parent.mkdir(parents=True, exist_ok=True)
    dest_key.write_text(key_body, encoding="utf-8", newline="\n")
    cfg = write_deploy_config(ddir, host=ssh_host, user=ssh_user)
    print(f"Wrote {cfg} and {dest_key.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-dotenv", action="store_true", help="Fill deploy.config.env from SSH_* in .env")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.from_dotenv:
        ap.print_help()
        return 0
    return apply_from_dotenv(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
