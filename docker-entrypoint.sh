#!/bin/bash
set -e

echo "Checking for pending alembic migrations..."

# Check if there are pending migrations
if uv run alembic current 2>&1 | grep -q "No revision"; then
    echo "Database not initialized. Running migrations..."
    uv run alembic upgrade head
elif ! uv run alembic current 2>&1 | grep -q "(head)"; then
    echo "Pending migrations detected. Upgrading to head..."
    uv run alembic upgrade head
else
    echo "Database is up to date."
fi

echo "Starting application..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
