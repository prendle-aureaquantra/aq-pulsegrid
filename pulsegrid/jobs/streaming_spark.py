"""PySpark Structured Streaming ingest (rate source → foreachBatch → Delta bronze log)."""

from __future__ import annotations

from datetime import datetime, timezone

from pulsegrid.config import DELTA, get_city
from pulsegrid.ingest.cta import ingest_cta
from pulsegrid.ingest.noaa import ingest_noaa
from pulsegrid.io.delta_writer import append_delta_table, use_spark_engine


def _event_row(city: str, source: str, path: str) -> dict:
    return {
        "city": city,
        "source": source,
        "bronze_path": str(path),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }


def run_structured_stream(
    city_slug: str,
    *,
    max_batches: int = 5,
    trigger_interval: str = "10 seconds",
) -> None:
    """Structured Streaming micro-batch: poll APIs each trigger, append ingest_events Delta."""
    if not use_spark_engine():
        raise RuntimeError(
            "Set PULSEGRID_ENGINE=spark for Structured Streaming "
            "(see spark/streaming/README.md)."
        )

    from pulsegrid.spark_session import build_spark

    city = get_city(city_slug)
    log_path = DELTA / "bronze" / "ingest_events"
    checkpoint = DELTA / "_checkpoints" / f"stream_ingest_{city_slug}"
    checkpoint.mkdir(parents=True, exist_ok=True)

    spark = build_spark(f"pulsegrid-stream-{city_slug}")

    def foreach_batch(_batch_df, batch_id: int) -> None:
        print(f"  structured batch {batch_id + 1}/{max_batches}")
        rows: list[dict] = []
        for source, paths in (
            ("noaa", ingest_noaa(city)),
            ("cta", ingest_cta(city)),
        ):
            for p in paths:
                rows.append(_event_row(city.slug, source, p))
                print(f"    {source} -> {p.name}")
        if rows:
            append_delta_table(rows, log_path)

    print(
        f"Structured Streaming: {max_batches} batches, trigger={trigger_interval}, "
        f"checkpoint={checkpoint}"
    )
    query = (
        spark.readStream.format("rate")
        .option("rowsPerSecond", 1)
        .load()
        .writeStream.foreachBatch(foreach_batch)
        .trigger(processingTime=trigger_interval)
        .option("checkpointLocation", str(checkpoint))
        .queryName(f"pulsegrid_ingest_{city_slug}")
        .start()
    )
    try:
        interval_sec = 10
        if trigger_interval.endswith(" seconds"):
            interval_sec = int(trigger_interval.split()[0])
        timeout_ms = (max_batches * interval_sec + 30) * 1000
        query.awaitTermination(timeout=timeout_ms)
    finally:
        if query.isActive:
            query.stop()
        spark.stop()
    print(f"  bronze.ingest_events -> {log_path}")
