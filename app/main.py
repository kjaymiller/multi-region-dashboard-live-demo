"""FastAPI application and lifespan management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.feature_flags import init_launchdarkly, close_launchdarkly
from app.routers import pages, api


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    init_launchdarkly()
    yield
    # Shutdown
    close_launchdarkly()


app = FastAPI(
    title="Multi-Region PostgreSQL Testing Dashboard",
    description="Interactive dashboard for testing PostgreSQL connectivity across multiple Aiven regions",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(pages.router)
app.include_router(api.router, prefix="/api")

# Create templates instance for use in routers
templates = Jinja2Templates(directory="app/templates")
