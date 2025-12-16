"""HTML page routes for the dashboard."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import get_database
from app.database import get_connection_health_metrics
from app.db_manager_postgres import db_manager

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

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "database": database,
            "user_key": user_key,
        },
    )


@router.get("/partials/health_result")
async def health_result_partial(request: Request):
    """Render health result as a partial template for AJAX loading."""
    connection_id_param = request.query_params.get("connection_id")

    if not connection_id_param:
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": "Connection ID is required",
            },
        )

    try:
        connection_id = int(connection_id_param)
        connection = await db_manager.get_connection(connection_id)
        if not connection:
            return templates.TemplateResponse(
                "partials/error.html",
                {
                    "request": request,
                    "error": "Database connection not found",
                },
            )

        # Get health metrics for the specific database connection
        result = await get_connection_health_metrics(connection)

        return templates.TemplateResponse(
            "partials/health_result.html",
            {
                "request": request,
                "result": result,
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/error.html",
            {
                "request": request,
                "error": f"Failed to get health metrics: {str(e)}",
            },
        )
