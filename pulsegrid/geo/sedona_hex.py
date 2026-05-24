"""Apache Sedona + PulseGrid geospatial UDFs for Spark (hex assignment, distance)."""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from pulsegrid.geo.hex_grid import (
    REF_HEX,
    _load_hex_centroids,
    CITYWIDE_HEX_ID,
    CITYWIDE_NEIGHBORHOOD,
    chicago_default_hex,
    lat_lon_to_hex,
    neighborhood_to_hex,
)

EARTH_RADIUS_M = 6_371_000.0


def sedona_available() -> bool:
    try:
        import sedona.spark  # noqa: F401

        return True
    except ImportError:
        return False


def init_sedona(spark) -> bool:
    """Register Sedona SQL functions on the Spark session. Returns True if Sedona loaded."""
    try:
        from sedona.spark import SedonaContext

        SedonaContext.create(spark)
        return True
    except ImportError:
        return False


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters (WGS84)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


@lru_cache(maxsize=1)
def _centroid_tuples() -> tuple[tuple[str, str, float, float], ...]:
    return tuple(
        (
            str(row["hex_id"]),
            str(row.get("neighborhood", "")),
            float(row["lat"]),
            float(row["lon"]),
        )
        for row in _load_hex_centroids()
    )


def nearest_hex_id(lat: float, lon: float) -> str:
    """Snap a WGS84 point to the nearest reference hex centroid."""
    centroids = _centroid_tuples()
    if not centroids:
        return lat_lon_to_hex(lat, lon)
    best_id = centroids[0][0]
    best_d = float("inf")
    for hex_id, _name, clat, clon in centroids:
        d = haversine_m(lat, lon, clat, clon)
        if d < best_d:
            best_d = d
            best_id = hex_id
    return best_id


def udf_nearest_hex(lat, lon):
    if lat is None or lon is None:
        return chicago_default_hex()
    return nearest_hex_id(float(lat), float(lon))


def udf_grid_hex(lat, lon, precision=0.05):
    if lat is None or lon is None:
        return chicago_default_hex()
    return lat_lon_to_hex(float(lat), float(lon), precision=float(precision))


def udf_geodesic_m(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    return haversine_m(float(lat1), float(lon1), float(lat2), float(lon2))


def udf_neighborhood_hex(name: str | None) -> str | None:
    if not name:
        return None
    return neighborhood_to_hex(str(name))


def register_sedona_hex_udfs(spark) -> bool:
    """Register PulseGrid geo UDFs; enable Sedona when the jar is on the classpath."""
    from pyspark.sql.types import DoubleType, StringType

    sedona_on = init_sedona(spark)

    spark.udf.register("pulsegrid_nearest_hex_id", udf_nearest_hex, StringType())
    spark.udf.register("pulsegrid_lat_lon_to_hex", udf_grid_hex, StringType())
    spark.udf.register("pulsegrid_geodesic_m", udf_geodesic_m, DoubleType())
    spark.udf.register("pulsegrid_neighborhood_to_hex", udf_neighborhood_hex, StringType())

    return True


def hex_reference_dataframe(spark):
    """Chicago reference hex centroids as a Spark DataFrame."""
    rows = [
        {
            "hex_id": h,
            "neighborhood": n,
            "lat": lat,
            "lon": lon,
        }
        for h, n, lat, lon in _centroid_tuples()
    ]
    if not rows:
        return spark.createDataFrame([], "hex_id string, neighborhood string, lat double, lon double")
    return spark.createDataFrame(rows)


def neighborhood_lookup_dataframe(spark):
    """Lowercase neighborhood label → hex_id for Spark joins."""
    rows: list[dict[str, Any]] = []
    for hex_id, neighborhood, _lat, _lon in _centroid_tuples():
        key = neighborhood.strip().lower()
        if key:
            rows.append(
                {
                    "neighborhood_key": key,
                    "hex_id": hex_id,
                    "neighborhood": neighborhood,
                }
            )
    return spark.createDataFrame(rows)


def aggregate_transit_alerts_hex_spark(spark, city_slug: str, snapshot_at: str):
    """Roll up silver transit_alerts to gold hex_pulse_grid via Spark (+ optional Sedona)."""
    from pyspark.sql import functions as F

    from pulsegrid.config import DELTA

    register_sedona_hex_udfs(spark)
    transit_path = DELTA / "silver" / "transit_alerts"
    if not transit_path.exists():
        return None

    transit = (
        spark.read.format("delta")
        .load(str(transit_path))
        .filter(F.col("city") == city_slug)
    )
    if not transit.head(1):
        return None

    lookup = neighborhood_lookup_dataframe(spark)
    default_hex = chicago_default_hex()

    enriched = (
        transit.withColumn(
            "nh_key",
            F.lower(F.trim(F.coalesce(F.col("neighborhood_hint"), F.lit("")))),
        )
        .join(lookup, F.col("nh_key") == lookup["neighborhood_key"], "left")
        .withColumn(
            "hex_id",
            F.coalesce(
                F.col("hex_id"),
                F.when(F.length(F.col("nh_key")) > 0, F.lit(default_hex)).otherwise(
                    F.lit(CITYWIDE_HEX_ID)
                ),
            ),
        )
        .withColumn(
            "neighborhood",
            F.coalesce(
                F.col("neighborhood"),
                F.when(F.length(F.col("nh_key")) > 0, F.col("nh_key")).otherwise(
                    F.lit(CITYWIDE_NEIGHBORHOOD)
                ),
            ),
        )
    )

    return (
        enriched.groupBy("hex_id", "neighborhood")
        .agg(
            F.count("*").alias("alert_count"),
            F.sum(
                F.when(F.col("alert_category") == "reroute", 1).otherwise(0)
            ).alias("reroute_count"),
            F.sum(F.when(F.col("alert_category") == "delay", 1).otherwise(0)).alias(
                "delay_count"
            ),
        )
        .withColumn("city", F.lit(city_slug))
        .withColumn("snapshot_at", F.lit(snapshot_at))
    )


def enrich_lat_lon_hex(df, lat_col: str = "lat", lon_col: str = "lon"):
    """Add hex_id column using registered UDFs (Sedona nearest or grid fallback)."""
    from pyspark.sql import functions as F

    return df.withColumn(
        "hex_id",
        F.expr(f"pulsegrid_nearest_hex_id(`{lat_col}`, `{lon_col}`)"),
    )


def assign_hex_from_geometry_sql(df, geom_col: str = "geometry"):
    """Assign hex_id from a Sedona geometry column via ST_Centroid + nearest hex UDF."""
    from pyspark.sql import functions as F

    return df.withColumn(
        "hex_id",
        F.expr(
            f"pulsegrid_nearest_hex_id("
            f"ST_Y(ST_Centroid({geom_col})), ST_X(ST_Centroid({geom_col}))"
            f")"
        ),
    )
