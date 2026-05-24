"""Last pipeline run metadata for ops console and Databricks jobs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pulsegrid.config import GENERATED


def status_path() -> Path:
    return GENERATED / "platform" / "last_pipeline_run.json"


def write_pipeline_status(
    *,
    job: str,
    metros_ok: int,
    metros_failed: int,
    detail: str = "",
    extra: dict[str, Any] | None = None,
) -> Path:
    path = status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "job": job,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "metros_ok": metros_ok,
        "metros_failed": metros_failed,
        "detail": detail,
        **(extra or {}),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_pipeline_status() -> dict[str, Any] | None:
    path = status_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
