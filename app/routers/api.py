"""HTMX API endpoints for the dashboard."""

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
    save_connection_check,
    save_health_metrics_check,
    save_latency_check,
    save_load_test_check,
    test_connection,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_user_key(request: Request) -> str:
    """Extract user key from request."""
    user_key = request.cookies.get("user_key")
    if not user_key:
        user_key = request.client.host if request.client else "anonymous"
    return user_key


@router.post("/database/test")
async def test_database_connection(request: Request):
    """Test connection to the database."""
    user_key = get_user_key(request)

    result = await test_connection()

    # Save the check result to database
    await save_connection_check(result, user_key)

    response = templates.TemplateResponse(
        "partials/connection_result.html",
        {"request": request, "database": get_database(), "result": result},
    )

    # Add test result data as a custom header
    import json
    response.headers["X-Test-Result"] = json.dumps({
        "database_name": "database",
        "test_type": "test",
        "success": result.get("success", False),
        "latency_ms": result.get("latency_ms"),
        "error": result.get("error")
    })

    return response


@router.post("/database/latency")
async def test_database_latency(request: Request, iterations: int = 5):
    """Measure latency to the database."""
    import json
    user_key = get_user_key(request)

    result = await measure_latency(iterations)

    # Save the check result to database
    await save_latency_check(result, user_key)

    response = templates.TemplateResponse(
        "partials/latency_result.html",
        {"request": request, "database": get_database(), "result": result},
    )

    # Add test result data as a custom header
    response.headers["X-Test-Result"] = json.dumps({
        "database_name": "database",
        "test_type": "latency",
        "success": result.get("success", False),
        "avg_latency_ms": result.get("avg_ms"),
        "min_latency_ms": result.get("min_ms"),
        "max_latency_ms": result.get("max_ms"),
        "error": result.get("error")
    })

    return response


@router.post("/database/load-test")
async def run_database_load_test(request: Request, concurrent: int = 10):
    """Run load test on the database."""
    import json
    user_key = get_user_key(request)

    if False:  # Load testing enabled
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Load testing is disabled"},
        )

    result = await load_test(concurrent)

    # Save the check result to database
    await save_load_test_check(result, user_key)

    response = templates.TemplateResponse(
        "partials/load_test_result.html",
        {"request": request, "database": get_database(), "result": result},
    )

    # Add test result data as a custom header
    response.headers["X-Test-Result"] = json.dumps({
        "database_name": "database",
        "test_type": "load-test",
        "success": result.get("success", False),
        "connections": concurrent,
        "avg_latency_ms": result.get("avg_ms"),
        "error": result.get("error")
    })

    return response


@router.post("/database/health")
async def get_database_health(request: Request):
    """Get health metrics for the database."""
    import json
    user_key = get_user_key(request)

    if False:  # Health checks enabled
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Health checks are disabled"},
        )

    result = await get_health_metrics()

    # Save the check result to database
    await save_health_metrics_check(result, user_key)

    response = templates.TemplateResponse(
        "partials/health_result.html",
        {"request": request, "database": get_database(), "result": result},
    )

    # Add test result data as a custom header
    response.headers["X-Test-Result"] = json.dumps({
        "database_name": "database",
        "test_type": "health",
        "success": result.get("success", False),
        "connections": result.get("active_connections"),
        "error": result.get("error")
    })

    return response


@router.post("/database/test-all")
async def test_database_all(request: Request):
    """Test all database functions."""
    user_key = get_user_key(request)

    # Run all tests
    connection_result = await test_connection()
    latency_result = await measure_latency()
    load_result = await load_test()
    health_result = await get_health_metrics()

    # Save all results
    await save_connection_check(connection_result, user_key)
    await save_latency_check(latency_result, user_key)
    await save_load_test_check(load_result, user_key)
    await save_health_metrics_check(health_result, user_key)

    results = [
        {"test_type": "connection", "result": connection_result, "database": get_database()},
        {"test_type": "latency", "result": latency_result, "database": get_database()},
        {"test_type": "load_test", "result": load_result, "database": get_database()},
        {"test_type": "health", "result": health_result, "database": get_database()},
    ]

    return templates.TemplateResponse(
        "partials/all_regions_result.html",
        {"request": request, "results": results},
    )


