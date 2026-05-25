from __future__ import annotations

import importlib
import os


def test_bronze_under_data_root_when_env_set(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("PULSEGRID_DATA_ROOT", str(tmp_path / "dbfs"))
    monkeypatch.delenv("PULSEGRID_BRONZE_ROOT", raising=False)
    import pulsegrid.config as cfg

    importlib.reload(cfg)
    assert cfg.BRONZE == tmp_path / "dbfs" / "bronze"
    assert cfg.DATA_ROOT == tmp_path / "dbfs"
