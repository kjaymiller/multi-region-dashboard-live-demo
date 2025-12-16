"""API endpoints for the dashboard."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.chat import get_chat_response, get_expensive_queries
from app.config import get_database
from app.database import (
    get_all_recent_checks,
    get_connection_health_metrics,
    measure_connection_latency,
    run_connection_load_test,
    save_connection_check,
    save_health_metrics_check,
    save_latency_check,
    save_load_test_check,
)
from app.db_manager_postgres import db_manager
from app.region_mapping import estimate_latency_distance, get_cloud_color, get_region_coordinates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/location")
async def get_user_location(request: Request):
    """Get user's approximate location based on their IP address."""
    import httpx

    client_ip = request.client.host if request.client else None

    # For local development, return a default location
    if not client_ip or client_ip in ["127.0.0.1", "::1", "localhost"]:
        return JSONResponse(
            content={
                "lat": 40.7128,
                "lon": -74.0060,
                "city": "New York",
                "country": "USA",
                "ip": client_ip,
                "is_local": True,
            }
        )

    # Use a free IP geolocation service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://ip-api.com/json/{client_ip}")
            data = response.json()

            if data.get("status") == "success":
                return JSONResponse(
                    content={
                        "lat": data.get("lat"),
                        "lon": data.get("lon"),
                        "city": data.get("city"),
                        "country": data.get("country"),
                        "ip": client_ip,
                        "is_local": False,
                    }
                )
    except Exception:
        pass

    # Fallback to default location
    return JSONResponse(
        content={
            "lat": 40.7128,
            "lon": -74.0060,
            "city": "New York",
            "country": "USA",
            "ip": client_ip,
            "is_local": True,
            "error": "Could not determine location",
        }
    )


def get_user_key(request: Request) -> str:
    """Extract user key from request."""
    user_key = request.cookies.get("user_key")
    if not user_key:
        user_key = request.client.host if request.client else "anonymous"
    return user_key


@router.get("/database/info")
async def get_database_info(request: Request):
    """Get database information."""
    database = get_database()

    return JSONResponse(
        content={
            "database": {
                "id": "database",
                "name": database.name,
            }
        }
    )


@router.post("/chat")
async def chat(request: Request):
    """Chat with AI assistant about database performance."""

    # Get the message from request body
    body = await request.json()
    message = body.get("message", "")

    if not message:
        return JSONResponse(content={"error": "No message provided"}, status_code=400)

    # Get recent checks for context
    recent_checks = await get_all_recent_checks(limit=10)

    # Get expensive queries for enhanced analysis
    expensive_queries = await get_expensive_queries()

    # Get database connections for context and format them
    connections = await db_manager.get_all_connections()

    # Add database context to recent checks
    if connections:
        db_context = {
            "check_type": "database_info",
            "region_id": "connections",
            "success": True,
            "metric_value": len(connections),
            "metric_unit": "connections",
            "connections": [
                {
                    "name": conn.name,
                    "region": conn.region,
                    "cloud_provider": conn.cloud_provider,
                    "host": f"{conn.host}:{conn.port}",
                }
                for conn in connections[:5]
            ],
        }
        recent_checks.append(db_context)

    # Get response from Ollama
    try:
        response = await get_chat_response(message, recent_checks, expensive_queries)
        return JSONResponse(content={"response": response})
    except Exception as e:
        return JSONResponse(content={"error": f"Chat service error: {str(e)}"}, status_code=500)


@router.get("/expensive-queries")
async def get_expensive_queries_data():
    """Get expensive queries data for analysis."""
    try:
        expensive_queries = await get_expensive_queries()
        return JSONResponse(
            content={
                "expensive_queries": expensive_queries,
                "total_count": len(expensive_queries),
                "description": "Top expensive queries from last 30 days, prioritized by mean execution time",
            }
        )
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to fetch expensive queries: {str(e)}"}, status_code=500
        )


