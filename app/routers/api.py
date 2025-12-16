"""API endpoints for the dashboard."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.chat import get_chat_response
from app.config import get_database
from app.database import (
    get_all_recent_checks,
    get_health_metrics,
    load_test,
    measure_latency,
    test_connection,
)
from app.db_manager import db_manager
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

    # Get response from Ollama
    try:
        response = await get_chat_response(message, recent_checks)
        return JSONResponse(content={"response": response})
    except Exception as e:
        return JSONResponse(content={"error": f"Chat service error: {str(e)}"}, status_code=500)


@router.get("/map-data")
async def get_map_data():
    """Get map data for all database connections with geolocation and performance metrics."""
    connections = db_manager.get_all_connections()
    map_data = []

    for conn in connections:
        coords = get_region_coordinates(conn.region) if conn.region else None

        if coords:
            # Get latest metrics for this connection
            try:
                # For now, use default metrics - in a real implementation,
                # you'd query the database for this specific connection
                latency_result = await test_connection()
                health_result = await get_health_metrics()

                map_data.append(
                    {
                        "id": conn.id,
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
                        "id": conn.id,
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
async def test_database_connection(connection_id: str):
    """Test a specific database connection."""
    connection = db_manager.get_connection(connection_id)
    if not connection:
        return JSONResponse(
            content={"success": False, "error": "Database connection not found"}, status_code=404
        )

    try:
        result = await db_manager.test_connection(connection)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/health-check/{connection_id}")
async def get_database_health(connection_id: str):
    """Get health metrics for a specific database connection."""
    connection = db_manager.get_connection(connection_id)
    if not connection:
        return JSONResponse(
            content={"success": False, "error": "Database connection not found"}, status_code=404
        )

    try:
        # For now, use the main database health check
        # In a real implementation, you'd connect to the specific database
        result = await get_health_metrics()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/latency-test/{connection_id}")
async def test_database_latency(connection_id: str, iterations: int = 5):
    """Test latency to a specific database connection."""
    connection = db_manager.get_connection(connection_id)
    if not connection:
        return JSONResponse(
            content={"success": False, "error": "Database connection not found"}, status_code=404
        )

    if iterations < 1 or iterations > 100:
        return JSONResponse(
            content={"success": False, "error": "Iterations must be between 1 and 100"},
            status_code=400,
        )

    try:
        # For now, use the main database latency test
        result = await measure_latency(iterations)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.post("/load-test/{connection_id}")
async def run_database_load_test(connection_id: str, concurrent: int = 10):
    """Run a load test against a specific database connection."""
    connection = db_manager.get_connection(connection_id)
    if not connection:
        return JSONResponse(
            content={"success": False, "error": "Database connection not found"}, status_code=404
        )

    if concurrent < 1 or concurrent > 100:
        return JSONResponse(
            content={"success": False, "error": "Concurrent connections must be between 1 and 100"},
            status_code=400,
        )

    try:
        # For now, use the main database load test
        result = await load_test(concurrent)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@router.get("/test-all-databases")
async def test_all_databases():
    """Test all configured database connections."""
    connections = db_manager.get_all_connections()
    results = []

    for conn in connections:
        try:
            result = await db_manager.test_connection(conn)
            results.append(
                {
                    "id": conn.id,
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
                    "id": conn.id,
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
async def health_check_all_databases():
    """Get health metrics for all configured database connections."""
    connections = db_manager.get_all_connections()
    results = []

    for conn in connections:
        try:
            # For now, use the main database health check
            # In a real implementation, you'd connect to each specific database
            health_result = await get_health_metrics()
            connection_result = await db_manager.test_connection(conn)

            results.append(
                {
                    "id": conn.id,
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
            results.append(
                {
                    "id": conn.id,
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
    connections = db_manager.get_all_connections()

    summary = {
        "total_databases": len(connections),
        "by_provider": {},
        "by_region": {},
        "connections": []
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
                "id": conn.id,
                "name": conn.name,
                "provider": provider,
                "region": region,
                "host": conn.host,
                "port": conn.port,
            }
        )

    return JSONResponse(content=summary)
