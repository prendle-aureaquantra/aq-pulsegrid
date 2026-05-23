"""Tests for bronze ingest (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pulsegrid.config import get_city
from pulsegrid.ingest.noaa import fetch_active_alerts


def test_noaa_alerts_shape():
    city = get_city("chicago")
    fake = {"features": [{"id": "alert-1"}]}
    with patch("pulsegrid.ingest.noaa.requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: fake)
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_active_alerts(city)
    assert result["source"] == "noaa_nws_alerts"
    assert result["feature_count"] == 1
    assert result["city"] == "chicago"
