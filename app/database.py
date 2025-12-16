"""Async database connection helper for PostgreSQL via Aiven."""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg

from app.config import get_dsn


@asynccontextmanager
async def get_connection(dsn: str) -> AsyncGenerator[asyncpg.Connection, None]:
    """Create an async PostgreSQL connection with conditional SSL."""
    # Use SSL for remote connections, disable for local development
    ssl_mode = (
        "require"
        if not any(
            local_host in dsn.lower() for local_host in ["localhost", "127.0.0.1", "postgres:"]
        )
        else None
    )
    conn = await asyncpg.connect(dsn=dsn, ssl=ssl_mode)
    try:
        yield conn
    finally:
        await conn.close()


async def test_connection() -> dict:
    """Test connection to the database and return connection info."""
    dsn = get_dsn()
    if not dsn:
        return {"success": False, "error": "No database connection string configured"}

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


async def measure_latency(iterations: int = 5) -> dict:
    """Measure latency to the database over multiple iterations."""
    dsn = get_dsn()
    if not dsn:
        return {"success": False, "error": "No database connection string configured"}

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


async def load_test(concurrent: int = 10) -> dict:
    """Run a load test with concurrent connections."""
    dsn = get_dsn()
    if not dsn:
        return {"success": False, "error": "No database connection string configured"}

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


async def get_health_metrics() -> dict:
    """Get database health metrics including cache hit ratio and connections."""
    dsn = get_dsn()
    if not dsn:
        return {"success": False, "error": "No database connection string configured"}

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
                result["cache_hit_ratio"] = (
                    float(cache_result["cache_hit_ratio"]) if cache_result["cache_hit_ratio"] else 0
                )
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
                              AND query NOT LIKE '%<insufficient privilege>%'
                            ORDER BY calls DESC
                            LIMIT 10
                            """
                        )

                        pg_stat_statements = []
                        for row in pg_stat_result:
                            try:
                                pg_stat_statements.append(
                                    {
                                        "query": row["query_preview"]
                                        + ("..." if len(row["query_preview"]) >= 150 else ""),
                                        "calls": int(row["calls"]),
                                        "total_time_ms": round(float(row["total_exec_time"]), 2),
                                        "mean_time_ms": round(float(row["mean_exec_time"]), 2),
                                        "max_time_ms": round(float(row["max_exec_time"]), 2),
                                        "cache_hit_pct": (
                                            round(float(row["cache_hit_pct"]), 2)
                                            if row["cache_hit_pct"]
                                            else None
                                        ),
                                        "shared_blks_hit": int(row["shared_blks_hit"]),
                                        "shared_blks_read": int(row["shared_blks_read"]),
                                    }
                                )
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
        if all(
            v is None
            for k, v in result.items()
            if k
            not in ["success", "warnings", "pg_stat_statements", "pg_stat_statements_available"]
        ):
            result["success"] = False
            result["error"] = "Unable to retrieve any health metrics. " + "; ".join(
                result["warnings"]
            )

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


async def test_database() -> dict:
    """Test database connection and return result."""
    result = await test_connection()
    return result


async def save_connection_check(result: dict, user_key: str | None = None) -> None:
    """Save connection check result to database."""
    dsn = get_dsn()
    if not dsn:
        return

    try:
        async with get_connection(dsn) as conn:
            await conn.execute(
                """
                INSERT INTO connection_checks (
                    region_id, success, latency_ms, server_ip, backend_pid,
                    pg_version, error_message, user_key
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                "database",
                result.get("success", False),
                result.get("latency_ms"),
                result.get("server_ip"),
                result.get("backend_pid"),
                result.get("pg_version"),
                result.get("error"),
                user_key,
            )
    except Exception as e:
        # Log error but don't fail request (table might not exist yet)
        import logging

        logging.warning(f"Failed to save connection check: {e}")


