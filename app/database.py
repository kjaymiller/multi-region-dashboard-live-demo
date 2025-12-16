"""Async database connection helper for PostgreSQL via Aiven."""

import asyncio
import ssl
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg

from app.config import get_dsn
from app.db_manager_postgres import DatabaseConnection


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
                                queryid,
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
                              AND queryid IS NOT NULL
                            ORDER BY calls DESC
                            LIMIT 10
                            """
                        )

                        pg_stat_statements = []
                        for row in pg_stat_result:
                            try:
                                pg_stat_statements.append(
                                    {
                                        "queryid": str(row["queryid"]) if row["queryid"] else None,
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


async def get_connection_health_metrics(
    connection: DatabaseConnection, timeout: float = 10.0
) -> dict:
    """Get health metrics for a specific database connection with timeout."""
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
        "connection_id": str(connection.id),
        "connection_name": connection.name,
        "host": connection.host,
        "port": connection.port,
        "database": connection.database,
    }

    try:
        # Password is already decrypted when retrieved from database
        password = connection.password

        # Use SSL for remote connections, disable for local development
        ssl_mode = (
            "require"
            if not any(
                local_host in connection.host.lower()
                for local_host in ["localhost", "127.0.0.1", "postgres"]
            )
            else None
        )

        # Build DSN with connection password
        if password:
            dsn = (
                f"postgresql://{connection.username}:{password}@"
                f"{connection.host}:{connection.port}/{connection.database}"
            )

            if ssl_mode:
                # Create SSL context that doesn't verify certificates (for testing with self-signed certs)
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                conn = await asyncio.wait_for(
                    asyncpg.connect(dsn, ssl=ssl_context), timeout=timeout
                )
            else:
                conn = await asyncio.wait_for(asyncpg.connect(dsn, ssl=False), timeout=timeout)
        else:
            # Fallback to connection testing if no password
            return {
                "success": False,
                "error": "No password provided for database connection",
                "connection_id": connection.id,
                "connection_name": connection.name,
            }

        try:
            # Get cache hit ratio
            try:
                cache_result = await asyncio.wait_for(
                    conn.fetchrow(
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
                    ),
                    timeout=timeout,
                )
                result["cache_hit_ratio"] = (
                    float(cache_result["cache_hit_ratio"]) if cache_result["cache_hit_ratio"] else 0
                )
            except asyncio.TimeoutError:
                result["warnings"].append("Cache hit ratio: query timeout")
            except Exception as e:
                error_msg = str(e)
                if _is_privilege_error(error_msg):
                    result["warnings"].append("Cache hit ratio: insufficient privileges")
                else:
                    result["warnings"].append(f"Cache hit ratio: {error_msg}")

            # Get active connections
            try:
                conn_result = await asyncio.wait_for(
                    conn.fetchrow(
                        """
                        SELECT
                            count(*) FILTER (WHERE state = 'active') AS active_connections,
                            count(*) FILTER (WHERE state = 'idle') AS idle_connections,
                            count(*) AS total_connections
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                        """
                    ),
                    timeout=timeout,
                )
                result["active_connections"] = conn_result["active_connections"]
                result["idle_connections"] = conn_result["idle_connections"]
                result["total_connections"] = conn_result["total_connections"]
            except asyncio.TimeoutError:
                result["warnings"].append("Connection stats: query timeout")
            except Exception as e:
                error_msg = str(e)
                if _is_privilege_error(error_msg):
                    result["warnings"].append("Connection stats: insufficient privileges")
                else:
                    result["warnings"].append(f"Connection stats: {error_msg}")

            # Get database size
            try:
                size_result = await asyncio.wait_for(
                    conn.fetchrow(
                        "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size"
                    ),
                    timeout=timeout,
                )
                result["db_size"] = size_result["db_size"]
            except asyncio.TimeoutError:
                result["warnings"].append("Database size: query timeout")
            except Exception as e:
                error_msg = str(e)
                if _is_privilege_error(error_msg):
                    result["warnings"].append("Database size: insufficient privileges")
                else:
                    result["warnings"].append(f"Database size: {error_msg}")

            # Get pg_stat_statements data (if extension is enabled)
            try:
                # Check if pg_stat_statements extension exists
                ext_check = await asyncio.wait_for(
                    conn.fetchval(
                        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements')"
                    ),
                    timeout=timeout,
                )

                if ext_check:
                    try:
                        pg_stat_result = await asyncio.wait_for(
                            conn.fetch(
                                """
                                SELECT
                                    queryid,
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
                                  AND queryid IS NOT NULL
                                ORDER BY calls DESC
                                LIMIT 10
                                """
                            ),
                            timeout=timeout,
                        )

                        pg_stat_statements = []
                        for row in pg_stat_result:
                            try:
                                pg_stat_statements.append(
                                    {
                                        "queryid": str(row["queryid"]) if row["queryid"] else None,
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
                    except asyncio.TimeoutError:
                        result["warnings"].append("pg_stat_statements: query timeout")
                        result["pg_stat_statements_available"] = False
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
            except asyncio.TimeoutError:
                result["warnings"].append("Extension check: query timeout")
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
                not in [
                    "success",
                    "warnings",
                    "pg_stat_statements",
                    "pg_stat_statements_available",
                    "connection_id",
                    "connection_name",
                    "host",
                    "port",
                    "database",
                ]
            ):
                result["success"] = False
                result["error"] = "Unable to retrieve any health metrics. " + "; ".join(
                    result["warnings"]
                )

            return result
        finally:
            await conn.close()

    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Connection timeout after {timeout} seconds",
            "connection_id": connection.id,
            "connection_name": connection.name,
            "warnings": ["Connection timeout"],
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "connection_id": connection.id,
            "connection_name": connection.name,
            "warnings": [f"Connection failed: {str(e)}"],
        }


async def measure_connection_latency(
    connection: DatabaseConnection, iterations: int = 5, timeout: float = 10.0
) -> dict:
    """Measure latency to a specific database connection over multiple iterations."""
    try:
        # Password is already decrypted when retrieved from database
        password = connection.password

        # Use SSL for remote connections, disable for local development
        ssl_mode = (
            "require"
            if not any(
                local_host in connection.host.lower()
                for local_host in ["localhost", "127.0.0.1", "postgres"]
            )
            else None
        )

        # Build DSN with connection password
        if not password:
            return {
                "success": False,
                "error": "No password provided for database connection",
                "connection_id": connection.id,
                "connection_name": connection.name,
            }

        dsn = (
            f"postgresql://{connection.username}:{password}@"
            f"{connection.host}:{connection.port}/{connection.database}"
        )

        timings = []
        for _ in range(iterations):
            start = time.perf_counter()

            if ssl_mode:
                # Create SSL context that doesn't verify certificates
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                conn = await asyncio.wait_for(
                    asyncpg.connect(dsn, ssl=ssl_context), timeout=timeout
                )
            else:
                conn = await asyncio.wait_for(asyncpg.connect(dsn, ssl=False), timeout=timeout)

            try:
                await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=timeout)
            finally:
                await conn.close()

            timings.append((time.perf_counter() - start) * 1000)

        return {
            "success": True,
            "iterations": iterations,
            "min_ms": round(min(timings), 2),
            "max_ms": round(max(timings), 2),
            "avg_ms": round(sum(timings) / len(timings), 2),
            "timings": [round(t, 2) for t in timings],
            "connection_id": connection.id,
            "connection_name": connection.name,
        }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Connection timeout after {timeout} seconds",
            "connection_id": connection.id,
            "connection_name": connection.name,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "connection_id": connection.id,
            "connection_name": connection.name,
        }


async def run_connection_load_test(
    connection: DatabaseConnection, concurrent: int = 10, timeout: float = 10.0
) -> dict:
    """Run a load test with concurrent connections to a specific database."""
    try:
        # Password is already decrypted when retrieved from database
        password = connection.password

        # Use SSL for remote connections, disable for local development
        ssl_mode = (
            "require"
            if not any(
                local_host in connection.host.lower()
                for local_host in ["localhost", "127.0.0.1", "postgres"]
            )
            else None
        )

        # Build DSN with connection password
        if not password:
            return {
                "success": False,
                "error": "No password provided for database connection",
                "connection_id": connection.id,
                "connection_name": connection.name,
            }

        dsn = (
            f"postgresql://{connection.username}:{password}@"
            f"{connection.host}:{connection.port}/{connection.database}"
        )

        async def single_query():
            start = time.perf_counter()

            if ssl_mode:
                # Create SSL context that doesn't verify certificates
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                conn = await asyncio.wait_for(
                    asyncpg.connect(dsn, ssl=ssl_context), timeout=timeout
                )
            else:
                conn = await asyncio.wait_for(asyncpg.connect(dsn, ssl=False), timeout=timeout)

            try:
                await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=timeout)
            finally:
                await conn.close()

            return (time.perf_counter() - start) * 1000

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
            "connection_id": connection.id,
            "connection_name": connection.name,
        }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": f"Connection timeout after {timeout} seconds",
            "connection_id": connection.id,
            "connection_name": connection.name,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "connection_id": connection.id,
            "connection_name": connection.name,
        }


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
        import json

        async with get_connection(dsn) as conn:
            # Store additional data in test_data JSONB column
            test_data = {"user_key": user_key} if user_key else {}

            await conn.execute(
                """
                INSERT INTO connection_tests (
                    connection_id, test_type, success, latency_ms, server_ip,
                    backend_pid, pg_version, error_message, test_data
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                result.get("connection_id"),
                "connection",
                result.get("success", False),
                result.get("latency_ms"),
                result.get("server_ip"),
                result.get("backend_pid"),
                result.get("pg_version"),
                result.get("error"),
                json.dumps(test_data),
            )
    except Exception as e:
        import logging

        logging.warning(f"Failed to save connection check: {e}")