@router.get("/map-data")
async def get_map_data():
    """Get map data for all database connections with geolocation and performance metrics."""
    connections = await db_manager.get_all_connections()
    map_data = []

    for conn in connections:
        coords = get_region_coordinates(conn.region) if conn.region else None

        if coords:
            # Get latest metrics for this connection
            try:
                # For now, use default metrics - in a real implementation,
                # you'd query the database for this specific connection
                latency_result = await db_manager.test_connection(conn)
                health_result = await get_connection_health_metrics(conn)

                map_data.append(
                    {
                        "id": str(conn.id),
                        "name": conn.name,
                        "host": conn.host,
                        "port": conn.port,
                        "database": conn.database,
                        "region": conn.region,
                        "cloud_provider": conn.cloud_provider or "Other",
                        "lat": coords["lat"],
                        "lng": coords["lng"],
                        "latency_ms": latency_result.get("latency_ms"),
                        "cache_hit_ratio": health_result.get("cache_hit_ratio"),
                        "connections": health_result.get("active_connections", 0),
                        "status": "healthy" if latency_result.get("success") else "unhealthy",
                        "color": get_cloud_color(conn.cloud_provider or "Other"),
                    }
                )
            except Exception:
                # Add connection without metrics if there's an error
                map_data.append(
                    {
                        "id": str(conn.id),
                        "name": conn.name,
                        "host": conn.host,
                        "port": conn.port,
                        "database": conn.database,
                        "region": conn.region,
                        "cloud_provider": conn.cloud_provider or "Other",
                        "lat": coords["lat"],
                        "lng": coords["lng"],
                        "latency_ms": None,
                        "cache_hit_ratio": None,
                        "connections": 0,
                        "status": "unknown",
                        "color": get_cloud_color(conn.cloud_provider or "Other"),
                    }
                )

    # Calculate connections between regions (latency lines)
    connections_lines = []
    for i, db1 in enumerate(map_data):
        for db2 in map_data[i + 1 :]:
            estimated_latency = estimate_latency_distance(
                db1["lat"], db1["lng"], db2["lat"], db2["lng"]
            )
            connections_lines.append(
                {
                    "from": {"lat": db1["lat"], "lng": db1["lng"], "name": db1["name"]},
                    "to": {"lat": db2["lat"], "lng": db2["lng"], "name": db2["name"]},
                    "estimated_latency_ms": estimated_latency,
                }
            )

    return JSONResponse(
        content={
            "databases": map_data,
            "connections": connections_lines,
            "timestamp": "now",  # In real implementation, use actual timestamp
        }
    )


@router.post("/test-database/{connection_id}")
async def test_database_connection(request: Request, connection_id: int):
    """Test a specific database connection."""
    connection = await db_manager.get_connection(connection_id)
    if not connection:
        return JSONResponse(
            content={"success": False, "error": "Database connection not found"}, status_code=404
        )

    coords = get_region_coordinates(connection.region) if connection.region else None

    try:
        result = await db_manager.test_connection(connection)
        if result.get("success"):
            await save_connection_check(result, user_key=get_user_key(request))
        if coords:
            result["coords"] = coords
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "coords": coords}, status_code=500
        )


@router.post("/health-check/{connection_id}")
async def get_database_health(request: Request, connection_id: int):
    """Get health metrics for a specific database connection."""
    connection = await db_manager.get_connection(connection_id)
    if not connection:
        return JSONResponse(
            content={"success": False, "error": "Database connection not found"}, status_code=404
        )

    coords = get_region_coordinates(connection.region) if connection.region else None

    try:
        # Get health metrics for the specific database connection
        result = await get_connection_health_metrics(connection)

        # Save health metrics to database for historical tracking
        if result.get("success"):
            try:
                await save_health_metrics_check(result, user_key=get_user_key(request))
            except Exception as save_error:
                result["warnings"].append(f"Failed to save health metrics: {str(save_error)}")

        if coords:
            result["coords"] = coords

        # Return appropriate HTTP status based on health check result
        if result.get("success"):
            return JSONResponse(content=result)
        else:
            return JSONResponse(content=result, status_code=503)

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Health check failed: {str(e)}",
                "connection_id": connection_id,
                "coords": coords,
            },
            status_code=500,
        )


