"""HTML page routes for the dashboard."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import get_all_regions, LAUNCHDARKLY_CLIENT_SIDE_ID
from app.feature_flags import (
    get_enabled_regions,
    get_refresh_interval,
    is_health_checks_enabled,
    is_load_testing_enabled,
    is_chatbot_enabled,
    is_refresh_table_button_enabled,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_user_key(request: Request) -> str:
    """Extract user key from request (cookie or IP)."""
    user_key = request.cookies.get("user_key")
    if not user_key:
        user_key = request.client.host if request.client else "anonymous"
    return user_key


@router.get("/")
async def dashboard(request: Request):
    """Render the main dashboard page."""
    user_key = get_user_key(request)

    # Get all regions and filter by enabled status
    all_regions = get_all_regions()
    enabled_region_ids = get_enabled_regions(user_key)
    regions = [r for r in all_regions if r.id in enabled_region_ids]

    # Get feature flags
    refresh_interval = get_refresh_interval(user_key)
    health_checks_enabled = is_health_checks_enabled(user_key)
    load_testing_enabled = is_load_testing_enabled(user_key)
    chatbot_enabled = is_chatbot_enabled(user_key)
    refresh_table_button_enabled = is_refresh_table_button_enabled(user_key)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "regions": regions,
            "refresh_interval": refresh_interval,
            "health_checks_enabled": health_checks_enabled,
            "load_testing_enabled": load_testing_enabled,
            "chatbot_enabled": chatbot_enabled,
            "refresh_table_button_enabled": refresh_table_button_enabled,
            "launchdarkly_client_side_id": LAUNCHDARKLY_CLIENT_SIDE_ID,
            "user_key": user_key,
        },
    )
