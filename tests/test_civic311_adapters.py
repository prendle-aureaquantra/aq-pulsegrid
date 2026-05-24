"""Civic 311 multi-adapter fetch tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pulsegrid.ingest.civic311 import fetch_arcgis_311, fetch_carto_311, fetch_socrata_311


def test_fetch_socrata_list_response():
    cfg = {"url": "https://example.com/resource/x.json", "limit": 10}
    mock_resp = MagicMock()
    mock_resp.json.return_value = [{"id": 1}]
    mock_resp.raise_for_status = MagicMock()
    with patch("pulsegrid.ingest.civic311.requests.get", return_value=mock_resp):
        rows = fetch_socrata_311(cfg)
    assert len(rows) == 1


def test_fetch_arcgis_features():
    cfg = {
        "url": "https://example.com/arcgis/query",
        "where": "1=1",
        "recent_days": 0,
        "limit": 5,
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "features": [{"attributes": {"CaseNumber": "1", "CaseType": "Pothole"}}]
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("pulsegrid.ingest.civic311.requests.get", return_value=mock_resp):
        rows = fetch_arcgis_311(cfg)
    assert rows[0]["CaseType"] == "Pothole"


def test_fetch_carto_rows():
    cfg = {
        "url": "https://phl.carto.com/api/v2/sql",
        "table": "public_cases_fc",
        "date_field": "requested_datetime",
        "recent_days": 7,
        "limit": 3,
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"rows": [{"service_request_type": "GRAFFITI"}]}
    mock_resp.raise_for_status = MagicMock()
    with patch("pulsegrid.ingest.civic311.requests.get", return_value=mock_resp):
        rows = fetch_carto_311(cfg)
    assert rows[0]["service_request_type"] == "GRAFFITI"