@router.post("/latency-test/{connection_id}")
async def test_database_latency(request: Request, connection_id: int, iterations: int = 5):
    """Test latency to a specific database connection."""
    connection = await db_manager.get_connection(connection_id)
    if not connection:
        return JSONResponse(
            content={"success": False, "error": "Database connection not found"}, status_code=404
        )

    coords = get_region_coordinates(connection.region) if connection.region else None

    if iterations < 1 or iterations > 100:
        return JSONResponse(
            content={"success": False, "error": "Iterations must be between 1 and 100"},
            status_code=400,
        )

    try:
        result = await measure_connection_latency(connection, iterations)
        if result.get("success"):
            await save_latency_check(result, user_key=get_user_key(request))
        if coords:
            result["coords"] = coords
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "coords": coords}, status_code=500
        )


@router.post("/load-test/{connection_id}")
async def run_database_load_test_endpoint(
    request: Request, connection_id: int, concurrent: int = 10
):
    """Run a load test against a specific database connection."""
    connection = await db_manager.get_connection(connection_id)
    if not connection:
        return JSONResponse(
            content={"success": False, "error": "Database connection not found"}, status_code=404
        )

    coords = get_region_coordinates(connection.region) if connection.region else None

    if concurrent < 1 or concurrent > 100:
        return JSONResponse(
            content={"success": False, "error": "Concurrent connections must be between 1 and 100"},
            status_code=400,
        )

    try:
        result = await run_connection_load_test(connection, concurrent)
        if result.get("success"):
            await save_load_test_check(result, user_key=get_user_key(request))
        if coords:
            result["coords"] = coords
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "coords": coords}, status_code=500
        )


@router.get("/test-all-databases")
async def test_all_databases():
    """Test all configured database connections."""
    connections = await db_manager.get_all_connections()
    results = []

    for conn in connections:
        try:
            result = await db_manager.test_connection(conn)
            results.append(
                {
                    "id": str(conn.id),
                    "name": conn.name,
                    "host": conn.host,
                    "port": conn.port,
                    "region": conn.region,
                    "cloud_provider": conn.cloud_provider,
                    "test_result": result,
                }
            )
        except Exception as e:
            results.append(
                {
                    "id": str(conn.id),
                    "name": conn.name,
                    "host": conn.host,
                    "port": conn.port,
                    "region": conn.region,
                    "cloud_provider": conn.cloud_provider,
                    "test_result": {"success": False, "error": str(e)},
                }
            )

    return JSONResponse(
        content={
            "results": results,
            "total_databases": len(connections),
            "successful_tests": len([r for r in results if r["test_result"].get("success", False)]),
            "failed_tests": len([r for r in results if not r["test_result"].get("success", False)]),
        }
    )


