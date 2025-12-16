"""API endpoints for database connection management."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.db_manager import DatabaseConnection, DatabaseManager

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class DatabaseCreateRequest(BaseModel):
    """Request model for creating a database connection."""

    name: str = Field(..., min_length=1, max_length=100)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=63)
    username: str = Field(..., min_length=1, max_length=63)
    password: str = Field(..., min_length=1)
    ssl_mode: str = Field(default="require")
    region: str | None = Field(None, max_length=50)
    cloud_provider: str | None = Field(None, max_length=50)


class DatabaseUpdateRequest(BaseModel):
    """Request model for updating a database connection."""

    name: str | None = Field(None, min_length=1, max_length=100)
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    database: str | None = Field(None, min_length=1, max_length=63)
    username: str | None = Field(None, min_length=1, max_length=63)
    password: str | None = Field(None, min_length=1)
    ssl_mode: str | None = Field(None)
    region: str | None = Field(None, max_length=50)
    cloud_provider: str | None = Field(None, max_length=50)
    is_active: bool | None = None


def get_db_manager() -> DatabaseManager:
    """Get the database manager instance."""
    return DatabaseManager()


@router.get("/connections")
async def list_connections(request: Request):
    """List all database connections."""
    db_manager = get_db_manager()
    connections = db_manager.get_all_connections()

    # Convert to dict for template rendering, exclude passwords
    connections_data = []
    for conn in connections:
        connections_data.append({
            "id": conn.id,
            "name": conn.name,
            "host": conn.host,
            "port": conn.port,
            "database": conn.database,
            "username": conn.username,
            "ssl_mode": conn.ssl_mode,
            "region": conn.region,
            "cloud_provider": conn.cloud_provider,
            "is_active": conn.is_active,
            "created_at": conn.created_at,
        })

    return templates.TemplateResponse(
        "partials/database_connections.html",
        {"request": request, "connections": connections_data},
    )


@router.post("/connections")
async def create_connection(request: Request, conn_data: DatabaseCreateRequest):
    """Create a new database connection."""
    db_manager = get_db_manager()

    # Generate unique ID
    conn_id = db_manager.generate_connection_id()

    # Create database connection
    connection = DatabaseConnection(
        id=conn_id,
        name=conn_data.name,
        host=conn_data.host,
        port=conn_data.port,
        database=conn_data.database,
        username=conn_data.username,
        password=conn_data.password,
        ssl_mode=conn_data.ssl_mode,
        region=conn_data.region,
        cloud_provider=conn_data.cloud_provider,
    )

    # Save connection
    success = db_manager.save_connection(connection)

    if not success:
        # Return error HTML
        return templates.TemplateResponse(
            "partials/connection_result.html",
            {"request": request, "result": {"success": False, "error": "Failed to save database connection"}},
            {"HX-Trigger": "connection-error"}
        )

    # Test connection
    test_result = db_manager.test_connection(connection)

    if not test_result.get("success", False):
        # Return test failure HTML but still refresh the list
        return templates.TemplateResponse(
            "partials/connection_result.html",
            {"request": request, "result": test_result},
            {
                "HX-Trigger": "connection-test-failed",
                "HX-Trigger-After-Swap": "htmx.trigger('#database-connections-container', 'load'); document.getElementById('connection-form-container').style.display='none';"
            }
        )

    # Return success HTML
    response = templates.TemplateResponse(
        "partials/connection_result.html",
        {"request": request, "result": test_result},
        {
            "HX-Trigger": "connection-created",
            "HX-Trigger-After-Swap": "htmx.trigger('#database-connections-container', 'load'); document.getElementById('connection-form-container').style.display='none';"
        }
    )

    return response


@router.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """Test a database connection."""
    db_manager = get_db_manager()
    connection = db_manager.get_connection(connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")

    result = db_manager.test_connection(connection)

    return JSONResponse(content=result)


@router.put("/connections/{connection_id}")
async def update_connection(connection_id: str, conn_data: DatabaseUpdateRequest):
    """Update a database connection."""
    db_manager = get_db_manager()
    connection = db_manager.get_connection(connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")

    # Update only provided fields
    update_data = conn_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(connection, field):
            setattr(connection, field, value)

    # Save updated connection
    success = db_manager.save_connection(connection)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update database connection")

    return JSONResponse(
        content={
            "success": True,
            "message": "Database connection updated successfully",
            "connection": {
                "id": connection.id,
                "name": connection.name,
                "host": connection.host,
                "port": connection.port,
                "database": connection.database,
                "username": connection.username,
                "ssl_mode": connection.ssl_mode,
                "region": connection.region,
                "cloud_provider": connection.cloud_provider,
                "is_active": connection.is_active,
            },
        }
    )


@router.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """Delete a database connection."""
    db_manager = get_db_manager()
    connection = db_manager.get_connection(connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")

    success = db_manager.delete_connection(connection_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete database connection")

    return JSONResponse(
        content={
            "success": True,
            "message": "Database connection deleted successfully",
        }
    )


@router.get("/connections/form")
async def get_connection_form(request: Request):
    """Get the database connection form."""
    return templates.TemplateResponse(
        "partials/connection_form.html",
        {"request": request},
    )


@router.get("/connections/{connection_id}")
async def get_connection_details(request: Request, connection_id: str):
    """Get details of a specific database connection."""
    db_manager = get_db_manager()
    connection = db_manager.get_connection(connection_id)

    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")

    connection_data = {
        "id": connection.id,
        "name": connection.name,
        "host": connection.host,
        "port": connection.port,
        "database": connection.database,
        "username": connection.username,
        "ssl_mode": connection.ssl_mode,
        "region": connection.region,
        "cloud_provider": connection.cloud_provider,
        "is_active": connection.is_active,
        "created_at": connection.created_at,
    }

    return templates.TemplateResponse(
        "partials/connection_details.html",
        {"request": request, "connection": connection_data},
    )