@router.get("/database/summary")
async def database_summary(request: Request):
    """Get summary of database status (for auto-refresh)."""

    # Run all tests for summary
    connection_result = await test_connection()
    latency_result = await measure_latency()
    health_result = await get_health_metrics()

    results = [
        {"test_type": "connection", "result": connection_result, "database": get_database()},
        {"test_type": "latency", "result": latency_result, "database": get_database()},
        {"test_type": "health", "result": health_result, "database": get_database()},
    ]

    return templates.TemplateResponse(
        "partials/regions_summary.html",
        {"request": request, "results": results},
    )


@router.get("/database/info")
async def get_database_info(request: Request):
    """Get database information."""
    database = get_database()

    return JSONResponse(content={
        "database": {
            "id": "database",
            "name": database.name,
        }
    })


@router.get("/checks/history")
async def get_check_history(request: Request, limit: int = 20):
    """Get recent check history for the database."""

    checks = await get_all_recent_checks(limit)

    return templates.TemplateResponse(
        "partials/check_history.html",
        {"request": request, "checks": checks},
    )


@router.get("/checks/chart-data")
async def get_check_chart_data(request: Request):
    """Get check data formatted for charts, grouped by check type."""

    # Get recent checks
    checks = await get_all_recent_checks(limit=100)

    # Group by check type
    from collections import defaultdict
    check_data = defaultdict(list)

    for check in checks:
        check_type = check["check_type"]

        if check["success"] and check["metric_value"]:
            check_data[check_type].append({
                "timestamp": check["checked_at"].isoformat(),
                "value": float(check["metric_value"])
            })

    # Prepare data for Chart.js - use a single color for the database
    base_color = "rgb(64, 91, 255)"  # LaunchDarkly purple
    bg_color = base_color.replace("rgb", "rgba").replace(")", ", 0.1)")
    database = get_database()

    # Create separate datasets for each check type
    result = {
        "connection": {"datasets": []},
        "latency": {"datasets": []},
        "load_test": {"datasets": []},
        "health": {"datasets": []}
    }

    # Connection data
    connection_data = check_data.get("connection", [])
    if connection_data:
        connection_data.sort(key=lambda x: x["timestamp"])
        result["connection"]["datasets"].append({
            "label": database.name,
            "data": [{"x": d["timestamp"], "y": d["value"]} for d in connection_data[-30:]],
            "borderColor": base_color,
            "backgroundColor": bg_color,
            "tension": 0.4,
            "fill": True
        })

    # Latency data
    latency_data = check_data.get("latency", [])
    if latency_data:
        latency_data.sort(key=lambda x: x["timestamp"])
        result["latency"]["datasets"].append({
            "label": database.name,
            "data": [{"x": d["timestamp"], "y": d["value"]} for d in latency_data[-30:]],
            "borderColor": base_color,
            "backgroundColor": bg_color,
            "tension": 0.4,
            "fill": True
        })

    # Load test data (queries per second)
    load_test_data = check_data.get("load_test", [])
    if load_test_data:
        load_test_data.sort(key=lambda x: x["timestamp"])
        result["load_test"]["datasets"].append({
            "label": database.name,
            "data": [{"x": d["timestamp"], "y": d["value"]} for d in load_test_data[-30:]],
            "borderColor": base_color,
            "backgroundColor": bg_color,
            "tension": 0.4,
            "fill": True
        })

    # Health data (cache hit ratio)
    health_data = check_data.get("health", [])
    if health_data:
        health_data.sort(key=lambda x: x["timestamp"])
        result["health"]["datasets"].append({
            "label": database.name,
            "data": [{"x": d["timestamp"], "y": d["value"]} for d in health_data[-30:]],
            "borderColor": base_color,
            "backgroundColor": bg_color,
            "tension": 0.4,
            "fill": True
        })

    return JSONResponse(content=result)


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
        return JSONResponse(
            content={"error": f"Chat service error: {str(e)}"},
            status_code=500
        )