@router.get("/health-all-databases")
async def health_check_all_databases(request: Request):
    """Get health metrics for all configured database connections."""
    connections = await db_manager.get_all_connections()
    results = []
    user_key = get_user_key(request)

    # Create tasks for parallel health checks
    health_check_tasks = []
    for conn in connections:
        health_check_tasks.append(
            {
                "connection": conn,
                "health_task": get_connection_health_metrics(conn),
                "connection_test_task": measure_connection_latency(conn),
            }
        )

    # Execute all health checks in parallel
    import asyncio

    for task_data in health_check_tasks:
        conn = task_data["connection"]

        try:
            # Wait for both health check and connection test
            health_result, connection_result = await asyncio.gather(
                task_data["health_task"], task_data["connection_test_task"], return_exceptions=True
            )

            # Handle health check result
            if isinstance(health_result, Exception):
                health_result = {"success": False, "error": str(health_result)}

            # Handle connection test result
            if isinstance(connection_result, Exception):
                connection_result = {"success": False, "error": str(connection_result)}

            # Save health metrics to database for historical tracking
            if health_result.get("success"):
                try:
                    await save_health_metrics_check(health_result, user_key=user_key)
                except Exception as save_error:
                    if "warnings" not in health_result:
                        health_result["warnings"] = []
                    health_result["warnings"].append(
                        f"Failed to save health metrics: {str(save_error)}"
                    )

            results.append(
                {
                    "id": str(conn.id),
                    "name": conn.name,
                    "host": conn.host,
                    "port": conn.port,
                    "region": conn.region,
                    "cloud_provider": conn.cloud_provider,
                    "connection_test": connection_result,
                    "health_metrics": health_result,
                    "overall_status": (
                        "healthy"
                        if connection_result.get("success") and health_result.get("success")
                        else "unhealthy"
                    ),
                }
            )
        except Exception as e:
            # Fallback for any unexpected errors
            results.append(
                {
                    "id": str(conn.id),
                    "name": conn.name,
                    "host": conn.host,
                    "port": conn.port,
                    "region": conn.region,
                    "cloud_provider": conn.cloud_provider,
                    "connection_test": {"success": False, "error": str(e)},
                    "health_metrics": {"success": False, "error": str(e)},
                    "overall_status": "unhealthy",
                }
            )

    return JSONResponse(
        content={
            "results": results,
            "total_databases": len(connections),
            "healthy_databases": len([r for r in results if r["overall_status"] == "healthy"]),
            "unhealthy_databases": len([r for r in results if r["overall_status"] == "unhealthy"]),
            "timestamp": "now",
        }
    )


@router.get("/database-summary")
async def get_database_summary():
    """Get a summary of all database connections and their status."""
    connections = await db_manager.get_all_connections()

    summary = {
        "total_databases": len(connections),
        "by_provider": {},
        "by_region": {},
        "connections": [],
    }

    for conn in connections:
        provider = conn.cloud_provider or "Other"
        region = conn.region or "Unknown"

        # Count by provider
        if provider not in summary["by_provider"]:
            summary["by_provider"][provider] = 0
        summary["by_provider"][provider] += 1

        # Count by region
        if region not in summary["by_region"]:
            summary["by_region"][region] = 0
        summary["by_region"][region] += 1

        # Add connection summary
        summary["connections"].append(
            {
                "id": str(conn.id),
                "name": conn.name,
                "provider": provider,
                "region": region,
                "host": conn.host,
                "port": conn.port,
            }
        )

    return JSONResponse(content=summary)


@router.get("/recent-checks")
async def get_recent_checks_endpoint(request: Request, limit: int = 20):
    """Get a list of recent checks and their results."""
    recent_checks = await get_all_recent_checks(limit=limit)
    return templates.TemplateResponse(
        "partials/recent_checks_table_body.html",
        {"request": request, "checks": recent_checks},
    )


@router.get("/charts/latency")
async def get_latency_chart_data(hours: int = 24):
    """Get latency time series data for all database connections."""
    from app.config import get_dsn
    from app.database import get_connection

    dsn = get_dsn()
    if not dsn:
        return JSONResponse(content={"error": "Database not configured"}, status_code=500)

    try:
        import json

        async with get_connection(dsn) as conn:
            # Get latency data from the last X hours
            rows = await conn.fetch(
                f"""
                SELECT
                    ct.connection_id as region_id,
                    ct.timestamp as checked_at,
                    ct.latency_ms as avg_ms,
                    ct.test_data,
                    dc.name as connection_name
                FROM connection_tests ct
                LEFT JOIN database_connections dc ON ct.connection_id = dc.id
                WHERE ct.test_type = 'latency'
                    AND ct.timestamp >= NOW() - INTERVAL '{hours} hours'
                    AND ct.success = true
                    AND ct.connection_id IS NOT NULL
                ORDER BY ct.timestamp ASC
                """
            )

            # Group data by connection
            data_by_connection = {}
            for row in rows:
                conn_id = row["region_id"]
                conn_name = row["connection_name"] or f"Database {conn_id}"

                if conn_id not in data_by_connection:
                    data_by_connection[conn_id] = {"label": conn_name, "data": [], "timestamps": []}

                # avg_ms is stored in latency_ms column for latency tests
                data_by_connection[conn_id]["data"].append(float(row["avg_ms"]))
                data_by_connection[conn_id]["timestamps"].append(row["checked_at"].isoformat())

            return JSONResponse(
                content={
                    "datasets": list(data_by_connection.values()),
                    "title": f"Database Latency - Last {hours} Hours",
                }
            )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/charts/health-metrics")