async def save_latency_check(result: dict, user_key: str | None = None) -> None:
    """Save latency check result to database."""
    dsn = get_dsn()
    if not dsn:
        return

    try:
        import json

        async with get_connection(dsn) as conn:
            # Store latency-specific data in test_data JSONB column
            test_data = {
                "iterations": result.get("iterations"),
                "min_ms": result.get("min_ms"),
                "max_ms": result.get("max_ms"),
                "timings": result.get("timings", []),
            }
            if user_key:
                test_data["user_key"] = user_key

            await conn.execute(
                """
                INSERT INTO connection_tests (
                    connection_id, test_type, success, latency_ms,
                    error_message, test_data
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                result.get("connection_id"),
                "latency",
                result.get("success", False),
                result.get("avg_ms"),  # Use avg_ms as the main latency value
                result.get("error"),
                json.dumps(test_data),
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
        import json

        async with get_connection(dsn) as conn:
            # Store load test-specific data in test_data JSONB column
            test_data = {
                "concurrent_connections": result.get("concurrent"),
                "min_ms": result.get("min_ms"),
                "max_ms": result.get("max_ms"),
                "total_time_ms": result.get("total_time_ms"),
                "queries_per_second": result.get("queries_per_second"),
            }
            if user_key:
                test_data["user_key"] = user_key

            await conn.execute(
                """
                INSERT INTO connection_tests (
                    connection_id, test_type, success, latency_ms,
                    error_message, test_data
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                result.get("connection_id"),
                "load",
                result.get("success", False),
                result.get("avg_ms"),  # Use avg_ms as the main latency value
                result.get("error"),
                json.dumps(test_data),
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
        import json

        async with get_connection(dsn) as conn:
            # Store health metrics-specific data in test_data JSONB column
            test_data = {
                "cache_hit_ratio": result.get("cache_hit_ratio"),
                "active_connections": result.get("active_connections"),
                "idle_connections": result.get("idle_connections"),
                "total_connections": result.get("total_connections"),
                "db_size": result.get("db_size"),
                "pg_stat_statements_available": result.get("pg_stat_statements_available", False),
                "warnings": result.get("warnings", []),
            }
            if user_key:
                test_data["user_key"] = user_key

            await conn.execute(
                """
                INSERT INTO connection_tests (
                    connection_id, test_type, success, error_message, test_data
                ) VALUES ($1, $2, $3, $4, $5)
                """,
                result.get("connection_id", "unknown"),
                "health",
                result.get("success", False),
                result.get("error"),
                json.dumps(test_data),
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
                    id, connection_id as region_id, timestamp as checked_at,
                    success, latency_ms, server_ip, backend_pid, error_message
                FROM connection_tests
                WHERE test_type = 'connection'
                ORDER BY timestamp DESC
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
        import json

        async with get_connection(dsn) as conn:
            # Get all types of checks from connection_tests table
            rows = await conn.fetch(
                """
                SELECT
                    test_type as check_type,
                    connection_id as region_id,
                    timestamp as checked_at,
                    success,
                    latency_ms,
                    error_message,
                    test_data
                FROM connection_tests
                ORDER BY timestamp DESC
                LIMIT $1
                """,
                limit,
            )

            # Process rows to extract metric_value and metric_unit based on test type
            results = []
            for row in rows:
                test_data = json.loads(row["test_data"]) if row["test_data"] else {}

                # Determine metric value and unit based on test type
                if row["check_type"] == "connection":
                    metric_value = row["latency_ms"]
                    metric_unit = "ms"
                elif row["check_type"] == "latency":
                    metric_value = row["latency_ms"]  # avg_ms is stored in latency_ms
                    metric_unit = "ms"
                elif row["check_type"] == "load":
                    metric_value = test_data.get("queries_per_second")
                    metric_unit = "qps"
                elif row["check_type"] == "health":
                    metric_value = test_data.get("cache_hit_ratio")
                    metric_unit = "%"
                else:
                    metric_value = None
                    metric_unit = ""

                results.append({
                    "check_type": row["check_type"],
                    "region_id": row["region_id"],
                    "checked_at": row["checked_at"],
                    "success": row["success"],
                    "metric_value": metric_value,
                    "metric_unit": metric_unit,
                    "error_message": row["error_message"],
                    "user_key": test_data.get("user_key"),
                })

            return results
    except Exception as e:
        import logging
        logging.warning(f"Failed to get recent checks: {e}")
        return []