async def save_latency_check(result: dict, user_key: str | None = None) -> None:
    """Save latency check result to database."""
    dsn = get_dsn()
    if not dsn:
        return

    try:
        async with get_connection(dsn) as conn:
            # Convert timings list to JSON
            import json

            timings_json = json.dumps(result.get("timings", []))

            await conn.execute(
                """
                INSERT INTO latency_checks (
                    region_id, success, iterations, min_ms, max_ms, avg_ms,
                    timings, error_message, user_key
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                "database",
                result.get("success", False),
                result.get("iterations"),
                result.get("min_ms"),
                result.get("max_ms"),
                result.get("avg_ms"),
                timings_json,
                result.get("error"),
                user_key,
            )
    except Exception as e:
        import logging

        logging.warning(f"Failed to save latency check: {e}")


async def save_load_test_check(result: dict, user_key: str | None = None) -> None:
    """Save load test result to database."""
    dsn = get_dsn()
    if not dsn:
        return

    try:
        async with get_connection(dsn) as conn:
            await conn.execute(
                """
                INSERT INTO load_test_checks (
                    region_id, success, concurrent_connections, min_ms, max_ms,
                    avg_ms, total_time_ms, queries_per_second, error_message, user_key
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                "database",
                result.get("success", False),
                result.get("concurrent"),
                result.get("min_ms"),
                result.get("max_ms"),
                result.get("avg_ms"),
                result.get("total_time_ms"),
                result.get("queries_per_second"),
                result.get("error"),
                user_key,
            )
    except Exception as e:
        import logging

        logging.warning(f"Failed to save load test check: {e}")


async def save_health_metrics_check(result: dict, user_key: str | None = None) -> None:
    """Save health metrics check result to database."""
    dsn = get_dsn()
    if not dsn:
        return

    try:
        async with get_connection(dsn) as conn:
            # Convert warnings list to JSON
            import json

            warnings_json = json.dumps(result.get("warnings", []))

            await conn.execute(
                """
                INSERT INTO health_metrics_checks (
                    region_id, success, cache_hit_ratio, active_connections,
                    idle_connections, total_connections, db_size,
                    pg_stat_statements_available, warnings, error_message, user_key
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                "database",
                result.get("success", False),
                result.get("cache_hit_ratio"),
                result.get("active_connections"),
                result.get("idle_connections"),
                result.get("total_connections"),
                result.get("db_size"),
                result.get("pg_stat_statements_available", False),
                warnings_json,
                result.get("error"),
                user_key,
            )
    except Exception as e:
        import logging

        logging.warning(f"Failed to save health metrics check: {e}")


async def get_recent_connection_checks(limit: int = 10) -> list[dict]:
    """Get recent connection check history."""
    dsn = get_dsn()
    if not dsn:
        return []

    try:
        async with get_connection(dsn) as conn:
            rows = await conn.fetch(
                """
                SELECT
                    id, region_id, checked_at, success, latency_ms,
                    server_ip, backend_pid, error_message
                FROM connection_checks
                ORDER BY checked_at DESC
                LIMIT $1
                """,
                limit,
            )

            return [dict(row) for row in rows]
    except Exception:
        return []


async def get_connection_check_summary() -> dict:
    """Get summary statistics for connection checks in the last 24 hours."""
    dsn = get_dsn()
    if not dsn:
        return {}

    try:
        async with get_connection(dsn) as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM recent_connection_checks
                WHERE region_id = $1
                """,
                "database",
            )

            return dict(row) if row else {}
    except Exception:
        return {}


async def get_all_recent_checks(limit: int = 20) -> list[dict]:
    """Get recent checks across all regions combined, sorted by timestamp."""
    dsn = get_dsn()
    if not dsn:
        return []

    try:
        async with get_connection(dsn) as conn:
            # Get all types of checks across all regions
            rows = await conn.fetch(
                """
                SELECT
                    'connection' as check_type,
                    region_id,
                    checked_at,
                    success,
                    latency_ms as metric_value,
                    'ms' as metric_unit,
                    error_message,
                    user_key
                FROM connection_checks

                UNION ALL

                SELECT
                    'latency' as check_type,
                    region_id,
                    checked_at,
                    success,
                    avg_ms as metric_value,
                    'ms' as metric_unit,
                    error_message,
                    user_key
                FROM latency_checks

                UNION ALL

                SELECT
                    'load_test' as check_type,
                    region_id,
                    checked_at,
                    success,
                    queries_per_second as metric_value,
                    'qps' as metric_unit,
                    error_message,
                    user_key
                FROM load_test_checks

                UNION ALL

                SELECT
                    'health' as check_type,
                    region_id,
                    checked_at,
                    success,
                    cache_hit_ratio as metric_value,
                    '%' as metric_unit,
                    error_message,
                    user_key
                FROM health_metrics_checks

                ORDER BY checked_at DESC
                LIMIT $1
                """,
                limit,
            )

            return [dict(row) for row in rows]
    except Exception:
        # Table might not exist yet
        return []