async def get_health_metrics_chart_data(hours: int = 24):
    """Get health metrics time series data for all database connections."""
    from app.config import get_dsn
    from app.database import get_connection

    dsn = get_dsn()
    if not dsn:
        return JSONResponse(content={"error": "Database not configured"}, status_code=500)

    try:
        import json

        async with get_connection(dsn) as conn:
            # Get health metrics data from the last X hours
            rows = await conn.fetch(
                f"""
                SELECT
                    ct.connection_id as region_id,
                    ct.timestamp as checked_at,
                    ct.test_data,
                    dc.name as connection_name
                FROM connection_tests ct
                LEFT JOIN database_connections dc ON ct.connection_id = dc.id
                WHERE ct.test_type = 'health'
                    AND ct.timestamp >= NOW() - INTERVAL '{hours} hours'
                    AND ct.success = true
                    AND ct.connection_id IS NOT NULL
                ORDER BY ct.timestamp ASC
                """
            )

            # Group data by connection and metric type
            cache_hit_data = {}
            connections_data = {}

            for row in rows:
                conn_id = row["region_id"]
                conn_name = row["connection_name"] or f"Database {conn_id}"
                timestamp = row["checked_at"].isoformat()

                # Parse test_data JSON
                test_data = json.loads(row["test_data"]) if row["test_data"] else {}

                # Cache hit ratio data
                if conn_id not in cache_hit_data:
                    cache_hit_data[conn_id] = {
                        "label": f"{conn_name} - Cache Hit %",
                        "data": [],
                        "timestamps": [],
                    }

                cache_hit_ratio = test_data.get("cache_hit_ratio")
                if cache_hit_ratio is not None:
                    cache_hit_data[conn_id]["data"].append(float(cache_hit_ratio))
                    cache_hit_data[conn_id]["timestamps"].append(timestamp)

                # Active connections data
                if conn_id not in connections_data:
                    connections_data[conn_id] = {
                        "label": f"{conn_name} - Active Conns",
                        "data": [],
                        "timestamps": [],
                    }

                active_connections = test_data.get("active_connections")
                if active_connections is not None:
                    connections_data[conn_id]["data"].append(int(active_connections))
                    connections_data[conn_id]["timestamps"].append(timestamp)

            return JSONResponse(
                content={
                    "cache_hit_datasets": list(cache_hit_data.values()),
                    "connections_datasets": list(connections_data.values()),
                    "title": f"Database Health Metrics - Last {hours} Hours",
                }
            )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@router.get("/charts/performance-summary")
