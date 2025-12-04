"""HTMX API endpoints for the dashboard."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import get_region, get_all_regions
from app.database import (
    test_connection,
    measure_latency,
    load_test,
    get_health_metrics,
    test_all_regions,
)
from app.feature_flags import (
    is_region_enabled,
    is_health_checks_enabled,
    is_load_testing_enabled,
    is_test_all_regions_enabled,
    get_enabled_regions,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_user_key(request: Request) -> str:
    """Extract user key from request."""
    user_key = request.cookies.get("user_key")
    if not user_key:
        user_key = request.client.host if request.client else "anonymous"
    return user_key


@router.post("/regions/{region_id}/test")
async def test_region(region_id: str, request: Request):
    """Test connection to a specific region."""
    user_key = get_user_key(request)

    # Check if region is enabled
    if not is_region_enabled(region_id, user_key):
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Region unavailable"},
        )

    region = get_region(region_id)
    if not region:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": f"Unknown region: {region_id}"},
        )

    result = await test_connection(region_id)

    return templates.TemplateResponse(
        "partials/connection_result.html",
        {"request": request, "region": region, "result": result},
    )


@router.post("/regions/{region_id}/latency")
async def test_latency(region_id: str, request: Request, iterations: int = 5):
    """Measure latency to a specific region."""
    user_key = get_user_key(request)

    if not is_region_enabled(region_id, user_key):
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Region unavailable"},
        )

    region = get_region(region_id)
    if not region:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": f"Unknown region: {region_id}"},
        )

    result = await measure_latency(region_id, iterations)

    return templates.TemplateResponse(
        "partials/latency_result.html",
        {"request": request, "region": region, "result": result},
    )


@router.post("/regions/{region_id}/load-test")
async def run_load_test(region_id: str, request: Request, concurrent: int = 10):
    """Run load test on a specific region."""
    user_key = get_user_key(request)

    if not is_load_testing_enabled(user_key):
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Load testing is disabled"},
        )

    if not is_region_enabled(region_id, user_key):
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Region unavailable"},
        )

    region = get_region(region_id)
    if not region:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": f"Unknown region: {region_id}"},
        )

    result = await load_test(region_id, concurrent)

    return templates.TemplateResponse(
        "partials/load_test_result.html",
        {"request": request, "region": region, "result": result},
    )


@router.post("/regions/{region_id}/health")
async def get_region_health(region_id: str, request: Request):
    """Get health metrics for a specific region."""
    user_key = get_user_key(request)

    if not is_health_checks_enabled(user_key):
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Health checks are disabled"},
        )

    if not is_region_enabled(region_id, user_key):
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Region unavailable"},
        )

    region = get_region(region_id)
    if not region:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": f"Unknown region: {region_id}"},
        )

    result = await get_health_metrics(region_id)

    return templates.TemplateResponse(
        "partials/health_result.html",
        {"request": request, "region": region, "result": result},
    )


@router.post("/regions/test-all")
async def test_all(request: Request):
    """Test all enabled regions simultaneously."""
    user_key = get_user_key(request)

    if not is_test_all_regions_enabled(user_key):
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "Test all regions is disabled"},
        )

    enabled_regions = get_enabled_regions(user_key)

    if not enabled_regions:
        return templates.TemplateResponse(
            "partials/error.html",
            {"request": request, "error": "No regions available"},
        )

    result = await test_all_regions(enabled_regions)

    # Enrich results with region info
    all_regions = {r.id: r for r in get_all_regions()}
    for r in result["results"]:
        r["region"] = all_regions.get(r["region_id"])

    return templates.TemplateResponse(
        "partials/all_regions_result.html",
        {"request": request, "results": result["results"]},
    )


@router.get("/regions/summary")
async def regions_summary(request: Request):
    """Get summary of all regions (for auto-refresh)."""
    user_key = get_user_key(request)
    enabled_regions = get_enabled_regions(user_key)

    if not enabled_regions:
        return HTMLResponse("<div class='text-muted'>No regions available</div>")

    result = await test_all_regions(enabled_regions)

    all_regions = {r.id: r for r in get_all_regions()}
    for r in result["results"]:
        r["region"] = all_regions.get(r["region_id"])

    return templates.TemplateResponse(
        "partials/regions_summary.html",
        {"request": request, "results": result["results"]},
    )
