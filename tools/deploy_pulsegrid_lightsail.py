#!/usr/bin/env python3
"""
One-shot deploy for AQ PulseGrid status app on Lightsail.

1. Fills deploy/lightsail/deploy.config.env + secrets/lightsail-key.pem from
   monorepo .env (SSH_HOST, SSH_USER, SSH_KEY_FILE or SSH_KEY_CONTENT).
2. Runs deploy/lightsail/deploy.ps1 (Windows) or deploy.sh (Unix).

Examples:
  python tools/deploy_pulsegrid_lightsail.py
  python tools/deploy_pulsegrid_lightsail.py --from-dotenv
  python tools/deploy_pulsegrid_lightsail.py --dry-run
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


def pulsegrid_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_prepare():
    path = pulsegrid_root() / "tools" / "prepare_pulsegrid_deploy.py"
    spec = importlib.util.spec_from_file_location("prepare_pulsegrid_deploy", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def config_incomplete(deploy_dir: Path, parse_dotenv) -> bool:
    env_path = deploy_dir / "deploy.config.env"
    key_path = deploy_dir / "secrets" / "lightsail-key.pem"
    if not env_path.is_file() or not key_path.is_file():
        return True
    d = parse_dotenv(env_path)
    return (
        not (d.get("AQ_LIGHTSAIL_HOST") or "").strip()
        and not (d.get("AQ_LIGHTSAIL_INSTANCE_NAME") or "").strip()
    )


def run_deploy(deploy_dir: Path, *, dry_run: bool, skip_publish: bool) -> int:
    if sys.platform == "win32":
        ps1 = deploy_dir / "deploy.ps1"
        exe = next((c for c in ("pwsh", "powershell") if shutil.which(c)), None)
        if not exe:
            print("Need pwsh or powershell.", file=sys.stderr)
            return 1
        cmd = [exe, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)]
        if skip_publish:
            cmd.append("-SkipPublish")
        if dry_run:
            cmd.append("-DryRun")
        print("Running:", " ".join(cmd))
        return subprocess.call(cmd, cwd=str(deploy_dir))

    sh = deploy_dir / "deploy.sh"
    bash = shutil.which("bash")
    if not bash:
        print("Need bash for deploy.sh", file=sys.stderr)
        return 1
    cmd = [bash, str(sh)]
    if dry_run:
        cmd.append("--dry-run")
    if skip_publish:
        cmd.append("--skip-publish")
    st = os.stat(sh)
    os.chmod(sh, st.st_mode | 0o111)
    return subprocess.call(cmd, cwd=str(deploy_dir))


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--from-dotenv", action="store_true")
    ap.add_argument("--no-auto-prepare", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-publish", action="store_true")
    args = ap.parse_args()

    prep = load_prepare()
    prep.load_env_files(pulsegrid_root())
    deploy_dir = prep.deploy_dir()

    want = args.from_dotenv or (
        not args.no_auto_prepare and config_incomplete(deploy_dir, prep.parse_dotenv)
    )
    if want and args.dry_run:
        print(
            "ERROR: run once without --dry-run to write deploy.config.env first.",
            file=sys.stderr,
        )
        return 2
    if want:
        rc = prep.apply_from_dotenv(dry_run=False)
        if rc != 0:
            return rc
    if config_incomplete(deploy_dir, prep.parse_dotenv):
        print("Deploy config incomplete.", file=sys.stderr)
        return 1
    return run_deploy(deploy_dir, dry_run=args.dry_run, skip_publish=args.skip_publish)


if __name__ == "__main__":
    raise SystemExit(main())