async def get_performance_summary_chart_data():
    """Get aggregated performance comparison across all databases."""
    from app.config import get_dsn
    from app.database import get_connection

    dsn = get_dsn()
    if not dsn:
        return JSONResponse(content={"error": "Database not configured"}, status_code=500)

    try:
        import json

        async with get_connection(dsn) as conn:
            # Get average latency per database from the last 24 hours
            latency_rows = await conn.fetch(
                """
                SELECT
                    ct.connection_id as region_id,
                    dc.name as connection_name,
                    ROUND(AVG(ct.latency_ms)::numeric, 2) as avg_latency,
                    COUNT(*) as check_count
                FROM connection_tests ct
                LEFT JOIN database_connections dc ON ct.connection_id = dc.id
                WHERE ct.test_type = 'latency'
                    AND ct.timestamp >= NOW() - INTERVAL '24 hours'
                    AND ct.success = true
                    AND ct.connection_id IS NOT NULL
                GROUP BY ct.connection_id, dc.name
                ORDER BY avg_latency ASC
                """
            )

            # Get success rate per database from the last 24 hours
            success_rows = await conn.fetch(
                """
                SELECT
                    ct.connection_id as region_id,
                    dc.name as connection_name,
                    COUNT(*) FILTER (WHERE ct.success = true) as success_count,
                    COUNT(*) as total_count,
                    ROUND((COUNT(*) FILTER (WHERE ct.success = true)::numeric / COUNT(*)::numeric * 100), 2) as success_rate
                FROM connection_tests ct
                LEFT JOIN database_connections dc ON ct.connection_id = dc.id
                WHERE ct.test_type = 'connection'
                    AND ct.timestamp >= NOW() - INTERVAL '24 hours'
                    AND ct.connection_id IS NOT NULL
                GROUP BY ct.connection_id, dc.name
                ORDER BY success_rate DESC
                """
            )

            # Get cache hit ratio per database from the last 24 hours
            # Need to parse test_data JSONB to get cache_hit_ratio
            cache_rows_raw = await conn.fetch(
                """
                SELECT
                    ct.connection_id as region_id,
                    dc.name as connection_name,
                    ct.test_data
                FROM connection_tests ct
                LEFT JOIN database_connections dc ON ct.connection_id = dc.id
                WHERE ct.test_type = 'health'
                    AND ct.timestamp >= NOW() - INTERVAL '24 hours'
                    AND ct.success = true
                    AND ct.test_data IS NOT NULL
                    AND ct.connection_id IS NOT NULL
                ORDER BY ct.timestamp DESC
                """
            )

            # Process cache hit ratio data from JSON
            cache_by_connection = {}
            for row in cache_rows_raw:
                test_data = json.loads(row["test_data"]) if row["test_data"] else {}
                cache_hit_ratio = test_data.get("cache_hit_ratio")

                if cache_hit_ratio is not None:
                    conn_id = row["region_id"]
                    if conn_id not in cache_by_connection:
                        cache_by_connection[conn_id] = {
                            "name": row["connection_name"],
                            "values": []
                        }
                    cache_by_connection[conn_id]["values"].append(float(cache_hit_ratio))

            # Calculate averages
            cache_rows = []
            for conn_id, data in cache_by_connection.items():
                if data["values"]:
                    avg_cache_hit = round(sum(data["values"]) / len(data["values"]), 2)
                    cache_rows.append({
                        "region_id": conn_id,
                        "connection_name": data["name"],
                        "avg_cache_hit": avg_cache_hit
                    })

            # Sort by avg_cache_hit descending
            cache_rows.sort(key=lambda x: x["avg_cache_hit"], reverse=True)

            # Format data for charts
            latency_data = {
                "labels": [
                    row["connection_name"] or f"DB {row['region_id']}" for row in latency_rows
                ],
                "values": [float(row["avg_latency"]) for row in latency_rows],
            }

            success_data = {
                "labels": [
                    row["connection_name"] or f"DB {row['region_id']}" for row in success_rows
                ],
                "values": [float(row["success_rate"]) for row in success_rows],
            }

            cache_data = {
                "labels": [
                    row["connection_name"] or f"DB {row['region_id']}" for row in cache_rows
                ],
                "values": [float(row["avg_cache_hit"]) for row in cache_rows],
            }

            return JSONResponse(
                content={
                    "latency": latency_data,
                    "success_rate": success_data,
                    "cache_hit": cache_data,
                    "title": "24-Hour Performance Summary",
                }
            )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
