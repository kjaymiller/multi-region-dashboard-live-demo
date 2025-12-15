"""HTML page routes for the dashboard."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import get_database

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

    # Get database info
    database = get_database()

    # Default values (all features enabled)
    refresh_interval = 30
    health_checks_enabled = True
    load_testing_enabled = True
    chatbot_enabled = True
    refresh_table_button_enabled = True

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "database": database,
            "refresh_interval": refresh_interval,
            "health_checks_enabled": health_checks_enabled,
            "load_testing_enabled": load_testing_enabled,
            "chatbot_enabled": chatbot_enabled,
            "refresh_table_button_enabled": refresh_table_button_enabled,

            "user_key": user_key,
        },
    )
