"""Data API routes — table catalog, generic CSV access, domain bundles."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

try:
    from csv_store import (
        DEFAULT_PAGE_SIZE,
        DOMAIN_TABLES,
        MAX_PAGE_SIZE,
        list_tables,
        query_domain,
        query_table,
        resolve_table,
    )
except ImportError:
    from pulsegrid.web.csv_store import (  # type: ignore[no-redef]
        DEFAULT_PAGE_SIZE,
        DOMAIN_TABLES,
        MAX_PAGE_SIZE,
        list_tables,
        query_domain,
        query_table,
        resolve_table,
    )

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/data")
def api_data_catalog() -> JSONResponse:
    return JSONResponse({"tables": list_tables(available_only=True)})


@router.get("/data/{table_slug}")
def api_data_table(
    table_slug: str,
    metro: str = Query(default=""),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
) -> JSONResponse:
    table = resolve_table(table_slug)
    if not table:
        raise HTTPException(status_code=404, detail=f"Unknown table slug: {table_slug}")
    result = query_table(table, metro=metro, limit=limit, offset=offset)
    if "error" in result:
        raise HTTPException(status_code=404, detail=str(result["error"]))
    return JSONResponse(result)


@router.get("/weather")
def api_weather(
    metro: str = Query(default=""),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> JSONResponse:
    return JSONResponse(query_domain("weather", metro=metro, limit=limit))


@router.get("/infrastructure")
def api_infrastructure(
    metro: str = Query(default=""),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> JSONResponse:
    return JSONResponse(query_domain("infrastructure", metro=metro, limit=limit))


@router.get("/events")
def api_events(
    metro: str = Query(default=""),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> JSONResponse:
    return JSONResponse(query_domain("events", metro=metro, limit=limit))


@router.get("/airport")
def api_airport(
    metro: str = Query(default=""),
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> JSONResponse:
    return JSONResponse(query_domain("airport", metro=metro, limit=limit))


@router.get("/domains")
def api_domains() -> JSONResponse:
    return JSONResponse(
        {
            "domains": [
                {
                    "domain": name,
                    "tables": tables,
                    "endpoint": f"/api/{name}",
                }
                for name, tables in sorted(DOMAIN_TABLES.items())
            ]
        }
    )
