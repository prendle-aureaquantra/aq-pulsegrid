"""Sedona / PulseGrid geo UDF tests."""

from __future__ import annotations

import os

import pytest

from pulsegrid.geo.sedona_hex import (
    haversine_m,
    nearest_hex_id,
    register_sedona_hex_udfs,
)


def test_nearest_hex_loop():
    assert nearest_hex_id(41.8819, -87.6278) == "hex_837_941"


def test_haversine_positive():
    d = haversine_m(41.88, -87.63, 41.79, -87.59)
    assert 10_000 < d < 20_000


@pytest.mark.skipif(os.name == "nt", reason="Spark Python UDF pickling flaky on Windows")
def test_register_udfs_local_spark():
    from pulsegrid.spark_session import build_spark

    spark = build_spark("test-sedona-udf")
    try:
        assert register_sedona_hex_udfs(spark) is True
        row = spark.sql(
            "SELECT pulsegrid_nearest_hex_id(41.8819, -87.6278) AS hex_id"
        ).collect()[0]
        assert row.hex_id == "hex_837_941"
        row2 = spark.sql(
            "SELECT pulsegrid_geodesic_m(41.88, -87.63, 41.88, -87.63) AS d"
        ).collect()[0]
        assert row2.d == 0.0
    finally:
        spark.stop()
