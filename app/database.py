"""Async database connection helper for PostgreSQL via Aiven."""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from app.config import get_dsn


@asynccontextmanager
async def get_connection(dsn: str) -> AsyncGenerator[asyncpg.Connection, None]:
    """Create an async PostgreSQL connection with SSL required for Aiven."""
    conn = await asyncpg.connect(dsn=dsn, ssl="require")
    try:
        yield conn
    finally:
        await conn.close()


async def test_connection(region_id: str) -> dict:
    """Test connection to a specific region and return connection info."""
    dsn = get_dsn(region_id)
    if not dsn:
        return {"success": False, "error": f"No connection string for region: {region_id}"}

    try:
        start = time.perf_counter()
        async with get_connection(dsn) as conn:
            result = await conn.fetchrow(
                """
                SELECT
                    inet_server_addr()::text AS server_ip,
                    pg_backend_pid() AS backend_pid,
                    version() AS pg_version
                """
            )
            latency_ms = (time.perf_counter() - start) * 1000

        return {
            "success": True,
            "server_ip": result["server_ip"],
            "backend_pid": result["backend_pid"],
            "pg_version": result["pg_version"],
            "latency_ms": round(latency_ms, 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def measure_latency(region_id: str, iterations: int = 5) -> dict:
    """Measure latency to a region over multiple iterations."""
    dsn = get_dsn(region_id)
    if not dsn:
        return {"success": False, "error": f"No connection string for region: {region_id}"}

    try:
        timings = []
        for _ in range(iterations):
            start = time.perf_counter()
            async with get_connection(dsn) as conn:
                await conn.fetchval("SELECT 1")
            timings.append((time.perf_counter() - start) * 1000)

        return {
            "success": True,
            "iterations": iterations,
            "min_ms": round(min(timings), 2),
            "max_ms": round(max(timings), 2),
            "avg_ms": round(sum(timings) / len(timings), 2),
            "timings": [round(t, 2) for t in timings],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def load_test(region_id: str, concurrent: int = 10) -> dict:
    """Run a load test with concurrent connections."""
    dsn = get_dsn(region_id)
    if not dsn:
        return {"success": False, "error": f"No connection string for region: {region_id}"}

    async def single_query():
        start = time.perf_counter()
        async with get_connection(dsn) as conn:
            await conn.fetchval("SELECT 1")
        return (time.perf_counter() - start) * 1000

    try:
        start_total = time.perf_counter()
        tasks = [single_query() for _ in range(concurrent)]
        timings = await asyncio.gather(*tasks)
        total_time = (time.perf_counter() - start_total) * 1000

        return {
            "success": True,
            "concurrent": concurrent,
            "min_ms": round(min(timings), 2),
            "max_ms": round(max(timings), 2),
            "avg_ms": round(sum(timings) / len(timings), 2),
            "total_time_ms": round(total_time, 2),
            "queries_per_second": round(concurrent / (total_time / 1000), 2),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _is_privilege_error(error_msg: str) -> bool:
    """Check if an error message indicates insufficient privileges."""
    error_lower = error_msg.lower()
    privilege_indicators = [
        "permission denied",
        "insufficient privilege",
        "must be superuser",
        "access denied",
        "must be owner",
        "privilege",
        "not authorized",
    ]
    return any(indicator in error_lower for indicator in privilege_indicators)


async def get_health_metrics(region_id: str) -> dict:
    """Get database health metrics including cache hit ratio and connections."""
    dsn = get_dsn(region_id)
    if not dsn:
        return {"success": False, "error": f"No connection string for region: {region_id}"}

    result = {
        "success": True,
        "cache_hit_ratio": None,
        "active_connections": None,
        "idle_connections": None,
        "total_connections": None,
        "db_size": None,
        "pg_stat_statements": None,
        "pg_stat_statements_available": False,
        "warnings": [],
    }

    try:
        async with get_connection(dsn) as conn:
            # Get cache hit ratio
            try:
                cache_result = await conn.fetchrow(
                    """
                    SELECT
                        ROUND(
                            CASE
                                WHEN blks_hit + blks_read = 0 THEN 0::numeric
                                ELSE (blks_hit::numeric / (blks_hit + blks_read) * 100)
                            END, 2
                        ) AS cache_hit_ratio
                    FROM pg_stat_database
                    WHERE datname = current_database()
                    """
                )
                result["cache_hit_ratio"] = float(cache_result["cache_hit_ratio"]) if cache_result["cache_hit_ratio"] else 0
            except Exception as e:
                error_msg = str(e)
                if _is_privilege_error(error_msg):
                    result["warnings"].append("Cache hit ratio: insufficient privileges")
                else:
                    result["warnings"].append(f"Cache hit ratio: {error_msg}")

            # Get active connections
            try:
                conn_result = await conn.fetchrow(
                    """
                    SELECT
                        count(*) FILTER (WHERE state = 'active') AS active_connections,
                        count(*) FILTER (WHERE state = 'idle') AS idle_connections,
                        count(*) AS total_connections
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    """
                )
                result["active_connections"] = conn_result["active_connections"]
                result["idle_connections"] = conn_result["idle_connections"]
                result["total_connections"] = conn_result["total_connections"]
            except Exception as e:
                error_msg = str(e)
                if _is_privilege_error(error_msg):
                    result["warnings"].append("Connection stats: insufficient privileges")
                else:
                    result["warnings"].append(f"Connection stats: {error_msg}")

            # Get database size
            try:
                size_result = await conn.fetchrow(
                    """
                    SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size
                    """
                )
                result["db_size"] = size_result["db_size"]
            except Exception as e:
                error_msg = str(e)
                if _is_privilege_error(error_msg):
                    result["warnings"].append("Database size: insufficient privileges")
                else:
                    result["warnings"].append(f"Database size: {error_msg}")

            # Get pg_stat_statements data (if extension is enabled)
            try:
                # Check if pg_stat_statements extension exists
                ext_check = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
                )
                
                if ext_check:
                    try:
                        pg_stat_result = await conn.fetch(
                            """
                            SELECT 
                                LEFT(query, 150) AS query_preview,
                                calls,
                                total_exec_time,
                                mean_exec_time,
                                max_exec_time,
                                ROUND((100.0 * shared_blks_hit / NULLIF(shared_blks_hit + shared_blks_read, 0))::numeric, 2) AS cache_hit_pct,
                                shared_blks_hit,
                                shared_blks_read
                            FROM pg_stat_statements
                            WHERE query NOT LIKE '%pg_stat_statements%'
                              AND query NOT LIKE '%pg_catalog%'
                            ORDER BY calls DESC
                            LIMIT 10
                            """
                        )
                        
                        pg_stat_statements = []
                        for row in pg_stat_result:
                            try:
                                pg_stat_statements.append({
                                    "query": row["query_preview"] + ("..." if len(row["query_preview"]) >= 150 else ""),
                                    "calls": row["calls"],
                                    "total_time_ms": round(row["total_exec_time"], 2),
                                    "mean_time_ms": round(row["mean_exec_time"], 2),
                                    "max_time_ms": round(row["max_exec_time"], 2),
                                    "cache_hit_pct": round(row["cache_hit_pct"], 2) if row["cache_hit_pct"] else None,
                                    "shared_blks_hit": row["shared_blks_hit"],
                                    "shared_blks_read": row["shared_blks_read"],
                                })
                            except Exception:
                                # Skip rows with privilege issues
                                continue
                        
                        result["pg_stat_statements"] = pg_stat_statements
                        result["pg_stat_statements_available"] = True
                    except Exception as pg_stat_error:
                        error_msg = str(pg_stat_error)
                        if _is_privilege_error(error_msg):
                            result["warnings"].append("pg_stat_statements: insufficient privileges")
                            result["pg_stat_statements_available"] = False
                        else:
                            result["warnings"].append(f"pg_stat_statements: {error_msg}")
                            result["pg_stat_statements_available"] = False
                else:
                    result["pg_stat_statements_available"] = False
            except Exception as ext_error:
                error_msg = str(ext_error)
                if _is_privilege_error(error_msg):
                    result["warnings"].append("Extension check: insufficient privileges")
                else:
                    result["warnings"].append(f"Extension check: {error_msg}")
                result["pg_stat_statements_available"] = False

        # Only mark as failed if we couldn't get any data at all
        if all(v is None for k, v in result.items() if k not in ["success", "warnings", "pg_stat_statements", "pg_stat_statements_available"]):
            result["success"] = False
            result["error"] = "Unable to retrieve any health metrics. " + "; ".join(result["warnings"])

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def test_all_regions(region_ids: list[str]) -> dict:
    """Test all regions concurrently and return results ranked by latency."""
    tasks = [test_connection(region_id) for region_id in region_ids]
    results = await asyncio.gather(*tasks)

    region_results = []
    for region_id, result in zip(region_ids, results):
        result["region_id"] = region_id
        region_results.append(result)

    # Sort by latency (successful ones first, then by latency)
    region_results.sort(
        key=lambda x: (not x["success"], x.get("latency_ms", float("inf")))
    )

    return {"results": region_results}
