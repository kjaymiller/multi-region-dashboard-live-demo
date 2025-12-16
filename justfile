# Multi-Region PostgreSQL Testing Dashboard - Justfile

# List available commands
default:
    @just --list

# Install dependencies from pyproject.toml
install:
    uv sync

# Install with dev dependencies
install-dev:
    uv sync --extra dev

# Run the development server
dev:
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run the production server
serve:
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run with custom host and port
run host="0.0.0.0" port="8000":
    uv run uvicorn app.main:app --reload --host {{host}} --port {{port}}

# Check for missing environment variables
check-env:
    @echo "Checking environment configuration..."
    @test -f .env || (echo "❌ .env file not found! Copy .env.example to .env" && exit 1)
    @echo "✓ .env file exists"

# Setup environment file from example
setup-env:
    @test -f .env && echo ".env already exists" || cp .env.example .env
    @echo "✓ Environment file ready. Please update .env with your credentials."

# Clean Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name "*.coverage" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Format code with black
format:
    uv run black app/

# Lint code with ruff
lint:
    uv run ruff check app/

# Type check with mypy
typecheck:
    uv run mypy app/

# Run all checks (lint + typecheck)
check: lint typecheck

# Show application info
info:
    @echo "Multi-Region PostgreSQL Testing Dashboard"
    @echo "FastAPI application for testing PostgreSQL connectivity"
    @echo ""
    @echo "Python version:"
    @uv run python --version
    @echo ""
    @echo "UV version:"
    @uv --version
    @echo ""
    @echo "Installed packages:"
    @uv pip list | grep -E "(fastapi|uvicorn|asyncpg|jinja2|python-dotenv)"

# Freeze current dependencies
freeze:
    uv pip freeze > requirements.txt

# Add a new dependency
add *packages:
    uv add {{packages}}

# Add a dev dependency
add-dev *packages:
    uv add --dev {{packages}}

# Full setup: install deps and setup env
setup: install-dev setup-env
    @echo ""
    @echo "✓ Setup complete!"
    @echo "  1. Update .env with your credentials"
    @echo "  2. Run the app: just dev"

# Database migration commands
migrate:
    uv run alembic upgrade head

migrate-create:
    uv run alembic revision --autogenerate -m "$(message)"

migrate-downgrade:
    uv run alembic downgrade -1

migrate-current:
    uv run alembic current

migrate-history:
    uv run alembic history

migrate-reset:
    uv run alembic downgrade base && uv run alembic upgrade head

# Restart development server (useful with tmux/screen)
restart:
    pkill -f "uvicorn app.main:app" || true
    sleep 1
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
