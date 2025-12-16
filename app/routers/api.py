"""API endpoints for the dashboard."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.chat import get_chat_response
from app.config import get_database
from app.db_manager import db_manager
from app.region_mapping import estimate_latency_distance, get_cloud_color, get_region_coordinates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


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

                map_data.append({
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
                })
            except Exception:
                # Add connection without metrics if there's an error
                map_data.append({
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
                })

    # Calculate connections between regions (latency lines)
    connections_lines = []
    for i, db1 in enumerate(map_data):
        for db2 in map_data[i+1:]:
            estimated_latency = estimate_latency_distance(
                db1["lat"], db1["lng"],
                db2["lat"], db2["lng"]
            )
            connections_lines.append({
                "from": {"lat": db1["lat"], "lng": db1["lng"], "name": db1["name"]},
                "to": {"lat": db2["lat"], "lng": db2["lng"], "name": db2["name"]},
                "estimated_latency_ms": estimated_latency
            })

    return JSONResponse(content={
        "databases": map_data,
        "connections": connections_lines,
        "timestamp": "now"  # In real implementation, use actual timestamp
    })
